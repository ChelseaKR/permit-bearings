"""Excerpt survival: does a rule's quoted text outlive a change to its source.

The contract under test is narrow on purpose. A changed source stales every
dependent rule, and nothing here alters that. What this adds is the ordering
question — *which* of the stale rules lost the words it quotes — and, more
importantly, the refusal to answer it when the document was never read.

The two fixtures below are the ones the feature was specified against: a
footer edit that moves the hash but leaves every quoted passage intact, and a
section rewrite that removes exactly one.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from permit_pathways.excerpt_survival import (
    counts,
    survival_for_source,
    text_from_bytes,
)
from permit_pathways.harness.watch import check_sources
from permit_pathways.screening import load_rules
from permit_pathways.source_state import load_source_state_snapshot

SOURCE_ID = "example-handout-2026"
SOURCE_URL = "https://example.gov/handout.html"

HEIGHT_EXCERPT = "An accessory dwelling unit may not exceed sixteen feet in height."
SETBACK_EXCERPT = "Side and rear setbacks shall be four feet."

BEFORE = f"""<html><body>
<h1>Accessory Dwelling Units</h1>
<p>{HEIGHT_EXCERPT}</p>
<p>{SETBACK_EXCERPT}</p>
<footer>Page last reviewed January 2026.</footer>
</body></html>"""

# A footer edit: the bytes move, every quoted passage is untouched.
FOOTER_CHANGED = BEFORE.replace(
    "Page last reviewed January 2026.", "Page last reviewed August 2026."
)

# A section rewrite: the height sentence is replaced, the setback one is not.
SECTION_REWRITTEN = BEFORE.replace(
    HEIGHT_EXCERPT,
    "An accessory dwelling unit may not exceed eighteen feet in height.",
)


def _rule(rule_id: str, excerpt: str | None) -> dict:
    citation: dict[str, object] = {
        "source": "Example handout",
        "url": SOURCE_URL,
        "verified_on": "2026-07-28",
    }
    if excerpt is not None:
        citation["excerpt"] = excerpt
    return {
        "rule_id": rule_id,
        "pathway": "Test pathway",
        "route_class": "ministerial",
        "jurisdiction_scope": "statewide",
        "criteria": [{"field": "project_type", "op": "eq", "value": "adu"}],
        "citation": citation,
        "source_dependencies": [SOURCE_ID],
        "display_group": "route",
        "required_documents": ["Application"],
        "notes": "Synthetic rule for excerpt-survival tests.",
    }


def _rules(tmp_path: Path, records: list[dict] | None = None) -> Path:
    path = tmp_path / "rules.json"
    path.write_text(
        json.dumps(
            records
            if records is not None
            else [
                _rule("height-rule", HEIGHT_EXCERPT),
                _rule("setback-rule", SETBACK_EXCERPT),
            ]
        ),
        encoding="utf-8",
    )
    return path


def _sources(tmp_path: Path, recorded: str) -> Path:
    # The retained copy the recorded digest was taken from. It is what makes
    # `excerpt_lost` mean "this was here and is not any more".
    copy = tmp_path / "corpus" / "example" / "handout.html"
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.write_text(recorded, encoding="utf-8")
    path = tmp_path / "sources.json"
    path.write_text(
        json.dumps(
            {
                SOURCE_URL: {
                    "source_id": SOURCE_ID,
                    "label": "Example handout",
                    "local_copy": "corpus/example/handout.html",
                    "sha256": hashlib.sha256(recorded.encode("utf-8")).hexdigest(),
                    "fetched_on": "2026-07-28",
                    "watch": True,
                }
            }
        ),
        encoding="utf-8",
    )
    return path


class _Response:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.status = 200

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def _serve(monkeypatch, payload: bytes) -> None:
    def fake_urlopen(request, timeout):
        assert timeout > 0
        return _Response(payload)

    monkeypatch.setattr(
        "permit_pathways.harness.watch.urllib.request.urlopen", fake_urlopen
    )
    monkeypatch.setattr("permit_pathways.harness.watch.FETCH_BACKOFF_SECONDS", 0.0)


def _statuses(survival) -> dict[str, str]:
    return {item.rule_id: item.status for item in survival}


# --------------------------------------------------------------------------
# The two specified fixtures
# --------------------------------------------------------------------------


def test_a_footer_edit_moves_the_hash_and_leaves_every_excerpt_standing(
    tmp_path, monkeypatch
):
    rules_path = _rules(tmp_path)
    sources_path = _sources(tmp_path, BEFORE)
    _serve(monkeypatch, FOOTER_CHANGED.encode("utf-8"))

    result = check_sources(
        sources_path,
        backoff_seconds=0.0,
        rules=load_rules(rules_path),
        repository_root=tmp_path,
    )

    # The source really did change: survival is an ordering aid on top of a
    # stale set, never a reason to shrink it.
    assert result.changed == [SOURCE_ID]
    assert _statuses(result.excerpt_survival[SOURCE_ID]) == {
        "height-rule": "excerpt_survives",
        "setback-rule": "excerpt_survives",
    }
    assert counts(result.excerpt_survival[SOURCE_ID]) == {
        "excerpt_survives": 2,
        "excerpt_lost": 0,
        "not_checkable": 0,
    }


def test_a_section_rewrite_loses_exactly_the_rule_that_quoted_it(tmp_path, monkeypatch):
    rules_path = _rules(tmp_path)
    sources_path = _sources(tmp_path, BEFORE)
    _serve(monkeypatch, SECTION_REWRITTEN.encode("utf-8"))

    result = check_sources(
        sources_path,
        backoff_seconds=0.0,
        rules=load_rules(rules_path),
        repository_root=tmp_path,
    )

    assert result.changed == [SOURCE_ID]
    assert _statuses(result.excerpt_survival[SOURCE_ID]) == {
        "height-rule": "excerpt_lost",
        "setback-rule": "excerpt_survives",
    }


# --------------------------------------------------------------------------
# What must never be answered
# --------------------------------------------------------------------------


def test_an_unverifiable_source_reports_not_checkable_and_never_lost(
    tmp_path, monkeypatch
):
    """A fetch that failed is not evidence the words are gone.

    `excerpt_lost` on a document nobody read would be the project's dominant
    defect in miniature: an absence rendered as a finding.
    """

    rules_path = _rules(tmp_path)
    sources_path = _sources(tmp_path, BEFORE)

    def fake_urlopen(request, timeout):
        raise OSError("offline")

    monkeypatch.setattr(
        "permit_pathways.harness.watch.urllib.request.urlopen", fake_urlopen
    )
    monkeypatch.setattr("permit_pathways.harness.watch.FETCH_BACKOFF_SECONDS", 0.0)

    result = check_sources(
        sources_path,
        backoff_seconds=0.0,
        rules=load_rules(rules_path),
        repository_root=tmp_path,
    )

    assert result.changed == []
    assert set(result.unverifiable) == {SOURCE_ID}
    # Reported per rule, and reported as the one thing it can be.
    assert _statuses(result.excerpt_survival[SOURCE_ID]) == {
        "height-rule": "not_checkable",
        "setback-rule": "not_checkable",
    }
    assert all(
        "could not be read" in (item.reason or "")
        for item in result.excerpt_survival[SOURCE_ID]
    )
    # And never the other two, whatever the rules quote.
    assert not any(
        item.status in ("excerpt_survives", "excerpt_lost")
        for item in result.excerpt_survival[SOURCE_ID]
    )


def test_an_unreadable_changed_document_is_not_checkable_with_a_reason(tmp_path):
    rules = load_rules(_rules(tmp_path))
    text, reason = text_from_bytes(b"\x00\x01\x02", suffix=".bin")
    assert text is None
    assert reason is not None

    survival = survival_for_source(
        SOURCE_ID,
        SOURCE_URL,
        rules,
        new_text=text,
        previous_text=BEFORE,
        not_checkable_reason=reason,
    )

    assert _statuses(survival) == {
        "height-rule": "not_checkable",
        "setback-rule": "not_checkable",
    }
    assert all(item.reason == reason for item in survival)


def test_a_rule_that_quotes_nothing_is_not_checkable_rather_than_lost():
    """`Citation.excerpt` is optional in the type, required by the loader.

    No committed rule can reach this branch, so it is held here against a
    directly built `Rule`. The point is the direction of the default: a rule
    with nothing to look for is `not_checkable`, never `excerpt_lost`.
    """

    from permit_pathways.screening import Citation, Rule

    rule = Rule(
        rule_id="quoteless-rule",
        pathway="Test pathway",
        route_class="ministerial",
        jurisdiction_scope="statewide",
        criteria=[{"field": "project_type", "op": "eq", "value": "adu"}],
        citation=Citation(source="Example handout", url=SOURCE_URL, excerpt=None),
        source_dependencies=[SOURCE_ID],
        display_group="route",
    )

    survival = survival_for_source(
        SOURCE_ID, SOURCE_URL, [rule], new_text=FOOTER_CHANGED, previous_text=BEFORE
    )

    assert _statuses(survival) == {"quoteless-rule": "not_checkable"}
    assert survival[0].reason is not None


def test_survival_is_reported_only_for_rules_that_depend_on_the_source(tmp_path):
    other = _rule("other-rule", HEIGHT_EXCERPT)
    other["source_dependencies"] = ["some-other-source"]
    rules = load_rules(_rules(tmp_path, [_rule("height-rule", HEIGHT_EXCERPT), other]))

    survival = survival_for_source(
        SOURCE_ID, SOURCE_URL, rules, new_text=FOOTER_CHANGED, previous_text=BEFORE
    )

    assert [item.rule_id for item in survival] == ["height-rule"]


def test_no_rules_supplied_means_no_survival_claim(tmp_path, monkeypatch):
    """The watch must not invent an answer it was never asked for."""

    sources_path = _sources(tmp_path, BEFORE)
    _serve(monkeypatch, SECTION_REWRITTEN.encode("utf-8"))

    result = check_sources(sources_path, backoff_seconds=0.0)

    assert result.changed == [SOURCE_ID]
    assert result.excerpt_survival == {}


# --------------------------------------------------------------------------
# The receipt loader
# --------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources.json"
RULES = ROOT / "data" / "rules"
GOLDEN = ROOT / "data" / "golden" / "example.json"
CURRENT = ROOT / "data" / "source-status" / "current.json"


def _committed_receipt() -> dict:
    return json.loads(CURRENT.read_text(encoding="utf-8"))


def _observation(payload: dict, source_id: str) -> dict:
    return next(
        item for item in payload["observations"] if item["source_id"] == source_id
    )


def _load(tmp_path: Path, payload: dict):
    path = tmp_path / "current.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return load_source_state_snapshot(path, SOURCES, RULES, GOLDEN)


def test_the_committed_receipt_still_loads_and_claims_no_survival(tmp_path):
    # The field is additive: a receipt written before it existed stays
    # byte-identical and keeps its fingerprint.
    snapshot = _load(tmp_path, _committed_receipt())
    assert all(item.excerpt_survival is None for item in snapshot.observations)


@pytest.mark.parametrize("verdict", ["excerpt_survives", "excerpt_lost"])
def test_a_receipt_claiming_a_verdict_for_an_unverifiable_source_is_rejected(
    tmp_path, verdict
):
    """The load-bearing refusal.

    `davis-adu-handout-2026` answered 404 in the committed receipt. Any
    verdict about the words inside it asserts a read that never happened.
    """

    payload = _committed_receipt()
    _observation(payload, "davis-adu-handout-2026")["excerpt_survival"] = [
        {"rule_id": "davis-local-adu-process", "status": verdict}
    ]

    with pytest.raises(ValueError, match="can only report not_checkable"):
        _load(tmp_path, payload)


def test_an_unverifiable_source_may_record_that_it_could_not_be_checked(tmp_path):
    """Saying "I could not look" is the honest half, and it is allowed."""

    payload = _committed_receipt()
    _observation(payload, "davis-adu-handout-2026")["excerpt_survival"] = [
        {
            "rule_id": "davis-local-adu-process",
            "status": "not_checkable",
            "reason": "HTTP 404 Not Found",
        }
    ]

    snapshot = _load(tmp_path, payload)
    observation = next(
        item
        for item in snapshot.observations
        if item.source_id == "davis-adu-handout-2026"
    )
    assert observation.excerpt_survival is not None
    assert observation.excerpt_survival[0].status == "not_checkable"


def test_a_receipt_claiming_survival_for_an_unchanged_source_is_rejected(tmp_path):
    payload = _committed_receipt()
    _observation(payload, "ca-gov-66321")["excerpt_survival"] = [
        {"rule_id": "sb9-urban-lot-split", "status": "excerpt_survives"}
    ]

    with pytest.raises(ValueError, match="only a changed or unverifiable"):
        _load(tmp_path, payload)


def _synthetic_receipt(tmp_path: Path, survival: list[dict] | None) -> tuple:
    """A real receipt for a real changed source, written by the real builder.

    Mutating the committed receipt to fake a changed source desynchronizes its
    dependency-impact arrays, and the loader rightly rejects that before it
    ever looks at excerpt survival. Building the snapshot properly keeps the
    entry under test the only thing in question.
    """

    from permit_pathways.harness.watch import WatchResult, normalized_digest
    from permit_pathways.source_state import (
        build_source_state_snapshot,
        encoded_source_state,
    )

    rules_path = _rules(tmp_path)
    sources_path = _sources(tmp_path, BEFORE)
    golden_path = tmp_path / "golden.json"
    golden_path.write_text("[]", encoding="utf-8")

    watch = WatchResult(
        changed=[SOURCE_ID],
        observed_digests={
            SOURCE_ID: normalized_digest(SECTION_REWRITTEN.encode("utf-8"), None)
        },
    )
    snapshot = build_source_state_snapshot(
        watch,
        sources_path,
        rules_path,
        golden_path,
        snapshot_id="source-watch-1-1",
        checked_at="2026-08-31T15:12:05Z",
        receipt_status="proposed",
        method="github_actions_source_currency_watch",
        run_url="https://github.com/ChelseaKR/permit-bearings/actions/runs/1",
        commit_sha="0" * 40,
    )
    payload = json.loads(encoded_source_state(snapshot))
    observation = _observation(payload, SOURCE_ID)
    if survival is None:
        observation.pop("excerpt_survival", None)
    else:
        observation["excerpt_survival"] = survival
    path = tmp_path / "current.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, sources_path, rules_path, golden_path


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ({"rule_id": "a-rule", "status": "invented"}, "invalid status"),
        ({"rule_id": "", "status": "excerpt_survives"}, "invalid rule_id"),
        ({"status": "excerpt_survives"}, "invalid entry"),
        (
            {"rule_id": "a-rule", "status": "not_checkable"},
            "not_checkable needs a reason",
        ),
        (
            {"rule_id": "a-rule", "status": "excerpt_survives", "reason": "because"},
            "only not_checkable carries a reason",
        ),
        (
            {"rule_id": "a-rule", "status": "excerpt_survives", "extra": 1},
            "invalid entry",
        ),
    ],
)
def test_malformed_survival_entries_are_rejected(tmp_path, entry, expected):
    path, sources_path, rules_path, golden_path = _synthetic_receipt(tmp_path, [entry])

    with pytest.raises(ValueError, match=expected):
        load_source_state_snapshot(path, sources_path, rules_path, golden_path)


def test_survival_entries_must_be_sorted_and_unique(tmp_path):
    path, sources_path, rules_path, golden_path = _synthetic_receipt(
        tmp_path,
        [
            {"rule_id": "z-rule", "status": "excerpt_survives"},
            {"rule_id": "a-rule", "status": "excerpt_lost"},
        ],
    )

    with pytest.raises(ValueError, match="expected sorted rules"):
        load_source_state_snapshot(path, sources_path, rules_path, golden_path)


def test_an_empty_survival_list_is_rejected_rather_than_read_as_no_finding(tmp_path):
    path, sources_path, rules_path, golden_path = _synthetic_receipt(tmp_path, [])

    with pytest.raises(ValueError, match="expected a non-empty list"):
        load_source_state_snapshot(path, sources_path, rules_path, golden_path)


def test_a_survival_record_round_trips_through_the_receipt(tmp_path):
    entries = [
        {"rule_id": "a-rule", "status": "excerpt_lost"},
        {"rule_id": "b-rule", "status": "excerpt_survives"},
        {"rule_id": "c-rule", "status": "not_checkable", "reason": "scanned image"},
    ]
    path, sources_path, rules_path, golden_path = _synthetic_receipt(tmp_path, entries)

    snapshot = load_source_state_snapshot(path, sources_path, rules_path, golden_path)
    observation = next(
        item for item in snapshot.observations if item.source_id == SOURCE_ID
    )
    assert observation.excerpt_survival is not None
    assert [item.to_dict() for item in observation.excerpt_survival] == entries


def test_the_builder_records_the_survival_the_watch_computed(tmp_path, monkeypatch):
    """End to end: fetch, classify, check excerpts, write the receipt."""

    from permit_pathways.source_state import (
        build_source_state_snapshot,
        encoded_source_state,
    )

    rules_path = _rules(tmp_path)
    sources_path = _sources(tmp_path, BEFORE)
    golden_path = tmp_path / "golden.json"
    golden_path.write_text("[]", encoding="utf-8")
    _serve(monkeypatch, SECTION_REWRITTEN.encode("utf-8"))

    watch = check_sources(
        sources_path,
        backoff_seconds=0.0,
        rules=load_rules(rules_path),
        repository_root=tmp_path,
    )
    snapshot = build_source_state_snapshot(
        watch,
        sources_path,
        rules_path,
        golden_path,
        snapshot_id="source-watch-2-1",
        checked_at="2026-08-31T15:12:05Z",
        receipt_status="proposed",
        method="github_actions_source_currency_watch",
        run_url="https://github.com/ChelseaKR/permit-bearings/actions/runs/2",
        commit_sha="0" * 40,
    )

    payload = json.loads(encoded_source_state(snapshot))
    assert _observation(payload, SOURCE_ID)["excerpt_survival"] == [
        {"rule_id": "height-rule", "status": "excerpt_lost"},
        {"rule_id": "setback-rule", "status": "excerpt_survives"},
    ]
    # The receipt it just wrote is one the loader accepts.
    path = tmp_path / "written.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    load_source_state_snapshot(path, sources_path, rules_path, golden_path)


# --------------------------------------------------------------------------
# The committed corpus. Both of these caught a real bug in this feature.
# --------------------------------------------------------------------------


def _committed_survival():
    """Every watched source held against its own retained copy, unchanged."""

    from permit_pathways.harness.watch import load_sources

    rules = load_rules(RULES)
    results = {}
    for source_id, source in sorted(load_sources(SOURCES).items()):
        if not source.watch or not source.local_copy:
            continue
        copy = ROOT / source.local_copy
        if not copy.is_file():
            continue
        text, reason = text_from_bytes(copy.read_bytes(), suffix=copy.suffix)
        results[source_id] = survival_for_source(
            source_id,
            source.url,
            rules,
            new_text=text,
            previous_text=text,
            not_checkable_reason=reason,
        )
    return results


def test_no_committed_rule_is_reported_lost_against_an_unchanged_document():
    """The baseline invariant: a document that did not change loses nothing.

    This is the test that caught the feature's two real defects.

    1. Holding a rule's excerpt against a source it merely *depends on*
       reported thirteen HCD Handbook dependants as having lost text that was
       never in that PDF — they quote statutes.
    2. This project's excerpts are curated citations, not raw quotations:
       several carry editorial brackets condensing a list, so they do not
       occur verbatim even now.

    Together they reported 36 losses across this corpus with nothing changed.
    That is what the first real source change would have printed: a page of
    findings nobody could act on, which is worse than no signal at all.
    """

    lost = {
        source_id: [item.rule_id for item in survival if item.status == "excerpt_lost"]
        for source_id, survival in _committed_survival().items()
    }
    assert {k: v for k, v in lost.items() if v} == {}


def test_the_committed_corpus_can_actually_track_something():
    """A check that can never fire is not a check.

    The complement of the invariant above: `not_checkable` everywhere would
    also pass it, so this pins that real excerpts really are tracked.
    """

    survives = sum(
        1
        for survival in _committed_survival().values()
        for item in survival
        if item.status == "excerpt_survives"
    )
    assert survives >= 7


def test_depending_on_a_source_is_not_quoting_it():
    """The HCD Handbook is the case that makes the distinction load-bearing."""

    survival = _committed_survival()["hcd-adu-handbook-2026-03"]
    by_status = {}
    for item in survival:
        by_status.setdefault(item.status, []).append(item.rule_id)

    # Exactly the two rules whose own citation URL is the Handbook.
    assert sorted(by_status.get("excerpt_survives", [])) == [
        "sb9-adu-interaction",
        "sb9-lot-split-adu-interaction",
    ]
    # The other thirteen depend on it and quote a statute instead.
    assert len(by_status.get("not_checkable", [])) == 13
    assert "excerpt_lost" not in by_status
