"""Offline tests for the HCD HAU letters drift check.

Two dated issues (#63, #65) reported the same condition with the same
numbers, `dashboard rows: 1317; committed rows: 1314; CHANGED`. Three is the
difference between two row totals, not a count of new letters: HCD edits
published rows in place, so the same run can add rows, remove rows, and edit
rows, and the totals hide all of it. These tests pin the distinctions the
report has to keep, and the one it must never make — reporting an
unreachable dashboard as a change.

No test here touches the network.
"""

import json

import pytest
from scripts.pull_hau_letters import (
    Drift,
    classify,
    describe,
    main,
)

COLUMNS = ["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9"]


def row(jurisdiction, number, *, keywords="", url=None):
    return [
        jurisdiction,
        1784246400000,
        "Technical Assistance Letter",
        "Potential Violation",
        "Housing Element Law",
        "65583",
        keywords,
        url,
        "summary",
        number,
    ]


COMMITTED = [
    row("Davis", "HAU0000001"),
    row("Woodland", "HAU0000002"),
    row("Napa", "HAU0000003", keywords="flood zone"),
]


def payload(rows):
    return {"columns": COLUMNS, "rows": list(rows)}


def test_identical_rows_in_any_order_are_not_drift():
    drift = classify(list(reversed(COMMITTED)), COMMITTED)
    assert not drift.changed
    assert drift.added == []
    assert drift.removed == []
    assert describe(drift) == ["dashboard rows: 3; committed rows: 3; unchanged"]


def test_an_edited_row_is_reported_as_edited_not_as_nothing():
    """The failure mode the row totals hide.

    An in-place edit leaves the row count identical. Reporting only totals
    makes an edited legal-authority field indistinguishable from no change.
    """
    edited = [
        row("Davis", "HAU0000001"),
        row("Woodland", "HAU0000002"),
        row("Napa", "HAU0000003", keywords="flood zone; FEMA"),
    ]
    drift = classify(edited, COMMITTED)

    assert drift.dashboard_rows == drift.committed_rows == 3
    assert drift.changed, "an in-place edit is drift even at an identical row count"
    assert len(drift.added) == 1
    assert len(drift.removed) == 1
    assert drift.edited_jurisdictions == ["Napa"]
    assert drift.added_only_jurisdictions == []
    text = "\n".join(describe(drift))
    assert "edited in place" in text
    assert "Napa" in text


def test_a_new_letter_is_not_reported_as_an_edit():
    drift = classify([*COMMITTED, row("Colusa", "HAU0000004")], COMMITTED)

    assert drift.added_only_jurisdictions == ["Colusa"]
    assert drift.edited_jurisdictions == []
    assert drift.removed_only_jurisdictions == []
    assert "added rows only" in "\n".join(describe(drift))


def test_a_row_total_difference_is_never_reported_as_a_letter_count():
    """The exact shape of the two filed issues.

    Six added rows and five removed rows net to a difference of one. The
    report must not let that be read as one new letter.
    """
    dashboard = [
        row("Davis", "HAU0000001"),
        row("Woodland", "HAU0000002"),
        row("Napa", "HAU0000003", keywords="flood zone; FEMA"),
        row("Colusa", "HAU0000004"),
    ]
    drift = classify(dashboard, COMMITTED)

    assert drift.dashboard_rows - drift.committed_rows == 1
    assert len(drift.added) == 2
    assert len(drift.removed) == 1
    text = "\n".join(describe(drift))
    assert "rows added: 2; rows removed: 1" in text
    assert "A row total is not a letter count" in text
    # The two lists stay separate, so an edit can never be counted as new.
    assert drift.added_only_jurisdictions == ["Colusa"]
    assert drift.edited_jurisdictions == ["Napa"]


def test_a_duplicated_row_is_a_difference():
    drift = classify([*COMMITTED, row("Davis", "HAU0000001")], COMMITTED)
    assert drift.changed
    assert len(drift.added) == 1


def test_check_exits_three_only_when_the_dashboard_was_read_and_moved(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path,
) -> None:
    raw = tmp_path / "hau-letters-raw.json"
    raw.write_text(json.dumps(payload(COMMITTED)))
    monkeypatch.setattr("scripts.pull_hau_letters.RAW", raw)

    assert main(["--check"], fetch=lambda: payload(COMMITTED)) == 0
    assert "unchanged" in capsys.readouterr().out

    moved = [*COMMITTED, row("Colusa", "HAU0000004")]
    assert main(["--check"], fetch=lambda: payload(moved)) == 3
    assert "CHANGED" in capsys.readouterr().out
    # --check must not write.
    assert json.loads(raw.read_text())["rows"] == COMMITTED


def test_an_unreadable_dashboard_is_never_reported_as_drift(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path,
) -> None:
    """The distinction the source-currency watcher already makes.

    A fetch that fails is evidence about the network, not about HCD's
    letters. Exit 3 opens an issue saying HCD published something; a failed
    fetch must not reach it, and must not be silent either.
    """
    raw = tmp_path / "hau-letters-raw.json"
    raw.write_text(json.dumps(payload(COMMITTED)))
    monkeypatch.setattr("scripts.pull_hau_letters.RAW", raw)

    def unreachable():
        raise TimeoutError("read timed out")

    assert main(["--check"], fetch=unreachable) == 2
    output = capsys.readouterr().out
    assert "unverifiable" in output
    assert "CHANGED" not in output
    assert json.loads(raw.read_text())["rows"] == COMMITTED


def test_a_malformed_dashboard_payload_is_unverifiable_not_drift(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path,
) -> None:
    raw = tmp_path / "hau-letters-raw.json"
    raw.write_text(json.dumps(payload(COMMITTED)))
    monkeypatch.setattr("scripts.pull_hau_letters.RAW", raw)

    def republished():
        raise KeyError("dsr")

    assert main(["--check"], fetch=republished) == 2
    assert "unverifiable" in capsys.readouterr().out


def test_the_committed_corpus_classifies_against_itself_without_drift():
    """Non-vacuity: the real 1,314-row corpus, not just synthetic rows."""
    from scripts.pull_hau_letters import committed_rows

    rows = committed_rows()
    assert len(rows) > 1000, "the committed corpus is loaded"
    drift = classify(rows, rows)
    assert not drift.changed

    # And a single edited field in that corpus is caught.
    edited = [list(rows[0]), *[list(r) for r in rows[1:]]]
    edited[0][6] = str(edited[0][6]) + "; added keyword"
    moved = classify(edited, rows)
    assert moved.changed
    assert moved.dashboard_rows == moved.committed_rows
    assert moved.edited_jurisdictions == [str(rows[0][0])]


def test_the_fetch_identifies_itself():
    """Politeness: the dashboard sees who is calling.

    urllib's default User-Agent identifies nothing but the interpreter. The
    repository's source-currency watcher already sends a named agent.
    """
    import scripts.pull_hau_letters as puller

    captured = {}

    class Recorder:
        def __init__(self, url, data=None, headers=None, **kwargs):
            captured.update(headers or {})

    original = puller.urllib.request.Request
    puller.urllib.request.Request = Recorder
    try:
        with pytest.raises(Exception):  # noqa: B017 - urlopen gets a Recorder
            puller.query()
    finally:
        puller.urllib.request.Request = original
    assert captured.get("User-Agent") == "permit-pathways-hau-letters-watch/0.1"
    assert "permit-pathways" in captured["User-Agent"]


def test_drift_defaults_are_empty():
    empty = Drift(dashboard_rows=0, committed_rows=0)
    assert not empty.changed
    assert empty.edited_jurisdictions == []
