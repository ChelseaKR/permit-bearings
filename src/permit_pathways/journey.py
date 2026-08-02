"""Versioned composition of one synthetic route-to-packet journey.

The canonical journey record contains references only. This module resolves
those references against the existing golden screening case, source-bound
rules, readiness workflow, and readiness packet. It never evaluates packet
requirements a second time.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .explanations import rule_fingerprint
from .readiness import (
    SOURCE_MAX_AGE_DAYS,
    ReadinessPacket,
    ReadinessResult,
    ReadinessWorkflow,
)
from .screening import Rule, screen

SCHEMA_VERSION = 1
JOURNEY_STATUSES = ("prototype",)

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class JourneyConfig:
    journey_id: str
    version: str
    status: str
    label: str
    synthetic: bool
    screening_case_id: str
    candidate_route_rule_ids: tuple[str, ...]
    readiness_workflow_id: str
    readiness_packet_id: str
    editable_applicability_fact_ids: tuple[str, ...]
    boundary: str


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected non-blank text")
    return value.strip()


def _identifier(value: Any, field: str) -> str:
    identifier = _required_text(value, field)
    if not _IDENTIFIER.fullmatch(identifier):
        raise ValueError(f"{field}: invalid stable identifier")
    return identifier


def _identifier_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field}: expected a non-empty list")
    identifiers = tuple(
        _identifier(item, f"{field}[{index}]") for index, item in enumerate(value)
    )
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f"{field}: duplicate values are not allowed")
    return identifiers


def _exact_keys(
    record: dict[str, Any],
    expected: set[str],
    field: str,
) -> None:
    unknown = sorted(set(record) - expected)
    missing = sorted(expected - set(record))
    if unknown:
        raise ValueError(f"{field}: unknown fields: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{field}: missing fields: {', '.join(missing)}")


def _load_json(path: Path, field: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{field}: could not load JSON") from error


def _fingerprint(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_journey_config(path: Path) -> JourneyConfig:
    """Load one strict reference-only journey definition."""

    raw = _load_json(path, str(path))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected an object")
    _exact_keys(raw, {"schema_version", "journey"}, str(path))
    if raw["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"{path}.schema_version: expected {SCHEMA_VERSION}")
    record = raw["journey"]
    if not isinstance(record, dict):
        raise ValueError(f"{path}.journey: expected an object")
    expected = {
        "journey_id",
        "version",
        "status",
        "label",
        "synthetic",
        "screening_case_id",
        "candidate_route_rule_ids",
        "readiness_workflow_id",
        "readiness_packet_id",
        "editable_applicability_fact_ids",
        "boundary",
    }
    _exact_keys(record, expected, f"{path}.journey")
    version = _required_text(record["version"], f"{path}.journey.version")
    if not _SEMVER.fullmatch(version):
        raise ValueError(f"{path}.journey.version: expected semantic version")
    status = _required_text(record["status"], f"{path}.journey.status")
    if status not in JOURNEY_STATUSES:
        raise ValueError(f"{path}.journey.status: unsupported status")
    if record["synthetic"] is not True:
        raise ValueError(f"{path}.journey.synthetic: expected true")
    return JourneyConfig(
        journey_id=_identifier(record["journey_id"], f"{path}.journey.journey_id"),
        version=version,
        status=status,
        label=_required_text(record["label"], f"{path}.journey.label"),
        synthetic=True,
        screening_case_id=_identifier(
            record["screening_case_id"],
            f"{path}.journey.screening_case_id",
        ),
        candidate_route_rule_ids=_identifier_list(
            record["candidate_route_rule_ids"],
            f"{path}.journey.candidate_route_rule_ids",
        ),
        readiness_workflow_id=_identifier(
            record["readiness_workflow_id"],
            f"{path}.journey.readiness_workflow_id",
        ),
        readiness_packet_id=_identifier(
            record["readiness_packet_id"],
            f"{path}.journey.readiness_packet_id",
        ),
        editable_applicability_fact_ids=_identifier_list(
            record["editable_applicability_fact_ids"],
            f"{path}.journey.editable_applicability_fact_ids",
        ),
        boundary=_required_text(record["boundary"], f"{path}.journey.boundary"),
    )


def _screening_case(path: Path, case_id: str) -> dict[str, Any]:
    raw = _load_json(path, str(path))
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected a list")
    matches = [
        record
        for record in raw
        if isinstance(record, dict) and record.get("case_id") == case_id
    ]
    if len(matches) != 1:
        raise ValueError(f"{path}: expected exactly one {case_id!r} case")
    record = matches[0]
    if not isinstance(record.get("intake"), dict):
        raise ValueError(f"{case_id}.intake: expected an object")
    expected_ids = record.get("expected_rule_ids")
    if (
        not isinstance(expected_ids, list)
        or not expected_ids
        or any(not isinstance(item, str) or not item for item in expected_ids)
        or len(expected_ids) != len(set(expected_ids))
    ):
        raise ValueError(f"{case_id}.expected_rule_ids: invalid rule IDs")
    return record


def _candidate_routes(
    config: JourneyConfig,
    case: dict[str, Any],
    rules: list[Rule],
    evaluated_on: str,
) -> list[dict[str, Any]]:
    intake = case["intake"]
    expected_ids = set(case["expected_rule_ids"])
    matched_results = screen(intake, rules)
    matched = {result.rule.rule_id: result.rule for result in matched_results}
    if set(matched) != expected_ids:
        raise ValueError("journey screening case no longer matches its rules")
    as_of = date.fromisoformat(evaluated_on)
    routes: list[dict[str, Any]] = []
    for rule_id in config.candidate_route_rule_ids:
        rule = matched.get(rule_id)
        if rule is None or rule_id not in expected_ids:
            raise ValueError(f"journey route {rule_id!r} does not match its case")
        if rule.display_group != "route":
            raise ValueError(f"journey route {rule_id!r} is not a route record")
        verified_on = rule.citation.verified_on
        if verified_on is None or rule.citation.is_stale(
            SOURCE_MAX_AGE_DAYS,
            as_of,
        ):
            raise ValueError(f"journey route {rule_id!r} is not current")
        review_due_on = (
            date.fromisoformat(verified_on) + timedelta(days=SOURCE_MAX_AGE_DAYS)
        ).isoformat()
        routes.append(
            {
                "rule_id": rule.rule_id,
                "pathway": rule.pathway,
                "route_class": rule.route_class,
                "jurisdiction_scope": rule.jurisdiction_scope,
                "citation": asdict(rule.citation),
                "source_dependencies": list(rule.source_dependencies),
                "source_status": "current",
                "source_status_as_of": evaluated_on,
                "source_review_due_on": review_due_on,
                "rule_fingerprint": rule_fingerprint(rule),
            }
        )
    return routes


def _applicability_facts(
    config: JourneyConfig,
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
) -> list[dict[str, Any]]:
    definitions = workflow.fact_map()
    packet_facts = {fact.fact_id: fact for fact in packet.facts}
    applicability_ids = tuple(condition.fact_id for condition in workflow.applicability)
    if len(applicability_ids) != len(set(applicability_ids)):
        raise ValueError("workflow applicability facts must be unique")
    editable = set(config.editable_applicability_fact_ids)
    if not editable <= set(applicability_ids):
        raise ValueError("journey editable facts must control applicability")
    resolved: list[dict[str, Any]] = []
    for condition in workflow.applicability:
        definition = definitions.get(condition.fact_id)
        fact = packet_facts.get(condition.fact_id)
        if definition is None or fact is None:
            raise ValueError(
                f"journey applicability fact {condition.fact_id!r} is missing"
            )
        if fact.value != condition.equals:
            raise ValueError(
                f"journey fact {fact.fact_id!r} does not satisfy applicability"
            )
        is_editable = fact.fact_id in editable
        if is_editable and fact.provenance not in {
            "synthetic_applicant_assertion",
            "applicant_assertion",
        }:
            raise ValueError(
                f"journey editable fact {fact.fact_id!r} is not applicant asserted"
            )
        resolved.append(
            {
                **asdict(fact),
                "label": definition.label,
                "question": definition.question,
                "expected_value": condition.equals,
                "editable": is_editable,
            }
        )
    return resolved


def _validate_readiness_binding(
    config: JourneyConfig,
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
    result: ReadinessResult,
) -> None:
    if workflow.workflow_id != config.readiness_workflow_id:
        raise ValueError("journey readiness workflow ID does not match")
    if packet.packet_id != config.readiness_packet_id:
        raise ValueError("journey readiness packet ID does not match")
    if not packet.synthetic:
        raise ValueError("journey readiness packet must be synthetic")
    if result.applicability_status != "applies":
        raise ValueError("journey canonical readiness result must apply")
    if result.source_status != "current":
        raise ValueError("journey canonical readiness sources must be current")
    if (
        result.workflow_id != workflow.workflow_id
        or result.packet_id != packet.packet_id
    ):
        raise ValueError("journey readiness result IDs do not match")
    if result.workflow_fingerprint != workflow.fingerprint():
        raise ValueError("journey readiness workflow fingerprint does not match")
    if result.packet_fingerprint != packet.fingerprint():
        raise ValueError("journey readiness packet fingerprint does not match")
    if result.evaluated_on != packet.evaluated_on:
        raise ValueError("journey readiness evaluation dates do not match")


def resolve_journey(
    config: JourneyConfig,
    golden_path: Path,
    rules: list[Rule],
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
    result: ReadinessResult,
) -> dict[str, Any]:
    """Resolve references into one deterministic, fingerprinted envelope."""

    _validate_readiness_binding(config, workflow, packet, result)
    case = _screening_case(golden_path, config.screening_case_id)
    intake = case["intake"]
    if any(
        intake.get(field) != getattr(workflow, field)
        or intake.get(field) != getattr(packet, field)
        for field in ("jurisdiction", "project_type")
    ):
        raise ValueError("journey screening and readiness scope do not match")
    routes = _candidate_routes(
        config,
        case,
        rules,
        result.evaluated_on,
    )
    applicability = _applicability_facts(config, workflow, packet)
    fact_envelope = {
        "schema_version": SCHEMA_VERSION,
        "synthetic": True,
        "screening_facts": [
            {
                "fact_id": fact_id,
                "value": intake[fact_id],
                "provenance": "synthetic_golden_fixture",
            }
            for fact_id in sorted(intake)
        ],
        "readiness_facts": [asdict(fact) for fact in packet.facts],
    }
    config_payload = asdict(config)
    config_payload["candidate_route_rule_ids"] = list(config.candidate_route_rule_ids)
    config_payload["editable_applicability_fact_ids"] = list(
        config.editable_applicability_fact_ids
    )
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        **config_payload,
        "screening_intake": intake,
        "screening_expected_rule_ids": case["expected_rule_ids"],
        "screening_case_fingerprint": _fingerprint(case),
        "candidate_routes": routes,
        "route_source_status": "current",
        "route_source_status_as_of": result.evaluated_on,
        "route_source_review_due_on": min(
            route["source_review_due_on"] for route in routes
        ),
        "readiness_workflow_fingerprint": result.workflow_fingerprint,
        "readiness_packet_fingerprint": result.packet_fingerprint,
        "applicability_status": result.applicability_status,
        "applicability_facts": applicability,
        "fact_envelope": fact_envelope,
        "fact_envelope_fingerprint": _fingerprint(fact_envelope),
        "readiness_evidence_manifest": result.to_manifest(workflow, packet),
    }
    manifest["journey_fingerprint"] = _fingerprint(manifest)
    return manifest
