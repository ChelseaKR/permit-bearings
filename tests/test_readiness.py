from __future__ import annotations

import copy
import hashlib
import json
import sys
from dataclasses import asdict, replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from permit_pathways.readiness import (
    FINDING_STATUSES,
    ReadinessPacket,
    ReadinessWorkflow,
    evaluate_readiness,
    load_and_evaluate_readiness,
    load_readiness_packet,
    load_readiness_remedies,
    load_readiness_workflow,
)
from permit_pathways.readiness_cli import main as readiness_cli_main

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 7, 30)
WORKFLOW_PATH = (
    ROOT / "data" / "readiness" / "workflows" / "woodland-preapproved-detached-adu.json"
)
PACKET_PATH = ROOT / "data" / "readiness" / "samples" / "woodland-preapproved-adu.json"
REMEDIES_PATH = (
    ROOT / "data" / "readiness" / "remedies" / "woodland-preapproved-detached-adu.json"
)
GENERATED_MANIFEST_PATH = (
    ROOT / "data" / "readiness" / "generated" / "woodland-preapproved-adu-evidence.json"
)
SOURCES_PATH = ROOT / "data" / "sources.json"
CHECKLIST_SOURCE_ID = "woodland-preapproved-adu-checklist"
PARCEL_SOURCE_ID = "yolo-public-parcels-layer"


@pytest.fixture(scope="module")
def workflow() -> ReadinessWorkflow:
    return load_readiness_workflow(
        WORKFLOW_PATH,
        SOURCES_PATH,
        today=AS_OF,
    )


@pytest.fixture(scope="module")
def packet(workflow: ReadinessWorkflow) -> ReadinessPacket:
    return load_readiness_packet(PACKET_PATH, workflow, today=AS_OF)


def _packet_variant(
    packet: ReadinessPacket,
    *,
    facts: dict[str, str] | None = None,
    inventory: dict[str, str] | None = None,
    **changes: object,
) -> ReadinessPacket:
    fact_changes = facts or {}
    inventory_changes = inventory or {}
    return replace(
        packet,
        facts=tuple(
            replace(fact, value=fact_changes.get(fact.fact_id, fact.value))
            for fact in packet.facts
        ),
        inventory=tuple(
            replace(
                item,
                status=inventory_changes.get(
                    item.requirement_id,
                    item.status,
                ),
            )
            for item in packet.inventory
        ),
        **changes,
    )


def _all_present_packet(
    packet: ReadinessPacket,
    *,
    conditional_value: str,
) -> ReadinessPacket:
    fact_values = {
        fact.fact_id: (
            "yes"
            if fact.fact_id
            in {
                "uses_city_preapproved_plan",
                "parcel_city_matches_woodland",
                "parcel_land_use_is_residential",
            }
            else conditional_value
        )
        for fact in packet.facts
    }
    inventory = {item.requirement_id: "present" for item in packet.inventory}
    return _packet_variant(packet, facts=fact_values, inventory=inventory)


def _finding_map(result) -> dict[str, object]:
    return {finding.requirement_id: finding for finding in result.findings}


def _write_json(
    tmp_path: Path,
    name: str,
    payload: object,
) -> Path:
    path = tmp_path / name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def _canonical_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _remedy_content_fingerprint(payload: dict) -> str:
    content = {
        "entries": payload["entries"],
        "version": payload["version"],
        "workflow_id": payload["workflow_id"],
    }
    encoded = json.dumps(
        content,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def test_canonical_woodland_sample_reports_bounded_known_gaps(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
):
    result = evaluate_readiness(workflow, packet, today=AS_OF)

    assert workflow.workflow_id == "woodland-preapproved-detached-adu"
    assert packet.synthetic is True
    assert len(workflow.requirements) == 25
    assert result.applicability_status == "applies"
    assert result.overall_status == "known_gaps"
    assert result.source_status == "current"
    assert result.source_status_as_of == AS_OF.isoformat()
    assert result.source_review_due_on == "2027-01-25"
    assert result.counts() == {
        "present": 14,
        "missing": 3,
        "not_applicable": 3,
        "conflicting": 0,
        "needs_staff_review": 5,
        "not_evaluated": 0,
    }
    assert {
        finding.requirement_id
        for finding in result.findings
        if finding.status == "missing"
    } == {
        "plot-plan-address-apn",
        "plot-plan-drainage",
        "electrical-load-calculations",
    }
    assert result.staff_questions == (
        "Do solar plans apply to this project?",
        "Do fire sprinkler plans apply to this project?",
        "Is the property in a flood zone?",
    )
    assert "inspect files" in result.boundary
    assert "does not query or verify a live parcel" in result.boundary
    assert "certify completeness" in result.boundary


def test_canonical_parcel_facts_are_source_shaped_but_explicitly_fabricated(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
):
    definitions = workflow.fact_map()
    parcel_facts = {
        fact.fact_id: fact
        for fact in packet.facts
        if fact.provenance == "synthetic_public_record_fixture"
    }

    assert set(parcel_facts) == {
        "parcel_city_matches_woodland",
        "parcel_land_use_is_residential",
    }
    assert {fact.source_id for fact in parcel_facts.values()} == {PARCEL_SOURCE_ID}
    assert {fact.source_field for fact in parcel_facts.values()} == {"CITY", "LU_Descr"}
    assert all(
        fact.source_checked_on == AS_OF.isoformat() for fact in parcel_facts.values()
    )
    assert all(fact.value == "yes" for fact in parcel_facts.values())
    assert all(
        definitions[fact.fact_id].source_id == fact.source_id
        and definitions[fact.fact_id].source_field == fact.source_field
        for fact in parcel_facts.values()
    )


def test_mapping_provenance_is_source_bound_and_explicitly_review_pending(
    workflow: ReadinessWorkflow,
):
    provenance = workflow.mapping_provenance

    assert provenance.version == "1.1.0"
    assert provenance.updated_on == AS_OF.isoformat()
    assert provenance.drafted_by == "ai_assisted"
    assert provenance.review_status == "prototype_review_pending"
    assert provenance.review_scope == "requirements_excerpts_and_fact_bindings"
    assert provenance.provider == "unknown"
    assert provenance.model == "unknown"
    assert provenance.run_record_status == "not_recorded"
    assert [
        (source.source_id, source.sha256)
        for source in provenance.input_source_fingerprints
    ] == [(binding.source_id, binding.sha256) for binding in workflow.source_bindings]


def test_all_reported_items_present_uses_only_the_bounded_outcome(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
):
    all_present = _all_present_packet(packet, conditional_value="yes")

    result = evaluate_readiness(workflow, all_present, today=AS_OF)

    assert result.overall_status == "no_known_gaps_in_bounded_manifest"
    assert result.counts() == {
        "present": 25,
        "missing": 0,
        "not_applicable": 0,
        "conflicting": 0,
        "needs_staff_review": 0,
        "not_evaluated": 0,
    }
    assert result.staff_questions == ()
    assert result.overall_status != "complete"
    assert "certify completeness" in result.boundary


@pytest.mark.parametrize(
    ("fact_value", "expected_status", "expected_overall", "has_question"),
    [
        ("yes", "missing", "known_gaps", False),
        (
            "no",
            "not_applicable",
            "no_known_gaps_in_bounded_manifest",
            False,
        ),
        ("unknown", "needs_staff_review", "needs_review", True),
    ],
)
def test_conditional_requirements_distinguish_yes_no_and_unknown(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
    fact_value: str,
    expected_status: str,
    expected_overall: str,
    has_question: bool,
):
    baseline = _all_present_packet(packet, conditional_value="no")
    variant = _packet_variant(
        baseline,
        facts={"solar_plans_applicable": fact_value},
        inventory={"solar-plans": "missing"},
    )

    result = evaluate_readiness(workflow, variant, today=AS_OF)
    solar = _finding_map(result)["solar-plans"]

    assert solar.status == expected_status
    assert result.overall_status == expected_overall
    assert (
        "Do solar plans apply to this project?" in result.staff_questions
    ) is has_question
    if fact_value != "yes":
        assert solar.status != "missing"


def test_missing_parent_suppresses_all_child_content_findings(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
):
    baseline = _all_present_packet(packet, conditional_value="no")
    child_ids = {
        requirement.requirement_id
        for requirement in workflow.requirements
        if requirement.parent_requirement_id == "dimensioned-plot-plan"
    }
    assert len(child_ids) == 11
    variant = _packet_variant(
        baseline,
        inventory={
            "dimensioned-plot-plan": "missing",
            "plot-plan-address-apn": "conflicting",
            "plot-plan-drainage": "missing",
        },
    )

    result = evaluate_readiness(workflow, variant, today=AS_OF)
    findings = _finding_map(result)

    assert findings["dimensioned-plot-plan"].status == "missing"
    assert all(
        findings[requirement_id].status == "not_evaluated"
        for requirement_id in child_ids
    )
    assert all(
        "parent document was not reported present" in findings[requirement_id].reason
        for requirement_id in child_ids
    )
    assert result.overall_status == "known_gaps"
    assert result.counts() == {
        "present": 6,
        "missing": 1,
        "not_applicable": 7,
        "conflicting": 0,
        "needs_staff_review": 0,
        "not_evaluated": 11,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("workflow_id", "different-workflow"),
        ("jurisdiction", "davis"),
        ("project_type", "jadu"),
    ],
)
def test_wrong_packet_scope_is_not_evaluated(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
    field: str,
    value: str,
):
    scoped_packet = _all_present_packet(packet, conditional_value="yes")
    wrong_scope = replace(scoped_packet, **{field: value})

    result = evaluate_readiness(workflow, wrong_scope, today=AS_OF)

    assert result.applicability_status == "does_not_apply"
    assert result.overall_status == "outside_bounded_workflow"
    assert result.source_status == "current"
    assert result.counts()["not_evaluated"] == len(workflow.requirements)
    assert {finding.status for finding in result.findings} == {"not_evaluated"}
    assert result.staff_questions == (
        "Ask Woodland staff which current checklist applies to this project.",
    )


def test_negative_workflow_applicability_is_outside_bounded_scope(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
):
    not_preapproved = _packet_variant(
        _all_present_packet(packet, conditional_value="no"),
        facts={"uses_city_preapproved_plan": "no"},
    )

    result = evaluate_readiness(workflow, not_preapproved, today=AS_OF)

    assert result.applicability_status == "does_not_apply"
    assert result.overall_status == "outside_bounded_workflow"
    assert result.counts()["not_evaluated"] == 25


def test_unknown_workflow_applicability_blocks_packet_evaluation(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
):
    unknown_plan = _packet_variant(
        _all_present_packet(packet, conditional_value="no"),
        facts={"uses_city_preapproved_plan": "unknown"},
    )

    result = evaluate_readiness(workflow, unknown_plan, today=AS_OF)

    assert result.applicability_status == "unknown"
    assert result.overall_status == "needs_review"
    assert result.counts()["not_evaluated"] == 25
    assert result.staff_questions == (
        "Is this packet using a City of Woodland preapproved ADU plan?",
    )


@pytest.mark.parametrize("changed_source_id", [CHECKLIST_SOURCE_ID, PARCEL_SOURCE_ID])
def test_changed_or_stale_source_fails_closed_for_every_requirement(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
    changed_source_id: str,
):
    changed = evaluate_readiness(
        workflow,
        packet,
        today=AS_OF,
        changed_source_ids={changed_source_id},
    )

    assert changed.overall_status == "source_review_required"
    assert changed.applicability_status == "applies"
    assert changed.source_status == "source_review_required"
    assert changed.source_status_as_of == AS_OF.isoformat()
    assert changed.source_review_due_on == "2027-01-25"
    assert changed.counts() == {
        "present": 0,
        "missing": 0,
        "not_applicable": 0,
        "conflicting": 0,
        "needs_staff_review": 25,
        "not_evaluated": 0,
    }
    assert all(finding.status == "needs_staff_review" for finding in changed.findings)
    assert changed.staff_questions == (
        "Confirm the current checklist and parcel-source fields before using "
        "this packet-presence result.",
    )

    exact_ids_only = evaluate_readiness(
        workflow,
        packet,
        today=AS_OF,
        changed_source_ids={"woodland-preapproved"},
    )
    assert exact_ids_only.overall_status == "known_gaps"

    due_date = evaluate_readiness(
        workflow,
        packet,
        today=AS_OF + timedelta(days=179),
    )
    assert due_date.source_status == "current"
    assert due_date.source_status_as_of == "2027-01-25"
    assert due_date.source_review_due_on == "2027-01-25"

    stale = evaluate_readiness(
        workflow,
        packet,
        today=AS_OF + timedelta(days=180),
    )
    assert stale.overall_status == "source_review_required"
    assert stale.source_status_as_of == "2027-01-26"
    assert stale.source_review_due_on == "2027-01-25"
    assert stale.counts()["needs_staff_review"] == 25


def test_workflow_loader_rejects_duplicate_orphan_and_schema_errors(
    tmp_path: Path,
):
    canonical = _canonical_payload(WORKFLOW_PATH)

    wrong_schema = copy.deepcopy(canonical)
    wrong_schema["schema_version"] = 2
    with pytest.raises(ValueError, match="unsupported schema version"):
        load_readiness_workflow(
            _write_json(tmp_path, "workflow-schema.json", wrong_schema),
            SOURCES_PATH,
            today=AS_OF,
        )

    duplicate_fact = copy.deepcopy(canonical)
    duplicate_fact["workflow"]["facts"].append(
        copy.deepcopy(duplicate_fact["workflow"]["facts"][0])
    )
    with pytest.raises(ValueError, match="duplicate fact"):
        load_readiness_workflow(
            _write_json(
                tmp_path,
                "workflow-duplicate-fact.json",
                duplicate_fact,
            ),
            SOURCES_PATH,
            today=AS_OF,
        )

    duplicate_requirement = copy.deepcopy(canonical)
    duplicate_requirement["workflow"]["requirements"].append(
        copy.deepcopy(duplicate_requirement["workflow"]["requirements"][0])
    )
    with pytest.raises(ValueError, match="duplicate requirement"):
        load_readiness_workflow(
            _write_json(
                tmp_path,
                "workflow-duplicate-requirement.json",
                duplicate_requirement,
            ),
            SOURCES_PATH,
            today=AS_OF,
        )

    orphan_parent = copy.deepcopy(canonical)
    orphan_parent["workflow"]["requirements"][3]["parent_requirement_id"] = (
        "missing-parent"
    )
    with pytest.raises(ValueError, match="parent must appear first"):
        load_readiness_workflow(
            _write_json(
                tmp_path,
                "workflow-orphan-parent.json",
                orphan_parent,
            ),
            SOURCES_PATH,
            today=AS_OF,
        )

    unknown_field = copy.deepcopy(canonical)
    unknown_field["workflow"]["requirements"][0]["unexpected"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        load_readiness_workflow(
            _write_json(
                tmp_path,
                "workflow-unknown-field.json",
                unknown_field,
            ),
            SOURCES_PATH,
            today=AS_OF,
        )

    wrong_mapping_digest = copy.deepcopy(canonical)
    wrong_mapping_digest["workflow"]["mapping_provenance"]["input_source_fingerprints"][
        0
    ]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="does not match bound source"):
        load_readiness_workflow(
            _write_json(
                tmp_path,
                "workflow-wrong-mapping-digest.json",
                wrong_mapping_digest,
            ),
            SOURCES_PATH,
            today=AS_OF,
        )

    unsupported_mapping_review = copy.deepcopy(canonical)
    unsupported_mapping_review["workflow"]["mapping_provenance"]["review_status"] = (
        "human_reviewed"
    )
    with pytest.raises(ValueError, match="remain review-pending"):
        load_readiness_workflow(
            _write_json(
                tmp_path,
                "workflow-unsupported-mapping-review.json",
                unsupported_mapping_review,
            ),
            SOURCES_PATH,
            today=AS_OF,
        )

    unrecorded_provider_claim = copy.deepcopy(canonical)
    unrecorded_provider_claim["workflow"]["mapping_provenance"]["provider"] = "OpenAI"
    with pytest.raises(ValueError, match="no provider was recorded"):
        load_readiness_workflow(
            _write_json(
                tmp_path,
                "workflow-unrecorded-provider.json",
                unrecorded_provider_claim,
            ),
            SOURCES_PATH,
            today=AS_OF,
        )


def test_packet_loader_rejects_duplicate_orphan_coverage_and_schema_errors(
    tmp_path: Path,
    workflow: ReadinessWorkflow,
):
    canonical = _canonical_payload(PACKET_PATH)

    wrong_schema = copy.deepcopy(canonical)
    wrong_schema["schema_version"] = 2
    with pytest.raises(ValueError, match="unsupported schema version"):
        load_readiness_packet(
            _write_json(tmp_path, "packet-schema.json", wrong_schema),
            workflow,
            today=AS_OF,
        )

    duplicate_fact = copy.deepcopy(canonical)
    duplicate_fact["packet"]["facts"].append(
        copy.deepcopy(duplicate_fact["packet"]["facts"][0])
    )
    with pytest.raises(ValueError, match="duplicate fact"):
        load_readiness_packet(
            _write_json(
                tmp_path,
                "packet-duplicate-fact.json",
                duplicate_fact,
            ),
            workflow,
            today=AS_OF,
        )

    duplicate_inventory = copy.deepcopy(canonical)
    duplicate_inventory["packet"]["inventory"].append(
        copy.deepcopy(duplicate_inventory["packet"]["inventory"][0])
    )
    with pytest.raises(ValueError, match="duplicate item"):
        load_readiness_packet(
            _write_json(
                tmp_path,
                "packet-duplicate-inventory.json",
                duplicate_inventory,
            ),
            workflow,
            today=AS_OF,
        )

    orphan_inventory = copy.deepcopy(canonical)
    orphan_inventory["packet"]["inventory"][0]["requirement_id"] = "orphan-requirement"
    with pytest.raises(ValueError, match="unknown workflow requirement"):
        load_readiness_packet(
            _write_json(
                tmp_path,
                "packet-orphan-inventory.json",
                orphan_inventory,
            ),
            workflow,
            today=AS_OF,
        )

    missing_inventory = copy.deepcopy(canonical)
    missing_inventory["packet"]["inventory"].pop()
    with pytest.raises(ValueError, match="missing requirements"):
        load_readiness_packet(
            _write_json(
                tmp_path,
                "packet-missing-inventory.json",
                missing_inventory,
            ),
            workflow,
            today=AS_OF,
        )

    unknown_field = copy.deepcopy(canonical)
    unknown_field["packet"]["inventory"][0]["unexpected"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        load_readiness_packet(
            _write_json(
                tmp_path,
                "packet-unknown-field.json",
                unknown_field,
            ),
            workflow,
            today=AS_OF,
        )

    unsupported_provenance = copy.deepcopy(canonical)
    unsupported_provenance["packet"]["facts"][0]["provenance"] = (
        "official_public_record"
    )
    with pytest.raises(ValueError, match="unsupported value"):
        load_readiness_packet(
            _write_json(
                tmp_path,
                "packet-unsupported-official-provenance.json",
                unsupported_provenance,
            ),
            workflow,
            today=AS_OF,
        )

    mismatched_field = copy.deepcopy(canonical)
    mismatched_field["packet"]["facts"][0]["source_field"] = "LU_Descr"
    with pytest.raises(ValueError, match="does not match workflow fact binding"):
        load_readiness_packet(
            _write_json(
                tmp_path,
                "packet-mismatched-source-field.json",
                mismatched_field,
            ),
            workflow,
            today=AS_OF,
        )

    unsupported_unknown_fixture = copy.deepcopy(canonical)
    unsupported_unknown_fixture["packet"]["facts"][0]["value"] = "unknown"
    with pytest.raises(ValueError, match="source fixture must be concrete"):
        load_readiness_packet(
            _write_json(
                tmp_path,
                "packet-unknown-source-fixture.json",
                unsupported_unknown_fixture,
            ),
            workflow,
            today=AS_OF,
        )

    assertion_with_source_claim = copy.deepcopy(canonical)
    assertion_with_source_claim["packet"]["facts"][2]["source_id"] = PARCEL_SOURCE_ID
    with pytest.raises(ValueError, match="cannot claim source evidence"):
        load_readiness_packet(
            _write_json(
                tmp_path,
                "packet-assertion-source-claim.json",
                assertion_with_source_claim,
            ),
            workflow,
            today=AS_OF,
        )

    non_synthetic_fixture = copy.deepcopy(canonical)
    non_synthetic_fixture["packet"]["synthetic"] = False
    with pytest.raises(ValueError, match="non-synthetic packet cannot use fixtures"):
        load_readiness_packet(
            _write_json(
                tmp_path,
                "packet-non-synthetic-fixture.json",
                non_synthetic_fixture,
            ),
            workflow,
            today=AS_OF,
        )


def test_canonical_remedies_cover_and_bind_every_requirement(
    workflow: ReadinessWorkflow,
):
    remedies = load_readiness_remedies(
        REMEDIES_PATH,
        workflow,
        today=AS_OF,
    )
    requirements = workflow.requirement_map()

    assert remedies.workflow_id == workflow.workflow_id
    assert remedies.workflow_fingerprint == workflow.fingerprint()
    assert set(remedies.entry_map()) == set(requirements)
    assert len(remedies.entries) == len(requirements) == 25
    assert all(
        entry.requirement_fingerprint
        == requirements[entry.requirement_id].fingerprint()
        for entry in remedies.entries
    )
    assert remedies.review.status == "prototype_review_pending"
    assert remedies.review.reviewer is None
    assert remedies.review.content_fingerprint is None


def test_remedy_loader_rejects_duplicate_orphan_missing_and_drifted_entries(
    tmp_path: Path,
    workflow: ReadinessWorkflow,
):
    canonical = _canonical_payload(REMEDIES_PATH)

    duplicate = copy.deepcopy(canonical)
    duplicate["entries"].append(copy.deepcopy(duplicate["entries"][0]))
    with pytest.raises(ValueError, match="duplicate entry"):
        load_readiness_remedies(
            _write_json(tmp_path, "remedy-duplicate.json", duplicate),
            workflow,
            today=AS_OF,
        )

    orphan = copy.deepcopy(canonical)
    orphan["entries"].append(
        {
            "requirement_id": "orphan-requirement",
            "requirement_fingerprint": "sha256:" + "0" * 64,
            "action": "Should never load.",
        }
    )
    with pytest.raises(ValueError, match="orphan entry"):
        load_readiness_remedies(
            _write_json(tmp_path, "remedy-orphan.json", orphan),
            workflow,
            today=AS_OF,
        )

    missing = copy.deepcopy(canonical)
    missing["entries"].pop()
    with pytest.raises(ValueError, match="missing requirements"):
        load_readiness_remedies(
            _write_json(tmp_path, "remedy-missing.json", missing),
            workflow,
            today=AS_OF,
        )

    drifted_requirement = copy.deepcopy(canonical)
    drifted_requirement["entries"][0]["requirement_fingerprint"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="requirement drifted"):
        load_readiness_remedies(
            _write_json(
                tmp_path,
                "remedy-requirement-drift.json",
                drifted_requirement,
            ),
            workflow,
            today=AS_OF,
        )

    drifted_workflow = copy.deepcopy(canonical)
    drifted_workflow["workflow_fingerprint"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="workflow content drifted"):
        load_readiness_remedies(
            _write_json(
                tmp_path,
                "remedy-workflow-drift.json",
                drifted_workflow,
            ),
            workflow,
            today=AS_OF,
        )


def test_remedy_review_metadata_is_versioned_and_copy_bound(
    tmp_path: Path,
    workflow: ReadinessWorkflow,
):
    canonical = _canonical_payload(REMEDIES_PATH)

    pending_with_claim = copy.deepcopy(canonical)
    pending_with_claim["review"]["reviewer"] = "Unbound reviewer"
    with pytest.raises(
        ValueError,
        match="pending review cannot carry review claims",
    ):
        load_readiness_remedies(
            _write_json(
                tmp_path,
                "remedy-pending-claim.json",
                pending_with_claim,
            ),
            workflow,
            today=AS_OF,
        )

    reviewed = copy.deepcopy(canonical)
    reviewed["review"] = {
        "status": "human_reviewed",
        "reviewer": "Named test reviewer",
        "method": "Compared every action with its bound requirement.",
        "reviewed_on": AS_OF.isoformat(),
        "reviewed_version": reviewed["version"],
        "content_fingerprint": _remedy_content_fingerprint(reviewed),
    }
    loaded = load_readiness_remedies(
        _write_json(tmp_path, "remedy-reviewed.json", reviewed),
        workflow,
        today=AS_OF,
    )
    assert loaded.review.status == "human_reviewed"
    assert loaded.review.reviewed_version == loaded.version

    wrong_version = copy.deepcopy(reviewed)
    wrong_version["review"]["reviewed_version"] = "0.9.0"
    with pytest.raises(
        ValueError,
        match="completed review must name reviewer",
    ):
        load_readiness_remedies(
            _write_json(
                tmp_path,
                "remedy-wrong-version.json",
                wrong_version,
            ),
            workflow,
            today=AS_OF,
        )

    copy_drift = copy.deepcopy(reviewed)
    copy_drift["entries"][0]["action"] += " Changed after review."
    with pytest.raises(ValueError, match="reviewed copy drifted"):
        load_readiness_remedies(
            _write_json(
                tmp_path,
                "remedy-copy-drift.json",
                copy_drift,
            ),
            workflow,
            today=AS_OF,
        )


def test_manifest_is_deterministic_and_matches_committed_evidence(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
):
    first = evaluate_readiness(workflow, packet, today=AS_OF)
    second = evaluate_readiness(workflow, packet, today=AS_OF)
    first_manifest = first.to_manifest(workflow, packet)
    second_manifest = second.to_manifest(workflow, packet)

    assert first_manifest == second_manifest
    assert json.dumps(
        first_manifest,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) == json.dumps(
        second_manifest,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    assert first_manifest == _canonical_payload(GENERATED_MANIFEST_PATH)
    assert [finding["requirement_id"] for finding in first_manifest["findings"]] == [
        requirement.requirement_id for requirement in workflow.requirements
    ]
    assert first_manifest["facts"] == [asdict(fact) for fact in packet.facts]
    assert first_manifest["inventory"] == [asdict(item) for item in packet.inventory]
    assert set(first_manifest["counts"]) == set(FINDING_STATUSES)
    assert first_manifest["workflow_fingerprint"].startswith("sha256:")
    assert first_manifest["packet_fingerprint"].startswith("sha256:")
    assert first_manifest["applicability_status"] == "applies"
    assert first_manifest["source_status"] == "current"
    assert first_manifest["source_status_as_of"] == AS_OF.isoformat()
    assert first_manifest["source_review_due_on"] == "2027-01-25"


def test_default_loader_and_cli_use_current_date_for_source_currency(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    runtime_as_of = AS_OF + timedelta(days=181)
    monkeypatch.setattr(
        "permit_pathways.dates.utc_today",
        lambda: runtime_as_of,
    )

    _workflow, packet, result = load_and_evaluate_readiness(
        WORKFLOW_PATH,
        PACKET_PATH,
        SOURCES_PATH,
    )

    assert packet.evaluated_on == AS_OF.isoformat()
    assert result.evaluated_on == runtime_as_of.isoformat()
    assert result.source_status_as_of == runtime_as_of.isoformat()
    assert result.source_review_due_on == "2027-01-25"
    assert result.source_status == "source_review_required"
    assert result.overall_status == "source_review_required"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "permit-pathways-readiness",
            "--workflow",
            str(WORKFLOW_PATH),
            "--packet",
            str(PACKET_PATH),
            "--sources",
            str(SOURCES_PATH),
        ],
    )

    assert readiness_cli_main() == 0
    cli_manifest = json.loads(capsys.readouterr().out)
    assert cli_manifest["evaluated_on"] == runtime_as_of.isoformat()
    assert cli_manifest["source_status_as_of"] == runtime_as_of.isoformat()
    assert cli_manifest["source_review_due_on"] == "2027-01-25"
    assert cli_manifest["source_status"] == "source_review_required"
    assert cli_manifest["applicability_status"] == "applies"
    assert cli_manifest["overall_status"] == "source_review_required"


def test_convenience_loader_and_cli_emit_the_canonical_manifest(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    workflow, packet, result = load_and_evaluate_readiness(
        WORKFLOW_PATH,
        PACKET_PATH,
        SOURCES_PATH,
        today=AS_OF,
    )
    expected = result.to_manifest(workflow, packet)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "permit-pathways-readiness",
            "--workflow",
            str(WORKFLOW_PATH),
            "--packet",
            str(PACKET_PATH),
            "--sources",
            str(SOURCES_PATH),
            "--as-of",
            AS_OF.isoformat(),
        ],
    )

    assert readiness_cli_main() == 0
    assert json.loads(capsys.readouterr().out) == expected
