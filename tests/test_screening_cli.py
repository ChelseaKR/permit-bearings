"""The screening CLI: the same matcher, reachable from outside the project.

The exit codes are the contract, and the one that matters is ``1``. A run whose
material facts were not all answered is neither a success nor an error: it is a
screening that stopped short, and a caller that reads it as ``0`` publishes an
absence as an answer. So it gets its own code, and the payload it prints carries
no candidate route at all.

Parity with the browser is asserted over the committed Golden corpus rather than
over invented fixtures: the corpus is what ``assets/demo.js`` is already held to,
so agreeing with it is agreeing with the browser.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.screening_cli import (
    EXIT_INVALID_INPUT,
    EXIT_NEEDS_STAFF_REVIEW,
    EXIT_OK,
    main,
)

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = json.loads(
    (ROOT / "data" / "golden" / "example.json").read_text(encoding="utf-8")
)
SNAPSHOT = ROOT / "data" / "source-status" / "current.json"


def _write(tmp_path: Path, document: Any) -> Path:
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _run(
    tmp_path: Path,
    document: Any,
    capsys: pytest.CaptureFixture[str],
    *extra: str,
) -> tuple[int, dict[str, Any], str]:
    code = main(
        [
            "--facts",
            str(_write(tmp_path, document)),
            "--format",
            "json",
            "--as-of",
            "2026-09-06",
            *extra,
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out) if captured.out.strip() else {}
    return code, payload, captured.err


ADU = {
    "project_type": "adu",
    "jurisdiction": "davis",
    "primary_dwelling_status": "existing_single_family",
    "adu_project_form": "new_detached",
    "unpermitted_existing": "no",
}


def test_a_complete_intake_exits_zero_with_candidate_routes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, payload, _ = _run(tmp_path, ADU, capsys)
    assert code == EXIT_OK
    assert payload["decision_boundary"] == "candidate_rules_only"
    assert payload["candidate_routes"]
    assert payload["as_of"] == "2026-09-06"


def test_an_unknown_material_fact_exits_one_and_names_the_question(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Not zero, and not an error. The middle code exists for exactly this."""
    code, payload, _ = _run(
        tmp_path, {**ADU, "unpermitted_existing": "unknown"}, capsys
    )
    assert code == EXIT_NEEDS_STAFF_REVIEW
    assert payload["unresolved_facts"] == ["unpermitted_existing"]
    assert payload["candidate_routes"] == []
    assert payload["decision_boundary"] == "needs_staff_review"


def test_an_unknown_value_exits_two_naming_the_field_and_its_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, payload, err = _run(
        tmp_path,
        {"project_type": "two_unit", "jurisdiction": "davis", "sf_zone": "maybe"},
        capsys,
    )
    assert code == EXIT_INVALID_INPUT
    assert payload == {}, "nothing is screened when the input is invalid"
    assert "sf_zone" in err
    assert "'maybe'" in err
    assert "'yes', 'no', 'unknown'" in err.replace('"', "'")


def test_a_contradicted_jurisdiction_is_refused_rather_than_resolved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Screening under a place the file does not name would misattribute it."""
    code, _, err = _run(tmp_path, ADU, capsys, "--jurisdiction", "woodland")
    assert code == EXIT_INVALID_INPUT
    assert "contradicts" in err


def test_the_jurisdiction_flag_fills_in_a_file_that_omits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    without = {key: value for key, value in ADU.items() if key != "jurisdiction"}
    code, payload, _ = _run(tmp_path, without, capsys, "--jurisdiction", "davis")
    assert code == EXIT_OK
    assert payload["jurisdiction"] == "davis"


def test_a_missing_facts_file_exits_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["--facts", str(tmp_path / "absent.json"), "--format", "json"])
    assert code == EXIT_INVALID_INPUT
    assert "cannot read" in capsys.readouterr().err


def test_a_missing_snapshot_says_so_instead_of_reading_as_a_clean_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The dominant defect, at the CLI boundary.

    A source-state file that is not there must not render the same as one that
    was read and reported no change.
    """
    code, payload, _ = _run(
        tmp_path, ADU, capsys, "--source-state", str(tmp_path / "absent.json")
    )
    assert code == EXIT_OK
    assert payload["source_state"]["available"] is False
    assert payload["source_state"]["changed_source_ids"] is None
    assert any("says nothing about whether" in n for n in payload["notices"])


def test_the_committed_snapshot_is_carried_into_the_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, payload, _ = _run(tmp_path, ADU, capsys, "--source-state", str(SNAPSHOT))
    assert code == EXIT_OK
    source = payload["source_state"]
    assert source["available"] is True
    assert source["snapshot_id"] and source["receipt_id"] == source["snapshot_id"]
    assert source["receipt_status"] == "reviewed"


def test_the_console_rendering_states_the_boundary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        [
            "--facts",
            str(_write(tmp_path, {**ADU, "unpermitted_existing": "unknown"})),
            "--as-of",
            "2026-09-06",
        ]
    )
    out = capsys.readouterr().out
    assert code == EXIT_NEEDS_STAFF_REVIEW
    assert "not an eligibility determination" in out
    assert "STAFF REVIEW NEEDED" in out
    assert "No candidate route is reported" in out
    assert "Candidate route classes" not in out


# --- parity with the corpus the browser is held to ---------------------------


@pytest.mark.parametrize("case", GOLDEN, ids=[c["case_id"] for c in GOLDEN])
def test_every_golden_case_matches_its_expected_rules_through_the_cli(
    case: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, payload, err = _run(tmp_path, case["intake"], capsys)
    assert code in (EXIT_OK, EXIT_NEEDS_STAFF_REVIEW), err
    matched = [rule["rule_id"] for rule in payload["matched_rules"]]
    assert sorted(matched) == sorted(case["expected_rule_ids"]), case["case_id"]


@pytest.mark.parametrize("case", GOLDEN, ids=[c["case_id"] for c in GOLDEN])
def test_every_golden_case_validates_against_the_published_result_schema(
    case: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The other half of the parity claim, over the whole corpus rather than one intake.

    `test_screening_contract.py` already validates *a* result against
    `result.schema.json`, and one intake exercises one shape: it is a complete
    ADU with a snapshot present, so the branches an integrator is most likely to
    hit first -- a withheld route, an empty `candidate_routes`, a null
    `source_state` field, an SB 9 project type -- were published without any
    document ever having been checked against the schema that describes them.
    The Golden corpus covers all four, so it is what the schema is held to here.

    The checker is imported from the contract test rather than re-implemented,
    so it stays the one whose keyword coverage that module already guards. A
    second, quieter validator would be the exact hole this repository writes
    that guard to prevent.
    """
    from tests.test_screening_contract import _committed, validate

    code, payload, err = _run(tmp_path, case["intake"], capsys)
    assert code in (EXIT_OK, EXIT_NEEDS_STAFF_REVIEW), err
    errors = validate(payload, _committed("result.schema.json"), case["case_id"])
    assert not errors, errors


def test_the_golden_corpus_is_not_empty_and_covers_both_exit_states() -> None:
    """A parametrized loop over an empty list passes without checking anything,
    and a corpus with no unknown-fact case would leave exit 1 unexercised."""
    assert len(GOLDEN) == 29
    unknown_cases = [
        case
        for case in GOLDEN
        if any(value == "unknown" for value in case["intake"].values())
    ]
    assert len(unknown_cases) == 8
