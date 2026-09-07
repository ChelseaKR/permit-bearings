"""The what-if CLI: the same inputs as the screening command, a different question.

The exit codes are deliberately the screening command's, including ``1``. A
what-if over an intake that still has an unanswered material fact is useful --
it is arguably the case the command exists for -- but the run is still not a
completed screening, and a caller must not read it as one.
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
)
from permit_pathways.what_if_cli import main

ROOT = Path(__file__).resolve().parents[1]
AS_OF = "2026-09-06"

WOODLAND = {
    "project_type": "adu",
    "jurisdiction": "woodland",
    "primary_dwelling_status": "existing_single_family",
    "adu_project_form": "new_detached",
    "unpermitted_existing": "no",
}


def _write(tmp_path: Path, document: Any) -> Path:
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _run(
    tmp_path: Path,
    document: Any,
    capsys: pytest.CaptureFixture[str],
    *extra: str,
) -> tuple[int, str, str]:
    code = main(["--facts", str(_write(tmp_path, document)), "--as-of", AS_OF, *extra])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_json_output_carries_the_boundary_and_the_deltas(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = _run(tmp_path, WOODLAND, capsys, "--format", "json")
    payload = json.loads(out)
    assert code == EXIT_OK
    assert payload["what_if_schema_version"] == 1
    assert payload["what_if_boundary_statement"]
    assert payload["decision_boundary_statement"]
    forms = next(
        entry for entry in payload["facts"] if entry["field"] == "adu_project_form"
    )
    conversion = next(
        item for item in forms["alternatives"] if item["value"] == "conversion"
    )
    assert conversion["rules_added"] == ["adu-conversion-exemptions"]


def test_console_output_names_the_unknown_branch_and_its_cost(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = _run(tmp_path, WOODLAND, capsys)
    assert code == EXIT_OK
    assert "no candidate route is reported for this answer" in out
    assert "needs staff review" in out
    assert "no rule or route changes" in out
    assert "rules that would apply: adu-conversion-exemptions" in out


def test_an_unanswered_material_fact_exits_needs_staff_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    document = {**WOODLAND, "unpermitted_existing": "unknown"}
    code, out, _ = _run(tmp_path, document, capsys)
    assert code == EXIT_NEEDS_STAFF_REVIEW
    # The branches are still printed: that is what the command is for.
    assert "unpermitted_existing (now: unanswered)" in out
    assert "Staff review needed; unanswered: unpermitted_existing" in out


def test_an_unknown_value_is_refused_naming_what_it_accepts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    document = {**WOODLAND, "adu_project_form": "garage_conversion"}
    code, _, err = _run(tmp_path, document, capsys)
    assert code == EXIT_INVALID_INPUT
    assert "adu_project_form" in err
    assert "new_detached" in err


def test_a_contradicting_jurisdiction_flag_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = _run(tmp_path, WOODLAND, capsys, "--jurisdiction", "davis")
    assert code == EXIT_INVALID_INPUT
    assert "contradicts" in err


def test_an_unreadable_rule_directory_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = _run(tmp_path, WOODLAND, capsys, "--rules", str(tmp_path))
    assert code == EXIT_INVALID_INPUT
    assert "--rules" in err


def test_a_malformed_as_of_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["--facts", str(_write(tmp_path, WOODLAND)), "--as-of", "not-a-date"])
    captured = capsys.readouterr()
    assert code == EXIT_INVALID_INPUT
    assert "--as-of" in captured.err


def test_a_missing_snapshot_path_runs_without_one_rather_than_substituting(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = _run(
        tmp_path,
        WOODLAND,
        capsys,
        "--format",
        "json",
        "--source-state",
        str(tmp_path / "absent.json"),
    )
    payload = json.loads(out)
    assert code == EXIT_OK
    assert payload["source_state"]["available"] is False
    assert payload["source_state"]["changed_source_ids"] is None
    assert any("No source-state snapshot" in n for n in payload["notices"])


def test_a_held_fact_prints_the_hold_instead_of_an_empty_delta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps(
            {
                "snapshot_id": "test-hold",
                "changed_source_ids": ["ca-gov-66311-7"],
                "unverifiable_source_ids": [],
                "affected_rule_ids": [],
                "checked_at": "2026-09-06T00:00:00Z",
                "receipt": {"status": "reviewed"},
            }
        ),
        encoding="utf-8",
    )
    code, out, _ = _run(tmp_path, WOODLAND, capsys, "--source-state", str(snapshot))
    assert code == EXIT_OK
    assert "Deltas withheld (source_on_review_hold)" in out
    assert "delta withheld — a rule reading this fact is on hold" in out
    # `adu-unpermitted-legalization` also has a criterion on
    # `primary_dwelling_status`, so holding its source withholds both facts.
    # One held rule reaching two facts is the normal case, not an edge one.
    assert (
        "No delta is reported for primary_dwelling_status, unpermitted_existing" in out
    )
    # `adu_project_form` is read only by `adu-conversion-exemptions`, whose
    # sources are not held, so its deltas survive.
    assert "rules that would apply: adu-conversion-exemptions" in out


def test_a_fact_no_rule_reads_differently_says_so_on_the_console(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    document = {
        "project_type": "two_unit",
        "jurisdiction": "example-city",
        "in_urbanized_area": "yes",
        "sf_zone": "yes",
        "demolishes_protected_housing": "no",
        "tenant_occupied_last_3_years": "yes",
        "ellis_withdrawal_last_15_years": "no",
        "on_protected_site": "no",
        "two_unit_contributing_historic_location": "no",
        "two_unit_individually_listed_historic_property": "no",
    }
    code, out, _ = _run(tmp_path, document, capsys)
    assert code == EXIT_OK
    assert "No rule reads this differently for this project." in out
