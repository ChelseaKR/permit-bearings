from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import urllib.error
from datetime import date, timedelta
from pathlib import Path

import pytest
from scripts.build_demo_bundle import (
    aggregate_rule_records,
    discover_rule_files,
    rule_manifest,
)

from permit_pathways.explanations import (
    LocalizedExplanation,
    citation_fingerprint,
    load_explanations,
    localized_content_fingerprint,
    rule_fingerprint,
)
from permit_pathways.harness.__main__ import main as harness_main
from permit_pathways.harness.runner import verify_rules
from permit_pathways.harness.watch import check_sources, load_sources, normalized_digest
from permit_pathways.screening import load_rules, screen

AS_OF = date(2026, 7, 28)
SOURCE_REGISTRY_AS_OF = date(2026, 8, 11)
ROOT = Path(__file__).resolve().parents[1]


def _rule_record(
    *,
    rule_id: str = "test-rule",
    criterion: dict | None = None,
    verified_on: str | None = "2026-07-28",
    source_id: str = "ca-gov-66321",
    source_url: str = "https://example.gov/source",
) -> dict:
    return {
        "rule_id": rule_id,
        "pathway": "Test pathway",
        "route_class": "ministerial",
        "jurisdiction_scope": "statewide",
        "criteria": [
            criterion or {"field": "project_type", "op": "eq", "value": "adu"}
        ],
        "citation": {
            "source": "Official test source",
            "url": source_url,
            "excerpt": "Supporting source passage.",
            "verified_on": verified_on,
        },
        "source_dependencies": [source_id],
        "display_group": "route",
        "required_documents": ["Application"],
        "notes": "Synthetic rule for validation tests.",
    }


def _write_rules(tmp_path: Path, records: list[dict]) -> Path:
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def _source_meta(
    source_id: str,
    content: bytes | None,
    *,
    watch: bool = True,
) -> dict:
    return {
        "source_id": source_id,
        "label": source_id,
        "local_copy": None,
        "sha256": (
            hashlib.sha256(content).hexdigest() if content is not None else None
        ),
        "fetched_on": "2026-07-28" if content is not None else None,
        "watch": watch,
    }


def test_rule_loader_rejects_unsupported_shapes_and_future_dates(tmp_path):
    unsupported = _rule_record(
        criterion={"field": "height", "op": "contains", "value": 16}
    )
    with pytest.raises(ValueError, match="unsupported operator"):
        load_rules(_write_rules(tmp_path, [unsupported]), today=AS_OF)

    future = _rule_record(verified_on="2026-07-29")
    with pytest.raises(ValueError, match="future dates"):
        load_rules(_write_rules(tmp_path, [future]), today=AS_OF)

    extra = _rule_record()
    extra["criterai"] = []
    with pytest.raises(ValueError, match="unknown fields"):
        load_rules(_write_rules(tmp_path, [extra]), today=AS_OF)


@pytest.mark.parametrize(
    "criterion",
    [
        {"field": "height", "op": "eq", "value": 16.0},
        {"field": "height", "op": "in", "value": [16.0]},
        {"field": "height", "op": "lte", "value": 16.0},
        {"field": "height", "op": "gte", "value": 16.0},
    ],
)
def test_rule_loader_rejects_float_criteria_for_cross_runtime_parity(
    tmp_path, criterion
):
    with pytest.raises(ValueError, match="integer"):
        load_rules(
            _write_rules(tmp_path, [_rule_record(criterion=criterion)]),
            today=AS_OF,
        )


@pytest.mark.parametrize(
    "value",
    [2**53, -(2**53)],
)
def test_rule_loader_rejects_integers_outside_javascript_safe_range(tmp_path, value):
    criterion = {"field": "height", "op": "lte", "value": value}
    with pytest.raises(ValueError, match="safe-integer"):
        load_rules(
            _write_rules(tmp_path, [_rule_record(criterion=criterion)]),
            today=AS_OF,
        )


def test_safe_integer_criterion_is_accepted_with_integer_fingerprint_form(
    tmp_path,
):
    criterion = {"field": "height", "op": "lte", "value": 16}
    rule = load_rules(
        _write_rules(tmp_path, [_rule_record(criterion=criterion)]),
        today=AS_OF,
    )[0]
    canonical_criteria = json.dumps(
        rule.criteria, separators=(",", ":"), sort_keys=True
    )
    assert '"value":16' in canonical_criteria
    assert '"value":16.0' not in canonical_criteria
    assert rule_fingerprint(rule).startswith("sha256:")
    assert rule.matches({"height": 16.0})


def test_rule_loader_requires_document_field_and_nonblank_notes(tmp_path):
    missing_documents = _rule_record()
    del missing_documents["required_documents"]
    with pytest.raises(ValueError, match="required_documents"):
        load_rules(_write_rules(tmp_path, [missing_documents]), today=AS_OF)

    blank_notes = _rule_record()
    blank_notes["notes"] = " "
    with pytest.raises(ValueError, match="non-blank"):
        load_rules(_write_rules(tmp_path, [blank_notes]), today=AS_OF)


def test_omitted_calendar_dates_use_injectable_utc_default(tmp_path, monkeypatch):
    monkeypatch.setattr("permit_pathways.dates.utc_today", lambda: AS_OF)
    future = _rule_record(verified_on="2026-07-29")
    with pytest.raises(ValueError, match="future dates"):
        load_rules(_write_rules(tmp_path, [future]))

    current_path = _write_rules(tmp_path, [_rule_record()])
    golden_path = tmp_path / "golden.json"
    golden_path.write_text("[]", encoding="utf-8")
    report = verify_rules(current_path, golden_path)
    assert report.checked_on == AS_OF.isoformat()


def test_matching_is_type_strict_and_fails_closed_on_unknown(tmp_path):
    boolean_rule = _rule_record(
        criterion={"field": "confirmed", "op": "eq", "value": True}
    )
    path = _write_rules(tmp_path, [boolean_rule])
    rules = load_rules(path, today=AS_OF)
    assert screen({"confirmed": True}, rules)
    assert screen({"confirmed": 1}, rules) == []
    assert screen({"confirmed": "unknown"}, rules) == []
    assert screen({}, rules) == []


def test_staleness_uses_one_calendar_day_contract(tmp_path):
    boundary = AS_OF - timedelta(days=180)
    path = _write_rules(
        tmp_path,
        [_rule_record(verified_on=boundary.isoformat())],
    )
    rule = load_rules(path, today=AS_OF)[0]
    assert not rule.citation.is_stale(180, AS_OF)
    assert rule.citation.is_stale(179, AS_OF)


def test_changed_source_ids_use_exact_dependency_edges(tmp_path):
    rules_path = _write_rules(tmp_path, [_rule_record()])
    golden_path = tmp_path / "golden.json"
    golden_path.write_text("[]", encoding="utf-8")

    substring = verify_rules(
        rules_path,
        golden_path,
        today=AS_OF,
        changed_source_ids=["66321"],
    )
    assert substring.stale == []
    exact = verify_rules(
        rules_path,
        golden_path,
        today=AS_OF,
        changed_source_ids=["ca-gov-66321"],
    )
    assert exact.stale == ["test-rule"]


class _Response:
    """Minimal stand-in for the object urlopen yields."""

    def __init__(self, content: bytes, status: int = 200):
        self.content = content
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.content


def _install_urlopen(monkeypatch, handler, *, requested: list[str] | None = None):
    """Route fetches to ``handler`` and remove retry backoff from tests."""

    def fake_urlopen(request, timeout):
        assert timeout > 0
        if requested is not None:
            requested.append(request.full_url)
        return handler(request.full_url)

    monkeypatch.setattr(
        "permit_pathways.harness.watch.urllib.request.urlopen",
        fake_urlopen,
    )
    monkeypatch.setattr(
        "permit_pathways.harness.watch.FETCH_BACKOFF_SECONDS",
        0.0,
    )


def _watch_argv(rules_path, golden_path, sources_path) -> list[str]:
    return [
        "permit_pathways.harness",
        "--rules",
        str(rules_path),
        "--golden",
        str(golden_path),
        "--sources",
        str(sources_path),
        "--as-of",
        AS_OF.isoformat(),
        "--fetch",
    ]


def test_watcher_reports_stable_ids_and_skips_non_watched_sources(
    tmp_path,
    monkeypatch,
):
    payload = {
        "https://example.gov/unchanged": _source_meta("source-unchanged", b"same"),
        "https://example.gov/changed": _source_meta("source-changed", b"before"),
        "https://example.gov/error": _source_meta("source-error", b"before"),
        "https://example.gov/manual": _source_meta("source-manual", None, watch=False),
    }
    sources_path = tmp_path / "sources.json"
    sources_path.write_text(json.dumps(payload), encoding="utf-8")
    requested: list[str] = []

    def handler(url):
        if url.endswith("/error"):
            raise OSError("offline")
        if url.endswith("/unchanged"):
            return _Response(b"same")
        return _Response(b"after")

    _install_urlopen(monkeypatch, handler, requested=requested)
    result = check_sources(sources_path, backoff_seconds=0.0)
    # A fetched, matching hash is the only thing that counts as unchanged;
    # a fetched, differing hash is the only thing that counts as changed.
    assert result.unchanged == ["source-unchanged"]
    assert result.changed == ["source-changed"]
    assert result.observed_digests == {
        "source-changed": normalized_digest(b"after", None),
        "source-unchanged": normalized_digest(b"same", None),
    }
    assert set(result.unverifiable) == {"source-error"}
    assert result.unverifiable["source-error"].reason == "OSError: offline"
    assert not any(url.endswith("/manual") for url in requested)


@pytest.mark.parametrize(
    ("failure", "expected_reason"),
    [
        (OSError("offline"), "OSError: offline"),
        (TimeoutError("timed out"), "timed out"),
        (urllib.error.URLError(TimeoutError("timed out")), "timed out"),
        (
            urllib.error.HTTPError(
                "https://example.gov/blocked", 403, "Forbidden", {}, None
            ),
            "HTTP 403 Forbidden",
        ),
        (
            urllib.error.HTTPError(
                "https://example.gov/blocked", 429, "Too Many Requests", {}, None
            ),
            "HTTP 429 Too Many Requests",
        ),
    ],
    ids=["network-error", "timeout", "wrapped-timeout", "waf-block", "rate-limit"],
)
def test_fetch_failures_are_unverifiable_never_changed(
    tmp_path,
    monkeypatch,
    failure,
    expected_reason,
):
    payload = {
        "https://example.gov/blocked": _source_meta("source-blocked", b"recorded"),
    }
    sources_path = tmp_path / "sources.json"
    sources_path.write_text(json.dumps(payload), encoding="utf-8")

    def handler(_url):
        raise failure

    _install_urlopen(monkeypatch, handler)
    result = check_sources(sources_path, backoff_seconds=0.0)
    assert result.changed == []
    assert result.unchanged == []
    unverifiable = result.unverifiable["source-blocked"]
    assert unverifiable.reason == expected_reason
    # The freshness claim degrades to the last confirmed date rather than
    # flipping to an unsupported "changed".
    assert unverifiable.last_verified_on == "2026-07-28"
    described = result.summary({"source-blocked": "Blocked source"})
    assert "unverifiable" in described
    assert "CHANGED" not in described
    assert "last confirmed 2026-07-28" in described


def test_transient_failure_retries_with_backoff_before_giving_up(
    tmp_path,
    monkeypatch,
):
    payload = {
        "https://example.gov/flaky": _source_meta("source-flaky", b"recorded"),
    }
    sources_path = tmp_path / "sources.json"
    sources_path.write_text(json.dumps(payload), encoding="utf-8")
    attempts = {"count": 0}

    def handler(_url):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise TimeoutError("timed out")
        return _Response(b"recorded")

    delays: list[float] = []
    _install_urlopen(monkeypatch, handler)
    monkeypatch.setattr(
        "permit_pathways.harness.watch.time.sleep",
        lambda seconds: delays.append(seconds),
    )
    result = check_sources(sources_path, backoff_seconds=1.0)
    # A blip on the first two attempts must not be reported at all.
    assert result.unchanged == ["source-flaky"]
    assert result.unverifiable == {}
    assert attempts["count"] == 3
    assert delays == [1.0, 2.0]  # exponential backoff between attempts


def test_a_dead_source_does_not_abort_the_rest_of_the_run(tmp_path, monkeypatch):
    payload = {
        "https://example.gov/dead": _source_meta("source-dead", b"recorded"),
        "https://example.gov/live": _source_meta("source-live", b"recorded"),
        "https://example.gov/moved": _source_meta("source-moved", b"recorded"),
    }
    sources_path = tmp_path / "sources.json"
    sources_path.write_text(json.dumps(payload), encoding="utf-8")

    def handler(url):
        if url.endswith("/dead"):
            raise OSError("connection reset")
        if url.endswith("/moved"):
            return _Response(b"amended")
        return _Response(b"recorded")

    _install_urlopen(monkeypatch, handler)
    result = check_sources(sources_path, backoff_seconds=0.0)
    assert result.unchanged == ["source-live"]
    assert result.changed == ["source-moved"]
    assert set(result.unverifiable) == {"source-dead"}
    assert result.checked == 3


def test_unverifiable_source_does_not_mark_its_dependent_rules_stale(
    tmp_path,
    monkeypatch,
    capsys,
):
    # The exact 08-03 scenario: the statute host blocks the runner, and the
    # rule that cites it must not be reported stale on that account.
    rules_path = _write_rules(
        tmp_path,
        [
            _rule_record(
                source_id="source-blocked",
                source_url="https://example.gov/blocked",
            )
        ],
    )
    golden_path = tmp_path / "golden.json"
    golden_path.write_text("[]", encoding="utf-8")
    sources_payload = {
        "https://example.gov/blocked": _source_meta("source-blocked", b"recorded"),
    }
    sources_path = tmp_path / "sources.json"
    sources_path.write_text(json.dumps(sources_payload), encoding="utf-8")

    def handler(_url):
        raise urllib.error.HTTPError(
            "https://example.gov/blocked", 403, "Forbidden", {}, None
        )

    _install_urlopen(monkeypatch, handler)
    monkeypatch.setattr(sys, "argv", _watch_argv(rules_path, golden_path, sources_path))
    # Exit 2 == "could not check", kept distinct from exit 1 == "review needed".
    assert harness_main() == 2
    printed = capsys.readouterr().out
    assert "rules stale:            0" in printed
    assert "unverifiable:" in printed
    assert "CHANGED" not in printed

    direct = verify_rules(
        rules_path,
        golden_path,
        today=AS_OF,
        changed_source_ids=[],
    )
    assert direct.stale == []
    assert direct.verified == ["test-rule"]


def test_unverifiable_source_exits_two_even_without_a_dependent_rule(
    tmp_path,
    monkeypatch,
):
    rules_path = _write_rules(
        tmp_path,
        [
            _rule_record(
                source_id="source-current",
                source_url="https://example.gov/current",
            )
        ],
    )
    golden_path = tmp_path / "golden.json"
    golden_path.write_text("[]", encoding="utf-8")
    sources_payload = {
        "https://example.gov/current": _source_meta("source-current", b"current"),
        "https://example.gov/unrelated": _source_meta("source-unrelated", b"current"),
    }
    sources_path = tmp_path / "sources.json"
    sources_path.write_text(json.dumps(sources_payload), encoding="utf-8")

    def handler(url):
        if url.endswith("/unrelated"):
            raise OSError("unreachable")
        return _Response(b"current")

    _install_urlopen(monkeypatch, handler)
    monkeypatch.setattr(sys, "argv", _watch_argv(rules_path, golden_path, sources_path))
    assert harness_main() == 2


def test_real_content_change_still_exits_with_the_review_code(
    tmp_path,
    monkeypatch,
    capsys,
):
    rules_path = _write_rules(
        tmp_path,
        [
            _rule_record(
                source_id="source-amended",
                source_url="https://example.gov/amended",
            )
        ],
    )
    golden_path = tmp_path / "golden.json"
    golden_path.write_text("[]", encoding="utf-8")
    sources_payload = {
        "https://example.gov/amended": _source_meta("source-amended", b"recorded"),
    }
    sources_path = tmp_path / "sources.json"
    sources_path.write_text(json.dumps(sources_payload), encoding="utf-8")

    _install_urlopen(monkeypatch, lambda _url: _Response(b"amended text"))
    monkeypatch.setattr(sys, "argv", _watch_argv(rules_path, golden_path, sources_path))
    # A genuine content drift still pages: exit 1, dependent rule stale.
    assert harness_main() == 1
    printed = capsys.readouterr().out
    assert "CHANGED" in printed
    assert "rules stale:            1" in printed


def test_harness_cli_reports_verification_level_coverage_for_a_rule_directory(
    tmp_path,
    monkeypatch,
    capsys,
):
    # The committed rule-verification ledger only covers the real 19 rules
    # in data/rules; --rules can point anywhere a directory of rule JSON
    # lives, including a fixture the ledger was never meant to cover. The
    # coverage line must load tolerantly (require_complete=False,
    # strict=False) and report the synthetic rule as machine_linked by
    # default rather than raise on "missing rule IDs" or an unrecognized
    # entry, since that default is exactly what effective_status uses for
    # any rule absent from the ledger.
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "rules.json").write_text(
        json.dumps([_rule_record()]), encoding="utf-8"
    )
    golden_path = tmp_path / "golden.json"
    golden_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "permit_pathways.harness",
            "--rules",
            str(rules_dir),
            "--golden",
            str(golden_path),
            "--as-of",
            AS_OF.isoformat(),
        ],
    )
    assert harness_main() == 0
    printed = capsys.readouterr().out
    assert (
        "1 rules; effective verification level: 1 machine_linked, "
        "0 human_reviewed, 0 jurisdiction_approved" in printed
    )


def test_non_2xx_status_without_an_exception_is_unverifiable(
    tmp_path,
    monkeypatch,
):
    # Some handlers hand back an error page instead of raising. An error page
    # hashes differently from the statute, so it must never read as "changed".
    payload = {
        "https://example.gov/interstitial": _source_meta("source-gate", b"recorded"),
    }
    sources_path = tmp_path / "sources.json"
    sources_path.write_text(json.dumps(payload), encoding="utf-8")

    _install_urlopen(
        monkeypatch,
        lambda _url: _Response(b"<html>Access denied</html>", status=403),
    )
    result = check_sources(sources_path, backoff_seconds=0.0)
    assert result.changed == []
    assert result.unverifiable["source-gate"].reason == "HTTP 403"


def test_completed_review_digest_is_bound_to_exact_copy(tmp_path):
    rules_path = _write_rules(tmp_path, [_rule_record()])
    rule = load_rules(rules_path, today=AS_OF)[0]
    english = LocalizedExplanation(
        title="What this means",
        summary="You can use this route if the listed facts are true.",
        next_steps=("Prepare the application.",),
        confirm_with_staff=("Is the current form posted online?",),
    )
    content_digest = localized_content_fingerprint("1.0.0", "en", english)
    entry = {
        "version": "1.0.0",
        "source_rule_id": rule.rule_id,
        "source_verified_on": rule.citation.verified_on,
        "citation_fingerprint": citation_fingerprint(rule),
        "rule_fingerprint": rule_fingerprint(rule),
        "display_group": rule.display_group,
        "drafted_by": "ai_assisted",
        "updated_on": "2026-07-28",
        "review": {
            "status": "human_reviewed",
            "reviewer": "Named reviewer",
            "reviewed_on": "2026-07-28",
            "method": "Compared with the source record",
            "reviewed_version": "1.0.0",
            "content_fingerprint": content_digest,
        },
        "en": {
            "title": english.title,
            "summary": english.summary,
            "next_steps": list(english.next_steps),
            "confirm_with_staff": list(english.confirm_with_staff),
            "highlights": None,
        },
        "es": {
            "title": "Qué significa",
            "summary": "Borrador de traducción.",
            "next_steps": ["Prepare la solicitud."],
            "confirm_with_staff": ["¿Está publicado el formulario actual?"],
            "highlights": None,
            "translation_status": "machine_draft",
            "reviewer": None,
            "reviewed_on": None,
        },
    }
    path = tmp_path / "plain-language.json"
    path.write_text(
        json.dumps({"schema_version": 1, "entries": [entry]}),
        encoding="utf-8",
    )
    assert load_explanations(path, [rule], today=AS_OF)[rule.rule_id]

    changed = copy.deepcopy(entry)
    changed["en"]["summary"] += " Changed after review."
    path.write_text(
        json.dumps({"schema_version": 1, "entries": [changed]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="does not match English copy"):
        load_explanations(path, [rule], today=AS_OF)

    reviewed_translation = copy.deepcopy(entry)
    spanish = LocalizedExplanation(
        title=reviewed_translation["es"]["title"],
        summary=reviewed_translation["es"]["summary"],
        next_steps=tuple(reviewed_translation["es"]["next_steps"]),
        confirm_with_staff=tuple(reviewed_translation["es"]["confirm_with_staff"]),
    )
    reviewed_translation["es"].update(
        {
            "translation_status": "human_reviewed",
            "reviewer": "Named translator",
            "reviewed_on": "2026-07-28",
            "method": "Compared Spanish and English meaning",
            "reviewed_version": "1.0.0",
            "content_fingerprint": localized_content_fingerprint(
                "1.0.0", "es", spanish
            ),
        }
    )
    path.write_text(
        json.dumps({"schema_version": 1, "entries": [reviewed_translation]}),
        encoding="utf-8",
    )
    assert load_explanations(path, [rule], today=AS_OF)[rule.rule_id].es
    reviewed_translation["es"]["summary"] += " Cambió después de la revisión."
    path.write_text(
        json.dumps({"schema_version": 1, "entries": [reviewed_translation]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="does not match translated copy"):
        load_explanations(path, [rule], today=AS_OF)

    future = copy.deepcopy(entry)
    future["updated_on"] = "2026-07-29"
    path.write_text(
        json.dumps({"schema_version": 1, "entries": [future]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="future dates"):
        load_explanations(path, [rule], today=AS_OF)


def test_source_registry_rejects_future_fetch_dates(tmp_path):
    payload = {
        "https://example.gov/source": {
            **_source_meta("source-one", b"content"),
            "fetched_on": "2026-07-29",
        }
    }
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="future dates"):
        load_sources(path, today=AS_OF)


def test_every_canonical_rule_dependency_resolves_to_the_source_registry():
    rules = load_rules(
        ROOT / "data" / "rules",
        today=SOURCE_REGISTRY_AS_OF,
    )
    source_ids = set(
        load_sources(
            ROOT / "data" / "sources.json",
            today=SOURCE_REGISTRY_AS_OF,
        )
    )
    unresolved = {
        rule.rule_id: sorted(set(rule.source_dependencies) - source_ids)
        for rule in rules
        if set(rule.source_dependencies) - source_ids
    }
    assert unresolved == {}


def test_retained_text_corpus_excludes_embedded_google_api_keys():
    google_api_key = re.compile(r"AIza[0-9A-Za-z_-]{35}")
    text_suffixes = {".csv", ".html", ".json", ".md", ".txt"}
    findings = []
    for path in (ROOT / "corpus").rglob("*"):
        if path.is_file() and path.suffix.lower() in text_suffixes:
            content = path.read_text(encoding="utf-8", errors="ignore")
            if google_api_key.search(content):
                findings.append(path.relative_to(ROOT).as_posix())
    assert findings == []


def test_rule_aggregate_and_manifest_discover_every_rule_file(tmp_path):
    rules_dir = tmp_path / "data" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "alpha.json").write_text(
        json.dumps([{"rule_id": "alpha"}]),
        encoding="utf-8",
    )
    (rules_dir / "beta.json").write_text(
        json.dumps([{"rule_id": "beta"}]),
        encoding="utf-8",
    )
    (rules_dir / "index.json").write_text("{}", encoding="utf-8")

    assert [path.name for path in discover_rule_files(tmp_path)] == [
        "alpha.json",
        "beta.json",
    ]
    records, digests = aggregate_rule_records(tmp_path)
    assert [record["rule_id"] for record in records] == ["alpha", "beta"]
    assert set(digests) == {
        "data/rules/alpha.json",
        "data/rules/beta.json",
    }
    assert rule_manifest(tmp_path)["files"] == ["alpha.json", "beta.json"]
