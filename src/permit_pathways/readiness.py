"""Deterministic packet-presence evaluation for bounded local workflows.

This module does not decide legal sufficiency, code compliance, eligibility,
or approval. It compares an explicit packet inventory and explicit project
facts with a source-bound requirement manifest. Unknown conditions remain
questions for staff. A stale or changed source prevents a readiness summary
from being published.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .dates import resolve_today
from .harness.watch import load_sources

SCHEMA_VERSION = 1
SOURCE_MAX_AGE_DAYS = 180
TRI_VALUES = ("yes", "no", "unknown")
INVENTORY_STATUSES = ("present", "missing", "unknown", "conflicting")
FINDING_STATUSES = (
    "present",
    "missing",
    "not_applicable",
    "conflicting",
    "needs_staff_review",
    "not_evaluated",
)
OVERALL_STATUSES = (
    "known_gaps",
    "needs_review",
    "no_known_gaps_in_bounded_manifest",
    "outside_bounded_workflow",
    "source_review_required",
)
ITEM_TYPES = ("document", "document_content", "action")
PROVENANCE_VALUES = (
    "synthetic_applicant_assertion",
    "applicant_assertion",
)

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected non-blank text")
    return value.strip()


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field)


def _identifier(value: Any, field: str) -> str:
    identifier = _required_text(value, field)
    if not _IDENTIFIER.fullmatch(identifier):
        raise ValueError(f"{field}: invalid stable identifier")
    return identifier


def _exact_keys(
    record: dict[str, Any],
    allowed: set[str],
    required: set[str],
    field: str,
) -> None:
    unknown = sorted(set(record) - allowed)
    missing = sorted(required - set(record))
    if unknown:
        raise ValueError(f"{field}: unknown fields: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{field}: missing fields: {', '.join(missing)}")


def _iso_date(value: Any, field: str, *, today: date) -> str:
    text = _required_text(value, field)
    if not _DATE.fullmatch(text):
        raise ValueError(f"{field}: expected YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"{field}: invalid date {text!r}") from error
    if parsed > today:
        raise ValueError(f"{field}: future dates are not allowed")
    return text


def _read_json(path: Path, field: str) -> Any:
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


@dataclass(frozen=True)
class SourceBinding:
    source_id: str
    url: str
    sha256: str
    source_checked_on: str


@dataclass(frozen=True)
class Condition:
    fact_id: str
    equals: str


@dataclass(frozen=True)
class FactDefinition:
    fact_id: str
    label: str
    question: str
    allowed_values: tuple[str, ...]


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    label: str
    category: str
    item_type: str
    parent_requirement_id: str | None
    applies_when: tuple[Condition, ...]
    source_id: str
    source_locator: str
    source_excerpt: str

    def fingerprint(self) -> str:
        return _fingerprint(asdict(self))


@dataclass(frozen=True)
class MappingInputSource:
    source_id: str
    sha256: str


@dataclass(frozen=True)
class MappingProvenance:
    version: str
    updated_on: str
    drafted_by: str
    input_source_fingerprints: tuple[MappingInputSource, ...]
    review_status: str
    review_scope: str
    provider: str
    model: str
    run_record_status: str


@dataclass(frozen=True)
class ReadinessWorkflow:
    workflow_id: str
    jurisdiction: str
    project_type: str
    status: str
    title: str
    scope: str
    source_bindings: tuple[SourceBinding, ...]
    mapping_provenance: MappingProvenance
    applicability: tuple[Condition, ...]
    facts: tuple[FactDefinition, ...]
    requirements: tuple[Requirement, ...]

    def fingerprint(self) -> str:
        return _fingerprint(asdict(self))

    def fact_map(self) -> dict[str, FactDefinition]:
        return {fact.fact_id: fact for fact in self.facts}

    def requirement_map(self) -> dict[str, Requirement]:
        return {
            requirement.requirement_id: requirement for requirement in self.requirements
        }


@dataclass(frozen=True)
class PacketFact:
    fact_id: str
    value: str
    provenance: str


@dataclass(frozen=True)
class InventoryItem:
    requirement_id: str
    status: str


@dataclass(frozen=True)
class ReadinessPacket:
    packet_id: str
    workflow_id: str
    label: str
    synthetic: bool
    evaluated_on: str
    jurisdiction: str
    project_type: str
    facts: tuple[PacketFact, ...]
    inventory: tuple[InventoryItem, ...]

    def fingerprint(self) -> str:
        return _fingerprint(asdict(self))

    def fact_values(self) -> dict[str, str]:
        return {fact.fact_id: fact.value for fact in self.facts}

    def inventory_map(self) -> dict[str, str]:
        return {item.requirement_id: item.status for item in self.inventory}


@dataclass(frozen=True)
class ReadinessFinding:
    requirement_id: str
    label: str
    category: str
    status: str
    reason: str
    source_id: str
    source_locator: str
    source_excerpt: str
    requirement_fingerprint: str


@dataclass(frozen=True)
class ReadinessResult:
    packet_id: str
    workflow_id: str
    overall_status: str
    evaluated_on: str
    workflow_fingerprint: str
    packet_fingerprint: str
    source_status: str
    source_status_as_of: str
    source_review_due_on: str
    findings: tuple[ReadinessFinding, ...]
    staff_questions: tuple[str, ...]
    boundary: str

    def counts(self) -> dict[str, int]:
        return {
            status: sum(finding.status == status for finding in self.findings)
            for status in FINDING_STATUSES
        }

    def to_manifest(
        self,
        workflow: ReadinessWorkflow,
        packet: ReadinessPacket,
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "manifest_type": "prototype_packet_presence",
            "packet_id": self.packet_id,
            "workflow_id": self.workflow_id,
            "synthetic": packet.synthetic,
            "overall_status": self.overall_status,
            "evaluated_on": self.evaluated_on,
            "workflow_fingerprint": self.workflow_fingerprint,
            "packet_fingerprint": self.packet_fingerprint,
            "source_status": self.source_status,
            "source_status_as_of": self.source_status_as_of,
            "source_review_due_on": self.source_review_due_on,
            "source_bindings": [
                asdict(binding) for binding in workflow.source_bindings
            ],
            "facts": [asdict(fact) for fact in packet.facts],
            "inventory": [asdict(item) for item in packet.inventory],
            "counts": self.counts(),
            "findings": [asdict(finding) for finding in self.findings],
            "staff_questions": list(self.staff_questions),
            "boundary": self.boundary,
        }


@dataclass(frozen=True)
class RemedyReview:
    status: str
    reviewer: str | None
    method: str | None
    reviewed_on: str | None
    reviewed_version: str | None
    content_fingerprint: str | None


@dataclass(frozen=True)
class ReadinessRemedy:
    requirement_id: str
    requirement_fingerprint: str
    action: str


@dataclass(frozen=True)
class ReadinessRemedies:
    workflow_id: str
    workflow_fingerprint: str
    version: str
    updated_on: str
    drafted_by: str
    review: RemedyReview
    entries: tuple[ReadinessRemedy, ...]

    def entry_map(self) -> dict[str, ReadinessRemedy]:
        return {entry.requirement_id: entry for entry in self.entries}


def _load_condition(
    value: Any,
    field: str,
    facts: dict[str, FactDefinition],
) -> Condition:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    _exact_keys(value, {"fact_id", "equals"}, {"fact_id", "equals"}, field)
    fact_id = _identifier(value["fact_id"], f"{field}.fact_id")
    if fact_id not in facts:
        raise ValueError(f"{field}.fact_id: unknown fact {fact_id!r}")
    expected = _required_text(value["equals"], f"{field}.equals")
    if expected not in facts[fact_id].allowed_values or expected == "unknown":
        raise ValueError(f"{field}.equals: expected a concrete allowed value")
    return Condition(fact_id=fact_id, equals=expected)


def _required_literal(value: Any, field: str, expected: str, message: str) -> str:
    text = _required_text(value, field)
    if text != expected:
        raise ValueError(f"{field}: {message}")
    return text


def _mapping_input(
    value: Any,
    field: str,
    bindings_by_id: dict[str, SourceBinding],
) -> MappingInputSource:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    keys = {"source_id", "sha256"}
    _exact_keys(value, keys, keys, field)
    source_id = _identifier(value["source_id"], f"{field}.source_id")
    binding = bindings_by_id.get(source_id)
    if binding is None:
        raise ValueError(f"{field}.source_id: source is not bound")
    digest = _required_text(value["sha256"], f"{field}.sha256")
    if not _SHA256.fullmatch(digest):
        raise ValueError(f"{field}.sha256: expected a SHA-256 digest")
    if digest != binding.sha256:
        raise ValueError(f"{field}.sha256: does not match bound source")
    return MappingInputSource(source_id=source_id, sha256=digest)


def _mapping_inputs(
    value: Any,
    bindings: tuple[SourceBinding, ...],
    field: str,
) -> tuple[MappingInputSource, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field}: expected a non-empty list")
    bindings_by_id = {binding.source_id: binding for binding in bindings}
    inputs: list[MappingInputSource] = []
    seen: set[str] = set()
    for index, raw_input in enumerate(value):
        parsed = _mapping_input(raw_input, f"{field}[{index}]", bindings_by_id)
        if parsed.source_id in seen:
            raise ValueError(f"{field}[{index}].source_id: duplicate source")
        inputs.append(parsed)
        seen.add(parsed.source_id)
    missing = sorted(set(bindings_by_id) - seen)
    if missing:
        raise ValueError(f"{field}: missing sources: " + ", ".join(missing))
    return tuple(inputs)


def _load_mapping_provenance(
    value: Any,
    bindings: tuple[SourceBinding, ...],
    *,
    today: date,
) -> MappingProvenance:
    """Load truthful, review-pending provenance for the AI-assisted mapping."""

    field = "workflow.mapping_provenance"
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    keys = {
        "version",
        "updated_on",
        "drafted_by",
        "input_source_fingerprints",
        "review_status",
        "review_scope",
        "provider",
        "model",
        "run_record_status",
    }
    _exact_keys(value, keys, keys, field)

    version = _required_text(value["version"], f"{field}.version")
    if not _SEMVER.fullmatch(version):
        raise ValueError(f"{field}.version: expected semantic version")
    updated_on = _iso_date(value["updated_on"], f"{field}.updated_on", today=today)
    if date.fromisoformat(updated_on) < max(
        date.fromisoformat(binding.source_checked_on) for binding in bindings
    ):
        raise ValueError(
            f"{field}.updated_on: cannot predate an input source fingerprint"
        )

    drafted_by = _required_literal(
        value["drafted_by"],
        f"{field}.drafted_by",
        "ai_assisted",
        "current prototype requires ai_assisted",
    )
    review_status = _required_literal(
        value["review_status"],
        f"{field}.review_status",
        "prototype_review_pending",
        "mapping and excerpts remain review-pending",
    )
    review_scope = _required_literal(
        value["review_scope"],
        f"{field}.review_scope",
        "requirements_and_source_excerpts",
        "expected requirements_and_source_excerpts",
    )
    provider = _required_literal(
        value["provider"],
        f"{field}.provider",
        "unknown",
        "no provider was recorded for this draft",
    )
    model = _required_literal(
        value["model"],
        f"{field}.model",
        "unknown",
        "no model was recorded for this draft",
    )
    run_record_status = _required_literal(
        value["run_record_status"],
        f"{field}.run_record_status",
        "not_recorded",
        "current draft has no run record",
    )
    inputs = _mapping_inputs(
        value["input_source_fingerprints"],
        bindings,
        f"{field}.input_source_fingerprints",
    )

    return MappingProvenance(
        version=version,
        updated_on=updated_on,
        drafted_by=drafted_by,
        input_source_fingerprints=inputs,
        review_status=review_status,
        review_scope=review_scope,
        provider=provider,
        model=model,
        run_record_status=run_record_status,
    )


def _versioned_record(path: Path, record_name: str) -> dict[str, Any]:
    payload = _read_json(path, str(path))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected an object")
    keys = {"schema_version", record_name}
    _exact_keys(payload, keys, keys, str(path))
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported schema version")
    raw = payload[record_name]
    if not isinstance(raw, dict):
        raise ValueError(f"{path}.{record_name}: expected an object")
    return raw


def _workflow_record(path: Path) -> dict[str, Any]:
    raw = _versioned_record(path, "workflow")
    keys = {
        "workflow_id",
        "jurisdiction",
        "project_type",
        "status",
        "title",
        "scope",
        "source_bindings",
        "mapping_provenance",
        "applicability",
        "facts",
        "requirements",
    }
    _exact_keys(raw, keys, keys, f"{path}.workflow")
    return raw


def _source_binding(
    value: Any,
    field: str,
    sources: dict[str, Any],
    as_of: date,
) -> SourceBinding:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    keys = {"source_id", "url", "sha256", "source_checked_on"}
    _exact_keys(value, keys, keys, field)
    source_id = _identifier(value["source_id"], f"{field}.source_id")
    source = sources.get(source_id)
    if source is None:
        raise ValueError(f"{field}.source_id: unknown source")
    url = _required_text(value["url"], f"{field}.url")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(f"{field}.url: expected a public HTTPS URL")
    digest = _required_text(value["sha256"], f"{field}.sha256")
    if not _SHA256.fullmatch(digest):
        raise ValueError(f"{field}.sha256: expected a SHA-256 digest")
    checked = _iso_date(
        value["source_checked_on"], f"{field}.source_checked_on", today=as_of
    )
    if source.url != url or source.sha256 != digest or source.fetched_on != checked:
        raise ValueError(f"{field}: binding does not match the source registry")
    return SourceBinding(source_id, url, digest, checked)


def _source_bindings(
    value: Any,
    sources: dict[str, Any],
    as_of: date,
) -> tuple[SourceBinding, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("workflow.source_bindings: expected a non-empty list")
    bindings: list[SourceBinding] = []
    seen: set[str] = set()
    for index, raw_binding in enumerate(value):
        field = f"workflow.source_bindings[{index}]"
        binding = _source_binding(raw_binding, field, sources, as_of)
        if binding.source_id in seen:
            raise ValueError(f"{field}.source_id: duplicate source binding")
        bindings.append(binding)
        seen.add(binding.source_id)
    return tuple(bindings)


def _fact_definition(value: Any, field: str) -> FactDefinition:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    keys = {"fact_id", "label", "question", "allowed_values"}
    _exact_keys(value, keys, keys, field)
    allowed = value["allowed_values"]
    if not isinstance(allowed, list) or tuple(allowed) != TRI_VALUES:
        raise ValueError(f"{field}.allowed_values: expected yes, no, unknown")
    return FactDefinition(
        fact_id=_identifier(value["fact_id"], f"{field}.fact_id"),
        label=_required_text(value["label"], f"{field}.label"),
        question=_required_text(value["question"], f"{field}.question"),
        allowed_values=tuple(allowed),
    )


def _fact_definitions(
    value: Any,
) -> tuple[tuple[FactDefinition, ...], dict[str, FactDefinition]]:
    if not isinstance(value, list) or not value:
        raise ValueError("workflow.facts: expected a non-empty list")
    facts: list[FactDefinition] = []
    by_id: dict[str, FactDefinition] = {}
    for index, raw_fact in enumerate(value):
        field = f"workflow.facts[{index}]"
        fact = _fact_definition(raw_fact, field)
        if fact.fact_id in by_id:
            raise ValueError(f"{field}.fact_id: duplicate fact")
        facts.append(fact)
        by_id[fact.fact_id] = fact
    return tuple(facts), by_id


def _conditions(
    value: Any,
    field: str,
    facts: dict[str, FactDefinition],
    *,
    non_empty: bool = False,
) -> tuple[Condition, ...]:
    if not isinstance(value, list) or (non_empty and not value):
        expected = "a non-empty list" if non_empty else "a list"
        raise ValueError(f"{field}: expected {expected}")
    return tuple(
        _load_condition(item, f"{field}[{index}]", facts)
        for index, item in enumerate(value)
    )


def _requirement(
    value: Any,
    field: str,
    facts: dict[str, FactDefinition],
    prior_requirements: dict[str, Requirement],
    bound_source_ids: set[str],
) -> Requirement:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    keys = {
        "requirement_id",
        "label",
        "category",
        "item_type",
        "parent_requirement_id",
        "applies_when",
        "source_id",
        "source_locator",
        "source_excerpt",
    }
    _exact_keys(value, keys, keys, field)
    requirement_id = _identifier(value["requirement_id"], f"{field}.requirement_id")
    item_type = _required_text(value["item_type"], f"{field}.item_type")
    if item_type not in ITEM_TYPES:
        raise ValueError(f"{field}.item_type: unsupported value")
    parent_id = _optional_text(
        value["parent_requirement_id"], f"{field}.parent_requirement_id"
    )
    if parent_id is not None and not _IDENTIFIER.fullmatch(parent_id):
        raise ValueError(f"{field}.parent_requirement_id: invalid identifier")
    if parent_id is not None and parent_id not in prior_requirements:
        raise ValueError(f"{field}.parent_requirement_id: parent must appear first")
    source_id = _identifier(value["source_id"], f"{field}.source_id")
    if source_id not in bound_source_ids:
        raise ValueError(f"{field}.source_id: source is not bound to the workflow")
    return Requirement(
        requirement_id=requirement_id,
        label=_required_text(value["label"], f"{field}.label"),
        category=_required_text(value["category"], f"{field}.category"),
        item_type=item_type,
        parent_requirement_id=parent_id,
        applies_when=_conditions(value["applies_when"], f"{field}.applies_when", facts),
        source_id=source_id,
        source_locator=_required_text(
            value["source_locator"], f"{field}.source_locator"
        ),
        source_excerpt=_required_text(
            value["source_excerpt"], f"{field}.source_excerpt"
        ),
    )


def _requirements(
    value: Any,
    facts: dict[str, FactDefinition],
    bindings: tuple[SourceBinding, ...],
) -> tuple[Requirement, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("workflow.requirements: expected a non-empty list")
    requirements: list[Requirement] = []
    by_id: dict[str, Requirement] = {}
    bound_source_ids = {binding.source_id for binding in bindings}
    for index, raw_requirement in enumerate(value):
        field = f"workflow.requirements[{index}]"
        requirement = _requirement(
            raw_requirement, field, facts, by_id, bound_source_ids
        )
        if requirement.requirement_id in by_id:
            raise ValueError(f"{field}.requirement_id: duplicate requirement")
        requirements.append(requirement)
        by_id[requirement.requirement_id] = requirement
    return tuple(requirements)


def load_readiness_workflow(
    path: Path,
    sources_path: Path,
    *,
    today: date | None = None,
) -> ReadinessWorkflow:
    """Load and strictly validate one source-bound readiness workflow."""

    as_of = resolve_today(today)
    raw = _workflow_record(path)
    status = _required_text(raw["status"], "workflow.status")
    if status != "prototype":
        raise ValueError("workflow.status: current schema requires 'prototype'")
    bindings = _source_bindings(
        raw["source_bindings"],
        load_sources(sources_path, today=as_of),
        as_of,
    )
    facts, facts_by_id = _fact_definitions(raw["facts"])
    return ReadinessWorkflow(
        workflow_id=_identifier(raw["workflow_id"], "workflow.workflow_id"),
        jurisdiction=_identifier(raw["jurisdiction"], "workflow.jurisdiction"),
        project_type=_identifier(raw["project_type"], "workflow.project_type"),
        status=status,
        title=_required_text(raw["title"], "workflow.title"),
        scope=_required_text(raw["scope"], "workflow.scope"),
        source_bindings=bindings,
        mapping_provenance=_load_mapping_provenance(
            raw["mapping_provenance"], bindings, today=as_of
        ),
        applicability=_conditions(
            raw["applicability"],
            "workflow.applicability",
            facts_by_id,
            non_empty=True,
        ),
        facts=facts,
        requirements=_requirements(raw["requirements"], facts_by_id, bindings),
    )


def _packet_record(path: Path) -> dict[str, Any]:
    raw = _versioned_record(path, "packet")
    keys = {
        "packet_id",
        "workflow_id",
        "label",
        "synthetic",
        "evaluated_on",
        "jurisdiction",
        "project_type",
        "facts",
        "inventory",
    }
    _exact_keys(raw, keys, keys, f"{path}.packet")
    return raw


def _packet_fact(
    value: Any,
    field: str,
    definitions: dict[str, FactDefinition],
) -> PacketFact:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    keys = {"fact_id", "value", "provenance"}
    _exact_keys(value, keys, keys, field)
    fact_id = _identifier(value["fact_id"], f"{field}.fact_id")
    definition = definitions.get(fact_id)
    if definition is None:
        raise ValueError(f"{field}.fact_id: unknown workflow fact")
    fact_value = _required_text(value["value"], f"{field}.value")
    if fact_value not in definition.allowed_values:
        raise ValueError(f"{field}.value: unsupported value")
    provenance = _required_text(value["provenance"], f"{field}.provenance")
    if provenance not in PROVENANCE_VALUES:
        raise ValueError(f"{field}.provenance: unsupported value")
    return PacketFact(fact_id=fact_id, value=fact_value, provenance=provenance)


def _packet_facts(
    value: Any,
    workflow: ReadinessWorkflow,
) -> tuple[PacketFact, ...]:
    if not isinstance(value, list):
        raise ValueError("packet.facts: expected a list")
    definitions = workflow.fact_map()
    facts: list[PacketFact] = []
    seen: set[str] = set()
    for index, raw_fact in enumerate(value):
        field = f"packet.facts[{index}]"
        fact = _packet_fact(raw_fact, field, definitions)
        if fact.fact_id in seen:
            raise ValueError(f"{field}.fact_id: duplicate fact")
        facts.append(fact)
        seen.add(fact.fact_id)
    missing = sorted(set(definitions) - seen)
    if missing:
        raise ValueError("packet.facts: missing facts: " + ", ".join(missing))
    return tuple(facts)


def _packet_inventory_item(
    value: Any,
    field: str,
    requirements: dict[str, Requirement],
) -> InventoryItem:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    keys = {"requirement_id", "status"}
    _exact_keys(value, keys, keys, field)
    requirement_id = _identifier(value["requirement_id"], f"{field}.requirement_id")
    if requirement_id not in requirements:
        raise ValueError(f"{field}.requirement_id: unknown workflow requirement")
    status = _required_text(value["status"], f"{field}.status")
    if status not in INVENTORY_STATUSES:
        raise ValueError(f"{field}.status: unsupported value")
    return InventoryItem(requirement_id=requirement_id, status=status)


def _packet_inventory(
    value: Any,
    workflow: ReadinessWorkflow,
) -> tuple[InventoryItem, ...]:
    if not isinstance(value, list):
        raise ValueError("packet.inventory: expected a list")
    requirements = workflow.requirement_map()
    inventory: list[InventoryItem] = []
    seen: set[str] = set()
    for index, raw_item in enumerate(value):
        field = f"packet.inventory[{index}]"
        item = _packet_inventory_item(raw_item, field, requirements)
        if item.requirement_id in seen:
            raise ValueError(f"{field}.requirement_id: duplicate item")
        inventory.append(item)
        seen.add(item.requirement_id)
    missing = sorted(set(requirements) - seen)
    if missing:
        raise ValueError(
            "packet.inventory: missing requirements: " + ", ".join(missing)
        )
    return tuple(inventory)


def load_readiness_packet(
    path: Path,
    workflow: ReadinessWorkflow,
    *,
    today: date | None = None,
) -> ReadinessPacket:
    """Load an explicit packet inventory for a readiness workflow."""

    raw = _packet_record(path)
    synthetic = raw["synthetic"]
    if not isinstance(synthetic, bool):
        raise ValueError("packet.synthetic: expected boolean")
    return ReadinessPacket(
        packet_id=_identifier(raw["packet_id"], "packet.packet_id"),
        workflow_id=_identifier(raw["workflow_id"], "packet.workflow_id"),
        label=_required_text(raw["label"], "packet.label"),
        synthetic=synthetic,
        evaluated_on=_iso_date(
            raw["evaluated_on"],
            "packet.evaluated_on",
            today=resolve_today(today),
        ),
        jurisdiction=_identifier(raw["jurisdiction"], "packet.jurisdiction"),
        project_type=_identifier(raw["project_type"], "packet.project_type"),
        facts=_packet_facts(raw["facts"], workflow),
        inventory=_packet_inventory(raw["inventory"], workflow),
    )


def _remedies_record(path: Path) -> dict[str, Any]:
    payload = _read_json(path, str(path))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected an object")
    keys = {
        "schema_version",
        "workflow_id",
        "workflow_fingerprint",
        "version",
        "updated_on",
        "drafted_by",
        "review",
        "entries",
    }
    _exact_keys(payload, keys, keys, str(path))
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported schema version")
    return payload


def _remedy_review(
    value: Any,
    version: str,
    as_of: date,
) -> RemedyReview:
    if not isinstance(value, dict):
        raise ValueError("remedies.review: expected an object")
    keys = {
        "status",
        "reviewer",
        "method",
        "reviewed_on",
        "reviewed_version",
        "content_fingerprint",
    }
    _exact_keys(value, keys, keys, "remedies.review")
    status = _required_text(value["status"], "remedies.review.status")
    if status not in (
        "prototype_review_pending",
        "human_reviewed",
        "jurisdiction_approved",
    ):
        raise ValueError("remedies.review.status: unsupported status")
    reviewer = _optional_text(value["reviewer"], "remedies.review.reviewer")
    method = _optional_text(value["method"], "remedies.review.method")
    reviewed_version = _optional_text(
        value["reviewed_version"],
        "remedies.review.reviewed_version",
    )
    content_fingerprint = _optional_text(
        value["content_fingerprint"],
        "remedies.review.content_fingerprint",
    )
    if content_fingerprint is not None and not re.fullmatch(
        r"sha256:[0-9a-f]{64}", content_fingerprint
    ):
        raise ValueError("remedies.review.content_fingerprint: invalid fingerprint")
    reviewed_on_value = value["reviewed_on"]
    reviewed_on = (
        None
        if reviewed_on_value is None
        else _iso_date(
            reviewed_on_value,
            "remedies.review.reviewed_on",
            today=as_of,
        )
    )
    metadata = (reviewer, method, reviewed_on, reviewed_version, content_fingerprint)
    if status == "prototype_review_pending":
        if any(item is not None for item in metadata):
            raise ValueError(
                "remedies.review: pending review cannot carry review claims"
            )
    elif not all((reviewer, method, reviewed_on, content_fingerprint)) or (
        reviewed_version != version
    ):
        raise ValueError(
            "remedies.review: completed review must name reviewer, method, "
            "date, and exact version"
        )
    return RemedyReview(
        status=status,
        reviewer=reviewer,
        method=method,
        reviewed_on=reviewed_on,
        reviewed_version=reviewed_version,
        content_fingerprint=content_fingerprint,
    )


def _remedy_entry(
    value: Any,
    field: str,
    requirements: dict[str, Requirement],
) -> ReadinessRemedy:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    keys = {"requirement_id", "requirement_fingerprint", "action"}
    _exact_keys(value, keys, keys, field)
    requirement_id = _identifier(value["requirement_id"], f"{field}.requirement_id")
    requirement = requirements.get(requirement_id)
    if requirement is None:
        raise ValueError(f"{field}.requirement_id: orphan entry")
    fingerprint = _required_text(
        value["requirement_fingerprint"], f"{field}.requirement_fingerprint"
    )
    if fingerprint != requirement.fingerprint():
        raise ValueError(f"{field}.requirement_fingerprint: requirement drifted")
    return ReadinessRemedy(
        requirement_id=requirement_id,
        requirement_fingerprint=fingerprint,
        action=_required_text(value["action"], f"{field}.action"),
    )


def _remedy_entries(
    value: Any,
    workflow: ReadinessWorkflow,
) -> tuple[ReadinessRemedy, ...]:
    if not isinstance(value, list):
        raise ValueError("remedies.entries: expected a list")
    requirements = workflow.requirement_map()
    entries: list[ReadinessRemedy] = []
    seen: set[str] = set()
    for index, raw_entry in enumerate(value):
        field = f"remedies.entries[{index}]"
        entry = _remedy_entry(raw_entry, field, requirements)
        if entry.requirement_id in seen:
            raise ValueError(f"{field}.requirement_id: duplicate entry")
        entries.append(entry)
        seen.add(entry.requirement_id)
    missing = sorted(set(requirements) - seen)
    if missing:
        raise ValueError(
            "remedies.entries: missing requirements: " + ", ".join(missing)
        )
    return tuple(entries)


def _validate_remedy_review_fingerprint(
    review: RemedyReview,
    entries: tuple[ReadinessRemedy, ...],
    version: str,
    workflow_id: str,
) -> None:
    expected = _fingerprint(
        {
            "entries": [asdict(entry) for entry in entries],
            "version": version,
            "workflow_id": workflow_id,
        }
    )
    if (
        review.status != "prototype_review_pending"
        and review.content_fingerprint != expected
    ):
        raise ValueError("remedies.review.content_fingerprint: reviewed copy drifted")


def load_readiness_remedies(
    path: Path,
    workflow: ReadinessWorkflow,
    *,
    today: date | None = None,
) -> ReadinessRemedies:
    """Load versioned, review-tracked action copy for readiness findings.

    Remedy copy is display-only. The deterministic evaluator never imports it.
    """

    payload = _remedies_record(path)
    workflow_id = _identifier(payload["workflow_id"], "remedies.workflow_id")
    if workflow_id != workflow.workflow_id:
        raise ValueError("remedies.workflow_id: does not match workflow")
    workflow_fingerprint = _required_text(
        payload["workflow_fingerprint"], "remedies.workflow_fingerprint"
    )
    if workflow_fingerprint != workflow.fingerprint():
        raise ValueError("remedies.workflow_fingerprint: workflow content drifted")
    version = _required_text(payload["version"], "remedies.version")
    if not _SEMVER.fullmatch(version):
        raise ValueError("remedies.version: expected semantic version")
    as_of = resolve_today(today)
    updated_on = _iso_date(payload["updated_on"], "remedies.updated_on", today=as_of)
    drafted_by = _required_text(payload["drafted_by"], "remedies.drafted_by")
    if drafted_by != "ai_assisted":
        raise ValueError("remedies.drafted_by: current prototype requires ai_assisted")
    review = _remedy_review(payload["review"], version, as_of)
    entries = _remedy_entries(payload["entries"], workflow)
    _validate_remedy_review_fingerprint(review, entries, version, workflow_id)
    return ReadinessRemedies(
        workflow_id=workflow_id,
        workflow_fingerprint=workflow_fingerprint,
        version=version,
        updated_on=updated_on,
        drafted_by=drafted_by,
        review=review,
        entries=entries,
    )


def _condition_state(
    conditions: tuple[Condition, ...],
    facts: dict[str, str],
) -> str:
    """Return ``applies``, ``does_not_apply``, or ``unknown``."""

    saw_unknown = False
    for condition in conditions:
        actual = facts.get(condition.fact_id)
        if actual is None or actual == "unknown":
            saw_unknown = True
        elif actual != condition.equals:
            return "does_not_apply"
    return "unknown" if saw_unknown else "applies"


def _sources_current(
    workflow: ReadinessWorkflow,
    *,
    today: date,
    changed_source_ids: set[str],
    max_age_days: int,
) -> bool:
    for binding in workflow.source_bindings:
        if binding.source_id in changed_source_ids:
            return False
        checked = date.fromisoformat(binding.source_checked_on)
        age = (today - checked).days
        if age < 0 or age > max_age_days:
            return False
    return True


def _source_review_due_on(
    workflow: ReadinessWorkflow,
    *,
    max_age_days: int,
) -> str:
    """Return the last date every bound source remains inside its age window."""

    return min(
        date.fromisoformat(binding.source_checked_on) + timedelta(days=max_age_days)
        for binding in workflow.source_bindings
    ).isoformat()


def _finding(
    requirement: Requirement,
    status: str,
    reason: str,
) -> ReadinessFinding:
    return ReadinessFinding(
        requirement_id=requirement.requirement_id,
        label=requirement.label,
        category=requirement.category,
        status=status,
        reason=reason,
        source_id=requirement.source_id,
        source_locator=requirement.source_locator,
        source_excerpt=requirement.source_excerpt,
        requirement_fingerprint=requirement.fingerprint(),
    )


def _uniform_findings(
    workflow: ReadinessWorkflow,
    status: str,
    reason: str,
) -> list[ReadinessFinding]:
    return [
        _finding(requirement, status, reason) for requirement in workflow.requirements
    ]


def _append_unknown_questions(
    conditions: tuple[Condition, ...],
    fact_values: dict[str, str],
    fact_definitions: dict[str, FactDefinition],
    questions: list[str],
) -> None:
    for condition in conditions:
        if fact_values.get(condition.fact_id) in (None, "unknown"):
            question = fact_definitions[condition.fact_id].question
            if question not in questions:
                questions.append(question)


def _requirement_finding(
    requirement: Requirement,
    fact_values: dict[str, str],
    fact_definitions: dict[str, FactDefinition],
    inventory: dict[str, str],
    prior_statuses: dict[str, str],
    questions: list[str],
) -> ReadinessFinding:
    state = _condition_state(requirement.applies_when, fact_values)
    if state == "does_not_apply":
        return _finding(
            requirement,
            "not_applicable",
            "The reported project facts do not trigger this item.",
        )
    if state == "unknown":
        _append_unknown_questions(
            requirement.applies_when,
            fact_values,
            fact_definitions,
            questions,
        )
        return _finding(
            requirement,
            "needs_staff_review",
            "A project fact that controls this item is unknown.",
        )
    parent_id = requirement.parent_requirement_id
    if parent_id is not None and prior_statuses.get(parent_id) != "present":
        return _finding(
            requirement,
            "not_evaluated",
            "This content was not evaluated because its parent document "
            "was not reported present.",
        )
    status, reason = _inventory_finding(inventory[requirement.requirement_id])
    return _finding(requirement, status, reason)


def _overall_status(findings: list[ReadinessFinding]) -> str:
    statuses = {finding.status for finding in findings}
    if "missing" in statuses:
        return "known_gaps"
    if statuses & {"conflicting", "needs_staff_review", "not_evaluated"}:
        return "needs_review"
    return "no_known_gaps_in_bounded_manifest"


def _active_findings(
    workflow: ReadinessWorkflow,
    fact_values: dict[str, str],
    inventory: dict[str, str],
) -> tuple[str, list[ReadinessFinding], list[str]]:
    fact_definitions = workflow.fact_map()
    findings: list[ReadinessFinding] = []
    statuses: dict[str, str] = {}
    questions: list[str] = []
    for requirement in workflow.requirements:
        finding = _requirement_finding(
            requirement,
            fact_values,
            fact_definitions,
            inventory,
            statuses,
            questions,
        )
        findings.append(finding)
        statuses[requirement.requirement_id] = finding.status
    return _overall_status(findings), findings, questions


def _applicability_state(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
    fact_values: dict[str, str],
) -> str:
    same_workflow = (
        packet.workflow_id == workflow.workflow_id
        and packet.jurisdiction == workflow.jurisdiction
        and packet.project_type == workflow.project_type
    )
    if not same_workflow:
        return "does_not_apply"
    return _condition_state(workflow.applicability, fact_values)


def _evaluation_outcome(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
    source_current: bool,
) -> tuple[str, str, list[ReadinessFinding], list[str]]:
    fact_values = packet.fact_values()
    if not source_current:
        findings = _uniform_findings(
            workflow,
            "needs_staff_review",
            "The linked checklist needs source review before this requirement "
            "can support a packet finding.",
        )
        question = (
            "Ask the City to confirm the current checklist before using this "
            "packet-presence result."
        )
        return "source_review_required", "source_review_required", findings, [question]
    applicability = _applicability_state(workflow, packet, fact_values)
    if applicability == "does_not_apply":
        findings = _uniform_findings(
            workflow,
            "not_evaluated",
            "This packet is outside the one preapproved-plan workflow encoded "
            "by the prototype.",
        )
        question = "Ask Woodland staff which current checklist applies to this project."
        return "outside_bounded_workflow", "current", findings, [question]
    if applicability == "unknown":
        questions: list[str] = []
        _append_unknown_questions(
            workflow.applicability,
            fact_values,
            workflow.fact_map(),
            questions,
        )
        findings = _uniform_findings(
            workflow,
            "not_evaluated",
            "Confirm that this is the encoded preapproved-plan workflow before "
            "checking its packet.",
        )
        return "needs_review", "current", findings, questions
    overall, findings, questions = _active_findings(
        workflow, fact_values, packet.inventory_map()
    )
    return overall, "current", findings, questions


def evaluate_readiness(
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
    *,
    today: date | None = None,
    changed_source_ids: set[str] | None = None,
    max_age_days: int = SOURCE_MAX_AGE_DAYS,
) -> ReadinessResult:
    """Evaluate a packet without treating unknowns as favorable.

    The result intentionally uses ``no_known_gaps_in_bounded_manifest`` rather
    than ``complete``. It is only a presence check against one source-bound
    manifest.
    """

    if max_age_days < 0:
        raise ValueError("max_age_days must be non-negative")
    as_of = resolve_today(today)
    boundary = (
        "This prototype checks reported item presence against one City "
        "checklist. It does not inspect files, verify parcel facts, determine "
        "legal sufficiency, certify completeness, or limit what staff may "
        "request."
    )

    overall, source_status, findings, questions = _evaluation_outcome(
        workflow,
        packet,
        _sources_current(
            workflow,
            today=as_of,
            changed_source_ids=set(changed_source_ids or set()),
            max_age_days=max_age_days,
        ),
    )

    if overall not in OVERALL_STATUSES:
        raise AssertionError("unreachable overall readiness status")
    if any(finding.status not in FINDING_STATUSES for finding in findings):
        raise AssertionError("unreachable finding status")
    return ReadinessResult(
        packet_id=packet.packet_id,
        workflow_id=workflow.workflow_id,
        overall_status=overall,
        evaluated_on=as_of.isoformat(),
        workflow_fingerprint=workflow.fingerprint(),
        packet_fingerprint=packet.fingerprint(),
        source_status=source_status,
        source_status_as_of=as_of.isoformat(),
        source_review_due_on=_source_review_due_on(
            workflow,
            max_age_days=max_age_days,
        ),
        findings=tuple(findings),
        staff_questions=tuple(questions),
        boundary=boundary,
    )


def _inventory_finding(status: str) -> tuple[str, str]:
    if status == "present":
        return (
            "present",
            "The synthetic inventory reports this item present. Its contents "
            "were not inspected.",
        )
    if status == "missing":
        return (
            "missing",
            "The synthetic inventory reports this item missing.",
        )
    if status == "conflicting":
        return (
            "conflicting",
            "The synthetic inventory contains conflicting information that "
            "needs review.",
        )
    return (
        "needs_staff_review",
        "The synthetic inventory does not confirm whether this item is present.",
    )


def load_and_evaluate_readiness(
    workflow_path: Path,
    packet_path: Path,
    sources_path: Path,
    *,
    today: date | None = None,
    changed_source_ids: set[str] | None = None,
) -> tuple[ReadinessWorkflow, ReadinessPacket, ReadinessResult]:
    """Convenience entry point for build scripts and the CLI."""

    workflow = load_readiness_workflow(
        workflow_path,
        sources_path,
        today=today,
    )
    packet = load_readiness_packet(packet_path, workflow, today=today)
    evaluation_date = resolve_today(today)
    result = evaluate_readiness(
        workflow,
        packet,
        today=evaluation_date,
        changed_source_ids=changed_source_ids,
    )
    return workflow, packet, result
