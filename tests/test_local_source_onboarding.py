from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.local_source_onboarding import (
    CLAIM_BOUNDARY,
    MAX_INTAKE_BYTES,
    TEMPLATE_ID,
    artifact_fingerprint,
    load_local_source_onboarding,
    passage_fingerprint,
)
from permit_pathways.local_source_onboarding_cli import main
from permit_pathways.screening import load_rules, screen

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "data" / "onboarding" / "local-source-intake-template.json"
AS_OF = date(2026, 8, 9)
SHA = "sha256:" + "a" * 64


def _payload() -> dict[str, Any]:
    value = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write(tmp_path: Path, payload: Any, name: str = "intake.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _source(
    source_id: str,
    source_type: str,
    suffix: str,
    *,
    enacted_on: str | None = None,
    effective_on: str | None = None,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "source_type": source_type,
        "title": f"Synthetic {source_type.replace('_', ' ')}",
        "publisher": "Synthetic jurisdiction",
        "official_url": f"https://planning.example/{suffix}",
        "content_fingerprint": SHA,
        "checked_on": "2026-08-01",
        "enacted_on": enacted_on,
        "effective_on": effective_on,
    }


def _prepared_payload() -> dict[str, Any]:
    payload = _payload()
    payload["onboarding_id"] = "synthetic-jurisdiction-adu-onboarding-v1"
    payload["status"] = "prepared_for_review"
    payload["project_scope"] = {
        "jurisdiction_id": "synthetic-jurisdiction",
        "jurisdiction_name": "Synthetic Jurisdiction",
        "permit_subtype_id": "detached-adu",
        "permit_subtype_name": "Detached ADU",
        "included_project_types": ["New detached ADU"],
        "excluded_project_types": ["Junior ADU"],
    }
    payload["sources"] = [
        _source(
            "synthetic-application-form",
            "application_form",
            "application-form.pdf",
        ),
        _source("synthetic-fee-schedule", "fee_schedule", "fees"),
        _source(
            "synthetic-ordinance",
            "ordinance",
            "ordinance",
            enacted_on="2026-01-01",
            effective_on="2026-02-01",
        ),
        _source("synthetic-parcel-dataset", "parcel_dataset", "parcel-data"),
        _source("synthetic-process-page", "process_page", "process"),
        _source(
            "synthetic-submission-checklist",
            "submission_checklist",
            "checklist.pdf",
        ),
    ]
    source_ids = {
        "operative_ordinance": "synthetic-ordinance",
        "application_form": "synthetic-application-form",
        "submission_checklist": "synthetic-submission-checklist",
        "fee_schedule": "synthetic-fee-schedule",
        "process_page": "synthetic-process-page",
    }
    for requirement in payload["source_requirements"]:
        requirement["status"] = "collected_unreviewed"
        requirement["source_ids"] = [source_ids[requirement["role"]]]
    exact_text = "Synthetic operative passage for schema testing only."
    payload["operative_passages"] = [
        {
            "passage_id": "synthetic-ordinance-section-one",
            "source_id": "synthetic-ordinance",
            "locator": "Section 1",
            "exact_text": exact_text,
            "text_fingerprint": passage_fingerprint(exact_text),
            "enacted_on": "2026-01-01",
            "effective_on": "2026-02-01",
            "checked_on": "2026-08-01",
        }
    ]
    payload["parcel_scope"] = {
        "description": "Synthetic parcels inside the hypothetical boundary.",
        "facts": [
            {
                "fact_id": "synthetic-zoning-fact",
                "label": "Synthetic zoning field",
                "collection_method": "official_dataset",
                "source_id": "synthetic-parcel-dataset",
                "source_field": "ZONE_TEST",
                "unresolved_behavior": "route_to_staff",
            }
        ],
        "unknown_behavior": "route_to_staff",
    }
    payload["exception_review"]["status"] = "collection_complete_unreviewed"
    payload["conflict_review"]["status"] = "collection_complete_unreviewed"
    payload["review_plan"].update(
        {
            "source_owner_role": "source-records-owner",
            "content_review_owner_role": "content-review-lead",
            "jurisdiction_approval_owner_role": "jurisdiction-approval-authority",
            "publication_owner_role": "publication-release-owner",
            "reverification_cadence_days": 90,
        }
    )
    return payload


def _add_open_question(payload: dict[str, Any]) -> None:
    payload["open_questions"] = [
        {
            "question_id": "synthetic-conflict-question",
            "question": "Which candidate source controls this conflict?",
            "blocking": True,
            "owner_role": "authorized-jurisdiction-reviewer",
            "source_ids": ["synthetic-ordinance", "synthetic-process-page"],
            "passage_ids": ["synthetic-ordinance-section-one"],
        }
    ]


def test_committed_template_is_valid_and_claims_no_local_layer():
    intake = load_local_source_onboarding(TEMPLATE, today=AS_OF)

    assert intake.onboarding_id == TEMPLATE_ID
    assert intake.status == "not_run"
    assert intake.review_status == "not_run"
    assert intake.local_layer_status == "not_encoded"
    assert intake.source_requirement_count == 5
    assert intake.collected_source_requirement_count == 0
    assert intake.source_count == 0
    assert intake.operative_passage_count == 0
    assert intake.parcel_fact_count == 0
    assert intake.open_question_count == 0
    assert intake.ready_for_review is False
    assert intake.validated_as_of == "2026-08-09"
    assert intake.earliest_reverification_due_on is None
    assert intake.artifact_fingerprint == artifact_fingerprint(_payload())


def test_committed_template_keeps_review_ownership_and_evidence_empty():
    payload = _payload()

    assert payload["claim_boundary"] == CLAIM_BOUNDARY
    assert payload["review_plan"] == {
        "status": "not_run",
        "source_owner_role": None,
        "content_review_owner_role": None,
        "jurisdiction_approval_owner_role": None,
        "publication_owner_role": None,
        "reverification_cadence_days": None,
        "reviewer": None,
        "method": None,
        "reviewed_on": None,
        "reviewed_artifact_fingerprint": None,
        "approver": None,
        "approved_on": None,
        "approved_artifact_fingerprint": None,
    }
    assert {item["status"] for item in payload["source_requirements"]} == {
        "not_collected"
    }


def test_synthetic_complete_intake_can_only_be_prepared_for_review(tmp_path: Path):
    intake = load_local_source_onboarding(
        _write(tmp_path, _prepared_payload()), today=AS_OF
    )

    assert intake.status == "prepared_for_review"
    assert intake.ready_for_review is True
    assert intake.review_status == "not_run"
    assert intake.local_layer_status == "not_encoded"
    assert intake.collected_source_requirement_count == 5
    assert intake.source_count == 6
    assert intake.operative_passage_count == 1
    assert intake.parcel_fact_count == 1
    assert intake.validated_as_of == "2026-08-09"
    assert intake.earliest_reverification_due_on == "2026-10-30"


def test_claim_boundary_policy_is_immutable():
    with pytest.raises(TypeError):
        CLAIM_BOUNDARY["records_human_review"] = True  # type: ignore[index]


def test_loading_a_prepared_intake_cannot_change_rule_matching(tmp_path: Path):
    rules = load_rules(ROOT / "data" / "rules", today=AS_OF)
    facts = {
        "project_type": "adu",
        "primary_dwelling_status": "existing_single_family",
        "adu_project_form": "new_detached",
        "unpermitted_existing": "no",
        "jurisdiction": "davis",
    }
    before = [result.rule.rule_id for result in screen(facts, rules)]
    load_local_source_onboarding(_write(tmp_path, _prepared_payload()), today=AS_OF)
    after = [result.rule.rule_id for result in screen(facts, rules)]

    assert after == before


def test_collection_in_progress_requires_a_new_id_and_actual_work(tmp_path: Path):
    payload = _payload()
    payload["status"] = "collection_in_progress"
    with pytest.raises(ValueError, match="distinct stable onboarding_id"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    payload["onboarding_id"] = "synthetic-partial-intake-v1"
    with pytest.raises(ValueError, match="must contain collected intake work"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    payload["project_scope"]["jurisdiction_id"] = "synthetic-jurisdiction"
    intake = load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)
    assert intake.status == "collection_in_progress"
    assert intake.ready_for_review is False


@pytest.mark.parametrize("status", ["reviewed", "approved", "published"])
def test_lifecycle_cannot_be_promoted_to_review_or_approval(
    tmp_path: Path, status: str
):
    payload = _prepared_payload()
    payload["status"] = status
    with pytest.raises(ValueError, match="status: unsupported value"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reviewer", "A reviewer"),
        ("method", "Compared against source"),
        ("reviewed_on", "2026-08-02"),
        ("reviewed_artifact_fingerprint", SHA),
        ("approver", "An approver"),
        ("approved_on", "2026-08-03"),
        ("approved_artifact_fingerprint", SHA),
    ],
)
def test_onboarding_intake_rejects_any_completed_review_evidence(
    tmp_path: Path, field: str, value: str
):
    payload = _prepared_payload()
    payload["review_plan"][field] = value
    with pytest.raises(ValueError, match="cannot record completed review or approval"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_review_status_cannot_be_promoted(tmp_path: Path):
    payload = _prepared_payload()
    payload["review_plan"]["status"] = "completed"
    with pytest.raises(ValueError, match="must remain 'not_run'"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("local_layer_status", "encoded"),
        ("creates_or_publishes_local_rule", True),
        ("establishes_operative_law", True),
        ("establishes_comprehensive_local_coverage", True),
        ("determines_compliance_or_eligibility", True),
        ("records_human_review", True),
        ("records_jurisdiction_approval", True),
        ("statement", "Approved local layer."),
    ],
)
def test_claim_boundary_cannot_be_weakened(tmp_path: Path, field: str, value: object):
    payload = _prepared_payload()
    payload["claim_boundary"][field] = value
    with pytest.raises(ValueError, match="must preserve"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_claim_boundary_rejects_json_number_boolean_aliases(tmp_path: Path):
    payload = _prepared_payload()
    payload["claim_boundary"]["creates_or_publishes_local_rule"] = 0
    with pytest.raises(ValueError, match="must preserve"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_source_link_alone_cannot_create_a_prepared_intake(tmp_path: Path):
    payload = _payload()
    payload["onboarding_id"] = "synthetic-link-only-intake-v1"
    payload["status"] = "prepared_for_review"
    payload["sources"] = [
        _source(
            "synthetic-ordinance",
            "ordinance",
            "ordinance",
            enacted_on="2026-01-01",
            effective_on="2026-02-01",
        )
    ]
    payload["source_requirements"][0].update(
        {
            "status": "collected_unreviewed",
            "source_ids": ["synthetic-ordinance"],
        }
    )
    with pytest.raises(ValueError, match="complete project_scope"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_prepared_intake_requires_all_source_roles_passages_scope_and_owners(
    tmp_path: Path,
):
    cases: list[tuple[str, Any, str]] = [
        (
            "missing role",
            lambda p: p["source_requirements"][1].update(
                {"status": "not_collected", "source_ids": []}
            ),
            "every source role",
        ),
        (
            "missing passage",
            lambda p: p.update({"operative_passages": []}),
            "at least one operative passage",
        ),
        (
            "exception search not run",
            lambda p: p["exception_review"].update({"status": "not_run"}),
            "exception collection",
        ),
        (
            "conflict search not run",
            lambda p: p["conflict_review"].update({"status": "not_run"}),
            "conflict collection",
        ),
        (
            "owner missing",
            lambda p: p["review_plan"].update({"content_review_owner_role": None}),
            "accountable owner role IDs",
        ),
        (
            "placeholder owner",
            lambda p: p["review_plan"].update({"source_owner_role": "tbd"}),
            "placeholder owner roles",
        ),
        (
            "parcel description missing",
            lambda p: p["parcel_scope"].update({"description": None}),
            "parcel_scope description",
        ),
    ]
    for name, mutate, message in cases:
        payload = _prepared_payload()
        mutate(payload)
        with pytest.raises(ValueError, match=message):
            load_local_source_onboarding(
                _write(tmp_path, payload, f"{name}.json"), today=AS_OF
            )


def test_prepared_intake_requires_passage_for_each_ordinance_source(tmp_path: Path):
    payload = _prepared_payload()
    second = _source(
        "synthetic-ordinance-two",
        "ordinance",
        "ordinance-two",
        enacted_on="2026-01-02",
        effective_on="2026-02-02",
    )
    payload["sources"].insert(3, second)
    payload["source_requirements"][0]["source_ids"].append("synthetic-ordinance-two")
    with pytest.raises(ValueError, match="exactly the operative_ordinance"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_prepared_intake_rejects_passage_from_unbound_ordinance(tmp_path: Path):
    payload = _prepared_payload()
    second = _source(
        "synthetic-ordinance-two",
        "ordinance",
        "ordinance-two",
        enacted_on="2026-01-02",
        effective_on="2026-02-02",
    )
    payload["sources"].insert(3, second)
    payload["operative_passages"].append(
        {
            "passage_id": "synthetic-ordinance-two-section-one",
            "source_id": "synthetic-ordinance-two",
            "locator": "Section 1",
            "exact_text": "Synthetic second operative passage.",
            "text_fingerprint": passage_fingerprint(
                "Synthetic second operative passage."
            ),
            "enacted_on": "2026-01-02",
            "effective_on": "2026-02-02",
            "checked_on": "2026-08-01",
        }
    )
    with pytest.raises(ValueError, match="exactly the operative_ordinance"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_prepared_intake_rejects_unreferenced_source(tmp_path: Path):
    payload = _prepared_payload()
    payload["sources"].append(
        _source("synthetic-unused-source", "other_official", "unused")
    )
    with pytest.raises(ValueError, match="unreferenced source"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda p: p["sources"][0].update({"content_fingerprint": "bad"}), "sha256"),
        (
            lambda p: p["sources"][0].update(
                {"official_url": "http://planning.example/form"}
            ),
            "HTTPS URL",
        ),
        (
            lambda p: p["sources"][0].update(
                {"official_url": "https://user@planning.example/form"}
            ),
            "HTTPS URL",
        ),
        (
            lambda p: p["sources"][0].update(
                {"official_url": "https://planning.example/form#claim"}
            ),
            "HTTPS URL",
        ),
        (
            lambda p: p["sources"][0].update(
                {"official_url": "https://planning.example:bad/form"}
            ),
            "HTTPS URL",
        ),
        (
            lambda p: p["sources"][0].update(
                {"official_url": "https://planning.example/for\nm"}
            ),
            "HTTPS URL",
        ),
        (
            lambda p: p["sources"][0].update(
                {"official_url": "https://planning.example\\@evil.example/form"}
            ),
            "HTTPS URL",
        ),
        (
            lambda p: p["sources"][0].update(
                {"official_url": "https://planning.example/%not-escaped"}
            ),
            "HTTPS URL",
        ),
        (
            lambda p: p["sources"][0].update({"checked_on": "2026-08-10"}),
            "future dates",
        ),
        (
            lambda p: p["sources"][2].update({"enacted_on": None}),
            "require enacted_on",
        ),
        (
            lambda p: p["sources"][2].update({"effective_on": None}),
            "require enacted_on",
        ),
        (
            lambda p: p["sources"][2].update({"enacted_on": "2026-03-01"}),
            "enacted_on must not be after effective_on",
        ),
        (
            lambda p: p["sources"][2].update(
                {"effective_on": "2026-08-02", "checked_on": "2026-08-01"}
            ),
            "effective_on must not be after checked_on",
        ),
        (
            lambda p: p["sources"][0].update({"enacted_on": "2026-01-01"}),
            "allowed only for ordinance",
        ),
        (
            lambda p: p["sources"][0].update({"effective_on": "2026-08-02"}),
            "effective_on must not be after checked_on",
        ),
    ],
)
def test_source_metadata_fails_closed(tmp_path: Path, mutation: Any, message: str):
    payload = _prepared_payload()
    mutation(payload)
    with pytest.raises(ValueError, match=message):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_passage_fingerprint_and_dates_are_bound_to_ordinance(tmp_path: Path):
    cases: list[tuple[str, Any, str]] = [
        (
            "text drift",
            lambda p: p["operative_passages"][0].update(
                {"exact_text": "Changed without fingerprint update."}
            ),
            "does not match exact_text",
        ),
        (
            "effective drift",
            lambda p: p["operative_passages"][0].update({"effective_on": "2026-02-02"}),
            "match the linked ordinance",
        ),
        (
            "check drift",
            lambda p: p["operative_passages"][0].update({"checked_on": "2026-07-31"}),
            "match the linked ordinance",
        ),
        (
            "wrong source type",
            lambda p: p["operative_passages"][0].update(
                {"source_id": "synthetic-process-page"}
            ),
            "requires ordinance source",
        ),
    ]
    for name, mutate, message in cases:
        payload = _prepared_payload()
        mutate(payload)
        with pytest.raises(ValueError, match=message):
            load_local_source_onboarding(
                _write(tmp_path, payload, f"{name}.json"), today=AS_OF
            )


def test_passage_fingerprint_preserves_exact_whitespace(tmp_path: Path):
    payload = _prepared_payload()
    exact_text = "  Synthetic retained passage.\n"
    payload["operative_passages"][0]["exact_text"] = exact_text
    payload["operative_passages"][0]["text_fingerprint"] = passage_fingerprint(
        exact_text
    )

    intake = load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)
    assert intake.operative_passage_count == 1

    payload["operative_passages"][0]["text_fingerprint"] = passage_fingerprint(
        exact_text.strip()
    )
    with pytest.raises(ValueError, match="does not match exact_text"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_role_bindings_require_known_source_of_exact_type(tmp_path: Path):
    payload = _prepared_payload()
    payload["source_requirements"][1]["source_ids"] = ["missing-source"]
    with pytest.raises(ValueError, match="unknown source ID"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    payload = _prepared_payload()
    payload["source_requirements"][1]["source_ids"] = ["synthetic-process-page"]
    with pytest.raises(ValueError, match="must have type 'application_form'"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    payload = _prepared_payload()
    payload["source_requirements"][1]["status"] = "not_collected"
    with pytest.raises(ValueError, match="status and source_ids do not agree"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_parcel_facts_preserve_unknown_staff_routing(tmp_path: Path):
    payload = _prepared_payload()
    payload["parcel_scope"]["unknown_behavior"] = "assume_eligible"
    with pytest.raises(ValueError, match="route_to_staff"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    payload = _prepared_payload()
    payload["parcel_scope"]["facts"][0]["unresolved_behavior"] = "assume_yes"
    with pytest.raises(ValueError, match="route_to_staff"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_parcel_fact_source_contracts(tmp_path: Path):
    payload = _prepared_payload()
    payload["parcel_scope"]["facts"][0]["source_id"] = "synthetic-process-page"
    with pytest.raises(ValueError, match="parcel_dataset source"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    payload = _prepared_payload()
    payload["parcel_scope"]["facts"][0]["source_field"] = None
    with pytest.raises(ValueError, match="requires source_id and source_field"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    for method in ("applicant_assertion", "staff_confirmation"):
        payload = _prepared_payload()
        fact = payload["parcel_scope"]["facts"][0]
        fact["collection_method"] = method
        fact["source_id"] = None
        fact["source_field"] = None
        payload["sources"] = [
            source
            for source in payload["sources"]
            if source["source_id"] != "synthetic-parcel-dataset"
        ]
        intake = load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)
        assert intake.parcel_fact_count == 1

    payload = _prepared_payload()
    payload["parcel_scope"]["facts"][0]["collection_method"] = "applicant_assertion"
    with pytest.raises(ValueError, match="cannot claim source bindings"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_exceptions_and_conflicts_remain_candidates_and_unresolved(tmp_path: Path):
    payload = _prepared_payload()
    _add_open_question(payload)
    payload["exception_review"]["items"] = [
        {
            "exception_id": "synthetic-exception",
            "candidate_summary": "Potential exception requiring source review.",
            "passage_ids": ["synthetic-ordinance-section-one"],
            "question_id": "synthetic-conflict-question",
        }
    ]
    payload["conflict_review"]["items"] = [
        {
            "conflict_id": "synthetic-source-conflict",
            "candidate_summary": "Candidate materials appear inconsistent.",
            "source_ids": ["synthetic-ordinance", "synthetic-process-page"],
            "passage_ids": ["synthetic-ordinance-section-one"],
            "resolution_status": "unresolved",
            "question_id": "synthetic-conflict-question",
        }
    ]
    intake = load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)
    assert intake.open_question_count == 1

    payload["conflict_review"]["items"][0]["resolution_status"] = "resolved"
    with pytest.raises(ValueError, match="must remain 'unresolved'"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_exception_and_conflict_records_require_open_question_references(
    tmp_path: Path,
):
    payload = _prepared_payload()
    _add_open_question(payload)
    payload["exception_review"]["items"] = [
        {
            "exception_id": "synthetic-exception",
            "candidate_summary": "Potential exception.",
            "passage_ids": ["synthetic-ordinance-section-one"],
            "question_id": "missing-question",
        }
    ]
    with pytest.raises(ValueError, match="unknown open question"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    payload = _prepared_payload()
    _add_open_question(payload)
    payload["conflict_review"]["items"] = [
        {
            "conflict_id": "synthetic-conflict",
            "candidate_summary": "Potential conflict.",
            "source_ids": ["synthetic-ordinance"],
            "passage_ids": [],
            "resolution_status": "unresolved",
            "question_id": "synthetic-conflict-question",
        }
    ]
    with pytest.raises(ValueError, match="at least 2 source"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_not_run_exception_or_conflict_state_cannot_contain_items(tmp_path: Path):
    payload = _prepared_payload()
    _add_open_question(payload)
    payload["exception_review"].update(
        {
            "status": "not_run",
            "items": [
                {
                    "exception_id": "synthetic-exception",
                    "candidate_summary": "Potential exception.",
                    "passage_ids": ["synthetic-ordinance-section-one"],
                    "question_id": "synthetic-conflict-question",
                }
            ],
        }
    )
    with pytest.raises(ValueError, match="not_run cannot contain items"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_prepared_questions_require_owner_role(tmp_path: Path):
    payload = _prepared_payload()
    _add_open_question(payload)
    payload["open_questions"][0]["owner_role"] = None
    with pytest.raises(ValueError, match="owner_role"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    payload = _prepared_payload()
    _add_open_question(payload)
    payload["open_questions"][0]["owner_role"] = "tbd"
    with pytest.raises(ValueError, match="placeholder owner roles"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


@pytest.mark.parametrize("cadence", [True, 0, 367, "90"])
def test_reverification_cadence_is_bounded(tmp_path: Path, cadence: object):
    payload = _prepared_payload()
    payload["review_plan"]["reverification_cadence_days"] = cadence
    with pytest.raises(ValueError, match="integer from 1 to 366"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_prepared_sources_must_be_inside_planned_reverification_cadence(
    tmp_path: Path,
):
    payload = _prepared_payload()
    payload["review_plan"]["reverification_cadence_days"] = 5
    with pytest.raises(ValueError, match="outside the planned cadence"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_ids_and_lists_must_be_stable_unique_and_sorted(tmp_path: Path):
    payload = _prepared_payload()
    payload["onboarding_id"] = "Not Stable"
    with pytest.raises(ValueError, match="stable ID"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    payload = _prepared_payload()
    payload["sources"].reverse()
    with pytest.raises(ValueError, match="unique and sorted"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    payload = _prepared_payload()
    payload["project_scope"]["included_project_types"] = ["Z", "A"]
    with pytest.raises(ValueError, match="unique and sorted"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    payload = _prepared_payload()
    payload["project_scope"]["excluded_project_types"] = ["New detached ADU"]
    with pytest.raises(ValueError, match="overlap"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_exact_schema_rejects_unknown_missing_and_wrong_root_shapes(tmp_path: Path):
    payload = _payload()
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    payload = _payload()
    del payload["project_scope"]
    with pytest.raises(ValueError, match="missing fields"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)

    with pytest.raises(ValueError, match="root: expected an object"):
        load_local_source_onboarding(_write(tmp_path, []), today=AS_OF)

    payload = _payload()
    payload["sources"] = ["not-an-object"]
    with pytest.raises(ValueError, match="expected an object"):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_duplicate_json_object_fields_are_rejected(tmp_path: Path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON field"):
        load_local_source_onboarding(path, today=AS_OF)


def test_parser_rejects_nonfinite_oversize_and_non_utf8_inputs(tmp_path: Path):
    with pytest.raises(ValueError, match="regular file"):
        load_local_source_onboarding(tmp_path, today=AS_OF)

    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"schema_version":NaN}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite JSON value NaN"):
        load_local_source_onboarding(nonfinite, today=AS_OF)

    oversize = tmp_path / "oversize.json"
    oversize.write_bytes(b" " * (MAX_INTAKE_BYTES + 1))
    with pytest.raises(ValueError, match="1048576-byte limit"):
        load_local_source_onboarding(oversize, today=AS_OF)

    non_utf8 = tmp_path / "non-utf8.json"
    non_utf8.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="not valid UTF-8"):
        load_local_source_onboarding(non_utf8, today=AS_OF)

    nested = tmp_path / "nested.json"
    nested.write_text("[" * 100_000 + "0" + "]" * 100_000, encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_local_source_onboarding(nested, today=AS_OF)


def test_malformed_missing_and_future_template_inputs_fail(tmp_path: Path):
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{bad", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_local_source_onboarding(malformed, today=AS_OF)

    with pytest.raises(ValueError, match="could not be read"):
        load_local_source_onboarding(tmp_path / "missing.json", today=AS_OF)

    with pytest.raises(ValueError, match="future dates"):
        load_local_source_onboarding(TEMPLATE, today=date(2026, 8, 8))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", 2, "schema_version"),
        ("schema_version", True, "schema_version"),
        ("schema_version", 1.0, "schema_version"),
        ("record_type", "local_layer", "record_type"),
        ("status", " prepared_for_review ", "unsupported value"),
        ("template_version", "2.0.0", "template_version"),
        ("template_published_on", "2026-08-08", "template_published_on"),
    ],
)
def test_root_identity_is_pinned(
    tmp_path: Path, field: str, value: object, message: str
):
    payload = _payload()
    payload[field] = value
    with pytest.raises(ValueError, match=message):
        load_local_source_onboarding(_write(tmp_path, payload), today=AS_OF)


def test_cli_emits_machine_readable_non_claim_summary(
    capsys: pytest.CaptureFixture[str],
):
    assert main(["--root", str(ROOT), "validate", "--as-of", "2026-08-09"]) == 0
    output = json.loads(capsys.readouterr().out)

    assert output["record_status"] == "not_run"
    assert output["review_status"] == "not_run"
    assert output["local_layer_status"] == "not_encoded"
    assert output["ready_for_review"] is False
    assert output["ready_for_review_as_of"] is False
    assert output["validated_as_of"] == "2026-08-09"
    assert output["validation_mode"] == "historical_replay"
    assert output["earliest_reverification_due_on"] is None
    assert output["supports_review_claim"] is False
    assert output["supports_approval_claim"] is False
    assert output["supports_local_layer_claim"] is False


def test_cli_historical_replay_never_reports_current_review_readiness(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    _write(tmp_path, _prepared_payload())
    assert (
        main(
            [
                "--root",
                str(tmp_path),
                "validate",
                "--input",
                "intake.json",
                "--as-of",
                "2026-08-09",
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)

    assert output["ready_for_review"] is False
    assert output["ready_for_review_as_of"] is True
    assert output["validation_mode"] == "historical_replay"
    assert output["validated_as_of"] == "2026-08-09"
    assert output["earliest_reverification_due_on"] == "2026-10-30"


def test_cli_rejects_input_that_resolves_outside_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    outside = tmp_path.parent / "outside-intake.json"
    outside.write_text("{}", encoding="utf-8")

    assert (
        main(
            [
                "--root",
                str(tmp_path),
                "validate",
                "--input",
                str(outside),
            ]
        )
        == 2
    )
    assert "inside --root" in capsys.readouterr().err


def test_cli_returns_two_for_invalid_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    invalid = _payload()
    invalid["status"] = "approved"
    path = _write(tmp_path, invalid)

    assert (
        main(
            [
                "--root",
                str(ROOT),
                "validate",
                "--input",
                str(path),
                "--as-of",
                "2026-08-09",
            ]
        )
        == 2
    )
    assert "invalid input" in capsys.readouterr().err


def test_cli_module_entrypoint_runs_without_writes():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "permit_pathways.local_source_onboarding_cli",
            "--root",
            str(ROOT),
            "validate",
            "--as-of",
            "2026-08-09",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["supports_local_layer_claim"] is False
