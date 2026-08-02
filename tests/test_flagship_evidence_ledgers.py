from __future__ import annotations

import copy
import json
import re
from datetime import date, datetime
from itertools import pairwise
from math import isclose
from pathlib import Path
from statistics import median
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_ROOT = ROOT / "data" / "validation"
GATE_PATH = VALIDATION_ROOT / "woodland-flagship-gate.json"
CONTENT_PATH = VALIDATION_ROOT / "woodland-content-review.json"
PARTICIPANT_PATH = VALIDATION_ROOT / "woodland-participant-sessions.json"
MANUAL_PATH = VALIDATION_ROOT / "woodland-manual-evidence.json"
REHEARSAL_PATH = VALIDATION_ROOT / "woodland-source-change-rehearsal.json"

COMMIT = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
RAW_SHA256 = re.compile(r"^[0-9a-f]{64}$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PAGES_URL = "https://chelseakr.github.io/permit-pathways/"
PARTICIPANT_IDS = [f"P{number:02d}" for number in range(1, 7)]
REHEARSAL_STAGE_IDS = [
    "detect",
    "identify_affected_and_unaffected",
    "review",
    "update_or_suppress",
    "approve",
    "republish",
]
TASK_RESULTS = {
    "independent",
    "assisted",
    "partial",
    "not_completed",
    "not_observed",
}
ERROR_CODES = {
    "CANDIDATE_AS_APPROVAL",
    "HYPOTHETICAL_AS_REAL",
    "SOURCE_STATUS_MISREAD",
    "UNKNOWN_ASSUMED_FAVORABLE",
    "EVIDENCE_NOT_FOUND",
    "PRESENT_AS_COMPLIANT",
    "STAFF_REVIEW_MISSED",
    "NEXT_ACTION_NOT_FOUND",
    "NAVIGATION_BLOCKER",
    "TECHNICAL_ERROR",
}
REHEARSAL_DISPOSITIONS = {"retain", "revise", "route_to_staff", "suppress"}
REHEARSAL_STAGE_ACTORS = {
    "detect": "maintainer",
    "identify_affected_and_unaffected": "maintainer",
    "review": "reviewer",
    "update_or_suppress": "maintainer",
    "approve": "reviewer",
    "republish": "maintainer",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _status_for_count(completed: int, required: int) -> str:
    if completed == 0:
        return "not_run"
    if completed == required:
        return "complete"
    return "in_progress"


def _non_blank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _parse_date(value: Any) -> date | None:
    if not _non_blank(value) or not ISO_DATE.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _is_iso_date(value: Any) -> bool:
    return _parse_date(value) is not None


def _parse_timestamp(value: Any) -> datetime | None:
    if not _non_blank(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _is_date_or_timestamp(value: Any) -> bool:
    return _is_iso_date(value) or _parse_timestamp(value) is not None


def _evidence_date(value: Any) -> date | None:
    parsed_date = _parse_date(value)
    if parsed_date is not None:
        return parsed_date
    parsed_timestamp = _parse_timestamp(value)
    return parsed_timestamp.date() if parsed_timestamp is not None else None


def _is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def _exact_unique_members(value: Any, expected: set[str]) -> bool:
    return bool(
        isinstance(value, list)
        and len(value) == len(expected)
        and len(value) == len(set(value))
        and set(value) == expected
    )


def _valid_completed_task(
    task: dict[str, Any], correctness_fields: tuple[str, ...]
) -> bool:
    correctness = [task[field] for field in correctness_fields]
    if not (
        task["status"] == "complete"
        and task["result"] in TASK_RESULTS
        and isinstance(task["duration_seconds"], int)
        and not isinstance(task["duration_seconds"], bool)
        and 0 < task["duration_seconds"] <= 3600
        and isinstance(task["directional_assistance_count"], int)
        and not isinstance(task["directional_assistance_count"], bool)
        and task["directional_assistance_count"] >= 0
        and isinstance(task["error_codes"], list)
        and len(task["error_codes"]) == len(set(task["error_codes"]))
        and set(task["error_codes"]).issubset(ERROR_CODES)
        and all(value in {True, False, "not_observed"} for value in correctness)
    ):
        return False

    result = task["result"]
    assistance = task["directional_assistance_count"]
    return bool(
        (
            result == "independent"
            and assistance == 0
            and all(value is True for value in correctness)
        )
        or (
            result == "assisted"
            and assistance > 0
            and all(value is True for value in correctness)
        )
        or (
            result == "partial"
            and any(value is True for value in correctness)
            and not all(value is True for value in correctness)
        )
        or (
            result == "not_completed"
            and all(value is not True for value in correctness)
        )
        or (
            result == "not_observed"
            and all(value == "not_observed" for value in correctness)
        )
    )


def _valid_safety_readback(safety: dict[str, Any]) -> bool:
    if not (
        safety["status"] == "complete"
        and isinstance(safety["candidate_route_treated_as_approval"], bool)
        and isinstance(
            safety["reported_presence_treated_as_compliant_or_accepted"], bool
        )
        and isinstance(safety["confidence_rating"], int)
        and not isinstance(safety["confidence_rating"], bool)
        and 1 <= safety["confidence_rating"] <= 5
        and isinstance(safety["misunderstanding_repeated_after_neutral_prompt"], bool)
        and isinstance(safety["confident_critical_error"], bool)
        and (
            safety["safety_correction_after_timing"] is None
            or _non_blank(safety["safety_correction_after_timing"])
        )
    ):
        return False

    misunderstood = bool(
        safety["candidate_route_treated_as_approval"]
        or safety["reported_presence_treated_as_compliant_or_accepted"]
    )
    expected_critical_error = bool(
        misunderstood
        and (
            safety["confidence_rating"] >= 4
            or safety["misunderstanding_repeated_after_neutral_prompt"]
        )
    )
    return bool(
        (not safety["misunderstanding_repeated_after_neutral_prompt"] or misunderstood)
        and safety["confident_critical_error"] is expected_critical_error
        and (not misunderstood or _non_blank(safety["safety_correction_after_timing"]))
    )


def _valid_completed_scorecard(
    scorecard: dict[str, Any], ledger: dict[str, Any]
) -> bool:
    lock = ledger["artifact_lock"]
    artifact = scorecard["artifact_receipt"]
    frozen_on = _parse_date(lock["frozen_on"])
    artifact_verified_on = _evidence_date(artifact["artifact_verified_on"])
    if not (
        scorecard["status"] == "complete"
        and lock["status"] == "complete"
        and COMMIT.fullmatch(lock["commit_sha"] or "")
        and lock["deployed_url"] == PAGES_URL
        and frozen_on is not None
        and _non_blank(lock["frozen_by_code"])
        and _non_blank(lock["source_snapshot_receipt_id"])
        and artifact["lock_id"] == lock["lock_id"]
        and artifact["commit_sha"] == lock["commit_sha"]
        and artifact["deployed_url"] == lock["deployed_url"]
        and artifact["source_snapshot_id"] == lock["source_snapshot_id"]
        and artifact_verified_on is not None
        and frozen_on <= artifact_verified_on
        and _non_blank(artifact["artifact_verified_by_code"])
        and _non_blank(artifact["artifact_verification_receipt_id"])
    ):
        return False

    receipts = scorecard["receipts"]
    if not (
        _non_blank(receipts["private_screening_receipt_id"])
        and _non_blank(receipts["private_consent_receipt_id"])
        and _non_blank(receipts["privacy_review_receipt_id"])
        and SHA256.fullmatch(receipts["scorecard_integrity_sha256"] or "")
    ):
        return False

    eligibility = scorecard["cohort_eligibility"]
    if eligibility["qualified"] is not True or not all(
        isinstance(value, bool)
        for field, value in eligibility.items()
        if field != "qualified"
    ):
        return False

    session = scorecard["session"]
    session_date = _parse_date(session["session_date"])
    started = _parse_timestamp(session["started_at"])
    completed = _parse_timestamp(session["completed_at"])
    if not (
        session_date is not None
        and started is not None
        and completed is not None
        and started <= completed
        and started.date() == session_date
        and artifact_verified_on <= session_date
        and _non_blank(session["moderator_code"])
        and _non_blank(session["browser_device_category"])
        and (
            session["protocol_deviation"] is None
            or _non_blank(session["protocol_deviation"])
        )
    ):
        return False

    incident = scorecard["critical_incident"]
    if not (
        incident["status"] == "complete"
        and _non_blank(incident["trigger_category"])
        and _non_blank(incident["consequence_category"])
        and _non_blank(incident["workaround_category"])
        and incident["recurrence"]
        in {"once", "less_than_monthly", "monthly", "weekly", "more_often"}
        and incident["specific_recent_pain_threshold_met"]
        in {True, False, "not_observed"}
    ):
        return False

    task_specs = (
        (
            "route_task",
            ("candidate_guidance_correct", "source_and_unknown_escalation_correct"),
        ),
        (
            "packet_task",
            ("packet_and_next_action_correct", "presence_boundary_correct"),
        ),
    )
    for section, correctness_fields in task_specs:
        if not _valid_completed_task(scorecard[section], correctness_fields):
            return False

    safety = scorecard["final_safety_readback"]
    if not _valid_safety_readback(safety):
        return False
    if (
        safety["candidate_route_treated_as_approval"]
        and "CANDIDATE_AS_APPROVAL" not in scorecard["route_task"]["error_codes"]
    ) or (
        safety["reported_presence_treated_as_compliant_or_accepted"]
        and "PRESENT_AS_COMPLIANT" not in scorecard["packet_task"]["error_codes"]
    ):
        return False

    return all(
        _non_blank(value) for value in scorecard["deidentified_synthesis"].values()
    )


def _completed_scorecards(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    if [
        scorecard["scorecard_id"] for scorecard in ledger["scorecards"]
    ] != PARTICIPANT_IDS:
        raise ValueError("participant scorecard slots drifted")
    if any(
        scorecard["status"] not in {"not_run", "complete"}
        for scorecard in ledger["scorecards"]
    ):
        raise ValueError("participant scorecard status is unsupported")
    completed: list[dict[str, Any]] = []
    for scorecard in ledger["scorecards"]:
        if scorecard["status"] != "complete":
            continue
        if not _valid_completed_scorecard(scorecard, ledger):
            raise ValueError(
                f"{scorecard['scorecard_id']}: completed scorecard is invalid"
            )
        completed.append(scorecard)

    expected_ledger_status = (
        "prepared_not_executed"
        if not completed
        else "complete"
        if len(completed) == len(ledger["scorecards"])
        else "in_progress"
    )
    if ledger["status"] != expected_ledger_status:
        raise ValueError("participant ledger status does not match its scorecards")
    return completed


def derive_participant_aggregate(ledger: dict[str, Any]) -> dict[str, Any]:
    completed = _completed_scorecards(ledger)
    lock = ledger["artifact_lock"]
    same_version = None
    invalidated = None
    if completed:
        same_version = all(
            scorecard["artifact_receipt"]["lock_id"] == lock["lock_id"]
            and scorecard["artifact_receipt"]["commit_sha"] == lock["commit_sha"]
            and scorecard["artifact_receipt"]["deployed_url"] == lock["deployed_url"]
            and scorecard["artifact_receipt"]["source_snapshot_id"]
            == lock["source_snapshot_id"]
            for scorecard in completed
        )
        invalidated = not same_version

    def count_eligibility(field: str) -> int:
        return sum(
            scorecard["cohort_eligibility"][field] is True for scorecard in completed
        )

    def count_field(section: str, field: str) -> int | None:
        if not completed:
            return None
        return sum(scorecard[section][field] is True for scorecard in completed)

    route_times = [
        scorecard["route_task"]["duration_seconds"] for scorecard in completed
    ]
    packet_times = [
        scorecard["packet_task"]["duration_seconds"] for scorecard in completed
    ]
    navigation_blockers = None
    if completed:
        navigation_blockers = sum(
            "NAVIGATION_BLOCKER" in (scorecard["route_task"]["error_codes"] or [])
            or "NAVIGATION_BLOCKER" in (scorecard["packet_task"]["error_codes"] or [])
            for scorecard in completed
        )

    return {
        "status": _status_for_count(len(completed), len(ledger["scorecards"])),
        "same_version_verified": same_version,
        "sessions_completed": len(completed),
        "primary_beneficiaries_completed": count_eligibility("primary_beneficiary"),
        "primary_with_recent_attempt_completed": sum(
            scorecard["cohort_eligibility"]["primary_beneficiary"] is True
            and scorecard["cohort_eligibility"]["recent_analogous_packet_attempt"]
            is True
            for scorecard in completed
        ),
        "primary_with_preapproved_plan_exposure_completed": sum(
            scorecard["cohort_eligibility"]["primary_beneficiary"] is True
            and scorecard["cohort_eligibility"]["preapproved_plan_exposure"] is True
            for scorecard in completed
        ),
        "practitioners_completed": count_eligibility(
            "practitioner_with_recent_adu_packet_experience"
        ),
        "participants_with_small_jurisdiction_experience_completed": (
            count_eligibility("smaller_jurisdiction_experience")
        ),
        "problem_evidence_count": count_field(
            "critical_incident", "specific_recent_pain_threshold_met"
        ),
        "primary_problem_evidence_count": (
            None
            if not completed
            else sum(
                scorecard["cohort_eligibility"]["primary_beneficiary"] is True
                and scorecard["critical_incident"]["specific_recent_pain_threshold_met"]
                is True
                for scorecard in completed
            )
        ),
        "monthly_recurrence_count": (
            None
            if not completed
            else sum(
                scorecard["critical_incident"]["recurrence"]
                in {"monthly", "weekly", "more_often"}
                for scorecard in completed
            )
        ),
        "candidate_guidance_correct_count": count_field(
            "route_task", "candidate_guidance_correct"
        ),
        "source_and_unknown_escalation_correct_count": count_field(
            "route_task", "source_and_unknown_escalation_correct"
        ),
        "packet_and_next_action_correct_count": count_field(
            "packet_task", "packet_and_next_action_correct"
        ),
        "median_route_seconds": median(route_times) if route_times else None,
        "median_packet_seconds": median(packet_times) if packet_times else None,
        "repeated_navigation_blocker_sessions": navigation_blockers,
        "confident_critical_errors": count_field(
            "final_safety_readback", "confident_critical_error"
        ),
        "cohort_invalidated_by_version_change": invalidated,
    }


def derive_content_aggregate(ledger: dict[str, Any]) -> dict[str, Any]:
    reviewers_completed = sum(
        slot["status"] == "complete"
        and all(
            slot[field] is not None
            for field in (
                "reviewer",
                "qualification_summary",
                "method",
                "reviewed_on",
                "reviewed_execution_commit",
            )
        )
        and slot["independence_attested"] is True
        for slot in ledger["reviewer_slots"]
    )
    reviewed_rows = [
        row
        for row in ledger["rows"]
        if row["reviewer_1"] is not None
        and row["reviewer_2"] is not None
        and row["synthesis"] is not None
    ]
    return {
        "status": "not_run" if not reviewed_rows else ledger["gate"]["status"],
        "reviewers_completed": reviewers_completed,
        "requirements_reviewed": len(reviewed_rows),
        "initial_agreement_count": (
            None
            if not reviewed_rows
            else sum(
                row["synthesis"]["initial_agreement"] is True for row in reviewed_rows
            )
        ),
        "disagreements_resolved_count": sum(
            row["synthesis"]["initial_agreement"] is False
            and row["synthesis"]["resolution"]["status"] == "resolved"
            for row in reviewed_rows
        ),
        "known_blocking_content_defects": (
            None
            if not reviewed_rows
            else sum(
                row["synthesis"]["blocking_defect_remaining"] is True
                for row in reviewed_rows
            )
        ),
    }


def derive_manual_aggregates(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    spanish_usability = next(
        check
        for check in ledger["manual_checks"]
        if check["check_id"] == "ES-USABILITY-JOURNEY"
    )
    accessibility_checks = [
        check
        for check in ledger["manual_checks"]
        if check["check_id"] != spanish_usability["check_id"]
    ]
    completed_access = [
        check for check in accessibility_checks if check["result"] != "not_run"
    ]
    reviewed_spanish = [
        row for row in ledger["spanish_semantic_reviews"] if row["result"] != "not_run"
    ]
    usability_completed = spanish_usability["result"] != "not_run"
    return {
        "manual_accessibility": {
            "status": _status_for_count(
                len(completed_access), len(accessibility_checks)
            ),
            "required_check_count": len(accessibility_checks),
            "checks_completed": len(completed_access),
            "checks_passing": (
                None
                if not completed_access
                else sum(check["result"] == "pass" for check in completed_access)
            ),
        },
        "spanish_semantic_review": {
            "status": _status_for_count(
                len(reviewed_spanish), len(ledger["spanish_semantic_reviews"])
            ),
            "records_required": len(ledger["spanish_semantic_reviews"]),
            "records_reviewed": len(reviewed_spanish),
            "records_approved": (
                None
                if not reviewed_spanish
                else sum(row["result"] == "approved" for row in reviewed_spanish)
            ),
        },
        "spanish_usability": {
            "check_id": spanish_usability["check_id"],
            "status": "complete" if usability_completed else "not_run",
            "checks_required": 1,
            "checks_completed": int(usability_completed),
            "checks_passing": (
                None
                if not usability_completed
                else int(spanish_usability["result"] == "pass")
            ),
        },
    }


def _validate_completed_rehearsal(ledger: dict[str, Any]) -> bool:
    lock = ledger["artifact_lock"]
    contract = ledger["simulation_contract"]
    execution = ledger["execution"]
    observed = ledger["observed_impact"]
    publication = ledger["publication_receipt"]
    timing = ledger["timing"]
    burden = ledger["partner_burden_decision"]

    if not (
        ledger["status"] == "complete"
        and lock["status"] == "complete"
        and COMMIT.fullmatch(lock["baseline_commit_sha"] or "")
        and lock["baseline_deployed_url"] == PAGES_URL
        and _non_blank(lock["source_snapshot_receipt_id"])
        and RAW_SHA256.fullmatch(contract["baseline_sha256"] or "")
        and RAW_SHA256.fullmatch(contract["simulated_changed_sha256"] or "")
        and contract["simulated_changed_sha256"] != contract["baseline_sha256"]
        and _non_blank(contract["changed_fixture_receipt_id"])
    ):
        return False

    stage_times: list[tuple[datetime, datetime]] = []
    for stage in ledger["stages"]:
        started = _parse_timestamp(stage["started_at"])
        completed = _parse_timestamp(stage["completed_at"])
        actor_role = REHEARSAL_STAGE_ACTORS[stage["stage_id"]]
        expected_actor_code = execution[f"{actor_role}_code"]
        if not (
            stage["status"] == "complete"
            and started is not None
            and completed is not None
            and started <= completed
            and _non_blank(expected_actor_code)
            and stage["actor_code"] == expected_actor_code
            and _non_blank(stage["method"])
            and _non_blank(stage["observed_result"])
            and _non_blank(stage["evidence_receipt_id"])
            and _non_blank(stage["review_receipt_id"])
        ):
            return False
        stage_times.append((started, completed))
    if any(
        stage_times[index - 1][1] > stage_times[index][0]
        for index in range(1, len(stage_times))
    ):
        return False

    rehearsal_started = _parse_timestamp(execution["rehearsal_started_at"])
    rehearsal_completed = _parse_timestamp(execution["rehearsal_completed_at"])
    if not (
        rehearsal_started is not None
        and rehearsal_completed is not None
        and rehearsal_started <= stage_times[0][0]
        and stage_times[-1][1] <= rehearsal_completed
        and _parse_date(contract["baseline_recorded_on"]) is not None
        and _parse_date(contract["baseline_recorded_on"]) <= rehearsal_started.date()
        and _non_blank(execution["maintainer_code"])
        and _non_blank(execution["reviewer_code"])
        and execution["maintainer_code"] != execution["reviewer_code"]
        and _non_blank(execution["human_owner_role"])
        and _non_blank(execution["privacy_review_receipt_id"])
        and (
            execution["protocol_deviations"] is None
            or _non_blank(execution["protocol_deviations"])
        )
    ):
        return False

    expected = ledger["expected_impact"]
    expected_requirements = set(expected["affected_requirement_ids"])
    expected_records = set(expected["affected_records"])
    expected_controls = {
        control["control_id"] for control in expected["unaffected_controls"]
    }
    dispositions = observed["dispositions"]
    if not (
        observed["detected_source_state"] == contract["expected_source_state"]
        and observed["detected_sha256"] == contract["simulated_changed_sha256"]
        and _exact_unique_members(
            observed["affected_requirement_ids"], expected_requirements
        )
        and _exact_unique_members(
            observed["affected_action_requirement_ids"], expected_requirements
        )
        and _exact_unique_members(observed["affected_record_paths"], expected_records)
        and _exact_unique_members(observed["unaffected_control_ids"], expected_controls)
        and isinstance(dispositions, list)
        and len(dispositions) == len(expected_requirements)
        and {entry.get("requirement_id") for entry in dispositions}
        == expected_requirements
        and all(
            set(entry) == {"requirement_id", "disposition", "evidence_receipt_id"}
            and entry.get("disposition") in REHEARSAL_DISPOSITIONS
            and _non_blank(entry.get("evidence_receipt_id"))
            for entry in dispositions
        )
        and isinstance(observed["blocking_defects_found"], int)
        and not isinstance(observed["blocking_defects_found"], bool)
        and observed["blocking_defects_found"] == 0
    ):
        return False

    if not (
        _non_blank(publication["approval_receipt_id"])
        and COMMIT.fullmatch(publication["republished_commit_sha"] or "")
        and publication["republished_commit_sha"] != lock["baseline_commit_sha"]
        and publication["republished_url"] == PAGES_URL
        and publication["republished_source_sha256"]
        == contract["simulated_changed_sha256"]
        and _non_blank(publication["verification_receipt_id"])
        and (
            publication["rollback_receipt_id"] is None
            or _non_blank(publication["rollback_receipt_id"])
        )
    ):
        return False

    elapsed_minutes = (rehearsal_completed - rehearsal_started).total_seconds() / 60
    maintainer_minutes = sum(
        (completed - started).total_seconds() / 60
        for stage, (started, completed) in zip(
            ledger["stages"], stage_times, strict=True
        )
        if REHEARSAL_STAGE_ACTORS[stage["stage_id"]] == "maintainer"
    )
    reviewer_minutes = sum(
        (completed - started).total_seconds() / 60
        for stage, (started, completed) in zip(
            ledger["stages"], stage_times, strict=True
        )
        if REHEARSAL_STAGE_ACTORS[stage["stage_id"]] == "reviewer"
    )
    if not (
        _is_number(timing["elapsed_minutes"])
        and timing["elapsed_minutes"] > 0
        and isclose(timing["elapsed_minutes"], elapsed_minutes, abs_tol=0.01)
        and _is_number(timing["maintainer_active_minutes"])
        and isclose(
            timing["maintainer_active_minutes"], maintainer_minutes, abs_tol=0.01
        )
        and _is_number(timing["reviewer_active_minutes"])
        and isclose(timing["reviewer_active_minutes"], reviewer_minutes, abs_tol=0.01)
    ):
        return False

    burden_decided_on = _parse_date(burden["decided_on"])
    burden_verified_on = _parse_date(burden["receipt_verified_on"])
    return bool(
        burden["status"] == "complete"
        and isinstance(burden["acceptable"], bool)
        and _non_blank(burden["partner_role"])
        and burden_decided_on is not None
        and rehearsal_completed.date() <= burden_decided_on
        and _non_blank(burden["private_evidence_receipt_id"])
        and burden_verified_on is not None
        and burden_decided_on <= burden_verified_on
        and _non_blank(burden["receipt_verified_by_code"])
    )


def derive_rehearsal_aggregate(ledger: dict[str, Any]) -> dict[str, Any]:
    if [stage["stage_id"] for stage in ledger["stages"]] != REHEARSAL_STAGE_IDS:
        raise ValueError("rehearsal stage contract drifted")
    if any(
        stage["status"] not in {"not_run", "complete"} for stage in ledger["stages"]
    ):
        raise ValueError("rehearsal stage status is unsupported")
    completed_stages = sum(stage["status"] == "complete" for stage in ledger["stages"])
    execution = ledger["execution"]
    observed = ledger["observed_impact"]
    burden = ledger["partner_burden_decision"]
    fully_complete = completed_stages == len(ledger["stages"])
    if fully_complete and not _validate_completed_rehearsal(ledger):
        raise ValueError("completed rehearsal lacks required evidence")
    status = (
        "complete"
        if fully_complete
        else "not_run"
        if not completed_stages
        else "in_progress"
    )
    return {
        "status": status,
        "stages_completed": completed_stages,
        "rehearsals_completed": int(fully_complete),
        "affected_requirements_confirmed": (
            len(observed["affected_requirement_ids"]) if fully_complete else None
        ),
        "unaffected_controls_confirmed": (
            len(observed["unaffected_control_ids"]) if fully_complete else None
        ),
        "defects_found": observed["blocking_defects_found"] if fully_complete else None,
        "human_owner_recorded": (
            execution["human_owner_role"] is not None if fully_complete else None
        ),
        "republication_verified": True if fully_complete else None,
        "acceptable_burden": burden["acceptable"] if fully_complete else None,
        "acceptable_burden_decided_by_partner": (
            burden["status"] == "complete" if fully_complete else None
        ),
    }


def _valid_gate_lock(gate: dict[str, Any]) -> bool:
    lock = gate["artifact_lock"]
    dry_run = lock["internal_dry_run"]
    frozen_on = _parse_date(lock["frozen_on"])
    dry_run_on = _parse_date(dry_run["run_on"])
    return bool(
        gate["status"] == "complete"
        and lock["status"] == "complete"
        and COMMIT.fullmatch(lock["commit_sha"] or "")
        and lock["deployed_url"] == PAGES_URL
        and frozen_on is not None
        and _non_blank(lock["frozen_by_code"])
        and _non_blank(lock["source_snapshot_receipt_id"])
        and dry_run["status"] == "complete"
        and dry_run["artifact_lock_id"] == lock["lock_id"]
        and dry_run["commit_sha"] == lock["commit_sha"]
        and dry_run["deployed_url"] == lock["deployed_url"]
        and dry_run["source_snapshot_id"] == lock["source_snapshot_id"]
        and dry_run["source_snapshot_receipt_id"] == lock["source_snapshot_receipt_id"]
        and dry_run_on is not None
        and frozen_on <= dry_run_on
        and _non_blank(dry_run["tester_code"])
        and dry_run["result"] == "pass"
        and _non_blank(dry_run["evidence_receipt_id"])
    )


def _valid_funnel(record: dict[str, Any], sequence: tuple[str, ...]) -> bool:
    if not all(isinstance(value, int) and value >= 0 for value in record.values()):
        return False
    return all(record[left] >= record[right] for left, right in pairwise(sequence))


def _valid_recruitment_for_evidence(
    gate: dict[str, Any],
    content_aggregate: dict[str, Any],
    participant_aggregate: dict[str, Any] | None,
) -> bool:
    recruitment = gate["recruitment"]
    reviewers = recruitment["reviewers"]
    participants = recruitment["participants"]
    partners = recruitment["partners"]
    return bool(
        recruitment["status"] == "complete"
        and participant_aggregate is not None
        and _valid_funnel(
            reviewers,
            ("contacted", "screened", "qualified", "scheduled", "completed"),
        )
        and _valid_funnel(
            participants,
            ("contacted", "screened", "qualified", "scheduled", "completed"),
        )
        and _valid_funnel(
            partners,
            (
                "contacted",
                "discovery_conversations_completed",
                "qualifying_written_next_steps",
            ),
        )
        and reviewers["completed"] == content_aggregate["reviewers_completed"]
        and participants["completed"] == participant_aggregate["sessions_completed"]
        and partners["qualifying_written_next_steps"]
        == gate["external_evidence"]["partner_gate"]["qualifying_written_next_steps"]
    )


def _valid_partner_gate(gate: dict[str, Any], commit: str | None) -> bool:
    partner = gate["external_evidence"]["partner_gate"]
    thresholds = gate["thresholds"]["partner"]
    return bool(
        partner["status"] == "complete"
        and partner["artifact_lock_id"] == gate["artifact_lock"]["lock_id"]
        and partner["tested_commit_sha"] == commit
        and partner["journey_id"] == gate["artifact_lock"]["journey_id"]
        and partner["journey_version"] == gate["artifact_lock"]["journey_version"]
        and partner["qualifying_written_next_steps"]
        >= thresholds["qualifying_written_next_steps_required"]
        and partner["next_step_type"] in thresholds["qualifying_next_step_types"]
        and _non_blank(partner["partner_category"])
        and _non_blank(partner["owner_role"])
        and _is_iso_date(partner["due_on"])
        and _is_iso_date(partner["written_on"])
        and partner["written_on"] <= partner["due_on"]
        and _non_blank(partner["private_evidence_receipt_id"])
        and _is_iso_date(partner["receipt_verified_on"])
        and partner["written_on"] <= partner["receipt_verified_on"]
        and _non_blank(partner["receipt_verified_by_code"])
        and partner["institutional_authorization"]
        in {"individual_only", "explicit_institutional_authorization"}
    )


def _latest_evidence_date(
    gate: dict[str, Any],
    content: dict[str, Any],
    participants: dict[str, Any],
    manual: dict[str, Any],
    rehearsal: dict[str, Any],
) -> date | None:
    try:
        values: list[Any] = [
            gate["artifact_lock"]["frozen_on"],
            gate["artifact_lock"]["internal_dry_run"]["run_on"],
            gate["external_evidence"]["partner_gate"]["written_on"],
            gate["external_evidence"]["partner_gate"]["receipt_verified_on"],
            content["artifact_lock"]["frozen_on"],
            participants["artifact_lock"]["frozen_on"],
            manual["privacy_protocol"]["reviewer"]["reviewed_on"],
            manual["privacy_protocol"]["signoff"]["signed_on"],
            rehearsal["execution"]["rehearsal_started_at"],
            rehearsal["execution"]["rehearsal_completed_at"],
            rehearsal["partner_burden_decision"]["decided_on"],
            rehearsal["partner_burden_decision"]["receipt_verified_on"],
        ]
        values.extend(slot["reviewed_on"] for slot in content["reviewer_slots"])
        values.extend(
            item["synthesis"]["resolution"]["resolved_on"]
            for item in (*content["rows"], *content["cross_cutting_checks"])
        )
        values.extend(
            timestamp
            for scorecard in participants["scorecards"]
            for timestamp in (
                scorecard["session"]["started_at"],
                scorecard["session"]["completed_at"],
            )
        )
        for check in manual["manual_checks"]:
            values.extend(
                (
                    check["execution"]["started_at"],
                    check["execution"]["completed_at"],
                    check["reviewer"]["reviewed_on"],
                    check["signoff"]["signed_on"],
                )
            )
        for row in manual["spanish_semantic_reviews"]:
            values.extend((row["reviewed_on"], row["signoff"]["signed_on"]))
    except (KeyError, TypeError):
        return None

    parsed = [_evidence_date(value) for value in values]
    if any(value is None for value in parsed):
        return None
    dated_values = [value for value in parsed if value is not None]
    frozen_on = dated_values[0]
    if any(value < frozen_on for value in dated_values[1:]):
        return None
    return max(dated_values)


def _valid_proceed_decision(
    gate: dict[str, Any], evidence_latest_on: date | None
) -> bool:
    decision = gate["decision"]
    evaluated_on = _parse_date(decision["evaluated_on"])
    decided_on = _parse_date(decision["decided_on"])
    return bool(
        gate["status"] == "complete"
        and decision["status"] == "complete"
        and decision["recommendation"] == "proceed"
        and decided_on is not None
        and _non_blank(decision["decision_owner_code"])
        and decision["tested_commit_sha"] == gate["artifact_lock"]["commit_sha"]
        and evidence_latest_on is not None
        and evaluated_on is not None
        and evidence_latest_on <= evaluated_on <= decided_on
        and _non_blank(decision["evaluation_receipt_id"])
        and decision["failure_reasons"] == []
    )


def _participant_aggregate_or_none(
    participants: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        return derive_participant_aggregate(participants)
    except ValueError:
        return None


def _rehearsal_aggregate_or_none(
    rehearsal: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        return derive_rehearsal_aggregate(rehearsal)
    except ValueError:
        return None


def proceed_failures(
    gate: dict[str, Any],
    content: dict[str, Any],
    participants: dict[str, Any],
    manual: dict[str, Any],
    rehearsal: dict[str, Any],
) -> set[str]:
    failures: set[str] = set()
    lock = gate["artifact_lock"]
    commit = lock["commit_sha"]
    deployed_url = lock["deployed_url"]
    if not _valid_gate_lock(gate):
        failures.add("artifact_lock")

    content_gate = content["gate"]
    content_aggregate = derive_content_aggregate(content)
    content_thresholds = gate["thresholds"]["content_authority"]
    if not (
        content["artifact_lock"]["status"] == "locked"
        and content["artifact_lock"]["execution_commit"] == commit
        and content["artifact_lock"]["deployed_url"] == deployed_url
        and content_gate["reviewers_completed"]
        == content_thresholds["independent_reviewers_required"]
        and content_gate["initial_agreement_count"] is not None
        and content_gate["initial_agreement_count"]
        >= content_thresholds["minimum_initial_agreement"]
        and content_gate["known_blocking_content_defects"]
        == content_thresholds["known_blocking_content_defects_allowed"]
        and content_gate["all_disagreements_resolved"] is True
        and content_gate["eligible_for_applicant_testing"] is True
    ):
        failures.add("content_authority")

    participant_aggregate = _participant_aggregate_or_none(participants)
    cohort = gate["thresholds"]["cohort"]
    problem = gate["thresholds"]["problem_evidence"]
    task = gate["thresholds"]["trust_and_task"]
    if not participant_aggregate or not (
        participants["artifact_lock"]["status"] == "complete"
        and participants["artifact_lock"]["commit_sha"] == commit
        and participants["artifact_lock"]["deployed_url"] == deployed_url
        and participants["artifact_lock"]["frozen_on"] == lock["frozen_on"]
        and participants["artifact_lock"]["frozen_by_code"] == lock["frozen_by_code"]
        and participants["artifact_lock"]["source_snapshot_receipt_id"]
        == lock["source_snapshot_receipt_id"]
        and participants["privacy_protocol"]["status"] == "confirmed"
        and _non_blank(participants["privacy_protocol"]["execution_confirmation"])
        and _non_blank(participants["privacy_protocol"]["privacy_review_receipt_id"])
        and participant_aggregate["same_version_verified"] is True
        and participant_aggregate["sessions_completed"] == cohort["sessions_required"]
        and participant_aggregate["primary_beneficiaries_completed"]
        >= cohort["minimum_primary_beneficiaries"]
        and participant_aggregate["primary_with_recent_attempt_completed"]
        >= cohort["minimum_primary_with_recent_attempt"]
        and participant_aggregate["primary_with_preapproved_plan_exposure_completed"]
        >= cohort["minimum_primary_with_preapproved_plan_exposure"]
        and participant_aggregate["practitioners_completed"]
        >= cohort["minimum_practitioners"]
        and participant_aggregate[
            "participants_with_small_jurisdiction_experience_completed"
        ]
        >= cohort["minimum_with_small_jurisdiction_experience"]
        and participant_aggregate["problem_evidence_count"]
        >= problem["minimum_participants_with_specific_recent_pain"]
        and participant_aggregate["primary_problem_evidence_count"]
        >= problem["minimum_primary_beneficiaries_with_specific_recent_pain"]
        and participant_aggregate["monthly_recurrence_count"]
        >= problem["minimum_domain_participants_reporting_monthly_recurrence"]
        and participant_aggregate["candidate_guidance_correct_count"]
        >= task["minimum_candidate_guidance_correct"]
        and participant_aggregate["source_and_unknown_escalation_correct_count"]
        >= task["minimum_source_and_unknown_escalation_correct"]
        and participant_aggregate["packet_and_next_action_correct_count"]
        >= task["minimum_packet_and_next_action_correct"]
        and participant_aggregate["median_route_seconds"]
        <= task["maximum_median_route_seconds"]
        and participant_aggregate["median_packet_seconds"]
        <= task["maximum_median_packet_seconds"]
        and participant_aggregate["repeated_navigation_blocker_sessions"]
        <= task["maximum_repeated_navigation_blocker_sessions"]
        and participant_aggregate["confident_critical_errors"]
        == task["confident_critical_errors_allowed"]
        and participant_aggregate["cohort_invalidated_by_version_change"] is False
    ):
        failures.add("participant_sessions")

    manual_aggregates = derive_manual_aggregates(manual)
    if not (
        manual["artifact_lock"]["execution_status"] == "executed"
        and manual["artifact_lock"]["tested_commit"] == commit
        and manual["privacy_protocol"]["status"] == "confirmed"
        and manual_aggregates["manual_accessibility"]["status"] == "complete"
        and manual_aggregates["manual_accessibility"]["checks_passing"]
        == manual_aggregates["manual_accessibility"]["required_check_count"]
    ):
        failures.add("manual_accessibility")
    if not (
        manual_aggregates["spanish_semantic_review"]["status"] == "complete"
        and manual_aggregates["spanish_semantic_review"]["records_approved"]
        == manual_aggregates["spanish_semantic_review"]["records_required"]
    ):
        failures.add("spanish_semantic_review")
    if not (
        manual_aggregates["spanish_usability"]["status"] == "complete"
        and manual_aggregates["spanish_usability"]["checks_passing"] == 1
    ):
        failures.add("spanish_usability")

    if not _valid_partner_gate(gate, commit):
        failures.add("partner_gate")

    rehearsal_aggregate = _rehearsal_aggregate_or_none(rehearsal)
    if not rehearsal_aggregate or not (
        rehearsal["artifact_lock"]["status"] == "complete"
        and rehearsal["artifact_lock"]["baseline_commit_sha"] == commit
        and rehearsal["artifact_lock"]["baseline_deployed_url"] == deployed_url
        and rehearsal["artifact_lock"]["source_snapshot_receipt_id"]
        == lock["source_snapshot_receipt_id"]
        and rehearsal_aggregate["status"] == "complete"
        and rehearsal_aggregate["rehearsals_completed"]
        >= gate["thresholds"]["maintainability"][
            "completed_source_change_rehearsals_required"
        ]
        and rehearsal_aggregate["human_owner_recorded"] is True
        and rehearsal_aggregate["republication_verified"] is True
        and rehearsal_aggregate["acceptable_burden"] is True
        and rehearsal_aggregate["acceptable_burden_decided_by_partner"] is True
    ):
        failures.add("source_change_rehearsal")
    if not _valid_recruitment_for_evidence(
        gate,
        content_aggregate,
        participant_aggregate,
    ):
        failures.add("recruitment")
    return failures


def assert_decision_is_supported(
    gate: dict[str, Any],
    content: dict[str, Any],
    participants: dict[str, Any],
    manual: dict[str, Any],
    rehearsal: dict[str, Any],
) -> None:
    decision = gate["decision"]
    if decision["recommendation"] != "proceed":
        return
    failures = proceed_failures(gate, content, participants, manual, rehearsal)
    if failures:
        raise ValueError(
            "proceed recommendation is unsupported by: " + ", ".join(sorted(failures))
        )
    evidence_latest_on = _latest_evidence_date(
        gate, content, participants, manual, rehearsal
    )
    if not _valid_proceed_decision(gate, evidence_latest_on):
        raise ValueError("proceed recommendation lacks its decision receipt")


def test_gate_ledger_references_resolve_and_match_record_headers():
    gate = load_json(GATE_PATH)
    records = {
        "content_authority_review": load_json(CONTENT_PATH),
        "participant_sessions": load_json(PARTICIPANT_PATH),
        "manual_and_language_evidence": load_json(MANUAL_PATH),
        "source_change_rehearsal": load_json(REHEARSAL_PATH),
    }
    for key, reference in gate["evidence_ledgers"].items():
        path = ROOT / reference["path"]
        assert path.is_file()
        record = records[key]
        record_id_field = (
            "record_type" if key == "content_authority_review" else "record_id"
        )
        record_version_field = (
            "schema_version" if key == "content_authority_review" else "record_version"
        )
        assert reference["record_id"] == record[record_id_field]
        assert reference["record_version"] == record[record_version_field]


def test_participant_ledger_reserves_exactly_six_unexecuted_same_version_slots():
    gate = load_json(GATE_PATH)
    ledger = load_json(PARTICIPANT_PATH)

    assert ledger["status"] == "prepared_not_executed"
    assert [scorecard["scorecard_id"] for scorecard in ledger["scorecards"]] == (
        PARTICIPANT_IDS
    )
    assert all(scorecard["status"] == "not_run" for scorecard in ledger["scorecards"])
    assert ledger["artifact_lock"]["lock_id"] == gate["artifact_lock"]["lock_id"]
    for field in (
        "journey_id",
        "journey_version",
        "journey_fingerprint",
        "screening_case_id",
        "screening_case_fingerprint",
        "fact_envelope_fingerprint",
        "readiness_workflow_id",
        "readiness_workflow_fingerprint",
        "readiness_packet_id",
        "readiness_packet_fingerprint",
    ):
        assert ledger["artifact_lock"][field] == gate["artifact_lock"][field]
    assert (
        ledger["artifact_lock"]["answer_key_version"]
        == gate["artifact_lock"]["answer_key_version"]
    )
    for scorecard in ledger["scorecards"]:
        assert (
            scorecard["artifact_receipt"]["lock_id"]
            == ledger["artifact_lock"]["lock_id"]
        )
        assert scorecard["artifact_receipt"]["commit_sha"] is None
        assert scorecard["artifact_receipt"]["artifact_verification_receipt_id"] is None
        assert set(scorecard["cohort_eligibility"].values()) == {None}
        assert scorecard["critical_incident"]["status"] == "not_run"
        assert scorecard["route_task"]["status"] == "not_run"
        assert scorecard["packet_task"]["status"] == "not_run"
        assert scorecard["final_safety_readback"]["status"] == "not_run"
        assert set(scorecard["receipts"].values()) == {None}

    assert derive_participant_aggregate(ledger) == ledger["aggregate"]


def test_rehearsal_ledger_is_canonical_complete_in_scope_and_not_executed():
    gate = load_json(GATE_PATH)
    ledger = load_json(REHEARSAL_PATH)
    workflow = load_json(
        ROOT
        / "data"
        / "readiness"
        / "workflows"
        / "woodland-preapproved-detached-adu.json"
    )["workflow"]
    remedies = load_json(
        ROOT
        / "data"
        / "readiness"
        / "remedies"
        / "woodland-preapproved-detached-adu.json"
    )
    journey = load_json(
        ROOT
        / "data"
        / "journeys"
        / "generated"
        / "woodland-preapproved-detached-adu.json"
    )
    sources = load_json(ROOT / "data" / "sources.json")
    sources_by_id = {record["source_id"]: record for record in sources.values()}

    assert ledger["status"] == "prepared_not_executed"
    assert ledger["artifact_lock"]["lock_id"] == gate["artifact_lock"]["lock_id"]
    assert [stage["stage_id"] for stage in ledger["stages"]] == REHEARSAL_STAGE_IDS
    assert all(stage["status"] == "not_run" for stage in ledger["stages"])
    assert all(
        value is None
        for stage in ledger["stages"]
        for key, value in stage.items()
        if key not in {"stage_id", "status"}
    )
    contract = ledger["simulation_contract"]
    canonical_source = sources_by_id[contract["target_source_id"]]
    assert contract["baseline_sha256"] == canonical_source["sha256"]
    assert contract["baseline_recorded_on"] == canonical_source["fetched_on"]
    assert contract["simulated_changed_sha256"] is None
    requirement_ids = [
        requirement["requirement_id"] for requirement in workflow["requirements"]
    ]
    assert ledger["expected_impact"]["affected_requirement_ids"] == requirement_ids
    assert [entry["requirement_id"] for entry in remedies["entries"]] == requirement_ids
    unaffected = ledger["expected_impact"]["unaffected_controls"][0]
    route = journey["candidate_routes"][0]
    assert unaffected["rule_id"] == route["rule_id"]
    assert unaffected["rule_fingerprint"] == route["rule_fingerprint"]
    assert contract["target_source_id"] not in route["source_dependencies"]
    assert derive_rehearsal_aggregate(ledger) == ledger["aggregate"]


def test_gate_aggregates_are_derived_from_current_specialized_ledgers():
    gate = load_json(GATE_PATH)
    content = load_json(CONTENT_PATH)
    participants = load_json(PARTICIPANT_PATH)
    manual = load_json(MANUAL_PATH)
    rehearsal = load_json(REHEARSAL_PATH)
    external = gate["external_evidence"]

    content_expected = derive_content_aggregate(content)
    assert {
        key: external["content_authority_review"][key] for key in content_expected
    } == content_expected

    participant_expected = derive_participant_aggregate(participants)
    assert {
        key: external["participant_sessions"][key] for key in participant_expected
    } == participant_expected

    for key, expected in derive_manual_aggregates(manual).items():
        assert {field: external[key][field] for field in expected} == expected

    rehearsal_expected = derive_rehearsal_aggregate(rehearsal)
    rehearsal_external = external["source_change_rehearsal"]
    for key, expected in rehearsal_expected.items():
        assert rehearsal_external[key] == expected
    assert (
        rehearsal_external["elapsed_minutes"] == rehearsal["timing"]["elapsed_minutes"]
    )
    assert (
        rehearsal_external["maintainer_active_minutes"]
        == rehearsal["timing"]["maintainer_active_minutes"]
    )
    assert (
        rehearsal_external["reviewer_active_minutes"]
        == rehearsal["timing"]["reviewer_active_minutes"]
    )
    assert (
        rehearsal_external["human_owner_role"]
        == rehearsal["execution"]["human_owner_role"]
    )


def test_answer_key_binds_canonical_data_and_browser_fail_closed_states():
    gate = load_json(GATE_PATH)
    answer = gate["answer_key"]
    journey = load_json(
        ROOT
        / "data"
        / "journeys"
        / "generated"
        / "woodland-preapproved-detached-adu.json"
    )
    readiness_manifest = load_json(
        ROOT
        / "data"
        / "readiness"
        / "generated"
        / "woodland-preapproved-adu-evidence.json"
    )
    workflow = load_json(
        ROOT
        / "data"
        / "readiness"
        / "workflows"
        / "woodland-preapproved-detached-adu.json"
    )["workflow"]
    remedies = load_json(
        ROOT
        / "data"
        / "readiness"
        / "remedies"
        / "woodland-preapproved-detached-adu.json"
    )
    content_review = load_json(CONTENT_PATH)
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    bundle = (ROOT / "data" / "demo-data.js").read_text(encoding="utf-8")

    assert answer["applicability_conditions"] == workflow["applicability"]
    assert answer["applicability_status"] == journey["applicability_status"]
    assert (
        answer["editable_applicability_fact_ids"]
        == journey["editable_applicability_fact_ids"]
    )
    assert answer["route_source_review_due_on"] == journey["route_source_review_due_on"]
    assert answer["readiness_source_status"] == readiness_manifest["source_status"]
    assert (
        answer["readiness_source_status_as_of"]
        == readiness_manifest["source_status_as_of"]
    )
    assert (
        answer["readiness_source_review_due_on"]
        == readiness_manifest["source_review_due_on"]
    )
    assert answer["readiness_overall_status"] == readiness_manifest["overall_status"]
    assert answer["readiness_boundary"] == readiness_manifest["boundary"]
    assert answer["action_review_status"] == remedies["review"]["status"]
    assert (
        answer["action_content_fingerprint"]
        == content_review["artifact_lock"]["content_bindings"][
            "remedy_content_fingerprint"
        ]
    )
    assert answer["runtime_model_call"] is False
    assert answer["applicant_data_sent_to_model"] is False
    assert '"runtime_model_call":false' in bundle
    assert '"applicant_data_sent_to_model":false' in bundle
    assert (
        answer["valid_handoff_path"]
        == gate["artifact_lock"]["sample_urls"]["packet_result"]
    )
    assert answer["valid_handoff_query_keys"] == ["journey", "version"]
    assert set(answer["entry_state_contract"]) == {
        "start_required",
        "invalid",
        "source_review_required",
        "ready",
    }
    for fragment in (
        'if (!keys.length) return {status: "start_required"}',
        'return {status: "source_review_required"}',
        'return {status: "ready"}',
        'if (state.status !== "ready")',
        "if (evidenceSummary) evidenceSummary.hidden = true",
    ):
        assert fragment in application


def test_current_evidence_rejects_a_proceed_recommendation_across_every_gate():
    gate = load_json(GATE_PATH)
    content = load_json(CONTENT_PATH)
    participants = load_json(PARTICIPANT_PATH)
    manual = load_json(MANUAL_PATH)
    rehearsal = load_json(REHEARSAL_PATH)

    failures = proceed_failures(gate, content, participants, manual, rehearsal)
    assert failures == {
        "artifact_lock",
        "recruitment",
        "content_authority",
        "participant_sessions",
        "manual_accessibility",
        "spanish_semantic_review",
        "spanish_usability",
        "partner_gate",
        "source_change_rehearsal",
    }

    unsupported = copy.deepcopy(gate)
    unsupported["decision"].update(
        {
            "status": "complete",
            "recommendation": "proceed",
            "decided_on": "2026-08-31",
            "decision_owner_code": "D01",
            "tested_commit_sha": "a" * 40,
            "evaluated_on": "2026-08-31",
            "evaluation_receipt_id": "private-decision-receipt-1",
            "failure_reasons": [],
        }
    )
    with pytest.raises(ValueError, match="proceed recommendation is unsupported"):
        assert_decision_is_supported(
            unsupported,
            content,
            participants,
            manual,
            rehearsal,
        )


def test_current_pending_decision_and_ledgers_make_no_execution_claim():
    gate = load_json(GATE_PATH)
    participants = load_json(PARTICIPANT_PATH)
    rehearsal = load_json(REHEARSAL_PATH)

    assert gate["decision"]["recommendation"] is None
    assert gate["decision"]["evaluation_receipt_id"] is None
    assert participants["artifact_lock"]["commit_sha"] is None
    assert participants["privacy_protocol"]["status"] == "not_run"
    assert rehearsal["artifact_lock"]["baseline_commit_sha"] is None
    assert rehearsal["simulation_contract"]["changed_fixture_receipt_id"] is None
    assert rehearsal["publication_receipt"] == {
        "approval_receipt_id": None,
        "republished_commit_sha": None,
        "republished_url": None,
        "republished_source_sha256": None,
        "verification_receipt_id": None,
        "rollback_receipt_id": None,
    }
    assert rehearsal["partner_burden_decision"] == {
        "status": "pending",
        "acceptable": None,
        "partner_role": None,
        "decided_on": None,
        "private_evidence_receipt_id": None,
        "receipt_verified_on": None,
        "receipt_verified_by_code": None,
    }
    assert_decision_is_supported(
        gate,
        load_json(CONTENT_PATH),
        participants,
        load_json(MANUAL_PATH),
        rehearsal,
    )


def _valid_participant_ledger_fixture() -> dict[str, Any]:
    ledger = load_json(PARTICIPANT_PATH)
    ledger["status"] = "complete"
    ledger["artifact_lock"].update(
        {
            "status": "complete",
            "commit_sha": "a" * 40,
            "deployed_url": PAGES_URL,
            "frozen_on": "2026-08-03",
            "frozen_by_code": "F01",
            "source_snapshot_receipt_id": "private-source-snapshot-1",
        }
    )
    for scorecard in ledger["scorecards"]:
        code = scorecard["scorecard_id"]
        scorecard["status"] = "complete"
        scorecard["artifact_receipt"].update(
            {
                "commit_sha": "a" * 40,
                "deployed_url": PAGES_URL,
                "artifact_verified_on": "2026-08-03",
                "artifact_verified_by_code": "V01",
                "artifact_verification_receipt_id": f"private-artifact-{code}",
            }
        )
        scorecard["receipts"].update(
            {
                "private_screening_receipt_id": f"private-screening-{code}",
                "private_consent_receipt_id": f"private-consent-{code}",
                "privacy_review_receipt_id": f"private-privacy-{code}",
                "scorecard_integrity_sha256": "sha256:" + "0" * 64,
            }
        )
        scorecard["cohort_eligibility"].update(
            {
                "qualified": True,
                "primary_beneficiary": True,
                "recent_analogous_packet_attempt": True,
                "preapproved_plan_exposure": True,
                "practitioner_with_recent_adu_packet_experience": False,
                "smaller_jurisdiction_experience": True,
            }
        )
        scorecard["session"].update(
            {
                "session_date": "2026-08-04",
                "started_at": "2026-08-04T10:00:00Z",
                "completed_at": "2026-08-04T10:30:00Z",
                "moderator_code": "M01",
                "browser_device_category": "desktop_chromium",
            }
        )
        scorecard["critical_incident"].update(
            {
                "status": "complete",
                "trigger_category": "packet_start",
                "consequence_category": "delay",
                "workaround_category": "staff_contact",
                "recurrence": "monthly",
                "specific_recent_pain_threshold_met": True,
            }
        )
        scorecard["route_task"].update(
            {
                "status": "complete",
                "result": "independent",
                "duration_seconds": 120,
                "directional_assistance_count": 0,
                "error_codes": [],
                "candidate_guidance_correct": True,
                "source_and_unknown_escalation_correct": True,
            }
        )
        scorecard["packet_task"].update(
            {
                "status": "complete",
                "result": "independent",
                "duration_seconds": 180,
                "directional_assistance_count": 0,
                "error_codes": [],
                "packet_and_next_action_correct": True,
                "presence_boundary_correct": True,
            }
        )
        scorecard["final_safety_readback"].update(
            {
                "status": "complete",
                "candidate_route_treated_as_approval": False,
                "reported_presence_treated_as_compliant_or_accepted": False,
                "confidence_rating": 3,
                "misunderstanding_repeated_after_neutral_prompt": False,
                "confident_critical_error": False,
            }
        )
        scorecard["deidentified_synthesis"].update(
            {
                "supported_observation": "Located the bounded guidance.",
                "contrary_or_ambiguous_observation": "No contrary observation.",
                "recommended_change": "No change from this session.",
                "evidence_needed_before_broader_claim": "Complete the full gate.",
            }
        )
    return ledger


def test_completed_scorecards_derive_task_safety_and_time_consistency():
    ledger = _valid_participant_ledger_fixture()
    assert derive_participant_aggregate(ledger)["sessions_completed"] == 6

    not_observed = copy.deepcopy(ledger)
    not_observed["scorecards"][0]["route_task"]["result"] = "not_observed"
    with pytest.raises(ValueError, match="P01: completed scorecard is invalid"):
        derive_participant_aggregate(not_observed)

    hidden_critical_error = copy.deepcopy(ledger)
    safety = hidden_critical_error["scorecards"][0]["final_safety_readback"]
    safety.update(
        {
            "candidate_route_treated_as_approval": True,
            "confidence_rating": 5,
            "confident_critical_error": False,
            "safety_correction_after_timing": "Corrected after timing.",
        }
    )
    hidden_critical_error["scorecards"][0]["route_task"]["error_codes"] = [
        "CANDIDATE_AS_APPROVAL"
    ]
    with pytest.raises(ValueError, match="P01: completed scorecard is invalid"):
        derive_participant_aggregate(hidden_critical_error)

    pre_freeze = copy.deepcopy(ledger)
    pre_freeze["scorecards"][0]["artifact_receipt"]["artifact_verified_on"] = (
        "2026-08-02"
    )
    with pytest.raises(ValueError, match="P01: completed scorecard is invalid"):
        derive_participant_aggregate(pre_freeze)

    pre_verification_session = copy.deepcopy(ledger)
    pre_verification_session["scorecards"][0]["artifact_receipt"][
        "artifact_verified_on"
    ] = "2026-08-05"
    with pytest.raises(ValueError, match="P01: completed scorecard is invalid"):
        derive_participant_aggregate(pre_verification_session)


def test_status_only_completed_participant_scorecards_are_rejected():
    ledger = load_json(PARTICIPANT_PATH)
    ledger["status"] = "complete"
    ledger["artifact_lock"].update(
        {
            "status": "complete",
            "commit_sha": "a" * 40,
            "deployed_url": PAGES_URL,
            "frozen_on": "2026-08-03",
            "frozen_by_code": "F01",
            "source_snapshot_receipt_id": "private-source-snapshot-1",
        }
    )
    for scorecard in ledger["scorecards"]:
        scorecard["status"] = "complete"

    with pytest.raises(ValueError, match="P01: completed scorecard is invalid"):
        derive_participant_aggregate(ledger)


def _valid_rehearsal_fixture() -> dict[str, Any]:
    ledger = load_json(REHEARSAL_PATH)
    ledger["status"] = "complete"
    ledger["artifact_lock"].update(
        {
            "status": "complete",
            "baseline_commit_sha": "a" * 40,
            "baseline_deployed_url": PAGES_URL,
            "source_snapshot_receipt_id": "private-source-snapshot-1",
        }
    )
    ledger["simulation_contract"].update(
        {
            "simulated_changed_sha256": "b" * 64,
            "changed_fixture_receipt_id": "private-changed-fixture-1",
        }
    )
    ledger["execution"].update(
        {
            "rehearsal_started_at": "2026-08-04T09:00:00Z",
            "rehearsal_completed_at": "2026-08-04T09:30:00Z",
            "maintainer_code": "M01",
            "reviewer_code": "R01",
            "human_owner_role": "Content maintainer",
            "privacy_review_receipt_id": "private-rehearsal-privacy-1",
        }
    )
    for index, stage in enumerate(ledger["stages"]):
        start_minute = index * 5
        end_minute = start_minute + 5
        actor_role = REHEARSAL_STAGE_ACTORS[stage["stage_id"]]
        stage.update(
            {
                "status": "complete",
                "started_at": f"2026-08-04T09:{start_minute:02d}:00Z",
                "completed_at": f"2026-08-04T09:{end_minute:02d}:00Z",
                "actor_code": ledger["execution"][f"{actor_role}_code"],
                "method": f"Controlled {stage['stage_id']} method",
                "observed_result": f"Controlled {stage['stage_id']} result",
                "evidence_receipt_id": f"private-{stage['stage_id']}-evidence",
                "review_receipt_id": f"private-{stage['stage_id']}-review",
            }
        )
    expected = ledger["expected_impact"]
    ledger["observed_impact"].update(
        {
            "detected_source_state": ledger["simulation_contract"][
                "expected_source_state"
            ],
            "detected_sha256": "b" * 64,
            "affected_requirement_ids": copy.deepcopy(
                expected["affected_requirement_ids"]
            ),
            "affected_action_requirement_ids": copy.deepcopy(
                expected["affected_requirement_ids"]
            ),
            "affected_record_paths": copy.deepcopy(expected["affected_records"]),
            "unaffected_control_ids": [
                control["control_id"] for control in expected["unaffected_controls"]
            ],
            "dispositions": [
                {
                    "requirement_id": requirement_id,
                    "disposition": "retain",
                    "evidence_receipt_id": f"private-{requirement_id}-disposition",
                }
                for requirement_id in expected["affected_requirement_ids"]
            ],
            "blocking_defects_found": 0,
        }
    )
    ledger["publication_receipt"].update(
        {
            "approval_receipt_id": "private-publication-approval-1",
            "republished_commit_sha": "c" * 40,
            "republished_url": PAGES_URL,
            "republished_source_sha256": "b" * 64,
            "verification_receipt_id": "private-publication-verification-1",
        }
    )
    ledger["timing"].update(
        {
            "elapsed_minutes": 30,
            "maintainer_active_minutes": 20,
            "reviewer_active_minutes": 10,
        }
    )
    ledger["partner_burden_decision"].update(
        {
            "status": "complete",
            "acceptable": True,
            "partner_role": "Prospective pilot owner",
            "decided_on": "2026-08-04",
            "private_evidence_receipt_id": "private-burden-decision-1",
            "receipt_verified_on": "2026-08-05",
            "receipt_verified_by_code": "V01",
        }
    )
    return ledger


def test_completed_rehearsal_reconciles_actors_sets_timing_and_burden():
    ledger = _valid_rehearsal_fixture()
    assert derive_rehearsal_aggregate(ledger)["status"] == "complete"

    mutations = []
    wrong_actor = copy.deepcopy(ledger)
    wrong_actor["stages"][0]["actor_code"] = "UNRELATED"
    mutations.append(wrong_actor)

    unknown_disposition = copy.deepcopy(ledger)
    unknown_disposition["observed_impact"]["dispositions"][0]["disposition"] = (
        "looks_good"
    )
    mutations.append(unknown_disposition)

    duplicate_impact = copy.deepcopy(ledger)
    duplicate_impact["observed_impact"]["affected_requirement_ids"].append(
        duplicate_impact["observed_impact"]["affected_requirement_ids"][0]
    )
    mutations.append(duplicate_impact)

    hidden_defects = copy.deepcopy(ledger)
    hidden_defects["observed_impact"]["blocking_defects_found"] = 99
    mutations.append(hidden_defects)

    inaccurate_timing = copy.deepcopy(ledger)
    inaccurate_timing["timing"]["elapsed_minutes"] = 1
    mutations.append(inaccurate_timing)

    premature_burden = copy.deepcopy(ledger)
    premature_burden["partner_burden_decision"]["decided_on"] = "2026-08-03"
    mutations.append(premature_burden)

    for mutated in mutations:
        with pytest.raises(
            ValueError, match="completed rehearsal lacks required evidence"
        ):
            derive_rehearsal_aggregate(mutated)


def test_status_only_completed_rehearsal_stages_are_rejected():
    ledger = load_json(REHEARSAL_PATH)
    ledger["status"] = "complete"
    ledger["artifact_lock"].update(
        {
            "status": "complete",
            "baseline_commit_sha": "a" * 40,
            "baseline_deployed_url": PAGES_URL,
            "source_snapshot_receipt_id": "private-source-snapshot-1",
        }
    )
    ledger["simulation_contract"].update(
        {
            "simulated_changed_sha256": "b" * 64,
            "changed_fixture_receipt_id": "private-changed-fixture-1",
        }
    )
    ledger["publication_receipt"].update(
        {
            "approval_receipt_id": "superficial-approval-label",
            "republished_commit_sha": "c" * 40,
            "republished_url": PAGES_URL,
            "republished_source_sha256": "b" * 64,
            "verification_receipt_id": "superficial-verification-label",
        }
    )
    for stage in ledger["stages"]:
        stage["status"] = "complete"

    with pytest.raises(ValueError, match="completed rehearsal lacks required evidence"):
        derive_rehearsal_aggregate(ledger)


def test_gate_lock_requires_freeze_and_passing_dry_run_receipts():
    gate = load_json(GATE_PATH)
    gate["status"] = "complete"
    lock = gate["artifact_lock"]
    lock.update(
        {
            "status": "complete",
            "commit_sha": "a" * 40,
            "deployed_url": PAGES_URL,
        }
    )
    lock["internal_dry_run"].update(
        {
            "status": "complete",
            "run_on": "2026-08-03",
            "tester_code": "T01",
            "result": "pass",
        }
    )
    assert _valid_gate_lock(gate) is False

    lock.update(
        {
            "frozen_on": "2026-08-03",
            "frozen_by_code": "F01",
            "source_snapshot_receipt_id": "private-source-snapshot-1",
        }
    )
    lock["internal_dry_run"].update(
        {
            "artifact_lock_id": lock["lock_id"],
            "commit_sha": lock["commit_sha"],
            "deployed_url": lock["deployed_url"],
            "source_snapshot_id": lock["source_snapshot_id"],
            "source_snapshot_receipt_id": lock["source_snapshot_receipt_id"],
            "evidence_receipt_id": "private-dry-run-1",
        }
    )
    assert _valid_gate_lock(gate) is True

    lock["internal_dry_run"]["commit_sha"] = "b" * 40
    assert _valid_gate_lock(gate) is False
    lock["internal_dry_run"]["commit_sha"] = lock["commit_sha"]

    lock["internal_dry_run"]["run_on"] = "2026-08-02"
    assert _valid_gate_lock(gate) is False


def test_proceed_decision_requires_owner_date_and_receipt():
    gate = load_json(GATE_PATH)
    gate["status"] = "complete"
    gate["artifact_lock"]["commit_sha"] = "a" * 40
    gate["decision"].update(
        {
            "status": "complete",
            "recommendation": "proceed",
            "decided_on": "2026-08-31",
            "decision_owner_code": "D01",
            "tested_commit_sha": "a" * 40,
            "evaluated_on": "2026-08-30",
            "evaluation_receipt_id": "private-decision-receipt-1",
            "failure_reasons": [],
        }
    )
    evidence_latest_on = date(2026, 8, 30)
    assert _valid_proceed_decision(gate, evidence_latest_on) is True

    for field in ("decided_on", "decision_owner_code", "evaluation_receipt_id"):
        incomplete = copy.deepcopy(gate)
        incomplete["decision"][field] = None
        assert _valid_proceed_decision(incomplete, evidence_latest_on) is False

    assert _valid_proceed_decision(gate, date(2026, 8, 31)) is False


def test_decision_evidence_dates_follow_the_frozen_artifact():
    gate = load_json(GATE_PATH)
    gate["artifact_lock"]["frozen_on"] = "2026-08-03"
    gate["artifact_lock"]["internal_dry_run"]["run_on"] = "2026-08-03"
    gate["external_evidence"]["partner_gate"].update(
        {
            "written_on": "2026-08-04",
            "receipt_verified_on": "2026-08-05",
        }
    )
    content = {
        "artifact_lock": {"frozen_on": "2026-08-03"},
        "reviewer_slots": [
            {"reviewed_on": "2026-08-04"},
            {"reviewed_on": "2026-08-04"},
        ],
        "rows": [{"synthesis": {"resolution": {"resolved_on": "2026-08-04"}}}],
        "cross_cutting_checks": [
            {"synthesis": {"resolution": {"resolved_on": "2026-08-04"}}}
        ],
    }
    participants = _valid_participant_ledger_fixture()
    manual = {
        "privacy_protocol": {
            "reviewer": {"reviewed_on": "2026-08-04"},
            "signoff": {"signed_on": "2026-08-04"},
        },
        "manual_checks": [
            {
                "execution": {
                    "started_at": "2026-08-04T11:30:00Z",
                    "completed_at": "2026-08-04T12:00:00Z",
                },
                "reviewer": {"reviewed_on": "2026-08-04"},
                "signoff": {"signed_on": "2026-08-04"},
            }
        ],
        "spanish_semantic_reviews": [
            {
                "reviewed_on": "2026-08-04",
                "signoff": {"signed_on": "2026-08-04"},
            }
        ],
    }
    rehearsal = _valid_rehearsal_fixture()

    assert _latest_evidence_date(
        gate, content, participants, manual, rehearsal
    ) == date(2026, 8, 5)

    content["reviewer_slots"][0]["reviewed_on"] = "2026-08-02"
    assert _latest_evidence_date(gate, content, participants, manual, rehearsal) is None

    content["reviewer_slots"][0]["reviewed_on"] = "2026-08-04"
    manual["manual_checks"][0]["execution"]["started_at"] = "2026-08-02T11:30:00Z"
    assert _latest_evidence_date(gate, content, participants, manual, rehearsal) is None

    manual["manual_checks"][0]["execution"]["started_at"] = "2026-08-04T11:30:00Z"
    content["cross_cutting_checks"][0]["synthesis"]["resolution"]["resolved_on"] = (
        "2026-08-06"
    )
    assert _latest_evidence_date(
        gate, content, participants, manual, rehearsal
    ) == date(2026, 8, 6)


def test_recruitment_counts_reconcile_with_derived_evidence():
    gate = load_json(GATE_PATH)
    gate["recruitment"]["status"] = "complete"
    gate["recruitment"]["reviewers"].update(
        {
            "contacted": 4,
            "screened": 3,
            "qualified": 2,
            "scheduled": 2,
            "completed": 2,
            "withdrawn": 1,
            "excluded": 1,
        }
    )
    gate["recruitment"]["participants"].update(
        {
            "contacted": 9,
            "screened": 8,
            "qualified": 7,
            "scheduled": 6,
            "completed": 6,
            "withdrawn": 1,
            "excluded": 1,
            "technically_interrupted": 1,
        }
    )
    gate["recruitment"]["partners"].update(
        {
            "contacted": 3,
            "discovery_conversations_completed": 2,
            "qualifying_written_next_steps": 1,
        }
    )
    gate["external_evidence"]["partner_gate"]["qualifying_written_next_steps"] = 1
    content_aggregate = {"reviewers_completed": 2}
    participant_aggregate = {"sessions_completed": 6}

    assert _valid_recruitment_for_evidence(
        gate, content_aggregate, participant_aggregate
    )

    drift_cases = (
        ("reviewers", "completed", 1),
        ("participants", "completed", 5),
        ("partners", "qualifying_written_next_steps", 0),
    )
    for funnel, field, value in drift_cases:
        drifted = copy.deepcopy(gate)
        drifted["recruitment"][funnel][field] = value
        assert not _valid_recruitment_for_evidence(
            drifted, content_aggregate, participant_aggregate
        )

    assert not _valid_recruitment_for_evidence(gate, content_aggregate, None)
