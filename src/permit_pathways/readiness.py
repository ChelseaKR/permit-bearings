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


def _load_mapping_provenance(  # noqa: C901 — WVR-007
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
    updated_on = _iso_date(
        value["updated_on"],
        f"{field}.updated_on",
        today=today,
    )
    if date.fromisoformat(updated_on) < max(
        date.fromisoformat(binding.source_checked_on) for binding in bindings
    ):
        raise ValueError(
            f"{field}.updated_on: cannot predate an input source fingerprint"
        )

    drafted_by = _required_text(value["drafted_by"], f"{field}.drafted_by")
    if drafted_by != "ai_assisted":
        raise ValueError(f"{field}.drafted_by: current prototype requires ai_assisted")
    review_status = _required_text(value["review_status"], f"{field}.review_status")
    if review_status != "prototype_review_pending":
        raise ValueError(
            f"{field}.review_status: mapping and excerpts remain review-pending"
        )
    review_scope = _required_text(value["review_scope"], f"{field}.review_scope")
    if review_scope != "requirements_and_source_excerpts":
        raise ValueError(
            f"{field}.review_scope: expected requirements_and_source_excerpts"
        )
    provider = _required_text(value["provider"], f"{field}.provider")
    if provider != "unknown":
        raise ValueError(f"{field}.provider: no provider was recorded for this draft")
    model = _required_text(value["model"], f"{field}.model")
    if model != "unknown":
        raise ValueError(f"{field}.model: no model was recorded for this draft")
    run_record_status = _required_text(
        value["run_record_status"], f"{field}.run_record_status"
    )
    if run_record_status != "not_recorded":
        raise ValueError(f"{field}.run_record_status: current draft has no run record")

    raw_inputs = value["input_source_fingerprints"]
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise ValueError(
            f"{field}.input_source_fingerprints: expected a non-empty list"
        )
    bindings_by_id = {binding.source_id: binding for binding in bindings}
    inputs: list[MappingInputSource] = []
    seen: set[str] = set()
    for index, raw_input in enumerate(raw_inputs):
        input_field = f"{field}.input_source_fingerprints[{index}]"
        if not isinstance(raw_input, dict):
            raise ValueError(f"{input_field}: expected an object")
        _exact_keys(
            raw_input,
            {"source_id", "sha256"},
            {"source_id", "sha256"},
            input_field,
        )
        source_id = _identifier(raw_input["source_id"], f"{input_field}.source_id")
        if source_id in seen:
            raise ValueError(f"{input_field}.source_id: duplicate source")
        binding = bindings_by_id.get(source_id)
        if binding is None:
            raise ValueError(f"{input_field}.source_id: source is not bound")
        digest = _required_text(raw_input["sha256"], f"{input_field}.sha256")
        if not _SHA256.fullmatch(digest):
            raise ValueError(f"{input_field}.sha256: expected a SHA-256 digest")
        if digest != binding.sha256:
            raise ValueError(f"{input_field}.sha256: does not match bound source")
        inputs.append(MappingInputSource(source_id=source_id, sha256=digest))
        seen.add(source_id)
    missing = sorted(set(bindings_by_id) - seen)
    if missing:
        raise ValueError(
            f"{field}.input_source_fingerprints: missing sources: " + ", ".join(missing)
        )

    return MappingProvenance(
        version=version,
        updated_on=updated_on,
        drafted_by=drafted_by,
        input_source_fingerprints=tuple(inputs),
        review_status=review_status,
        review_scope=review_scope,
        provider=provider,
        model=model,
        run_record_status=run_record_status,
    )


def load_readiness_workflow(  # noqa: C901 — WVR-007
    path: Path,
    sources_path: Path,
    *,
    today: date | None = None,
) -> ReadinessWorkflow:
    """Load and strictly validate one source-bound readiness workflow."""

    as_of = resolve_today(today)
    payload = _read_json(path, str(path))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected an object")
    _exact_keys(
        payload,
        {"schema_version", "workflow"},
        {"schema_version", "workflow"},
        str(path),
    )
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported schema version")
    raw = payload["workflow"]
    if not isinstance(raw, dict):
        raise ValueError(f"{path}.workflow: expected an object")
    workflow_keys = {
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
    _exact_keys(raw, workflow_keys, workflow_keys, f"{path}.workflow")

    workflow_id = _identifier(raw["workflow_id"], "workflow.workflow_id")
    jurisdiction = _identifier(raw["jurisdiction"], "workflow.jurisdiction")
    project_type = _identifier(raw["project_type"], "workflow.project_type")
    status = _required_text(raw["status"], "workflow.status")
    if status != "prototype":
        raise ValueError("workflow.status: current schema requires 'prototype'")
    title = _required_text(raw["title"], "workflow.title")
    scope = _required_text(raw["scope"], "workflow.scope")

    sources = load_sources(sources_path, today=as_of)
    raw_bindings = raw["source_bindings"]
    if not isinstance(raw_bindings, list) or not raw_bindings:
        raise ValueError("workflow.source_bindings: expected a non-empty list")
    bindings: list[SourceBinding] = []
    bound_source_ids: set[str] = set()
    for index, value in enumerate(raw_bindings):
        field = f"workflow.source_bindings[{index}]"
        if not isinstance(value, dict):
            raise ValueError(f"{field}: expected an object")
        keys = {"source_id", "url", "sha256", "source_checked_on"}
        _exact_keys(value, keys, keys, field)
        source_id = _identifier(value["source_id"], f"{field}.source_id")
        if source_id in bound_source_ids:
            raise ValueError(f"{field}.source_id: duplicate source binding")
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
            value["source_checked_on"],
            f"{field}.source_checked_on",
            today=as_of,
        )
        if source.url != url or source.sha256 != digest or source.fetched_on != checked:
            raise ValueError(f"{field}: binding does not match the source registry")
        bound_source_ids.add(source_id)
        bindings.append(
            SourceBinding(
                source_id=source_id,
                url=url,
                sha256=digest,
                source_checked_on=checked,
            )
        )

    mapping_provenance = _load_mapping_provenance(
        raw["mapping_provenance"],
        tuple(bindings),
        today=as_of,
    )

    raw_facts = raw["facts"]
    if not isinstance(raw_facts, list) or not raw_facts:
        raise ValueError("workflow.facts: expected a non-empty list")
    facts: list[FactDefinition] = []
    facts_by_id: dict[str, FactDefinition] = {}
    for index, value in enumerate(raw_facts):
        field = f"workflow.facts[{index}]"
        if not isinstance(value, dict):
            raise ValueError(f"{field}: expected an object")
        keys = {"fact_id", "label", "question", "allowed_values"}
        _exact_keys(value, keys, keys, field)
        fact_id = _identifier(value["fact_id"], f"{field}.fact_id")
        if fact_id in facts_by_id:
            raise ValueError(f"{field}.fact_id: duplicate fact")
        allowed = value["allowed_values"]
        if not isinstance(allowed, list) or tuple(allowed) != TRI_VALUES:
            raise ValueError(f"{field}.allowed_values: expected yes, no, unknown")
        fact = FactDefinition(
            fact_id=fact_id,
            label=_required_text(value["label"], f"{field}.label"),
            question=_required_text(value["question"], f"{field}.question"),
            allowed_values=tuple(allowed),
        )
        facts.append(fact)
        facts_by_id[fact_id] = fact

    raw_applicability = raw["applicability"]
    if not isinstance(raw_applicability, list) or not raw_applicability:
        raise ValueError("workflow.applicability: expected a non-empty list")
    applicability = tuple(
        _load_condition(value, f"workflow.applicability[{index}]", facts_by_id)
        for index, value in enumerate(raw_applicability)
    )

    raw_requirements = raw["requirements"]
    if not isinstance(raw_requirements, list) or not raw_requirements:
        raise ValueError("workflow.requirements: expected a non-empty list")
    requirements: list[Requirement] = []
    requirements_by_id: dict[str, Requirement] = {}
    requirement_keys = {
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
    for index, value in enumerate(raw_requirements):
        field = f"workflow.requirements[{index}]"
        if not isinstance(value, dict):
            raise ValueError(f"{field}: expected an object")
        _exact_keys(value, requirement_keys, requirement_keys, field)
        requirement_id = _identifier(value["requirement_id"], f"{field}.requirement_id")
        if requirement_id in requirements_by_id:
            raise ValueError(f"{field}.requirement_id: duplicate requirement")
        item_type = _required_text(value["item_type"], f"{field}.item_type")
        if item_type not in ITEM_TYPES:
            raise ValueError(f"{field}.item_type: unsupported value")
        parent_id = _optional_text(
            value["parent_requirement_id"],
            f"{field}.parent_requirement_id",
        )
        if parent_id is not None:
            if not _IDENTIFIER.fullmatch(parent_id):
                raise ValueError(f"{field}.parent_requirement_id: invalid identifier")
            if parent_id not in requirements_by_id:
                raise ValueError(
                    f"{field}.parent_requirement_id: parent must appear first"
                )
        raw_conditions = value["applies_when"]
        if not isinstance(raw_conditions, list):
            raise ValueError(f"{field}.applies_when: expected a list")
        conditions = tuple(
            _load_condition(
                condition,
                f"{field}.applies_when[{condition_index}]",
                facts_by_id,
            )
            for condition_index, condition in enumerate(raw_conditions)
        )
        source_id = _identifier(value["source_id"], f"{field}.source_id")
        if source_id not in bound_source_ids:
            raise ValueError(f"{field}.source_id: source is not bound to the workflow")
        requirement = Requirement(
            requirement_id=requirement_id,
            label=_required_text(value["label"], f"{field}.label"),
            category=_required_text(value["category"], f"{field}.category"),
            item_type=item_type,
            parent_requirement_id=parent_id,
            applies_when=conditions,
            source_id=source_id,
            source_locator=_required_text(
                value["source_locator"], f"{field}.source_locator"
            ),
            source_excerpt=_required_text(
                value["source_excerpt"], f"{field}.source_excerpt"
            ),
        )
        requirements.append(requirement)
        requirements_by_id[requirement_id] = requirement

    return ReadinessWorkflow(
        workflow_id=workflow_id,
        jurisdiction=jurisdiction,
        project_type=project_type,
        status=status,
        title=title,
        scope=scope,
        source_bindings=tuple(bindings),
        mapping_provenance=mapping_provenance,
        applicability=applicability,
        facts=tuple(facts),
        requirements=tuple(requirements),
    )


def load_readiness_packet(  # noqa: C901 — WVR-007
    path: Path,
    workflow: ReadinessWorkflow,
    *,
    today: date | None = None,
) -> ReadinessPacket:
    """Load an explicit packet inventory for a readiness workflow."""

    payload = _read_json(path, str(path))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected an object")
    _exact_keys(
        payload,
        {"schema_version", "packet"},
        {"schema_version", "packet"},
        str(path),
    )
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported schema version")
    raw = payload["packet"]
    if not isinstance(raw, dict):
        raise ValueError(f"{path}.packet: expected an object")
    as_of = resolve_today(today)
    packet_keys = {
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
    _exact_keys(raw, packet_keys, packet_keys, f"{path}.packet")
    synthetic = raw["synthetic"]
    if not isinstance(synthetic, bool):
        raise ValueError("packet.synthetic: expected boolean")

    raw_facts = raw["facts"]
    if not isinstance(raw_facts, list):
        raise ValueError("packet.facts: expected a list")
    fact_definitions = workflow.fact_map()
    facts: list[PacketFact] = []
    seen_facts: set[str] = set()
    for index, value in enumerate(raw_facts):
        field = f"packet.facts[{index}]"
        if not isinstance(value, dict):
            raise ValueError(f"{field}: expected an object")
        keys = {"fact_id", "value", "provenance"}
        _exact_keys(value, keys, keys, field)
        fact_id = _identifier(value["fact_id"], f"{field}.fact_id")
        if fact_id in seen_facts:
            raise ValueError(f"{field}.fact_id: duplicate fact")
        definition = fact_definitions.get(fact_id)
        if definition is None:
            raise ValueError(f"{field}.fact_id: unknown workflow fact")
        fact_value = _required_text(value["value"], f"{field}.value")
        if fact_value not in definition.allowed_values:
            raise ValueError(f"{field}.value: unsupported value")
        provenance = _required_text(value["provenance"], f"{field}.provenance")
        if provenance not in PROVENANCE_VALUES:
            raise ValueError(f"{field}.provenance: unsupported value")
        facts.append(
            PacketFact(
                fact_id=fact_id,
                value=fact_value,
                provenance=provenance,
            )
        )
        seen_facts.add(fact_id)
    missing_facts = sorted(set(fact_definitions) - seen_facts)
    if missing_facts:
        raise ValueError("packet.facts: missing facts: " + ", ".join(missing_facts))

    raw_inventory = raw["inventory"]
    if not isinstance(raw_inventory, list):
        raise ValueError("packet.inventory: expected a list")
    requirement_definitions = workflow.requirement_map()
    inventory: list[InventoryItem] = []
    seen_requirements: set[str] = set()
    for index, value in enumerate(raw_inventory):
        field = f"packet.inventory[{index}]"
        if not isinstance(value, dict):
            raise ValueError(f"{field}: expected an object")
        keys = {"requirement_id", "status"}
        _exact_keys(value, keys, keys, field)
        requirement_id = _identifier(value["requirement_id"], f"{field}.requirement_id")
        if requirement_id in seen_requirements:
            raise ValueError(f"{field}.requirement_id: duplicate item")
        if requirement_id not in requirement_definitions:
            raise ValueError(f"{field}.requirement_id: unknown workflow requirement")
        status = _required_text(value["status"], f"{field}.status")
        if status not in INVENTORY_STATUSES:
            raise ValueError(f"{field}.status: unsupported value")
        inventory.append(InventoryItem(requirement_id=requirement_id, status=status))
        seen_requirements.add(requirement_id)
    missing_requirements = sorted(set(requirement_definitions) - seen_requirements)
    if missing_requirements:
        raise ValueError(
            "packet.inventory: missing requirements: " + ", ".join(missing_requirements)
        )

    return ReadinessPacket(
        packet_id=_identifier(raw["packet_id"], "packet.packet_id"),
        workflow_id=_identifier(raw["workflow_id"], "packet.workflow_id"),
        label=_required_text(raw["label"], "packet.label"),
        synthetic=synthetic,
        evaluated_on=_iso_date(raw["evaluated_on"], "packet.evaluated_on", today=as_of),
        jurisdiction=_identifier(raw["jurisdiction"], "packet.jurisdiction"),
        project_type=_identifier(raw["project_type"], "packet.project_type"),
        facts=tuple(facts),
        inventory=tuple(inventory),
    )


def load_readiness_remedies(  # noqa: C901 — WVR-007
    path: Path,
    workflow: ReadinessWorkflow,
    *,
    today: date | None = None,
) -> ReadinessRemedies:
    """Load versioned, review-tracked action copy for readiness findings.

    Remedy copy is display-only. The deterministic evaluator never imports it.
    """

    as_of = resolve_today(today)
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
    workflow_id = _identifier(payload["workflow_id"], "remedies.workflow_id")
    if workflow_id != workflow.workflow_id:
        raise ValueError("remedies.workflow_id: does not match workflow")
    workflow_fingerprint = _required_text(
        payload["workflow_fingerprint"],
        "remedies.workflow_fingerprint",
    )
    if workflow_fingerprint != workflow.fingerprint():
        raise ValueError("remedies.workflow_fingerprint: workflow content drifted")
    version = _required_text(payload["version"], "remedies.version")
    if not _SEMVER.fullmatch(version):
        raise ValueError("remedies.version: expected semantic version")
    updated_on = _iso_date(payload["updated_on"], "remedies.updated_on", today=as_of)
    drafted_by = _required_text(payload["drafted_by"], "remedies.drafted_by")
    if drafted_by != "ai_assisted":
        raise ValueError("remedies.drafted_by: current prototype requires ai_assisted")

    raw_review = payload["review"]
    if not isinstance(raw_review, dict):
        raise ValueError("remedies.review: expected an object")
    review_keys = {
        "status",
        "reviewer",
        "method",
        "reviewed_on",
        "reviewed_version",
        "content_fingerprint",
    }
    _exact_keys(raw_review, review_keys, review_keys, "remedies.review")
    review_status = _required_text(raw_review["status"], "remedies.review.status")
    if review_status not in (
        "prototype_review_pending",
        "human_reviewed",
        "jurisdiction_approved",
    ):
        raise ValueError("remedies.review.status: unsupported status")
    reviewer = _optional_text(raw_review["reviewer"], "remedies.review.reviewer")
    method = _optional_text(raw_review["method"], "remedies.review.method")
    reviewed_version = _optional_text(
        raw_review["reviewed_version"],
        "remedies.review.reviewed_version",
    )
    content_fingerprint = _optional_text(
        raw_review["content_fingerprint"],
        "remedies.review.content_fingerprint",
    )
    if content_fingerprint is not None and not re.fullmatch(
        r"sha256:[0-9a-f]{64}", content_fingerprint
    ):
        raise ValueError("remedies.review.content_fingerprint: invalid fingerprint")
    reviewed_on_value = raw_review["reviewed_on"]
    reviewed_on = (
        None
        if reviewed_on_value is None
        else _iso_date(
            reviewed_on_value,
            "remedies.review.reviewed_on",
            today=as_of,
        )
    )
    if review_status == "prototype_review_pending":
        if any(
            value is not None
            for value in (
                reviewer,
                method,
                reviewed_on,
                reviewed_version,
                content_fingerprint,
            )
        ):
            raise ValueError(
                "remedies.review: pending review cannot carry review claims"
            )
    elif (
        reviewer is None
        or method is None
        or reviewed_on is None
        or reviewed_version != version
        or content_fingerprint is None
    ):
        raise ValueError(
            "remedies.review: completed review must name reviewer, method, "
            "date, and exact version"
        )
    review = RemedyReview(
        status=review_status,
        reviewer=reviewer,
        method=method,
        reviewed_on=reviewed_on,
        reviewed_version=reviewed_version,
        content_fingerprint=content_fingerprint,
    )

    raw_entries = payload["entries"]
    if not isinstance(raw_entries, list):
        raise ValueError("remedies.entries: expected a list")
    requirements = workflow.requirement_map()
    entries: list[ReadinessRemedy] = []
    seen: set[str] = set()
    for index, value in enumerate(raw_entries):
        field = f"remedies.entries[{index}]"
        if not isinstance(value, dict):
            raise ValueError(f"{field}: expected an object")
        entry_keys = {
            "requirement_id",
            "requirement_fingerprint",
            "action",
        }
        _exact_keys(value, entry_keys, entry_keys, field)
        requirement_id = _identifier(value["requirement_id"], f"{field}.requirement_id")
        if requirement_id in seen:
            raise ValueError(f"{field}.requirement_id: duplicate entry")
        requirement = requirements.get(requirement_id)
        if requirement is None:
            raise ValueError(f"{field}.requirement_id: orphan entry")
        fingerprint = _required_text(
            value["requirement_fingerprint"],
            f"{field}.requirement_fingerprint",
        )
        if fingerprint != requirement.fingerprint():
            raise ValueError(f"{field}.requirement_fingerprint: requirement drifted")
        entries.append(
            ReadinessRemedy(
                requirement_id=requirement_id,
                requirement_fingerprint=fingerprint,
                action=_required_text(value["action"], f"{field}.action"),
            )
        )
        seen.add(requirement_id)
    missing = sorted(set(requirements) - seen)
    if missing:
        raise ValueError(
            "remedies.entries: missing requirements: " + ", ".join(missing)
        )
    expected_content_fingerprint = _fingerprint(
        {
            "entries": [asdict(entry) for entry in entries],
            "version": version,
            "workflow_id": workflow_id,
        }
    )
    if (
        review.status != "prototype_review_pending"
        and review.content_fingerprint != expected_content_fingerprint
    ):
        raise ValueError("remedies.review.content_fingerprint: reviewed copy drifted")
    return ReadinessRemedies(
        workflow_id=workflow_id,
        workflow_fingerprint=workflow_fingerprint,
        version=version,
        updated_on=updated_on,
        drafted_by=drafted_by,
        review=review,
        entries=tuple(entries),
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


def evaluate_readiness(  # noqa: C901 — WVR-007
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
    changed = set(changed_source_ids or set())
    fact_values = packet.fact_values()
    inventory = packet.inventory_map()
    fact_definitions = workflow.fact_map()
    findings: list[ReadinessFinding] = []
    questions: list[str] = []
    boundary = (
        "This prototype checks reported item presence against one City "
        "checklist. It does not inspect files, verify parcel facts, determine "
        "legal sufficiency, certify completeness, or limit what staff may "
        "request."
    )

    source_current = _sources_current(
        workflow,
        today=as_of,
        changed_source_ids=changed,
        max_age_days=max_age_days,
    )
    same_workflow = (
        packet.workflow_id == workflow.workflow_id
        and packet.jurisdiction == workflow.jurisdiction
        and packet.project_type == workflow.project_type
    )
    applicability_state = (
        _condition_state(workflow.applicability, fact_values)
        if same_workflow
        else "does_not_apply"
    )

    if not source_current:
        overall = "source_review_required"
        source_status = "source_review_required"
        questions.append(
            "Ask the City to confirm the current checklist before using this "
            "packet-presence result."
        )
        for requirement in workflow.requirements:
            findings.append(
                ReadinessFinding(
                    requirement_id=requirement.requirement_id,
                    label=requirement.label,
                    category=requirement.category,
                    status="needs_staff_review",
                    reason=(
                        "The linked checklist needs source review before this "
                        "requirement can support a packet finding."
                    ),
                    source_id=requirement.source_id,
                    source_locator=requirement.source_locator,
                    source_excerpt=requirement.source_excerpt,
                    requirement_fingerprint=requirement.fingerprint(),
                )
            )
    elif applicability_state == "does_not_apply":
        overall = "outside_bounded_workflow"
        source_status = "current"
        questions.append(
            "Ask Woodland staff which current checklist applies to this project."
        )
        for requirement in workflow.requirements:
            findings.append(
                ReadinessFinding(
                    requirement_id=requirement.requirement_id,
                    label=requirement.label,
                    category=requirement.category,
                    status="not_evaluated",
                    reason=(
                        "This packet is outside the one preapproved-plan "
                        "workflow encoded by the prototype."
                    ),
                    source_id=requirement.source_id,
                    source_locator=requirement.source_locator,
                    source_excerpt=requirement.source_excerpt,
                    requirement_fingerprint=requirement.fingerprint(),
                )
            )
    elif applicability_state == "unknown":
        overall = "needs_review"
        source_status = "current"
        for condition in workflow.applicability:
            if fact_values.get(condition.fact_id) in (None, "unknown"):
                question = fact_definitions[condition.fact_id].question
                if question not in questions:
                    questions.append(question)
        for requirement in workflow.requirements:
            findings.append(
                ReadinessFinding(
                    requirement_id=requirement.requirement_id,
                    label=requirement.label,
                    category=requirement.category,
                    status="not_evaluated",
                    reason=(
                        "Confirm that this is the encoded preapproved-plan "
                        "workflow before checking its packet."
                    ),
                    source_id=requirement.source_id,
                    source_locator=requirement.source_locator,
                    source_excerpt=requirement.source_excerpt,
                    requirement_fingerprint=requirement.fingerprint(),
                )
            )
    else:
        source_status = "current"
        finding_status_by_id: dict[str, str] = {}
        for requirement in workflow.requirements:
            condition_state = _condition_state(requirement.applies_when, fact_values)
            if condition_state == "does_not_apply":
                status = "not_applicable"
                reason = "The reported project facts do not trigger this item."
            elif condition_state == "unknown":
                status = "needs_staff_review"
                reason = "A project fact that controls this item is unknown."
                for condition in requirement.applies_when:
                    if fact_values.get(condition.fact_id) in (None, "unknown"):
                        question = fact_definitions[condition.fact_id].question
                        if question not in questions:
                            questions.append(question)
            elif requirement.parent_requirement_id is not None:
                parent_status = finding_status_by_id.get(
                    requirement.parent_requirement_id
                )
                if parent_status != "present":
                    status = "not_evaluated"
                    reason = (
                        "This content was not evaluated because its parent "
                        "document was not reported present."
                    )
                else:
                    status, reason = _inventory_finding(
                        inventory[requirement.requirement_id]
                    )
            else:
                status, reason = _inventory_finding(
                    inventory[requirement.requirement_id]
                )
            finding_status_by_id[requirement.requirement_id] = status
            findings.append(
                ReadinessFinding(
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
            )
        statuses = {finding.status for finding in findings}
        if "missing" in statuses:
            overall = "known_gaps"
        elif statuses & {"conflicting", "needs_staff_review", "not_evaluated"}:
            overall = "needs_review"
        else:
            overall = "no_known_gaps_in_bounded_manifest"

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
