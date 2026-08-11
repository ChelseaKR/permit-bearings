from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from permit_pathways.journey import (
    JourneyConfig,
    load_journey_config,
    resolve_journey,
)
from permit_pathways.readiness import (
    ReadinessPacket,
    ReadinessResult,
    ReadinessWorkflow,
    load_and_evaluate_readiness,
)
from permit_pathways.screening import Rule, load_rules

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 8, 11)
JOURNEY_PATH = ROOT / "data" / "journeys" / "woodland-preapproved-detached-adu.json"
GOLDEN_PATH = ROOT / "data" / "golden" / "example.json"
RULES_PATH = ROOT / "data" / "rules"
WORKFLOW_PATH = (
    ROOT / "data" / "readiness" / "workflows" / "woodland-preapproved-detached-adu.json"
)
PACKET_PATH = ROOT / "data" / "readiness" / "samples" / "woodland-preapproved-adu.json"
SOURCES_PATH = ROOT / "data" / "sources.json"


@pytest.fixture(scope="module")
def canonical() -> tuple[
    JourneyConfig,
    list[Rule],
    ReadinessWorkflow,
    ReadinessPacket,
    ReadinessResult,
]:
    config = load_journey_config(JOURNEY_PATH)
    rules = load_rules(RULES_PATH, today=AS_OF)
    workflow, packet, result = load_and_evaluate_readiness(
        WORKFLOW_PATH,
        PACKET_PATH,
        SOURCES_PATH,
        today=AS_OF,
    )
    return config, rules, workflow, packet, result


def _resolve(
    canonical: tuple[
        JourneyConfig,
        list[Rule],
        ReadinessWorkflow,
        ReadinessPacket,
        ReadinessResult,
    ],
    *,
    config: JourneyConfig | None = None,
    rules: list[Rule] | None = None,
    workflow: ReadinessWorkflow | None = None,
    packet: ReadinessPacket | None = None,
    result: ReadinessResult | None = None,
) -> dict[str, object]:
    base_config, base_rules, base_workflow, base_packet, base_result = canonical
    return resolve_journey(
        config or base_config,
        GOLDEN_PATH,
        rules or base_rules,
        workflow or base_workflow,
        packet or base_packet,
        result or base_result,
    )


def _packet_fact_variant(
    packet: ReadinessPacket,
    fact_id: str,
    **changes: object,
) -> ReadinessPacket:
    return replace(
        packet,
        facts=tuple(
            replace(fact, **changes) if fact.fact_id == fact_id else fact
            for fact in packet.facts
        ),
    )


def _write_config(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / "journey.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def test_canonical_journey_resolution_is_deterministic_and_source_bound(
    canonical,
):
    config, _rules, workflow, packet, result = canonical

    first = _resolve(canonical)
    second = _resolve(canonical)

    assert first == second
    assert first["journey_id"] == "woodland-preapproved-detached-adu-synthetic"
    assert first["version"] == "1.0.0"
    assert first["synthetic"] is True
    assert first["screening_case_id"] == "woodland-new-detached-adu-local-layer"
    assert first["candidate_route_rule_ids"] == ["adu-ministerial-review"]
    assert first["applicability_status"] == "applies"
    assert first["readiness_workflow_fingerprint"] == result.workflow_fingerprint
    assert first["readiness_packet_fingerprint"] == result.packet_fingerprint
    assert first["readiness_evidence_manifest"] == result.to_manifest(workflow, packet)

    routes = first["candidate_routes"]
    assert isinstance(routes, list)
    assert [route["rule_id"] for route in routes] == ["adu-ministerial-review"]
    assert routes[0]["citation"]["verified_on"] == "2026-07-27"
    assert routes[0]["source_status"] == "current"
    assert routes[0]["source_status_as_of"] == "2026-07-30"
    assert routes[0]["source_review_due_on"] == "2027-01-23"
    assert routes[0]["rule_fingerprint"].startswith("sha256:")
    assert first["route_source_status"] == "current"
    assert first["route_source_status_as_of"] == "2026-07-30"
    assert first["route_source_review_due_on"] == "2027-01-23"

    facts = first["applicability_facts"]
    assert isinstance(facts, list)
    assert [fact["fact_id"] for fact in facts] == [
        "uses_city_preapproved_plan",
        "parcel_city_matches_woodland",
        "parcel_land_use_is_residential",
    ]
    assert [fact["fact_id"] for fact in facts if fact["editable"]] == [
        "uses_city_preapproved_plan"
    ]
    assert all(fact["value"] == fact["expected_value"] == "yes" for fact in facts)
    fact_envelope = first["fact_envelope"]
    assert isinstance(fact_envelope, dict)
    assert fact_envelope["synthetic"] is True
    assert all(
        fact["provenance"] == "synthetic_golden_fixture"
        for fact in fact_envelope["screening_facts"]
    )
    encoded_envelope = json.dumps(
        fact_envelope,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    expected_envelope_fingerprint = (
        "sha256:" + hashlib.sha256(encoded_envelope.encode("utf-8")).hexdigest()
    )
    assert first["screening_case_fingerprint"].startswith("sha256:")
    assert first["fact_envelope_fingerprint"] == expected_envelope_fingerprint
    assert first["journey_fingerprint"].startswith("sha256:")
    assert first["boundary"] == config.boundary


@pytest.mark.parametrize(
    ("candidate_rule_ids", "message"),
    [
        (("missing-route",), "does not match its case"),
        (("adu-height-standards",), "is not a route record"),
    ],
)
def test_resolution_rejects_missing_or_non_route_candidates(
    canonical,
    candidate_rule_ids,
    message,
):
    config = replace(canonical[0], candidate_route_rule_ids=candidate_rule_ids)

    with pytest.raises(ValueError, match=message):
        _resolve(canonical, config=config)


def test_resolution_rejects_a_stale_candidate_route(canonical):
    stale_rules = [
        replace(
            rule,
            citation=replace(rule.citation, verified_on="2025-01-01"),
        )
        if rule.rule_id == "adu-ministerial-review"
        else rule
        for rule in canonical[1]
    ]

    with pytest.raises(ValueError, match="is not current"):
        _resolve(canonical, rules=stale_rules)


def test_resolution_rejects_drift_elsewhere_in_the_golden_case(canonical):
    incomplete_rules = [
        rule for rule in canonical[1] if rule.rule_id != "adu-height-standards"
    ]

    with pytest.raises(ValueError, match="screening case no longer matches"):
        _resolve(canonical, rules=incomplete_rules)


def test_resolution_rejects_readiness_reference_drift(canonical):
    workflow = replace(canonical[2], workflow_id="different-workflow")
    with pytest.raises(ValueError, match="workflow ID does not match"):
        _resolve(canonical, workflow=workflow)

    packet = replace(canonical[3], packet_id="different-packet")
    with pytest.raises(ValueError, match="packet ID does not match"):
        _resolve(canonical, packet=packet)

    packet = replace(canonical[3], synthetic=False)
    with pytest.raises(ValueError, match="packet must be synthetic"):
        _resolve(canonical, packet=packet)


def test_resolution_rejects_nonapplicable_or_mismatched_result(canonical):
    result = replace(canonical[4], applicability_status="unknown")
    with pytest.raises(ValueError, match="canonical readiness result must apply"):
        _resolve(canonical, result=result)


def test_resolution_rejects_source_or_fingerprint_drift(canonical):
    result = replace(canonical[4], source_status="changed")
    with pytest.raises(ValueError, match="sources must be current"):
        _resolve(canonical, result=result)

    workflow = replace(canonical[2], title="Changed title")
    with pytest.raises(ValueError, match="workflow fingerprint does not match"):
        _resolve(canonical, workflow=workflow)

    packet = replace(canonical[3], label="Changed label")
    with pytest.raises(ValueError, match="packet fingerprint does not match"):
        _resolve(canonical, packet=packet)


def test_resolution_rejects_evaluation_date_drift(canonical):
    result = replace(canonical[4], evaluated_on="2026-07-29")

    with pytest.raises(ValueError, match="evaluation dates do not match"):
        _resolve(canonical, result=result)

    result = replace(canonical[4], packet_id="different-packet")
    with pytest.raises(ValueError, match="readiness result IDs do not match"):
        _resolve(canonical, result=result)


def test_resolution_rejects_screening_and_packet_scope_drift(canonical):
    packet = replace(canonical[3], jurisdiction="davis")
    result = replace(canonical[4], packet_fingerprint=packet.fingerprint())

    with pytest.raises(ValueError, match="screening and readiness scope do not match"):
        _resolve(canonical, packet=packet, result=result)


def test_resolution_rejects_applicability_fact_value_or_provenance_drift(canonical):
    packet = _packet_fact_variant(
        canonical[3],
        "uses_city_preapproved_plan",
        value="unknown",
    )
    result = replace(canonical[4], packet_fingerprint=packet.fingerprint())
    with pytest.raises(ValueError, match="does not satisfy applicability"):
        _resolve(canonical, packet=packet, result=result)

    packet = _packet_fact_variant(
        canonical[3],
        "uses_city_preapproved_plan",
        provenance="synthetic_public_record_fixture",
    )
    result = replace(canonical[4], packet_fingerprint=packet.fingerprint())
    with pytest.raises(ValueError, match="is not applicant asserted"):
        _resolve(canonical, packet=packet, result=result)

    packet = replace(
        canonical[3],
        facts=tuple(
            fact
            for fact in canonical[3].facts
            if fact.fact_id != "uses_city_preapproved_plan"
        ),
    )
    result = replace(canonical[4], packet_fingerprint=packet.fingerprint())
    with pytest.raises(ValueError, match=r"applicability fact .* is missing"):
        _resolve(canonical, packet=packet, result=result)


def test_resolution_rejects_editable_facts_outside_applicability(canonical):
    config = replace(
        canonical[0],
        editable_applicability_fact_ids=("connects_to_primary_home_electrical",),
    )

    with pytest.raises(ValueError, match="editable facts must control applicability"):
        _resolve(canonical, config=config)


def test_config_loader_rejects_unknown_fields_and_wrong_schema(tmp_path: Path):
    payload = json.loads(JOURNEY_PATH.read_text(encoding="utf-8"))
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="unknown fields: unexpected"):
        load_journey_config(_write_config(tmp_path, payload))

    payload = json.loads(JOURNEY_PATH.read_text(encoding="utf-8"))
    payload["schema_version"] = 2
    with pytest.raises(ValueError, match="schema_version: expected 1"):
        load_journey_config(_write_config(tmp_path, payload))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("version", "v1", "expected semantic version"),
        ("status", "approved", "unsupported status"),
        ("synthetic", False, "expected true"),
        ("journey_id", "Not stable", "invalid stable identifier"),
        (
            "candidate_route_rule_ids",
            ["adu-ministerial-review", "adu-ministerial-review"],
            "duplicate values are not allowed",
        ),
    ],
)
def test_config_loader_rejects_invalid_journey_fields(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
):
    payload = copy.deepcopy(json.loads(JOURNEY_PATH.read_text(encoding="utf-8")))
    payload["journey"][field] = value

    with pytest.raises(ValueError, match=message):
        load_journey_config(_write_config(tmp_path, payload))
