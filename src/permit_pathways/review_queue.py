"""Portable, source-change re-verification worklists.

This module turns a validated source-state receipt into a deterministic
worklist for people who maintain the repository's published evidence. It is
not an approval workflow: a worklist decision cannot change a rule match,
clear a source-state hold, promote a verification level, or publish a
replacement record. Those actions remain separate, explicit repository
maintenance steps.

Only a source that was fetched and recorded as ``changed`` creates work.
An ``unverifiable`` fetch remains a warning in the source-state receipt and
never becomes a re-verification task here.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .dates import resolve_today
from .explanations import rule_fingerprint
from .harness.runner import GoldenCase
from .harness.watch import SourceRecord
from .journey import JourneyConfig
from .readiness import (
    FactDefinition,
    PacketFact,
    ReadinessPacket,
    ReadinessRemedies,
    ReadinessRemedy,
    ReadinessWorkflow,
    Requirement,
    SourceBinding,
)
from .screening import Rule, screen
from .source_state import SourceStateSnapshot, source_state_fingerprint

WORKLIST_SCHEMA_VERSION = 2
DECISIONS_SCHEMA_VERSION = 1
WORKLIST_STATUSES = ("clear", "open")
DECISION_STATUSES = ("unassigned", "assigned", "resolved")
DECISION_DISPOSITIONS = ("retain", "revise", "suppress", "route_to_staff")

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_WORK_ITEM_IDENTIFIER = re.compile(
    r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*:"
    r"[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$"
)
_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")
_OWNER_CODE = re.compile(r"^[A-Z][A-Z0-9_-]{1,15}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _fingerprint(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _work_item_identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _WORK_ITEM_IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field}: expected a stable work item identifier")
    return value


def _iso_date(value: Any, field: str, *, today: date) -> str:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise ValueError(f"{field}: expected YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field}: invalid calendar date") from error
    if parsed > today:
        raise ValueError(f"{field}: future dates are not allowed")
    return value


def _exact_keys(value: Any, expected: set[str], field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    unknown = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    if unknown:
        raise ValueError(f"{field}: unknown fields: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{field}: missing fields: {', '.join(missing)}")
    return value


@dataclass(frozen=True)
class ChangedSource:
    """One fetched source whose observed digest differs from its baseline."""

    source_id: str
    label: str
    url: str
    recorded_sha256: str
    observed_sha256: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ReadinessReviewContext:
    """One portable packet and handoff trace to re-verify after source change.

    The context holds already validated canonical records. It does not evaluate
    a packet, create a route, or allow an item decision to change any output.
    """

    workflow: ReadinessWorkflow
    packet: ReadinessPacket
    remedies: ReadinessRemedies
    journeys: tuple[JourneyConfig, ...] = ()


@dataclass(frozen=True)
class JourneyHandoffBinding:
    """The versioned journey record that can expose a packet handoff."""

    journey_id: str
    version: str
    configuration_fingerprint: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ReadinessContextBinding:
    """Fingerprint bindings for one packet context, even when no task is open."""

    workflow_id: str
    workflow_fingerprint: str
    packet_id: str
    packet_fingerprint: str
    remedies_version: str
    remedies_content_fingerprint: str
    journeys: tuple[JourneyHandoffBinding, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_fingerprint": self.workflow_fingerprint,
            "packet_id": self.packet_id,
            "packet_fingerprint": self.packet_fingerprint,
            "remedies_version": self.remedies_version,
            "remedies_content_fingerprint": self.remedies_content_fingerprint,
            "journeys": [journey.to_dict() for journey in self.journeys],
        }


@dataclass(frozen=True)
class ReviewWorkItem:
    """A deterministic work target, never a completed human decision."""

    item_id: str
    item_type: str
    target_id: str
    source_ids: tuple[str, ...]
    target_fingerprint: str
    reason: str

    def payload(self) -> dict[str, object]:
        return {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "target_id": self.target_id,
            "source_ids": list(self.source_ids),
            "target_fingerprint": self.target_fingerprint,
            "reason": self.reason,
        }

    def fingerprint(self) -> str:
        return _fingerprint(self.payload())

    def to_dict(self) -> dict[str, object]:
        return {**self.payload(), "item_fingerprint": self.fingerprint()}


@dataclass(frozen=True)
class ReviewWorklist:
    """Generated worklist bound to a single source-state receipt."""

    worklist_id: str
    source_snapshot_id: str
    source_snapshot_fingerprint: str
    checked_at: str
    receipt_status: str
    changed_source_ids: tuple[str, ...]
    unverifiable_source_ids: tuple[str, ...]
    changed_sources: tuple[ChangedSource, ...]
    readiness_contexts: tuple[ReadinessContextBinding, ...]
    status: str
    items: tuple[ReviewWorkItem, ...]

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": WORKLIST_SCHEMA_VERSION,
            "worklist_id": self.worklist_id,
            "source_state": {
                "snapshot_id": self.source_snapshot_id,
                "snapshot_fingerprint": self.source_snapshot_fingerprint,
                "checked_at": self.checked_at,
                "receipt_status": self.receipt_status,
                "changed_source_ids": list(self.changed_source_ids),
                "unverifiable_source_ids": list(self.unverifiable_source_ids),
            },
            "status": self.status,
            "changed_sources": [source.to_dict() for source in self.changed_sources],
            "readiness_contexts": [
                context.to_dict() for context in self.readiness_contexts
            ],
            "items": [item.to_dict() for item in self.items],
        }

    def fingerprint(self) -> str:
        return _fingerprint(self.payload())

    def to_dict(self) -> dict[str, object]:
        return {**self.payload(), "worklist_fingerprint": self.fingerprint()}

    def item_map(self) -> dict[str, ReviewWorkItem]:
        return {item.item_id: item for item in self.items}

    def summary(self) -> str:
        return (
            f"{len(self.items)} source-change work item(s) "
            f"for snapshot {self.source_snapshot_id} ({self.status})"
        )


@dataclass(frozen=True)
class ReviewDecision:
    """A human-maintained ledger entry bound to one generated work item."""

    item_id: str
    item_fingerprint: str
    status: str
    owner_code: str | None
    assigned_on: str | None
    disposition: str | None
    decided_on: str | None
    evidence_receipt_id: str | None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewDecisionLedger:
    """Separate decisions that deliberately cannot alter the worklist's holds."""

    worklist_id: str
    worklist_fingerprint: str
    entries: tuple[ReviewDecision, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": DECISIONS_SCHEMA_VERSION,
            "worklist_id": self.worklist_id,
            "worklist_fingerprint": self.worklist_fingerprint,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def fingerprint(self) -> str:
        """Bind a release receipt to the exact complete decision ledger."""

        return _fingerprint(self.to_dict())

    def summary(self) -> str:
        counts = {status: 0 for status in DECISION_STATUSES}
        for entry in self.entries:
            counts[entry.status] += 1
        return (
            f"{len(self.entries)} decision record(s): "
            f"{counts['unassigned']} unassigned, {counts['assigned']} assigned, "
            f"{counts['resolved']} resolved. Decisions cannot clear source-state "
            "holds, rule matching, verification levels, or publication."
        )


def _rules_by_id(rules: Sequence[Rule]) -> dict[str, Rule]:
    result: dict[str, Rule] = {}
    for rule in rules:
        if rule.rule_id in result:
            raise ValueError("canonical rules contain duplicate rule IDs")
        result[rule.rule_id] = rule
    return result


def _golden_by_id(cases: Sequence[GoldenCase]) -> dict[str, GoldenCase]:
    result: dict[str, GoldenCase] = {}
    for case in cases:
        if case.case_id in result:
            raise ValueError("canonical Golden cases contain duplicate case IDs")
        result[case.case_id] = case
    return result


def _changed_observations(
    snapshot: SourceStateSnapshot,
    sources: Mapping[str, SourceRecord],
) -> tuple[ChangedSource, ...]:
    changed_by_id = {
        observation.source_id: observation
        for observation in snapshot.observations
        if observation.status == "changed"
    }
    if tuple(sorted(changed_by_id)) != snapshot.changed_source_ids:
        raise ValueError("source-state changed IDs contradict changed observations")

    output: list[ChangedSource] = []
    for source_id in snapshot.changed_source_ids:
        source = sources.get(source_id)
        observation = changed_by_id[source_id]
        if (
            source is None
            or not source.watch
            or source.sha256 != observation.recorded_sha256
            or observation.observed_sha256 is None
        ):
            raise ValueError(f"{source_id}: changed source evidence is unavailable")
        output.append(
            ChangedSource(
                source_id=source_id,
                label=source.label,
                url=source.url,
                recorded_sha256=observation.recorded_sha256,
                observed_sha256=observation.observed_sha256,
            )
        )
    return tuple(output)


def _derived_impacts(
    snapshot: SourceStateSnapshot,
    rules: Sequence[Rule],
    golden_cases: Sequence[GoldenCase],
) -> tuple[tuple[Rule, ...], tuple[GoldenCase, ...]]:
    changed = set(snapshot.changed_source_ids)
    affected_rules = tuple(
        sorted(
            (rule for rule in rules if changed.intersection(rule.source_dependencies)),
            key=lambda rule: rule.rule_id,
        )
    )
    if tuple(rule.rule_id for rule in affected_rules) != snapshot.affected_rule_ids:
        raise ValueError("source-state affected rule IDs drifted from dependencies")

    affected_rule_ids = set(snapshot.affected_rule_ids)
    affected_cases = tuple(
        sorted(
            (
                case
                for case in golden_cases
                if affected_rule_ids.intersection(case.rule_dependency_ids)
            ),
            key=lambda case: case.case_id,
        )
    )
    if (
        tuple(case.case_id for case in affected_cases)
        != snapshot.affected_golden_case_ids
    ):
        raise ValueError("source-state affected Golden IDs drifted from dependencies")
    return affected_rules, affected_cases


def _source_item(source: ChangedSource) -> ReviewWorkItem:
    return ReviewWorkItem(
        item_id=f"source-reverification:{source.source_id}",
        item_type="source_reverification",
        target_id=source.source_id,
        source_ids=(source.source_id,),
        target_fingerprint=_fingerprint(source.to_dict()),
        reason="fetched_source_content_changed",
    )


def _rule_item(rule: Rule, changed_source_ids: set[str]) -> ReviewWorkItem:
    source_ids = tuple(sorted(set(rule.source_dependencies) & changed_source_ids))
    if not source_ids:
        raise ValueError(f"{rule.rule_id}: no changed source dependency")
    return ReviewWorkItem(
        item_id=f"rule-reverification:{rule.rule_id}",
        item_type="rule_reverification",
        target_id=rule.rule_id,
        source_ids=source_ids,
        target_fingerprint=rule_fingerprint(rule),
        reason="explicit_source_dependency_changed",
    )


def _golden_item(
    case: GoldenCase,
    rules_by_id: Mapping[str, Rule],
    changed_source_ids: set[str],
) -> ReviewWorkItem:
    source_ids: set[str] = set()
    for rule_id in case.rule_dependency_ids:
        rule = rules_by_id.get(rule_id)
        if rule is None:
            raise ValueError(f"{case.case_id}: references unknown rule ID {rule_id!r}")
        source_ids.update(set(rule.source_dependencies) & changed_source_ids)
    if not source_ids:
        raise ValueError(f"{case.case_id}: no changed rule dependency")
    return ReviewWorkItem(
        item_id=f"golden-replay:{case.case_id}",
        item_type="golden_replay",
        target_id=case.case_id,
        source_ids=tuple(sorted(source_ids)),
        target_fingerprint=_fingerprint(asdict(case)),
        reason="golden_rule_dependency_changed",
    )


@dataclass(frozen=True)
class _ReadinessContextState:
    source_bindings: Mapping[str, SourceBinding]
    requirements: Mapping[str, Requirement]
    packet_facts: Mapping[str, PacketFact]
    remedies: Mapping[str, ReadinessRemedy]
    journey_routes: tuple[tuple[JourneyConfig, tuple[Rule, ...]], ...]


def _source_bindings_by_id(
    workflow: ReadinessWorkflow,
) -> dict[str, SourceBinding]:
    bindings: dict[str, SourceBinding] = {}
    for binding in workflow.source_bindings:
        if binding.source_id in bindings:
            raise ValueError(f"{workflow.workflow_id}: duplicate source binding")
        bindings[binding.source_id] = binding
    if not bindings:
        raise ValueError(f"{workflow.workflow_id}: missing source bindings")
    return bindings


def _requirements_by_id(
    workflow: ReadinessWorkflow,
) -> dict[str, Requirement]:
    requirements: dict[str, Requirement] = {}
    for requirement in workflow.requirements:
        if requirement.requirement_id in requirements:
            raise ValueError(f"{workflow.workflow_id}: duplicate requirement ID")
        if requirement.source_id not in {
            binding.source_id for binding in workflow.source_bindings
        }:
            raise ValueError(
                f"{workflow.workflow_id}.{requirement.requirement_id}: "
                "requirement source is not bound"
            )
        requirements[requirement.requirement_id] = requirement
    if not requirements:
        raise ValueError(f"{workflow.workflow_id}: missing requirements")
    return requirements


def _packet_facts_by_id(packet: ReadinessPacket) -> dict[str, PacketFact]:
    facts: dict[str, PacketFact] = {}
    for fact in packet.facts:
        if fact.fact_id in facts:
            raise ValueError(f"{packet.packet_id}: duplicate packet fact ID")
        facts[fact.fact_id] = fact
    return facts


def _validate_packet_fact_binding(
    workflow: ReadinessWorkflow,
    definition: FactDefinition,
    packet_fact: PacketFact,
    bindings: Mapping[str, SourceBinding],
) -> None:
    if definition.source_id is None:
        if any(
            (
                packet_fact.source_id,
                packet_fact.source_field,
                packet_fact.source_checked_on,
            )
        ):
            raise ValueError(
                f"{workflow.workflow_id}.{definition.fact_id}: "
                "unbound fact carries source evidence"
            )
        return
    binding = bindings.get(definition.source_id)
    if binding is None:
        raise ValueError(
            f"{workflow.workflow_id}.{definition.fact_id}: missing fact source binding"
        )
    if (
        packet_fact.source_id != definition.source_id
        or packet_fact.source_field != definition.source_field
        or packet_fact.source_checked_on != binding.source_checked_on
    ):
        raise ValueError(
            f"{workflow.workflow_id}.{definition.fact_id}: packet fact binding drifted"
        )


def _validate_packet_binding(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
    bindings: Mapping[str, SourceBinding],
    requirements: Mapping[str, Requirement],
) -> dict[str, PacketFact]:
    if packet.workflow_id != workflow.workflow_id:
        raise ValueError("readiness packet workflow ID does not match")
    packet_facts = _packet_facts_by_id(packet)
    definitions = workflow.fact_map()
    if set(packet_facts) != set(definitions):
        raise ValueError("readiness packet facts do not match workflow")
    for definition in workflow.facts:
        _validate_packet_fact_binding(
            workflow,
            definition,
            packet_facts[definition.fact_id],
            bindings,
        )
    inventory_ids = [item.requirement_id for item in packet.inventory]
    if len(inventory_ids) != len(set(inventory_ids)):
        raise ValueError(f"{packet.packet_id}: duplicate inventory requirement ID")
    if set(inventory_ids) != set(requirements):
        raise ValueError("readiness packet inventory does not match workflow")
    return packet_facts


def _validate_remedies_binding(
    workflow: ReadinessWorkflow,
    remedies: ReadinessRemedies,
    requirements: Mapping[str, Requirement],
) -> dict[str, ReadinessRemedy]:
    if remedies.workflow_id != workflow.workflow_id:
        raise ValueError("readiness remedies workflow ID does not match")
    if remedies.workflow_fingerprint != workflow.fingerprint():
        raise ValueError("readiness remedies workflow fingerprint drifted")
    expected_content_fingerprint = _fingerprint(
        {
            "entries": [asdict(entry) for entry in remedies.entries],
            "version": remedies.version,
            "workflow_id": remedies.workflow_id,
        }
    )
    if remedies.content_fingerprint != expected_content_fingerprint:
        raise ValueError("readiness remedies content fingerprint drifted")
    entries: dict[str, ReadinessRemedy] = {}
    for remedy in remedies.entries:
        if remedy.requirement_id in entries:
            raise ValueError(f"{workflow.workflow_id}: duplicate remedy requirement ID")
        requirement = requirements.get(remedy.requirement_id)
        if (
            requirement is None
            or remedy.requirement_fingerprint != requirement.fingerprint()
        ):
            raise ValueError("readiness remedy requirement binding drifted")
        entries[remedy.requirement_id] = remedy
    if set(entries) != set(requirements):
        raise ValueError("readiness remedies do not cover workflow requirements")
    return entries


def _journey_route_rules(
    journey: JourneyConfig,
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
    rules: Sequence[Rule],
    golden_by_id: Mapping[str, GoldenCase],
) -> tuple[Rule, ...]:
    if journey.readiness_workflow_id != workflow.workflow_id:
        raise ValueError("journey readiness workflow ID does not match")
    if journey.readiness_packet_id != packet.packet_id:
        raise ValueError("journey readiness packet ID does not match")
    case = golden_by_id.get(journey.screening_case_id)
    if case is None:
        raise ValueError(
            f"journey references unknown Golden case {journey.screening_case_id!r}"
        )
    matched = {
        result.rule.rule_id: result.rule for result in screen(case.intake, list(rules))
    }
    if set(matched) != set(case.expected_rule_ids):
        raise ValueError("journey screening case no longer matches its rules")
    routes: list[Rule] = []
    for rule_id in journey.candidate_route_rule_ids:
        rule = matched.get(rule_id)
        if rule is None or rule_id not in case.expected_rule_ids:
            raise ValueError(f"journey route {rule_id!r} does not match its case")
        if rule.display_group != "route":
            raise ValueError(f"journey route {rule_id!r} is not a route record")
        routes.append(rule)
    return tuple(routes)


def _validate_readiness_context(
    context: ReadinessReviewContext,
    rules: Sequence[Rule],
    golden_by_id: Mapping[str, GoldenCase],
) -> _ReadinessContextState:
    workflow = context.workflow
    bindings = _source_bindings_by_id(workflow)
    requirements = _requirements_by_id(workflow)
    packet_facts = _validate_packet_binding(
        workflow,
        context.packet,
        bindings,
        requirements,
    )
    remedies = _validate_remedies_binding(workflow, context.remedies, requirements)
    seen_journeys: set[str] = set()
    journey_routes: list[tuple[JourneyConfig, tuple[Rule, ...]]] = []
    for journey in sorted(context.journeys, key=lambda item: item.journey_id):
        if journey.journey_id in seen_journeys:
            raise ValueError(f"{workflow.workflow_id}: duplicate journey ID")
        seen_journeys.add(journey.journey_id)
        journey_routes.append(
            (
                journey,
                _journey_route_rules(
                    journey,
                    workflow,
                    context.packet,
                    rules,
                    golden_by_id,
                ),
            )
        )
    return _ReadinessContextState(
        source_bindings=bindings,
        requirements=requirements,
        packet_facts=packet_facts,
        remedies=remedies,
        journey_routes=tuple(journey_routes),
    )


def _readiness_requirement_item(
    workflow: ReadinessWorkflow,
    requirement: Requirement,
    binding: SourceBinding,
) -> ReviewWorkItem:
    target_id = f"{workflow.workflow_id}.{requirement.requirement_id}"
    return ReviewWorkItem(
        item_id=f"readiness-requirement-reverification:{target_id}",
        item_type="readiness_requirement_reverification",
        target_id=target_id,
        source_ids=(requirement.source_id,),
        target_fingerprint=_fingerprint(
            {
                "workflow_id": workflow.workflow_id,
                "workflow_fingerprint": workflow.fingerprint(),
                "requirement": asdict(requirement),
                "source_binding": asdict(binding),
            }
        ),
        reason="readiness_requirement_source_changed",
    )


def _readiness_fact_binding_item(
    workflow: ReadinessWorkflow,
    definition: FactDefinition,
    packet_fact: PacketFact,
    binding: SourceBinding,
) -> ReviewWorkItem:
    if definition.source_id is None:
        raise ValueError(f"{definition.fact_id}: fact is not source backed")
    target_id = f"{workflow.workflow_id}.{definition.fact_id}"
    return ReviewWorkItem(
        item_id=f"readiness-fact-binding-reverification:{target_id}",
        item_type="readiness_fact_binding_reverification",
        target_id=target_id,
        source_ids=(definition.source_id,),
        target_fingerprint=_fingerprint(
            {
                "workflow_id": workflow.workflow_id,
                "workflow_fingerprint": workflow.fingerprint(),
                "fact_definition": asdict(definition),
                "packet_fact": asdict(packet_fact),
                "source_binding": asdict(binding),
            }
        ),
        reason="source_backed_fact_field_changed",
    )


def _readiness_remedy_item(
    workflow: ReadinessWorkflow,
    requirement: Requirement,
    remedies: ReadinessRemedies,
    remedy: ReadinessRemedy,
) -> ReviewWorkItem:
    target_id = f"{workflow.workflow_id}.{requirement.requirement_id}"
    return ReviewWorkItem(
        item_id=f"readiness-remedy-reverification:{target_id}",
        item_type="readiness_remedy_reverification",
        target_id=target_id,
        source_ids=(requirement.source_id,),
        target_fingerprint=_fingerprint(
            {
                "workflow_id": workflow.workflow_id,
                "workflow_fingerprint": workflow.fingerprint(),
                "remedies_version": remedies.version,
                "remedies_content_fingerprint": remedies.content_fingerprint,
                "requirement": asdict(requirement),
                "remedy": asdict(remedy),
            }
        ),
        reason="source_bound_remedy_requirement_changed",
    )


def _readiness_packet_item(
    context: ReadinessReviewContext,
    source_ids: tuple[str, ...],
) -> ReviewWorkItem:
    workflow = context.workflow
    packet = context.packet
    target_id = f"{workflow.workflow_id}.{packet.packet_id}"
    return ReviewWorkItem(
        item_id=f"readiness-packet-revalidation:{target_id}",
        item_type="readiness_packet_revalidation",
        target_id=target_id,
        source_ids=source_ids,
        target_fingerprint=_fingerprint(
            {
                "workflow_id": workflow.workflow_id,
                "workflow_fingerprint": workflow.fingerprint(),
                "packet_id": packet.packet_id,
                "packet_fingerprint": packet.fingerprint(),
                "remedies_version": context.remedies.version,
                "remedies_content_fingerprint": context.remedies.content_fingerprint,
            }
        ),
        reason="readiness_workflow_source_changed",
    )


def _journey_handoff_item(
    context: ReadinessReviewContext,
    journey: JourneyConfig,
    route_rules: tuple[Rule, ...],
    source_ids: tuple[str, ...],
) -> ReviewWorkItem:
    return ReviewWorkItem(
        item_id=f"journey-handoff-revalidation:{journey.journey_id}",
        item_type="journey_handoff_revalidation",
        target_id=journey.journey_id,
        source_ids=source_ids,
        target_fingerprint=_fingerprint(
            {
                "journey": asdict(journey),
                "journey_configuration_fingerprint": _fingerprint(asdict(journey)),
                "workflow_fingerprint": context.workflow.fingerprint(),
                "packet_fingerprint": context.packet.fingerprint(),
                "remedies_content_fingerprint": context.remedies.content_fingerprint,
                "candidate_routes": [
                    {
                        "rule_id": rule.rule_id,
                        "rule_fingerprint": rule_fingerprint(rule),
                    }
                    for rule in route_rules
                ],
            }
        ),
        reason="journey_or_packet_source_changed",
    )


def _readiness_context_items(
    context: ReadinessReviewContext,
    state: _ReadinessContextState,
    changed_source_ids: set[str],
) -> list[ReviewWorkItem]:
    workflow = context.workflow
    workflow_changed = set(state.source_bindings) & changed_source_ids
    items: list[ReviewWorkItem] = []
    for requirement in state.requirements.values():
        if requirement.source_id in changed_source_ids:
            items.append(
                _readiness_requirement_item(
                    workflow,
                    requirement,
                    state.source_bindings[requirement.source_id],
                )
            )
            items.append(
                _readiness_remedy_item(
                    workflow,
                    requirement,
                    context.remedies,
                    state.remedies[requirement.requirement_id],
                )
            )
    for definition in workflow.facts:
        if definition.source_id in changed_source_ids:
            source_id = definition.source_id
            if source_id is None:
                raise AssertionError("source-backed fact lost its source ID")
            items.append(
                _readiness_fact_binding_item(
                    workflow,
                    definition,
                    state.packet_facts[definition.fact_id],
                    state.source_bindings[source_id],
                )
            )
    workflow_source_ids = tuple(sorted(workflow_changed))
    if workflow_source_ids:
        items.append(_readiness_packet_item(context, workflow_source_ids))
    for journey, routes in state.journey_routes:
        route_changed = {
            source_id
            for rule in routes
            for source_id in rule.source_dependencies
            if source_id in changed_source_ids
        }
        journey_source_ids = tuple(sorted(workflow_changed | route_changed))
        if journey_source_ids:
            items.append(
                _journey_handoff_item(
                    context,
                    journey,
                    routes,
                    journey_source_ids,
                )
            )
    return items


def _readiness_context_binding(
    context: ReadinessReviewContext,
) -> ReadinessContextBinding:
    journeys = tuple(
        JourneyHandoffBinding(
            journey_id=journey.journey_id,
            version=journey.version,
            configuration_fingerprint=_fingerprint(asdict(journey)),
        )
        for journey in sorted(context.journeys, key=lambda item: item.journey_id)
    )
    return ReadinessContextBinding(
        workflow_id=context.workflow.workflow_id,
        workflow_fingerprint=context.workflow.fingerprint(),
        packet_id=context.packet.packet_id,
        packet_fingerprint=context.packet.fingerprint(),
        remedies_version=context.remedies.version,
        remedies_content_fingerprint=context.remedies.content_fingerprint,
        journeys=journeys,
    )


def _validate_context_id_uniqueness(
    contexts: Sequence[ReadinessReviewContext],
) -> None:
    workflow_ids: set[str] = set()
    packet_ids: set[str] = set()
    journey_ids: set[str] = set()
    for context in contexts:
        workflow_id = context.workflow.workflow_id
        packet_id = context.packet.packet_id
        if workflow_id in workflow_ids or packet_id in packet_ids:
            raise ValueError(
                "readiness review contexts must have unique workflow and packet IDs"
            )
        workflow_ids.add(workflow_id)
        packet_ids.add(packet_id)
        for journey in context.journeys:
            if journey.journey_id in journey_ids:
                raise ValueError(
                    "readiness review contexts must have unique journey IDs"
                )
            journey_ids.add(journey.journey_id)


def build_review_worklist(
    snapshot: SourceStateSnapshot,
    sources: Mapping[str, SourceRecord],
    rules: Sequence[Rule],
    golden_cases: Sequence[GoldenCase],
    *,
    readiness_contexts: Sequence[ReadinessReviewContext] = (),
) -> ReviewWorklist:
    """Build a read-only worklist from one validated source-state receipt.

    It derives the existing source→rule→Golden chain and any supplied
    source-bound packet contexts. Packet/journey bindings are read-only: they
    create re-verification work but cannot change matching or republish data.
    """

    rules_by_id = _rules_by_id(rules)
    golden_by_id = _golden_by_id(golden_cases)
    contexts = tuple(
        sorted(readiness_contexts, key=lambda context: context.workflow.workflow_id)
    )
    _validate_context_id_uniqueness(contexts)
    changed_sources = _changed_observations(snapshot, sources)
    affected_rules, affected_cases = _derived_impacts(snapshot, rules, golden_cases)
    changed_ids = set(snapshot.changed_source_ids)
    items = [
        *(_source_item(source) for source in changed_sources),
        *(_rule_item(rule, changed_ids) for rule in affected_rules),
        *(_golden_item(case, rules_by_id, changed_ids) for case in affected_cases),
    ]
    context_bindings: list[ReadinessContextBinding] = []
    for context in contexts:
        context_state = _validate_readiness_context(context, rules, golden_by_id)
        context_bindings.append(_readiness_context_binding(context))
        items.extend(_readiness_context_items(context, context_state, changed_ids))
    items.sort(key=lambda item: item.item_id)
    if len({item.item_id for item in items}) != len(items):
        raise ValueError("generated worklist contains duplicate item IDs")
    status = "open" if items else "clear"
    if status not in WORKLIST_STATUSES:
        raise AssertionError("invalid generated worklist status")
    return ReviewWorklist(
        worklist_id=f"source-reverification-{snapshot.snapshot_id}",
        source_snapshot_id=snapshot.snapshot_id,
        source_snapshot_fingerprint=source_state_fingerprint(snapshot),
        checked_at=snapshot.checked_at,
        receipt_status=snapshot.receipt.status,
        changed_source_ids=snapshot.changed_source_ids,
        unverifiable_source_ids=snapshot.unverifiable_source_ids,
        changed_sources=changed_sources,
        readiness_contexts=tuple(context_bindings),
        status=status,
        items=tuple(items),
    )


def encoded_review_worklist(worklist: ReviewWorklist) -> str:
    """Encode a generated worklist in a stable, portable JSON form."""

    return (
        json.dumps(worklist.to_dict(), ensure_ascii=True, indent=2, sort_keys=True)
        + "\n"
    )


def load_review_worklist(
    path: Path,
    snapshot: SourceStateSnapshot,
    sources: Mapping[str, SourceRecord],
    rules: Sequence[Rule],
    golden_cases: Sequence[GoldenCase],
    *,
    readiness_contexts: Sequence[ReadinessReviewContext] = (),
) -> ReviewWorklist:
    """Strictly verify a persisted worklist against its current inputs."""

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: review worklist could not be loaded") from error
    _exact_keys(
        raw,
        {
            "schema_version",
            "worklist_id",
            "source_state",
            "status",
            "changed_sources",
            "readiness_contexts",
            "items",
            "worklist_fingerprint",
        },
        str(path),
    )
    expected = build_review_worklist(
        snapshot,
        sources,
        rules,
        golden_cases,
        readiness_contexts=readiness_contexts,
    )
    if raw != expected.to_dict():
        raise ValueError(f"{path}: review worklist does not match source-state inputs")
    return expected


def decision_template(worklist: ReviewWorklist) -> ReviewDecisionLedger:
    """Return a complete, explicitly unassigned decision ledger template."""

    return ReviewDecisionLedger(
        worklist_id=worklist.worklist_id,
        worklist_fingerprint=worklist.fingerprint(),
        entries=tuple(
            ReviewDecision(
                item_id=item.item_id,
                item_fingerprint=item.fingerprint(),
                status="unassigned",
                owner_code=None,
                assigned_on=None,
                disposition=None,
                decided_on=None,
                evidence_receipt_id=None,
            )
            for item in sorted(worklist.items, key=lambda item: item.item_id)
        ),
    )


def encoded_decision_ledger(ledger: ReviewDecisionLedger) -> str:
    return (
        json.dumps(ledger.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    )


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected non-blank text or null")
    return value.strip()


@dataclass(frozen=True)
class _DecisionMetadata:
    owner_code: str | None
    assigned_on: str | None
    disposition: str | None
    decided_on: str | None
    evidence_receipt_id: str | None


def _choice(value: Any, allowed: tuple[str, ...], field: str) -> str:
    text = _optional_text(value, field)
    if text not in allowed:
        raise ValueError(f"{field}: unsupported value {text!r}")
    return text


def _validated_item(
    record: Mapping[str, Any],
    field: str,
    work_items: Mapping[str, ReviewWorkItem],
) -> tuple[str, str]:
    item_id = _work_item_identifier(record["item_id"], f"{field}.item_id")
    item = work_items.get(item_id)
    if item is None:
        raise ValueError(f"{field}: references unknown work item {item_id!r}")
    fingerprint = _optional_text(
        record["item_fingerprint"], f"{field}.item_fingerprint"
    )
    if fingerprint is None or not _FINGERPRINT.fullmatch(fingerprint):
        raise ValueError(f"{field}.item_fingerprint: expected SHA-256 fingerprint")
    if fingerprint != item.fingerprint():
        raise ValueError(f"{field}: item fingerprint does not match worklist")
    return item_id, fingerprint


def _decision_metadata(
    record: Mapping[str, Any],
    field: str,
    *,
    today: date,
) -> _DecisionMetadata:
    owner_code = _optional_text(record["owner_code"], f"{field}.owner_code")
    if owner_code is not None and not _OWNER_CODE.fullmatch(owner_code):
        raise ValueError(f"{field}.owner_code: expected an opaque uppercase owner code")
    assigned_on_raw = record["assigned_on"]
    assigned_on = (
        _iso_date(assigned_on_raw, f"{field}.assigned_on", today=today)
        if assigned_on_raw is not None
        else None
    )
    disposition = _optional_text(record["disposition"], f"{field}.disposition")
    if disposition is not None and disposition not in DECISION_DISPOSITIONS:
        raise ValueError(f"{field}.disposition: unsupported value {disposition!r}")
    decided_on_raw = record["decided_on"]
    decided_on = (
        _iso_date(decided_on_raw, f"{field}.decided_on", today=today)
        if decided_on_raw is not None
        else None
    )
    evidence_receipt_id = _optional_text(
        record["evidence_receipt_id"], f"{field}.evidence_receipt_id"
    )
    if evidence_receipt_id is not None and not _IDENTIFIER.fullmatch(
        evidence_receipt_id
    ):
        raise ValueError(f"{field}.evidence_receipt_id: expected stable identifier")
    return _DecisionMetadata(
        owner_code=owner_code,
        assigned_on=assigned_on,
        disposition=disposition,
        decided_on=decided_on,
        evidence_receipt_id=evidence_receipt_id,
    )


def _validate_decision_status(
    status: str,
    metadata: _DecisionMetadata,
    field: str,
) -> None:
    values = (
        metadata.owner_code,
        metadata.assigned_on,
        metadata.disposition,
        metadata.decided_on,
        metadata.evidence_receipt_id,
    )
    if status == "unassigned" and any(values):
        raise ValueError(f"{field}: unassigned entries cannot carry decision metadata")
    if status == "assigned":
        if metadata.owner_code is None or metadata.assigned_on is None:
            raise ValueError(
                f"{field}: assigned entries require owner_code and assigned_on"
            )
        if any(
            (
                metadata.disposition,
                metadata.decided_on,
                metadata.evidence_receipt_id,
            )
        ):
            raise ValueError(f"{field}: assigned entries cannot carry a disposition")
    if status == "resolved":
        if not all(values):
            raise ValueError(
                f"{field}: resolved entries require assignment, disposition, and evidence"
            )
        if (
            metadata.assigned_on is not None
            and metadata.decided_on is not None
            and metadata.decided_on < metadata.assigned_on
        ):
            raise ValueError(f"{field}: decided_on cannot predate assigned_on")


def _decision_entry(
    raw: Any,
    index: int,
    work_items: Mapping[str, ReviewWorkItem],
    *,
    today: date,
) -> ReviewDecision:
    field = f"entries[{index}]"
    record = _exact_keys(
        raw,
        {
            "item_id",
            "item_fingerprint",
            "status",
            "owner_code",
            "assigned_on",
            "disposition",
            "decided_on",
            "evidence_receipt_id",
        },
        field,
    )
    item_id, fingerprint = _validated_item(record, field, work_items)
    status = _choice(record["status"], DECISION_STATUSES, f"{field}.status")
    metadata = _decision_metadata(record, field, today=today)
    _validate_decision_status(status, metadata, field)
    return ReviewDecision(
        item_id=item_id,
        item_fingerprint=fingerprint,
        status=status,
        owner_code=metadata.owner_code,
        assigned_on=metadata.assigned_on,
        disposition=metadata.disposition,
        decided_on=metadata.decided_on,
        evidence_receipt_id=metadata.evidence_receipt_id,
    )


def load_review_decisions(
    path: Path,
    worklist: ReviewWorklist,
    *,
    today: date | None = None,
) -> ReviewDecisionLedger:
    """Load a complete ledger without letting decisions alter source state.

    A resolved entry is an auditable maintenance note only. Callers must not
    use it to make a stale record current, change matching, promote a review
    level, or republish anything.
    """

    as_of = resolve_today(today)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: review decisions could not be loaded") from error
    record = _exact_keys(
        raw,
        {"schema_version", "worklist_id", "worklist_fingerprint", "entries"},
        str(path),
    )
    if record["schema_version"] != DECISIONS_SCHEMA_VERSION:
        raise ValueError(f"{path}.schema_version: expected {DECISIONS_SCHEMA_VERSION}")
    if record["worklist_id"] != worklist.worklist_id:
        raise ValueError(f"{path}: worklist ID does not match")
    if record["worklist_fingerprint"] != worklist.fingerprint():
        raise ValueError(f"{path}: worklist fingerprint does not match")
    entries_raw = record["entries"]
    if not isinstance(entries_raw, list):
        raise ValueError(f"{path}.entries: expected a list")
    items = worklist.item_map()
    entries = tuple(
        _decision_entry(item, index, items, today=as_of)
        for index, item in enumerate(entries_raw)
    )
    ids = [entry.item_id for entry in entries]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValueError(f"{path}.entries: expected sorted unique item IDs")
    if set(ids) != set(items):
        raise ValueError(f"{path}.entries: must cover every work item exactly once")
    return ReviewDecisionLedger(
        worklist_id=worklist.worklist_id,
        worklist_fingerprint=worklist.fingerprint(),
        entries=entries,
    )
