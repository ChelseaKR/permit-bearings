from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

from permit_pathways.readiness import (
    ReadinessRemedies,
    ReadinessWorkflow,
    load_readiness_remedies,
    load_readiness_workflow,
)

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "data" / "validation" / "woodland-content-review.json"
WORKFLOW_PATH = (
    ROOT / "data" / "readiness" / "workflows" / "woodland-preapproved-detached-adu.json"
)
REMEDIES_PATH = (
    ROOT / "data" / "readiness" / "remedies" / "woodland-preapproved-detached-adu.json"
)
JOURNEY_PATH = (
    ROOT / "data" / "journeys" / "generated" / "woodland-preapproved-detached-adu.json"
)
EVIDENCE_PATH = (
    ROOT / "data" / "readiness" / "generated" / "woodland-preapproved-adu-evidence.json"
)
SOURCES_PATH = ROOT / "data" / "sources.json"
AS_OF = date(2026, 8, 11)
BASELINE_COMMIT = "9fd9595a8ca353d491513cd1652c3ab0b8210ab0"
EXECUTION_COMMIT = "a" * 40
DEPLOYED_URL = (
    "https://chelseakr.github.io/permit-pathways/"
    "prepare.html?journey=woodland-preapproved-detached-adu-synthetic&version=1.0.0"
)
FROZEN_ON = "2026-08-23"
REVIEWED_ON = "2026-08-24"

ROOT_KEYS = {
    "schema_version",
    "record_type",
    "status",
    "prepared_on",
    "baseline_provenance",
    "artifact_lock",
    "reviewer_slots",
    "thresholds",
    "scoring_key_version",
    "cross_cutting_checks",
    "rows",
    "gate",
}
CONTENT_BINDING_KEYS = {
    "workflow_id",
    "mapping_version",
    "workflow_fingerprint",
    "remedy_version",
    "remedy_content_fingerprint",
    "journey_id",
    "journey_version",
    "journey_fingerprint",
    "source_bindings",
}
BASELINE_KEYS = {"commit", "prepared_on", "content_bindings"}
LOCK_KEYS = {
    "status",
    "execution_commit",
    "deployed_url",
    "frozen_on",
    "freeze_owner_code",
    "content_bindings",
}
ROW_KEYS = {
    "requirement_id",
    "requirement_fingerprint",
    "draft_mapping",
    "draft_action",
    "reviewer_1",
    "reviewer_2",
    "synthesis",
}
MAPPING_KEYS = {
    "label",
    "category",
    "item_type",
    "parent_requirement_id",
    "applies_when",
    "source_id",
    "source_locator",
    "source_excerpt",
}
ROW_DECISION_KEYS = {
    "mapping_disposition",
    "action_disposition",
    "blocking_defect",
    "evidence_note",
    "proposed_mapping",
    "proposed_action",
}
CROSS_KEYS = {
    "check_id",
    "kind",
    "canonical_value",
    "reviewer_1",
    "reviewer_2",
    "synthesis",
}
CROSS_DECISION_KEYS = {
    "disposition",
    "blocking_defect",
    "evidence_note",
    "proposed_value",
}
SYNTHESIS_KEYS = {
    "initial_agreement",
    "final_disposition",
    "blocking_defect_remaining",
    "resolution",
}
RESOLUTION_KEYS = {
    "status",
    "method",
    "source_ids",
    "resolved_by",
    "resolved_on",
    "notes",
}
REVIEWER_SLOT_KEYS = {
    "reviewer_id",
    "required_qualification",
    "status",
    "reviewer",
    "qualification_summary",
    "method",
    "reviewed_on",
    "reviewed_execution_commit",
    "independence_attested",
}
GATE_KEYS = {
    "status",
    "reviewers_completed",
    "rows_completed",
    "cross_cutting_checks_completed",
    "initial_agreement_count",
    "disagreement_count",
    "known_blocking_content_defects",
    "all_disagreements_resolved",
    "eligible_for_applicant_testing",
}
MAPPING_DISPOSITIONS = {
    "supported",
    "changes_required",
    "blocked_by_source",
    "route_to_staff",
    "suppress",
}
ACTION_DISPOSITIONS = MAPPING_DISPOSITIONS
FINAL_DISPOSITIONS = {"retain", "revise", "route_to_staff", "suppress"}
RESOLUTION_METHODS = {
    "independent_agreement",
    "source_reconciliation",
    "safe_suppression",
    "staff_routing",
}
SHA = re.compile(r"^[0-9a-f]{40}$")
OWNER_CODE = re.compile(r"^[A-Z][A-Z0-9_-]{1,15}$")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _exact_keys(value: Any, expected: set[str], field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{field}: expected exact keys")
    return value


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected non-blank text")
    return value


def _iso_date(value: Any, field: str) -> date:
    text = _required_text(value, field)
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"{field}: expected ISO date") from error


@pytest.fixture(scope="module")
def workflow() -> ReadinessWorkflow:
    return load_readiness_workflow(WORKFLOW_PATH, SOURCES_PATH, today=AS_OF)


@pytest.fixture(scope="module")
def remedies(workflow: ReadinessWorkflow) -> ReadinessRemedies:
    return load_readiness_remedies(REMEDIES_PATH, workflow, today=AS_OF)


@pytest.fixture(scope="module")
def canonical_payload() -> dict[str, Any]:
    return _read_json(REVIEW_PATH)


def _canonical_bindings(
    workflow: ReadinessWorkflow,
    remedies: ReadinessRemedies,
) -> dict[str, Any]:
    journey = _read_json(JOURNEY_PATH)
    return {
        "workflow_id": workflow.workflow_id,
        "mapping_version": workflow.mapping_provenance.version,
        "workflow_fingerprint": workflow.fingerprint(),
        "remedy_version": remedies.version,
        "remedy_content_fingerprint": remedies.content_fingerprint,
        "journey_id": journey["journey_id"],
        "journey_version": journey["version"],
        "journey_fingerprint": journey["journey_fingerprint"],
        "source_bindings": [asdict(binding) for binding in workflow.source_bindings],
    }


def _validate_bindings(
    value: Any,
    workflow: ReadinessWorkflow,
    remedies: ReadinessRemedies,
    field: str,
) -> None:
    bindings = _exact_keys(value, CONTENT_BINDING_KEYS, field)
    if bindings != _canonical_bindings(workflow, remedies):
        raise ValueError(f"{field}: canonical content drifted")


def _validate_baseline(
    value: Any,
    workflow: ReadinessWorkflow,
    remedies: ReadinessRemedies,
) -> None:
    baseline = _exact_keys(value, BASELINE_KEYS, "baseline_provenance")
    if baseline["commit"] != BASELINE_COMMIT:
        raise ValueError("baseline_provenance.commit: provenance drifted")
    if baseline["prepared_on"] != "2026-08-22":
        raise ValueError("baseline_provenance.prepared_on: provenance drifted")
    _validate_bindings(
        baseline["content_bindings"],
        workflow,
        remedies,
        "baseline_provenance.content_bindings",
    )


def _validate_lock(
    value: Any,
    workflow: ReadinessWorkflow,
    remedies: ReadinessRemedies,
) -> dict[str, Any]:
    lock = _exact_keys(value, LOCK_KEYS, "artifact_lock")
    _validate_bindings(
        lock["content_bindings"],
        workflow,
        remedies,
        "artifact_lock.content_bindings",
    )
    identity = (
        lock["execution_commit"],
        lock["deployed_url"],
        lock["frozen_on"],
        lock["freeze_owner_code"],
    )
    if lock["status"] == "pending":
        if any(item is not None for item in identity):
            raise ValueError("artifact_lock: pending lock cannot carry freeze evidence")
        return lock
    if lock["status"] != "locked" or any(item is None for item in identity):
        raise ValueError("artifact_lock: expected pending or fully locked")
    if not SHA.fullmatch(lock["execution_commit"]):
        raise ValueError("artifact_lock.execution_commit: expected full SHA")
    deployed = urlsplit(lock["deployed_url"])
    if (
        deployed.scheme != "https"
        or deployed.netloc != "chelseakr.github.io"
        or not deployed.path.startswith("/permit-pathways/")
    ):
        raise ValueError("artifact_lock.deployed_url: unexpected deployment")
    if _iso_date(lock["frozen_on"], "artifact_lock.frozen_on") < AS_OF:
        raise ValueError("artifact_lock.frozen_on: predates prepared record")
    if not OWNER_CODE.fullmatch(lock["freeze_owner_code"]):
        raise ValueError("artifact_lock.freeze_owner_code: invalid owner code")
    return lock


def _blank_reviewer_slot(reviewer_id: str, qualification: str) -> dict[str, Any]:
    return {
        "reviewer_id": reviewer_id,
        "required_qualification": qualification,
        "status": "not_run",
        "reviewer": None,
        "qualification_summary": None,
        "method": None,
        "reviewed_on": None,
        "reviewed_execution_commit": None,
        "independence_attested": None,
    }


def _validate_completed_reviewer_slot(
    slot: dict[str, Any],
    qualification: str,
    field: str,
    lock: dict[str, Any],
) -> tuple[str, date]:
    if (
        slot["required_qualification"] != qualification
        or slot["status"] != "complete"
        or slot["reviewed_execution_commit"] != lock["execution_commit"]
        or slot["independence_attested"] is not True
    ):
        raise ValueError(f"{field}: incomplete or mismatched review receipt")
    for key in ("reviewer", "qualification_summary", "method"):
        _required_text(slot[key], f"{field}.{key}")
    reviewed_on = _iso_date(slot["reviewed_on"], f"{field}.reviewed_on")
    if reviewed_on < _iso_date(lock["frozen_on"], "artifact_lock.frozen_on"):
        raise ValueError(f"{field}.reviewed_on: predates artifact freeze")
    return slot["reviewer"].strip().casefold(), reviewed_on


def _validate_reviewer_slots(
    value: Any,
    *,
    complete: bool,
    lock: dict[str, Any],
) -> date | None:
    qualifications = {
        "R1": "Woodland checklist or permit-intake workflow knowledge",
        "R2": "California ADU design, intake, or packet-preparation experience",
    }
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("reviewer_slots: expected two slots")
    reviewer_names: list[str] = []
    reviewed_dates: list[date] = []
    for index, raw_slot in enumerate(value):
        field = f"reviewer_slots[{index}]"
        slot = _exact_keys(raw_slot, REVIEWER_SLOT_KEYS, field)
        reviewer_id = slot["reviewer_id"]
        qualification = qualifications.get(reviewer_id)
        if qualification is None:
            raise ValueError(f"{field}.reviewer_id: unexpected reviewer slot")
        if not complete:
            if slot != _blank_reviewer_slot(reviewer_id, qualification):
                raise ValueError(f"{field}: unexecuted slot must remain blank")
            continue
        reviewer_name, reviewed_on = _validate_completed_reviewer_slot(
            slot, qualification, field, lock
        )
        reviewer_names.append(reviewer_name)
        reviewed_dates.append(reviewed_on)
    if [slot["reviewer_id"] for slot in value] != ["R1", "R2"]:
        raise ValueError("reviewer_slots: expected R1 then R2")
    if complete and len(set(reviewer_names)) != 2:
        raise ValueError("reviewer_slots: independent reviewers must be distinct")
    return max(reviewed_dates) if reviewed_dates else None


def _validate_resolution_sequence(
    record: dict[str, Any], reviewed_through: date | None
) -> None:
    if reviewed_through is None:
        return
    reviewed_items = [*record["rows"], *record["cross_cutting_checks"]]
    for index, item in enumerate(reviewed_items):
        resolved_on = _iso_date(
            item["synthesis"]["resolution"]["resolved_on"],
            f"completed_items[{index}].resolution.resolved_on",
        )
        if resolved_on < reviewed_through:
            raise ValueError(
                "completed_items: reconciliation predates reviewer receipt"
            )


def _expected_mapping(requirement: Any) -> dict[str, Any]:
    return {
        "label": requirement.label,
        "category": requirement.category,
        "item_type": requirement.item_type,
        "parent_requirement_id": requirement.parent_requirement_id,
        "applies_when": [asdict(condition) for condition in requirement.applies_when],
        "source_id": requirement.source_id,
        "source_locator": requirement.source_locator,
        "source_excerpt": requirement.source_excerpt,
    }


def _validate_proposed_mapping(value: Any, field: str) -> None:
    mapping = _exact_keys(value, MAPPING_KEYS, field)
    for key in (
        "label",
        "category",
        "item_type",
        "source_id",
        "source_locator",
        "source_excerpt",
    ):
        _required_text(mapping[key], f"{field}.{key}")
    if mapping["parent_requirement_id"] is not None:
        _required_text(
            mapping["parent_requirement_id"], f"{field}.parent_requirement_id"
        )
    if not isinstance(mapping["applies_when"], list):
        raise ValueError(f"{field}.applies_when: expected list")


def _validate_row_decision(value: Any, field: str) -> tuple[str, str, str]:
    decision = _exact_keys(value, ROW_DECISION_KEYS, field)
    mapping_disposition = decision["mapping_disposition"]
    action_disposition = decision["action_disposition"]
    if mapping_disposition not in MAPPING_DISPOSITIONS:
        raise ValueError(f"{field}.mapping_disposition: unsupported value")
    if action_disposition not in ACTION_DISPOSITIONS:
        raise ValueError(f"{field}.action_disposition: unsupported value")
    if decision["blocking_defect"] not in {"none", "blocking"}:
        raise ValueError(f"{field}.blocking_defect: unsupported value")
    _required_text(decision["evidence_note"], f"{field}.evidence_note")
    if mapping_disposition == "changes_required":
        _validate_proposed_mapping(
            decision["proposed_mapping"], f"{field}.proposed_mapping"
        )
    elif decision["proposed_mapping"] is not None:
        raise ValueError(f"{field}.proposed_mapping: only valid for changes_required")
    if action_disposition == "changes_required":
        _required_text(decision["proposed_action"], f"{field}.proposed_action")
    elif decision["proposed_action"] is not None:
        raise ValueError(f"{field}.proposed_action: only valid for changes_required")
    return mapping_disposition, action_disposition, decision["blocking_defect"]


def _validate_cross_decision(value: Any, field: str) -> tuple[str, str]:
    decision = _exact_keys(value, CROSS_DECISION_KEYS, field)
    if decision["disposition"] not in MAPPING_DISPOSITIONS:
        raise ValueError(f"{field}.disposition: unsupported value")
    if decision["blocking_defect"] not in {"none", "blocking"}:
        raise ValueError(f"{field}.blocking_defect: unsupported value")
    _required_text(decision["evidence_note"], f"{field}.evidence_note")
    if decision["disposition"] == "changes_required":
        if decision["proposed_value"] is None:
            raise ValueError(f"{field}.proposed_value: required for changes_required")
    elif decision["proposed_value"] is not None:
        raise ValueError(f"{field}.proposed_value: only valid for changes_required")
    return decision["disposition"], decision["blocking_defect"]


def _validate_resolution(
    value: Any,
    *,
    lock: dict[str, Any],
    source_ids: set[str],
    field: str,
) -> None:
    resolution = _exact_keys(value, RESOLUTION_KEYS, field)
    if resolution["status"] != "resolved":
        raise ValueError(f"{field}.status: completed synthesis must be resolved")
    if resolution["method"] not in RESOLUTION_METHODS:
        raise ValueError(f"{field}.method: unsupported value")
    evidence_sources = resolution["source_ids"]
    if (
        not isinstance(evidence_sources, list)
        or not evidence_sources
        or len(evidence_sources) != len(set(evidence_sources))
        or not set(evidence_sources).issubset(source_ids)
    ):
        raise ValueError(f"{field}.source_ids: expected known source evidence")
    if not OWNER_CODE.fullmatch(
        _required_text(resolution["resolved_by"], f"{field}.resolved_by")
    ):
        raise ValueError(f"{field}.resolved_by: invalid owner code")
    resolved_on = _iso_date(resolution["resolved_on"], f"{field}.resolved_on")
    if resolved_on < _iso_date(lock["frozen_on"], "artifact_lock.frozen_on"):
        raise ValueError(f"{field}.resolved_on: predates artifact freeze")
    _required_text(resolution["notes"], f"{field}.notes")


def _validate_synthesis(
    value: Any,
    *,
    expected_agreement: bool,
    lock: dict[str, Any],
    source_ids: set[str],
    field: str,
) -> tuple[bool, bool]:
    synthesis = _exact_keys(value, SYNTHESIS_KEYS, field)
    if synthesis["initial_agreement"] is not expected_agreement:
        raise ValueError(
            f"{field}.initial_agreement: does not match reviewer decisions"
        )
    if synthesis["final_disposition"] not in FINAL_DISPOSITIONS:
        raise ValueError(f"{field}.final_disposition: unsupported value")
    remaining = synthesis["blocking_defect_remaining"]
    if not isinstance(remaining, bool):
        raise ValueError(f"{field}.blocking_defect_remaining: expected boolean")
    if synthesis["final_disposition"] == "revise" and remaining is not True:
        raise ValueError(f"{field}: an unapplied revision remains blocking")
    _validate_resolution(
        synthesis["resolution"],
        lock=lock,
        source_ids=source_ids,
        field=f"{field}.resolution",
    )
    return expected_agreement, remaining


def _validate_rows(
    value: Any,
    workflow: ReadinessWorkflow,
    remedies: ReadinessRemedies,
    *,
    complete: bool,
    lock: dict[str, Any],
    source_ids: set[str],
) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != len(workflow.requirements) != 25:
        raise ValueError("rows: expected all 25 canonical requirements")
    actions = remedies.entry_map()
    agreements = 0
    blockers = 0
    for index, (raw_row, requirement) in enumerate(
        zip(value, workflow.requirements, strict=True)
    ):
        field = f"rows[{index}]"
        row = _exact_keys(raw_row, ROW_KEYS, field)
        _exact_keys(row["draft_mapping"], MAPPING_KEYS, f"{field}.draft_mapping")
        if row["requirement_id"] != requirement.requirement_id:
            raise ValueError(f"{field}: requirement order or coverage drifted")
        if row["requirement_fingerprint"] != requirement.fingerprint():
            raise ValueError(f"{field}: requirement fingerprint drifted")
        if row["draft_mapping"] != _expected_mapping(requirement):
            raise ValueError(f"{field}: canonical mapping drifted")
        if row["draft_action"] != actions[requirement.requirement_id].action:
            raise ValueError(f"{field}: canonical action drifted")
        if not complete:
            if any(
                row[key] is not None
                for key in ("reviewer_1", "reviewer_2", "synthesis")
            ):
                raise ValueError(f"{field}: unexecuted outcomes must remain null")
            continue
        first = _validate_row_decision(row["reviewer_1"], f"{field}.reviewer_1")
        second = _validate_row_decision(row["reviewer_2"], f"{field}.reviewer_2")
        agreed, remaining = _validate_synthesis(
            row["synthesis"],
            expected_agreement=first[:2] == second[:2],
            lock=lock,
            source_ids=source_ids,
            field=f"{field}.synthesis",
        )
        agreements += int(agreed)
        blockers += int(remaining)
    return agreements, blockers


def _expected_cross_checks(workflow: ReadinessWorkflow) -> list[tuple[str, str, Any]]:
    facts = workflow.fact_map()
    expected: list[tuple[str, str, Any]] = [
        (
            "applicability-gate",
            "applicability_conditions",
            [asdict(condition) for condition in workflow.applicability],
        )
    ]
    for check_id, fact_id in zip(
        ("parcel-city-field-binding", "parcel-land-use-field-binding"),
        ("parcel_city_matches_woodland", "parcel_land_use_is_residential"),
        strict=True,
    ):
        fact = facts[fact_id]
        expected.append(
            (
                check_id,
                "fact_binding",
                {
                    "fact_id": fact.fact_id,
                    "source_id": fact.source_id,
                    "source_field": fact.source_field,
                    "allowed_values": list(fact.allowed_values),
                },
            )
        )
    expected.extend(
        [
            (
                "unknown-fails-closed",
                "behavioral_invariant",
                {
                    "fact_ids": [
                        condition.fact_id for condition in workflow.applicability
                    ],
                    "expected_behavior": "unknown_blocks_transition_and_routes_to_staff",
                },
            ),
            (
                "prototype-boundary",
                "claim_boundary",
                _read_json(EVIDENCE_PATH)["boundary"],
            ),
        ]
    )
    return expected


def _validate_cross_checks(
    value: Any,
    workflow: ReadinessWorkflow,
    *,
    complete: bool,
    lock: dict[str, Any],
    source_ids: set[str],
) -> int:
    expected = _expected_cross_checks(workflow)
    if not isinstance(value, list) or len(value) != len(expected):
        raise ValueError("cross_cutting_checks: expected complete canonical coverage")
    blockers = 0
    for index, (raw_check, canonical) in enumerate(zip(value, expected, strict=True)):
        field = f"cross_cutting_checks[{index}]"
        check = _exact_keys(raw_check, CROSS_KEYS, field)
        actual = (check["check_id"], check["kind"], check["canonical_value"])
        if actual != canonical:
            raise ValueError(f"{field}: canonical check drifted")
        if not complete:
            if any(
                check[key] is not None
                for key in ("reviewer_1", "reviewer_2", "synthesis")
            ):
                raise ValueError(f"{field}: unexecuted outcomes must remain null")
            continue
        first = _validate_cross_decision(check["reviewer_1"], f"{field}.reviewer_1")
        second = _validate_cross_decision(check["reviewer_2"], f"{field}.reviewer_2")
        _agreed, remaining = _validate_synthesis(
            check["synthesis"],
            expected_agreement=first[0] == second[0],
            lock=lock,
            source_ids=source_ids,
            field=f"{field}.synthesis",
        )
        blockers += int(remaining)
    return blockers


def _blank_gate() -> dict[str, Any]:
    return {
        "status": "not_run",
        "reviewers_completed": 0,
        "rows_completed": 0,
        "cross_cutting_checks_completed": 0,
        "initial_agreement_count": None,
        "disagreement_count": None,
        "known_blocking_content_defects": None,
        "all_disagreements_resolved": None,
        "eligible_for_applicant_testing": None,
    }


def _validate_gate(
    value: Any,
    *,
    complete: bool,
    agreements: int,
    blockers: int,
    thresholds: dict[str, Any],
) -> None:
    gate = _exact_keys(value, GATE_KEYS, "gate")
    if not complete:
        if gate != _blank_gate():
            raise ValueError(
                "gate: unexecuted gate must retain zero completion and null outcomes"
            )
        return
    eligible = (
        agreements >= thresholds["initial_agreement_minimum"]
        and blockers <= thresholds["known_blocking_content_defects_maximum"]
    )
    expected = {
        "status": "passed" if eligible else "failed",
        "reviewers_completed": 2,
        "rows_completed": 25,
        "cross_cutting_checks_completed": 5,
        "initial_agreement_count": agreements,
        "disagreement_count": 25 - agreements,
        "known_blocking_content_defects": blockers,
        "all_disagreements_resolved": True,
        "eligible_for_applicant_testing": eligible,
    }
    if gate != expected:
        raise ValueError("gate: counts or outcome do not match completed evidence")


def _validate_manifest(
    payload: Any,
    workflow: ReadinessWorkflow,
    remedies: ReadinessRemedies,
) -> None:
    record = _exact_keys(payload, ROOT_KEYS, "record")
    if {
        "schema_version": record["schema_version"],
        "record_type": record["record_type"],
        "prepared_on": record["prepared_on"],
        "scoring_key_version": record["scoring_key_version"],
    } != {
        "schema_version": 2,
        "record_type": "woodland_content_review_evidence",
        "prepared_on": "2026-08-22",
        "scoring_key_version": "1.0.0",
    }:
        raise ValueError("record: unsupported header")
    state = record["status"]
    if state not in {"prepared_not_executed", "locked_not_executed", "review_complete"}:
        raise ValueError("record.status: unsupported transition")
    _validate_baseline(record["baseline_provenance"], workflow, remedies)
    lock = _validate_lock(record["artifact_lock"], workflow, remedies)
    if (state == "prepared_not_executed") != (lock["status"] == "pending"):
        raise ValueError("record.status: does not match artifact lock")
    if state != "prepared_not_executed" and lock["status"] != "locked":
        raise ValueError("record.status: execution requires a locked artifact")
    thresholds = record["thresholds"]
    if thresholds != {
        "independent_reviewers_required": 2,
        "requirements_total": 25,
        "initial_agreement_minimum": 22,
        "known_blocking_content_defects_maximum": 0,
        "resolve_every_disagreement_before_applicant_testing": True,
    }:
        raise ValueError("thresholds: gate contract drifted")
    complete = state == "review_complete"
    reviewed_through = _validate_reviewer_slots(
        record["reviewer_slots"], complete=complete, lock=lock
    )
    source_ids = {
        source["source_id"] for source in lock["content_bindings"]["source_bindings"]
    }
    agreements, row_blockers = _validate_rows(
        record["rows"],
        workflow,
        remedies,
        complete=complete,
        lock=lock,
        source_ids=source_ids,
    )
    cross_blockers = _validate_cross_checks(
        record["cross_cutting_checks"],
        workflow,
        complete=complete,
        lock=lock,
        source_ids=source_ids,
    )
    _validate_resolution_sequence(record, reviewed_through)
    _validate_gate(
        record["gate"],
        complete=complete,
        agreements=agreements,
        blockers=row_blockers + cross_blockers,
        thresholds=thresholds,
    )


def _lock_payload(payload: dict[str, Any]) -> None:
    payload["status"] = "locked_not_executed"
    payload["artifact_lock"].update(
        {
            "status": "locked",
            "execution_commit": EXECUTION_COMMIT,
            "deployed_url": DEPLOYED_URL,
            "frozen_on": FROZEN_ON,
            "freeze_owner_code": "M01",
        }
    )


def _resolution(
    source_ids: list[str], method: str = "independent_agreement"
) -> dict[str, Any]:
    return {
        "status": "resolved",
        "method": method,
        "source_ids": source_ids,
        "resolved_by": "M01",
        "resolved_on": REVIEWED_ON,
        "notes": "Disposition recorded against the locked source snapshot.",
    }


def _supported_row_decision() -> dict[str, Any]:
    return {
        "mapping_disposition": "supported",
        "action_disposition": "supported",
        "blocking_defect": "none",
        "evidence_note": "Compared the mapping and action with the locked source passage.",
        "proposed_mapping": None,
        "proposed_action": None,
    }


def _supported_cross_decision() -> dict[str, Any]:
    return {
        "disposition": "supported",
        "blocking_defect": "none",
        "evidence_note": "Compared the cross-cutting contract with the locked evidence.",
        "proposed_value": None,
    }


def _complete_payload(payload: dict[str, Any], *, failing: bool = False) -> None:
    _lock_payload(payload)
    payload["status"] = "review_complete"
    for index, slot in enumerate(payload["reviewer_slots"], start=1):
        slot.update(
            {
                "status": "complete",
                "reviewer": f"Named reviewer {index}",
                "qualification_summary": "Required domain experience confirmed.",
                "method": "Independent comparison with the locked official sources.",
                "reviewed_on": REVIEWED_ON,
                "reviewed_execution_commit": EXECUTION_COMMIT,
                "independence_attested": True,
            }
        )
    source_ids = ["woodland-preapproved-adu-checklist"]
    for row in payload["rows"]:
        row["reviewer_1"] = _supported_row_decision()
        row["reviewer_2"] = _supported_row_decision()
        row["synthesis"] = {
            "initial_agreement": True,
            "final_disposition": "retain",
            "blocking_defect_remaining": False,
            "resolution": _resolution(source_ids),
        }
    for check in payload["cross_cutting_checks"]:
        check["reviewer_1"] = _supported_cross_decision()
        check["reviewer_2"] = _supported_cross_decision()
        check["synthesis"] = {
            "initial_agreement": True,
            "final_disposition": "retain",
            "blocking_defect_remaining": False,
            "resolution": _resolution(
                [
                    "woodland-preapproved-adu-checklist",
                    "yolo-public-parcels-layer",
                ]
            ),
        }
    agreements = 25
    blockers = 0
    if failing:
        first = payload["rows"][0]
        first["reviewer_1"] = {
            **_supported_row_decision(),
            "mapping_disposition": "changes_required",
            "blocking_defect": "blocking",
            "proposed_mapping": {
                **first["draft_mapping"],
                "label": "Revised source-bound label",
            },
        }
        first["synthesis"] = {
            "initial_agreement": False,
            "final_disposition": "revise",
            "blocking_defect_remaining": True,
            "resolution": _resolution(source_ids, "source_reconciliation"),
        }
        agreements = 24
        blockers = 1
    eligible = agreements >= 22 and blockers == 0
    payload["gate"] = {
        "status": "passed" if eligible else "failed",
        "reviewers_completed": 2,
        "rows_completed": 25,
        "cross_cutting_checks_completed": 5,
        "initial_agreement_count": agreements,
        "disagreement_count": 25 - agreements,
        "known_blocking_content_defects": blockers,
        "all_disagreements_resolved": True,
        "eligible_for_applicant_testing": eligible,
    }


def test_prepared_record_is_canonical_and_has_no_outcomes(
    canonical_payload: dict[str, Any],
    workflow: ReadinessWorkflow,
    remedies: ReadinessRemedies,
) -> None:
    _validate_manifest(canonical_payload, workflow, remedies)


def test_locked_unexecuted_transition_is_valid(
    canonical_payload: dict[str, Any],
    workflow: ReadinessWorkflow,
    remedies: ReadinessRemedies,
) -> None:
    locked = copy.deepcopy(canonical_payload)
    _lock_payload(locked)

    _validate_manifest(locked, workflow, remedies)


@pytest.mark.parametrize("failing", [False, True])
def test_complete_review_receipt_can_represent_pass_or_failure(
    failing: bool,
    canonical_payload: dict[str, Any],
    workflow: ReadinessWorkflow,
    remedies: ReadinessRemedies,
) -> None:
    completed = copy.deepcopy(canonical_payload)
    _complete_payload(completed, failing=failing)

    _validate_manifest(completed, workflow, remedies)


def _partial_lock(payload: dict[str, Any]) -> None:
    payload["status"] = "locked_not_executed"
    payload["artifact_lock"]["status"] = "locked"


def _promote_without_review(payload: dict[str, Any]) -> None:
    _lock_payload(payload)
    payload["status"] = "review_complete"


def _drift_artifact_binding(payload: dict[str, Any]) -> None:
    payload["artifact_lock"]["content_bindings"]["workflow_fingerprint"] = (
        "sha256:" + "0" * 64
    )


def _mismatch_reviewer_commit(payload: dict[str, Any]) -> None:
    _complete_payload(payload)
    payload["reviewer_slots"][0]["reviewed_execution_commit"] = "b" * 40


def _duplicate_reviewer_identity(payload: dict[str, Any]) -> None:
    _complete_payload(payload)
    payload["reviewer_slots"][1]["reviewer"] = payload["reviewer_slots"][0]["reviewer"]


def _reconcile_before_review(payload: dict[str, Any]) -> None:
    _complete_payload(payload)
    payload["reviewer_slots"][0]["reviewed_on"] = "2026-08-05"


def _remove_completed_row_decision(payload: dict[str, Any]) -> None:
    _complete_payload(payload)
    payload["rows"][0]["reviewer_1"] = None


def _unsupported_disposition(payload: dict[str, Any]) -> None:
    _complete_payload(payload)
    payload["rows"][0]["reviewer_1"]["mapping_disposition"] = "approved"


def _missing_proposed_mapping(payload: dict[str, Any]) -> None:
    _complete_payload(payload)
    payload["rows"][0]["reviewer_1"]["mapping_disposition"] = "changes_required"


def _mismatch_synthesized_agreement(payload: dict[str, Any]) -> None:
    _complete_payload(payload)
    payload["rows"][0]["synthesis"]["initial_agreement"] = False


def _unknown_resolution_source(payload: dict[str, Any]) -> None:
    _complete_payload(payload)
    payload["rows"][0]["synthesis"]["resolution"]["source_ids"] = ["unknown-source"]


def _incorrect_gate_count(payload: dict[str, Any]) -> None:
    _complete_payload(payload)
    payload["gate"]["initial_agreement_count"] = 24


def _claim_prepared_completion(payload: dict[str, Any]) -> None:
    payload["gate"]["reviewers_completed"] = 1


@pytest.mark.parametrize(
    "mutation",
    [
        _partial_lock,
        _promote_without_review,
        _drift_artifact_binding,
        _mismatch_reviewer_commit,
        _duplicate_reviewer_identity,
        _reconcile_before_review,
        _remove_completed_row_decision,
        _unsupported_disposition,
        _missing_proposed_mapping,
        _mismatch_synthesized_agreement,
        _unknown_resolution_source,
        _incorrect_gate_count,
        _claim_prepared_completion,
    ],
)
def test_validator_rejects_partial_locks_reviews_and_promotions(
    mutation: Callable[[dict[str, Any]], None],
    canonical_payload: dict[str, Any],
    workflow: ReadinessWorkflow,
    remedies: ReadinessRemedies,
) -> None:
    changed = copy.deepcopy(canonical_payload)
    mutation(changed)

    with pytest.raises(ValueError):
        _validate_manifest(changed, workflow, remedies)
