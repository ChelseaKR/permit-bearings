from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "data" / "validation" / "woodland-flagship-gate.json"
CONTENT_REVIEW_PATH = ROOT / "data" / "validation" / "woodland-content-review.json"
MANUAL_EVIDENCE_PATH = ROOT / "data" / "validation" / "woodland-manual-evidence.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def walk_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(walk_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(walk_keys(item) for item in value))
    return set()


def numeric_values(value: Any) -> list[int | float]:
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [value]
    if isinstance(value, dict):
        return [number for item in value.values() for number in numeric_values(item)]
    if isinstance(value, list):
        return [number for item in value for number in numeric_values(item)]
    return []


def test_gate_records_an_honest_not_run_external_state():
    gate = load_json(GATE_PATH)

    assert gate["schema_version"] == 1
    assert gate["status"] == "pending"
    assert gate["prepared_on"] == "2026-08-09"
    assert "not evidence of outreach" in gate["claim_boundary"]

    lock = gate["artifact_lock"]
    assert lock["status"] == "not_run"
    for field in (
        "commit_sha",
        "deployed_url",
        "frozen_on",
        "frozen_by_code",
    ):
        assert lock[field] is None
    assert lock["internal_dry_run"] == {
        "status": "not_run",
        "artifact_lock_id": None,
        "commit_sha": None,
        "deployed_url": None,
        "source_snapshot_id": None,
        "source_snapshot_receipt_id": None,
        "run_on": None,
        "tester_code": None,
        "result": None,
        "evidence_receipt_id": None,
    }

    assert gate["recruitment"]["status"] == "pending"
    assert set(numeric_values(gate["recruitment"])) == {0}

    evidence = gate["external_evidence"]
    assert {name: record["status"] for name, record in evidence.items()} == {
        "content_authority_review": "not_run",
        "participant_sessions": "not_run",
        "manual_accessibility": "not_run",
        "spanish_semantic_review": "not_run",
        "spanish_usability": "not_run",
        "partner_gate": "pending",
        "source_change_rehearsal": "not_run",
    }
    assert evidence["content_authority_review"]["reviewers_completed"] == 0
    assert evidence["content_authority_review"]["initial_agreement_count"] is None
    assert evidence["participant_sessions"]["sessions_completed"] == 0
    assert evidence["participant_sessions"]["candidate_guidance_correct_count"] is None
    assert evidence["manual_accessibility"]["checks_completed"] == 0
    assert evidence["spanish_semantic_review"]["records_reviewed"] == 0
    assert evidence["spanish_usability"]["checks_completed"] == 0
    assert evidence["partner_gate"]["qualifying_written_next_steps"] == 0
    assert evidence["partner_gate"]["private_evidence_receipt_id"] is None
    assert evidence["source_change_rehearsal"]["stages_completed"] == 0
    assert evidence["source_change_rehearsal"]["rehearsals_completed"] == 0

    decision = gate["decision"]
    assert decision["status"] == "pending"
    assert decision["recommendation"] is None
    assert decision["decided_on"] is None
    assert decision["tested_commit_sha"] is None
    assert decision["permitted_recommendations"] == [
        "proceed",
        "extend",
        "pivot",
        "stop",
    ]
    assert "have not been completed" in decision["bounded_public_claim"]


def test_gate_lock_is_bound_to_generated_journey_and_packet_evidence():
    gate = load_json(GATE_PATH)
    lock = gate["artifact_lock"]
    journey = load_json(
        ROOT
        / "data"
        / "journeys"
        / "generated"
        / "woodland-preapproved-detached-adu.json"
    )
    readiness = load_json(
        ROOT
        / "data"
        / "readiness"
        / "generated"
        / "woodland-preapproved-adu-evidence.json"
    )

    for field in (
        "journey_id",
        "journey_fingerprint",
        "fact_envelope_fingerprint",
        "screening_case_id",
        "screening_case_fingerprint",
        "readiness_workflow_id",
        "readiness_workflow_fingerprint",
        "readiness_packet_id",
        "readiness_packet_fingerprint",
    ):
        assert lock[field] == journey[field]
    assert lock["journey_version"] == journey["version"]
    assert lock["readiness_workflow_id"] == readiness["workflow_id"]
    assert lock["readiness_workflow_fingerprint"] == readiness["workflow_fingerprint"]
    assert lock["readiness_packet_id"] == readiness["packet_id"]
    assert lock["readiness_packet_fingerprint"] == readiness["packet_fingerprint"]
    assert lock["sample_urls"] == {
        "landing": "index.html",
        "journey_start": "check.html?sample=adu",
        "packet_result": (
            "prepare.html?journey=woodland-preapproved-detached-adu-synthetic"
            "&version=1.0.0"
        ),
    }


def test_gate_source_snapshot_matches_canonical_source_records():
    gate = load_json(GATE_PATH)
    sources = load_json(ROOT / "data" / "sources.json")
    sources_by_id = {record["source_id"]: record for record in sources.values()}
    snapshot = gate["artifact_lock"]["source_snapshot"]

    assert {record["source_id"] for record in snapshot} == {
        "ca-gov-66317",
        "hcd-adu-handbook-2026-03",
        "woodland-preapproved-adu-checklist",
        "yolo-public-parcels-layer",
    }
    for record in snapshot:
        canonical = sources_by_id[record["source_id"]]
        assert record["sha256"] == canonical["sha256"]
        assert record["recorded_on"] == canonical["fetched_on"]


def test_answer_key_matches_the_generated_frozen_candidate():
    gate = load_json(GATE_PATH)
    answer = gate["answer_key"]
    journey = load_json(
        ROOT
        / "data"
        / "journeys"
        / "generated"
        / "woodland-preapproved-detached-adu.json"
    )
    readiness = load_json(
        ROOT
        / "data"
        / "readiness"
        / "generated"
        / "woodland-preapproved-adu-evidence.json"
    )

    assert (
        answer["candidate_route_rule_id"] == journey["candidate_routes"][0]["rule_id"]
    )
    assert (
        answer["official_route_citation"]
        == journey["candidate_routes"][0]["citation"]["source"]
    )
    assert answer["route_source_status"] == journey["route_source_status"]
    assert answer["route_source_status_as_of"] == journey["route_source_status_as_of"]
    assert (
        answer["unknown_applicability_fact_id"]
        in journey["editable_applicability_fact_ids"]
    )
    unknown_fact = next(
        fact
        for fact in journey["applicability_facts"]
        if fact["fact_id"] == answer["unknown_applicability_fact_id"]
    )
    assert answer["unknown_staff_question"] == unknown_fact["question"]

    findings = readiness["findings"]
    assert set(answer["reported_missing_requirement_ids"]) == {
        finding["requirement_id"]
        for finding in findings
        if finding["status"] == "missing"
    }
    assert set(answer["needs_confirmation_requirement_ids"]) == {
        finding["requirement_id"]
        for finding in findings
        if finding["status"] == "needs_staff_review"
    }
    assert answer["staff_questions"] == readiness["staff_questions"]
    assert set(answer["reported_present_is_not"]) == {
        "correct",
        "compliant",
        "complete",
        "accepted",
        "approved",
    }


def test_gate_thresholds_encode_the_flagship_decision_rules():
    thresholds = load_json(GATE_PATH)["thresholds"]

    assert thresholds["content_authority"] == {
        "independent_reviewers_required": 2,
        "requirements_reviewed_per_reviewer": 25,
        "minimum_initial_agreement": 22,
        "known_blocking_content_defects_allowed": 0,
        "all_disagreements_must_be_resolved": True,
    }
    assert thresholds["cohort"] == {
        "sessions_required": 6,
        "minimum_primary_beneficiaries": 3,
        "minimum_primary_with_recent_attempt": 2,
        "minimum_primary_with_preapproved_plan_exposure": 1,
        "minimum_practitioners": 2,
        "minimum_with_small_jurisdiction_experience": 1,
        "single_frozen_version_required": True,
    }
    assert thresholds["problem_evidence"] == {
        "minimum_participants_with_specific_recent_pain": 3,
        "minimum_primary_beneficiaries_with_specific_recent_pain": 2,
        "minimum_domain_participants_reporting_monthly_recurrence": 1,
    }
    assert thresholds["trust_and_task"] == {
        "minimum_candidate_guidance_correct": 5,
        "minimum_source_and_unknown_escalation_correct": 5,
        "minimum_packet_and_next_action_correct": 5,
        "denominator": 6,
        "maximum_median_route_seconds": 300,
        "maximum_median_packet_seconds": 360,
        "maximum_repeated_navigation_blocker_sessions": 1,
        "confident_critical_errors_allowed": 0,
    }
    assert thresholds["partner"]["qualifying_written_next_steps_required"] == 1
    assert thresholds["partner"]["owner_role_required"] is True
    assert thresholds["partner"]["date_required"] is True
    assert thresholds["maintainability"] == {
        "completed_source_change_rehearsals_required": 1,
        "named_human_owner_required": True,
        "acceptable_burden_is_partner_decision": True,
    }


def test_specialized_ledgers_share_the_gate_lock_and_pending_state():
    gate = load_json(GATE_PATH)
    gate_lock = gate["artifact_lock"]
    content = load_json(CONTENT_REVIEW_PATH)
    content_lock = content["artifact_lock"]
    content_bindings = content_lock["content_bindings"]
    manual = load_json(MANUAL_EVIDENCE_PATH)
    manual_lock = manual["artifact_lock"]

    shared_lock_fields = (
        "journey_id",
        "journey_version",
        "journey_fingerprint",
        "readiness_workflow_id",
        "readiness_workflow_fingerprint",
    )
    for field in shared_lock_fields:
        assert manual_lock[field] == gate_lock[field]

    assert content_bindings["journey_id"] == gate_lock["journey_id"]
    assert content_bindings["journey_version"] == gate_lock["journey_version"]
    assert content_bindings["journey_fingerprint"] == gate_lock["journey_fingerprint"]
    assert content_bindings["workflow_id"] == gate_lock["readiness_workflow_id"]
    assert (
        content_bindings["workflow_fingerprint"]
        == gate_lock["readiness_workflow_fingerprint"]
    )
    assert manual_lock["screening_case_id"] == gate_lock["screening_case_id"]
    assert (
        manual_lock["screening_case_fingerprint"]
        == gate_lock["screening_case_fingerprint"]
    )
    assert (
        manual_lock["fact_envelope_fingerprint"]
        == gate_lock["fact_envelope_fingerprint"]
    )
    assert manual_lock["readiness_packet_id"] == gate_lock["readiness_packet_id"]
    assert (
        manual_lock["readiness_packet_fingerprint"]
        == gate_lock["readiness_packet_fingerprint"]
    )
    assert manual_lock["sample_entry_path"] == gate_lock["sample_urls"]["journey_start"]
    assert (
        manual_lock["valid_journey_path"] == gate_lock["sample_urls"]["packet_result"]
    )

    content_thresholds = content["thresholds"]
    gate_thresholds = gate["thresholds"]["content_authority"]
    assert content_thresholds == {
        "independent_reviewers_required": gate_thresholds[
            "independent_reviewers_required"
        ],
        "requirements_total": gate_thresholds["requirements_reviewed_per_reviewer"],
        "initial_agreement_minimum": gate_thresholds["minimum_initial_agreement"],
        "known_blocking_content_defects_maximum": gate_thresholds[
            "known_blocking_content_defects_allowed"
        ],
        "resolve_every_disagreement_before_applicant_testing": gate_thresholds[
            "all_disagreements_must_be_resolved"
        ],
    }

    assert content["status"] == "prepared_not_executed"
    assert content_lock["execution_commit"] is None
    assert all(slot["status"] == "not_run" for slot in content["reviewer_slots"])
    assert gate["external_evidence"]["content_authority_review"]["status"] == "not_run"
    assert manual["status"] == "prepared_not_executed"
    assert manual_lock["execution_status"] == "not_run"
    assert all(check["result"] == "not_run" for check in manual["manual_checks"])
    assert all(row["result"] == "not_run" for row in manual["spanish_semantic_reviews"])
    assert gate["external_evidence"]["manual_accessibility"] == {
        "ledger_id": "woodland-route-to-packet-manual-evidence",
        "ledger_version": "1.0.0",
        "ledger_path": "data/validation/woodland-manual-evidence.json",
        "status": "not_run",
        "required_check_count": 21,
        "checks_completed": 0,
        "checks_passing": None,
    }
    assert gate["external_evidence"]["spanish_semantic_review"] == {
        "ledger_id": "woodland-route-to-packet-manual-evidence",
        "ledger_version": "1.0.0",
        "ledger_path": "data/validation/woodland-manual-evidence.json",
        "status": "not_run",
        "records_required": 19,
        "records_reviewed": 0,
        "records_approved": None,
    }
    assert gate["external_evidence"]["spanish_usability"] == {
        "ledger_id": "woodland-route-to-packet-manual-evidence",
        "ledger_version": "1.0.0",
        "ledger_path": "data/validation/woodland-manual-evidence.json",
        "check_id": "ES-USABILITY-JOURNEY",
        "status": "not_run",
        "checks_required": 1,
        "checks_completed": 0,
        "checks_passing": None,
    }


def test_public_gate_record_has_no_pii_shaped_fields():
    gate = load_json(GATE_PATH)
    keys = walk_keys(gate)

    assert not keys.intersection(
        {
            "name",
            "email",
            "phone",
            "address",
            "apn",
            "permit_number",
            "application_number",
            "employer",
            "jurisdiction_name",
            "contact_details",
            "raw_notes",
            "transcript",
            "recording_url",
            "private_url",
        }
    )
    assert "participants" not in gate["external_evidence"]["participant_sessions"]
    assert "reviewers" not in gate["external_evidence"]["content_authority_review"]


def test_live_protocol_uses_the_current_same_version_journey():
    protocol = (ROOT / "docs" / "SHOWCASE-VALIDATION-PLAN.md").read_text(
        encoding="utf-8"
    )

    assert "Status: prepared, not started" in protocol
    assert "exactly six" in protocol.lower()
    assert "Session sequence, approximately 35 minutes" in protocol
    assert "two independent content-authority reviews" in protocol
    assert "`uses_city_preapproved_plan`" in protocol
    assert "`index.html`" in protocol
    assert "`check.html?sample=adu`" in protocol
    assert "without a product tour" in protocol
    assert "fresh cohort" in protocol
    assert "Never combine" in protocol
    assert "At least 22 of 25" in protocol
    assert "At least 5 of 6" in protocol
    assert "at most 300 seconds" in protocol
    assert "at most 360 seconds" in protocol
    assert "Zero confident critical errors" in protocol
    assert "No expert review, recruitment, participant session" in protocol
    assert "Each session is 25 minutes" not in protocol
    assert "3 to 5 California" not in protocol
    assert "July 29" not in protocol


def test_operating_guide_keeps_partner_rehearsal_and_claims_bounded():
    guide = (ROOT / "docs" / "VALIDATION-EVIDENCE.md").read_text(encoding="utf-8")

    assert "Status: prepared, not run" in guide
    assert "Recruitment has not started" in guide
    assert "The partner gate is pending" in guide
    assert "Praise, a demo invitation" in guide
    assert "owner role and date" in guide
    assert "opaque private-evidence receipt ID" in guide
    assert "record is not run" in guide
    assert "affected requirement, action, test, and user-facing output" in guide
    assert "at least one unaffected control" in guide
    assert "acceptable" in guide and "partner" in guide
    assert "### Proceed" in guide
    assert "### Extend" in guide
    assert "### Pivot" in guide
    assert "### Stop" in guide
    assert "have not been completed" in " ".join(guide.replace(">", "").split())


def test_new_validation_document_links_resolve():
    for path in (
        ROOT / "docs" / "VALIDATION-EVIDENCE.md",
        ROOT / "docs" / "SHOWCASE-VALIDATION-PLAN.md",
    ):
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
            if target.startswith(("https://", "http://", "#")):
                continue
            local_target = target.split("#", 1)[0]
            assert (path.parent / local_target).resolve().is_file(), (
                path,
                target,
            )
