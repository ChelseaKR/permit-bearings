"""A citation whose published address is gone is its own finding.

The watcher already refuses to call an unreachable source "changed". These
tests hold the line one level down: a fetch that got *no answer* and a
fetch whose answer was "no document is published here" are different
findings with different owners, and only the second one means the link this
project prints beside a rule resolves to nothing for a reader.

Nothing here may make a rule stale. That invariant is asserted directly.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.harness.runner import verify_rules
from permit_pathways.harness.watch import (
    FetchFailure,
    SourceRecord,
    UnverifiableSource,
    WatchResult,
    fetch_digest,
    load_sources,
)
from permit_pathways.screening import load_rules, screen
from permit_pathways.source_state import (
    build_source_state_snapshot,
    encoded_source_state,
    load_source_state_snapshot,
    withdrawn_citations,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources.json"
RULES = ROOT / "data" / "rules"
GOLDEN = ROOT / "data" / "golden" / "example.json"
CURRENT = ROOT / "data" / "source-status" / "current.json"
CHECKED_AT = "2026-08-03T17:08:28Z"
COMMIT_SHA = "8d841409dc5fd16fe56b52a8b57c826c07f176a6"
RUN_URL = "https://github.com/ChelseaKR/permit-pathways/actions/runs/30835371749"

# The one rule whose own citation URL is a city handout rather than a
# statute, which is exactly the kind of address that gets reorganised away.
WITHDRAWN_SOURCE_ID = "davis-adu-handout-2026"
WITHDRAWN_RULE_ID = "davis-local-adu-process"


def _record(url: str = "https://example.gov/handout.pdf") -> SourceRecord:
    return SourceRecord(
        source_id="example-source",
        url=url,
        label="Example handout",
        sha256="0" * 64,
        fetched_on="2026-07-30",
        normalize=None,
        local_copy="corpus/example/handout.pdf",
        watch=True,
    )


def _raise(error: BaseException):
    def _opener(*_args: Any, **_kwargs: Any):
        raise error

    return _opener


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://example.gov/handout.pdf", code, "Not Found", {}, None
    )


# --------------------------------------------------------------------------
# The watcher: which failures are answers, and which are silence
# --------------------------------------------------------------------------


@pytest.mark.parametrize("code", [404, 410])
def test_an_answered_absence_is_not_found_and_is_not_retried(monkeypatch, code):
    attempts = {"count": 0}

    def _opener(*_args: Any, **_kwargs: Any):
        attempts["count"] += 1
        raise _http_error(code)

    monkeypatch.setattr("urllib.request.urlopen", _opener)

    with pytest.raises(FetchFailure) as caught:
        fetch_digest(_record(), attempts=3, backoff_seconds=0)

    assert caught.value.kind == "not_found"
    assert caught.value.attempts == 1
    # The server already answered about this address. Asking twice more
    # cannot change the answer and makes a dead link look like a bad line.
    assert attempts["count"] == 1


@pytest.mark.parametrize(
    "error",
    [
        _http_error(403),
        _http_error(429),
        _http_error(500),
        urllib.error.URLError("certificate verify failed"),
        TimeoutError(),
    ],
    ids=["forbidden", "throttled", "server-error", "tls", "timeout"],
)
def test_every_other_failure_stays_transport_and_keeps_its_retries(monkeypatch, error):
    monkeypatch.setattr("urllib.request.urlopen", _raise(error))

    with pytest.raises(FetchFailure) as caught:
        fetch_digest(_record(), attempts=3, backoff_seconds=0)

    assert caught.value.kind == "transport"
    assert caught.value.attempts == 3


def test_a_refusal_is_not_an_absence(monkeypatch):
    """A 403 says the server will not tell us, not that nothing is there."""

    monkeypatch.setattr("urllib.request.urlopen", _raise(_http_error(403)))

    with pytest.raises(FetchFailure) as caught:
        fetch_digest(_record(), attempts=1, backoff_seconds=0)

    assert caught.value.kind != "not_found"


def test_the_two_kinds_do_not_describe_themselves_the_same_way():
    transport = UnverifiableSource(
        source_id="example-source",
        reason="timed out",
        last_verified_on="2026-07-30",
        attempts=3,
        kind="transport",
    )
    answered = UnverifiableSource(
        source_id="example-source",
        reason="HTTP 404 Not Found",
        last_verified_on="2026-07-30",
        attempts=1,
        kind="not_found",
    )

    assert not transport.is_not_found
    assert answered.is_not_found
    assert "could not fetch" in transport.describe()
    assert "no document is" in answered.describe()
    assert "no longer resolves" in answered.describe()
    # Neither may ever imply the law moved.
    assert "changed" not in answered.describe()


def test_the_run_summary_counts_and_labels_the_kinds_separately():
    result = WatchResult(
        unchanged=["kept"],
        unverifiable={
            "silent": UnverifiableSource(
                source_id="silent",
                reason="timed out",
                last_verified_on="2026-07-30",
                attempts=3,
                kind="transport",
            ),
            "gone": UnverifiableSource(
                source_id="gone",
                reason="HTTP 404 Not Found",
                last_verified_on="2026-07-30",
                attempts=1,
                kind="not_found",
            ),
        },
    )

    summary = result.summary({})

    assert result.not_found == ["gone"]
    assert result.unreachable == ["silent"]
    assert '1 got no answer, 1 published address answered "not found"' in summary
    assert "NOT FOUND:    gone" in summary
    assert "unverifiable: silent" in summary


# --------------------------------------------------------------------------
# The receipt: an unverifiable row must say which kind it was
# --------------------------------------------------------------------------


def _unchanged_watch() -> WatchResult:
    sources = load_sources(SOURCES)
    watched = {
        source_id: source for source_id, source in sources.items() if source.watch
    }
    return WatchResult(
        unchanged=sorted(watched),
        observed_digests={
            source_id: source.sha256
            for source_id, source in watched.items()
            if source.sha256 is not None
        },
    )


def _watch_with_failure(kind: str) -> WatchResult:
    watch = _unchanged_watch()
    watch.unchanged.remove(WITHDRAWN_SOURCE_ID)
    watch.observed_digests.pop(WITHDRAWN_SOURCE_ID)
    watch.unverifiable[WITHDRAWN_SOURCE_ID] = UnverifiableSource(
        source_id=WITHDRAWN_SOURCE_ID,
        reason="HTTP 404 Not Found" if kind == "not_found" else "timed out",
        last_verified_on="2026-07-30",
        attempts=1 if kind == "not_found" else 3,
        kind=kind,  # type: ignore[arg-type]
    )
    return watch


def _build(watch: WatchResult):
    return build_source_state_snapshot(
        watch,
        SOURCES,
        RULES,
        GOLDEN,
        snapshot_id="source-watch-test",
        checked_at=CHECKED_AT,
        receipt_status="reviewed",
        method="github_actions_scheduled_watch",
        run_url=RUN_URL,
        commit_sha=COMMIT_SHA,
    )


def _payload(kind: str) -> dict[str, Any]:
    return json.loads(encoded_source_state(_build(_watch_with_failure(kind))))


def _write(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "source-state.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _observation(payload: dict[str, Any]) -> dict[str, Any]:
    return next(
        item
        for item in payload["observations"]
        if item["source_id"] == WITHDRAWN_SOURCE_ID
    )


def test_a_written_receipt_records_the_kind_it_observed():
    payload = _payload("not_found")

    assert _observation(payload)["unverifiable_kind"] == "not_found"
    assert _build(_watch_with_failure("not_found")).not_found_source_ids == (
        WITHDRAWN_SOURCE_ID,
    )
    assert _build(_watch_with_failure("transport")).not_found_source_ids == ()


def test_a_fetched_observation_never_carries_a_kind():
    payload = json.loads(encoded_source_state(_build(_unchanged_watch())))

    assert all(
        "unverifiable_kind" not in observation
        for observation in payload["observations"]
    )


def test_the_committed_receipt_round_trips_byte_for_byte():
    """The new field must not rewrite a receipt that predates it."""

    snapshot = load_source_state_snapshot(CURRENT, SOURCES, RULES, GOLDEN)

    assert encoded_source_state(snapshot) == CURRENT.read_text(encoding="utf-8")


def test_an_unverifiable_row_without_a_kind_is_refused(tmp_path):
    payload = _payload("not_found")
    del _observation(payload)["unverifiable_kind"]

    with pytest.raises(ValueError, match="valid kind"):
        load_source_state_snapshot(_write(tmp_path, payload), SOURCES, RULES, GOLDEN)


def test_an_unrecognised_kind_is_refused(tmp_path):
    payload = _payload("not_found")
    _observation(payload)["unverifiable_kind"] = "probably_fine"

    with pytest.raises(ValueError, match="valid kind"):
        load_source_state_snapshot(_write(tmp_path, payload), SOURCES, RULES, GOLDEN)


def test_a_kind_on_a_fetched_row_is_refused(tmp_path):
    payload = json.loads(encoded_source_state(_build(_unchanged_watch())))
    payload["observations"][0]["unverifiable_kind"] = "not_found"

    with pytest.raises(ValueError, match="cannot have a kind"):
        load_source_state_snapshot(_write(tmp_path, payload), SOURCES, RULES, GOLDEN)


def test_a_valid_not_found_receipt_loads(tmp_path):
    snapshot = load_source_state_snapshot(
        _write(tmp_path, _payload("not_found")), SOURCES, RULES, GOLDEN
    )

    assert snapshot.not_found_source_ids == (WITHDRAWN_SOURCE_ID,)
    assert snapshot.unverifiable_source_ids == (WITHDRAWN_SOURCE_ID,)
    assert snapshot.changed_source_ids == ()


# --------------------------------------------------------------------------
# The derivation, and the line it must not cross
# --------------------------------------------------------------------------


def test_a_withdrawn_address_names_the_rule_that_prints_that_link():
    snapshot = _build(_watch_with_failure("not_found"))

    findings = withdrawn_citations(snapshot, SOURCES, RULES)

    assert [item.rule_id for item in findings] == [WITHDRAWN_RULE_ID]
    assert findings[0].source_id == WITHDRAWN_SOURCE_ID
    assert findings[0].last_verified_on == "2026-07-30"
    assert "does not resolve" in findings[0].describe()


def test_a_source_that_merely_went_quiet_names_no_rule():
    snapshot = _build(_watch_with_failure("transport"))

    assert withdrawn_citations(snapshot, SOURCES, RULES) == ()


def test_a_dependency_that_is_not_the_printed_citation_is_not_reported():
    """``hcd-davis-adu-ta-2025`` is a dependency of the Davis rule, not its
    citation URL. Only the link the card prints is in scope here."""

    watch = _unchanged_watch()
    watch.unchanged.remove("hcd-davis-adu-ta-2025")
    watch.observed_digests.pop("hcd-davis-adu-ta-2025")
    watch.unverifiable["hcd-davis-adu-ta-2025"] = UnverifiableSource(
        source_id="hcd-davis-adu-ta-2025",
        reason="HTTP 404 Not Found",
        last_verified_on="2026-07-30",
        attempts=1,
        kind="not_found",
    )

    assert withdrawn_citations(_build(watch), SOURCES, RULES) == ()


def test_a_withdrawn_address_never_stales_a_rule_or_moves_a_result():
    """The load-bearing invariant. A dead link is a fact about the address."""

    snapshot = _build(_watch_with_failure("not_found"))
    assert snapshot.affected_rule_ids == ()
    assert snapshot.affected_golden_case_ids == ()

    baseline = verify_rules(RULES, GOLDEN, changed_source_ids=[])
    after = verify_rules(
        RULES, GOLDEN, changed_source_ids=list(snapshot.changed_source_ids)
    )
    assert after.stale == baseline.stale
    assert after.golden_failed == baseline.golden_failed

    rules = load_rules(RULES)
    intake = {"jurisdiction": "davis", "project_type": "adu"}
    assert [result.rule.rule_id for result in screen(intake, rules)] == [
        result.rule.rule_id for result in screen(intake, load_rules(RULES))
    ]
    assert WITHDRAWN_RULE_ID in {
        result.rule.rule_id for result in screen(intake, rules)
    }


# --------------------------------------------------------------------------
# The report a maintainer actually reads
# --------------------------------------------------------------------------


def test_the_harness_reports_a_withdrawn_citation_from_the_adopted_receipt(
    monkeypatch, capsys, tmp_path
):
    from permit_pathways.harness import __main__ as harness_main

    receipt = _write(tmp_path, _payload("not_found"))
    monkeypatch.setattr(harness_main, "ADOPTED_SOURCE_STATE", receipt)
    monkeypatch.setattr("sys.argv", ["permit_pathways.harness"])

    assert harness_main.main() == 0

    printed = capsys.readouterr().out
    assert "published citation links: 1 cited source address(es)" in printed
    assert f"LINK NOT FOUND: {WITHDRAWN_RULE_ID}" in printed


def test_the_harness_says_so_when_no_citation_address_is_gone(monkeypatch, capsys):
    from permit_pathways.harness import __main__ as harness_main

    monkeypatch.setattr("sys.argv", ["permit_pathways.harness"])

    assert harness_main.main() == 0

    printed = capsys.readouterr().out
    assert 'records no cited source whose published address answered "not found"' in (
        printed
    )
    assert "LINK NOT FOUND" not in printed


# --------------------------------------------------------------------------
# The browser, which is where the applicant meets the link
# --------------------------------------------------------------------------


def _slice(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    return source[start_index : source.index(end, start_index)]


def _run_node(script: str) -> None:
    completed = subprocess.run(
        ["node", "--input-type=module"],
        input=script,
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr.strip() or "node exited nonzero")


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_the_browser_refuses_an_unverifiable_row_it_cannot_describe():
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    script = "\n".join(
        [
            "let SOURCE_STATE = null;",
            _slice(application, "function isJsonNumber", "function uiText"),
            _slice(application, "function safeExternalUrl", "function validTextList"),
            _slice(
                application, "const SOURCE_STATE_KEYS", "function sourceImpactLists"
            ),
            r"""
const source = {
  source_id: "davis-adu-handout-2026", sha256: "a".repeat(64),
  fetched_on: "2026-07-30", watch: true,
};
const base = {
  last_verified_on: "2026-07-30", observed_sha256: null,
  reason: "HTTP 404 Not Found", recorded_sha256: "a".repeat(64),
  source_id: "davis-adu-handout-2026", status: "unverifiable",
};
function check(condition, message) {
  if (!condition) throw new Error(message);
}
check(
  sourceStateObservationIsValid({...base, unverifiable_kind: "not_found"}, source),
  "a fully described not-found row was rejected",
);
check(
  sourceStateObservationIsValid({...base, unverifiable_kind: "transport"}, source),
  "a fully described transport row was rejected",
);
check(
  !sourceStateObservationIsValid(base, source),
  "an unverifiable row with no kind was accepted",
);
check(
  !sourceStateObservationIsValid({...base, unverifiable_kind: "fine"}, source),
  "an unrecognised kind was accepted",
);
const fetched = {
  ...base, observed_sha256: "a".repeat(64), reason: null, status: "unchanged",
  unverifiable_kind: "not_found",
};
check(
  !sourceStateObservationIsValid(fetched, source),
  "a fetched row carrying a kind was accepted",
);
""",
        ]
    )

    _run_node(script)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_the_browser_withholds_the_link_only_for_a_withdrawn_address():
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    script = "\n".join(
        [
            "let SOURCES = {};",
            "let SOURCE_STATE = null;",
            "let simulating = false;",
            _slice(application, "function isJsonNumber", "function uiText"),
            _slice(application, "function safeExternalUrl", "function validTextList"),
            r"""
const url = "https://example.gov/handout.pdf";
const rule = {
  rule_id: "davis-local-adu-process",
  citation: {url, source: "City of Davis handout", verified_on: "2026-07-30"},
  source_dependencies: ["davis-adu-handout-2026"],
};
SOURCES = {[url]: {source_id: "davis-adu-handout-2026", watch: true}};
function observation(kind) {
  return {
    observations: [{
      source_id: "davis-adu-handout-2026", status: "unverifiable",
      unverifiable_kind: kind,
    }],
  };
}
function check(condition, message) {
  if (!condition) throw new Error(message);
}
SOURCE_STATE = observation("not_found");
check(citationLinkNotFound(rule), "a withdrawn citation address was not seen");
check(
  notFoundSourceIds().join() === "davis-adu-handout-2026",
  "the withdrawn source id was not derived",
);
SOURCE_STATE = observation("transport");
check(
  !citationLinkNotFound(rule),
  "a source that merely went quiet withheld the link",
);
SOURCE_STATE = null;
check(!citationLinkNotFound(rule), "no receipt should withhold nothing");
SOURCE_STATE = observation("not_found");
check(
  !citationLinkNotFound({...rule, citation: {...rule.citation, url: "https://x.gov/"}}),
  "an unrelated citation url was treated as withdrawn",
);
""",
        ]
    )

    _run_node(script)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_the_shipped_result_card_stops_offering_a_link_that_resolves_to_nothing():
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    card = _slice(application, "function renderResultCard", "  const hasGuidance")

    assert "citationLinkNotFound(rule)" in card
    assert "const sourceUrl = linkNotFound ? null : safeExternalUrl(c.url);" in card
    assert "s.citationLinkNotFound(formatSourceDate(c.verified_on))" in card
    # The finding is about the link, so nothing else may move.
    assert "ruleStatus" not in card.split("const linkNotFound")[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_the_reference_server_and_the_browser_withhold_the_same_link():
    """Two runtimes print this citation. Neither may disagree with the other."""

    from demo.app import citation_link_not_found, citation_source_id

    rules = {rule.rule_id: rule for rule in load_rules(RULES)}
    citation = rules[WITHDRAWN_RULE_ID].citation

    assert citation_source_id(citation.url) == WITHDRAWN_SOURCE_ID
    assert citation_link_not_found(citation, [WITHDRAWN_SOURCE_ID])
    assert not citation_link_not_found(citation, [])

    snapshot = _build(_watch_with_failure("not_found"))
    python_rule_ids = [
        item.rule_id for item in withdrawn_citations(snapshot, SOURCES, RULES)
    ]
    assert [
        rule.rule_id
        for rule in load_rules(RULES)
        if citation_link_not_found(rule.citation, snapshot.not_found_source_ids)
    ] == python_rule_ids
