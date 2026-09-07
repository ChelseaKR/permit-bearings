"""The machine-readable contract around the deterministic matcher.

The matcher in :mod:`permit_pathways.screening` is reachable through three
runtimes -- the browser bundle, the Python reference demo, and the optional AI
service's internal re-run -- and until this module existed none of them shared a
written contract. That is risk 7 in ``docs/PRODUCT-CONTEXT.md`` (cross-runtime
drift), and it is why a third system consuming a result had no way to check what
it was being handed.

This module holds two things and no behaviour of its own:

* **The result envelope.** A screening result is not a list of rules. It is a
  list of rules *plus the boundary it was computed inside*: which rule set,
  which source snapshot, which facts the applicant could not answer, and the
  explicit statement that these are candidate rules rather than an eligibility
  determination. :func:`build_result` assembles that, and it is the only place
  the envelope's shape is decided.

* **The three JSON Schemas**, generated from the Python definitions rather than
  written beside them. ``schemas/*.schema.json`` is committed for integrators;
  ``tests/test_screening_contract.py`` regenerates and compares, so a schema
  cannot drift from the code it describes without failing a test.

Two rules this module exists to keep, both instances of the same mistake --
publishing an absence as though it were a measurement:

* A fact the applicant did not answer is **not** a fact answered "no". It is
  carried in ``unresolved_facts``, it sets ``decision_boundary`` to
  ``needs_staff_review``, and it withholds ``candidate_routes`` entirely. The
  matched rules are still reported, because hiding them would misrepresent
  coverage, but nothing derived from them is presented as a route.

* A missing source-state snapshot yields ``source_state.snapshot_id: null`` and
  a notice, never a placeholder id and never an empty object that reads like a
  clean bill of health. An unverifiable source is reported as unverifiable, not
  folded into "unchanged".

Dependency-free by construction: nothing here imports outside the standard
library and the project's own dependency-free modules.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict
from typing import Any

from .ai.facts import (
    FACT_FIELDS,
    FIELDS_BY_NAME,
    PROJECT_TYPES,
    UNKNOWN,
    material_fields,
)
from .screening import (
    DISPLAY_GROUPS,
    ROUTE_CLASSES,
    SUPPORTED_OPERATORS,
    PathwayResult,
    Rule,
)

#: Bumped when the envelope's shape changes in a way a consumer must notice.
SCHEMA_VERSION = 1

#: What a result is allowed to claim about itself. Neither value means
#: "eligible": the project does not make eligibility determinations, and the
#: boundary is carried in the payload so a consumer cannot drop it.
DECISION_BOUNDARIES = ("candidate_rules_only", "needs_staff_review")

#: The only provenance a fact reaching this contract can have. The CLI takes
#: facts from a file the applicant or their helper wrote; nothing here verifies
#: a parcel, a zoning designation, or a permit history against any authority.
FACT_PROVENANCE = "applicant_asserted"

#: Fields that are not rule facts but are required to screen at all.
_REQUIRED_NON_FACT_FIELDS = ("project_type", "jurisdiction")

_SCHEMA_BASE = "https://chelseakr.github.io/permit-bearings/schemas"


class FactsDocumentError(ValueError):
    """A facts document that cannot be screened, with every reason listed.

    Every reason, not the first: a CLI that reports one error per run makes an
    integrator fix a five-field file in five runs, and the failures are usually
    the same mistake repeated.
    """

    def __init__(self, reasons: Sequence[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = tuple(reasons)


def rules_fingerprint(rules: Iterable[Rule]) -> str:
    """A digest of the rule set a result was computed against.

    Taken over the parsed rules rather than the bytes on disk, so reformatting
    ``data/rules/*.json`` does not change it and an edit to a criterion does.
    Rules are sorted by id, so directory order cannot move the digest either.
    """
    payload = [
        {
            "rule_id": rule.rule_id,
            "pathway": rule.pathway,
            "route_class": rule.route_class,
            "jurisdiction_scope": rule.jurisdiction_scope,
            "display_group": rule.display_group,
            "criteria": rule.criteria,
            "citation": asdict(rule.citation),
            "source_dependencies": rule.source_dependencies,
            "required_documents": rule.required_documents,
            "notes": rule.notes,
        }
        for rule in sorted(rules, key=lambda r: r.rule_id)
    ]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_facts_document(document: Any) -> dict[str, Any]:
    """Return the intake to screen, or raise with every reason it cannot be.

    Fails closed. An unknown field name and an unknown value are both errors
    naming the field and what it accepts, because the alternative -- ignoring
    what it does not recognise -- silently screens a different project than the
    one described.
    """
    if not isinstance(document, dict):
        raise FactsDocumentError(["facts document must be a JSON object"])

    reasons, project_type = _check_required_fields(document)
    reasons.extend(_check_fact_entries(document, project_type))
    if reasons:
        raise FactsDocumentError(reasons)
    return dict(document)


def _check_required_fields(document: dict[str, Any]) -> tuple[list[str], str | None]:
    """The two fields that are not rule facts, plus the project type to screen as.

    Returns ``None`` for the project type when it is missing or unrecognised, so
    the per-fact applicability check below skips rather than reporting every
    field as inapplicable to a type that was never valid.
    """
    reasons: list[str] = []
    for required in _REQUIRED_NON_FACT_FIELDS:
        if required not in document:
            reasons.append(f"{required}: required")

    project_type = document.get("project_type")
    if "project_type" in document and project_type not in PROJECT_TYPES:
        reasons.append(
            f"project_type: {project_type!r} is not one of {list(PROJECT_TYPES)}"
        )
        project_type = None

    jurisdiction = document.get("jurisdiction")
    if "jurisdiction" in document and (
        not isinstance(jurisdiction, str) or not jurisdiction.strip()
    ):
        reasons.append("jurisdiction: must be a non-empty string")
    return reasons, project_type if isinstance(project_type, str) else None


def _check_fact_entries(
    document: dict[str, Any], project_type: str | None
) -> list[str]:
    reasons: list[str] = []
    for name, value in document.items():
        if name in _REQUIRED_NON_FACT_FIELDS:
            continue
        field = FIELDS_BY_NAME.get(name)
        if field is None:
            reasons.append(f"{name}: not a known fact; see {list(FACT_NAMES_SORTED)}")
        elif value not in field.values:
            reasons.append(f"{name}: {value!r} is not one of {list(field.values)}")
        elif project_type is not None and project_type not in field.applies_to:
            reasons.append(
                f"{name}: not read for project_type {project_type!r} "
                f"(applies to {list(field.applies_to)})"
            )
    return reasons


#: Sorted for a stable error message; `FACT_NAMES` is in intake order.
FACT_NAMES_SORTED: tuple[str, ...] = tuple(sorted(f.name for f in FACT_FIELDS))


def unresolved_facts(intake: Mapping[str, Any]) -> tuple[str, ...]:
    """Material facts the applicant did not answer, in the browser form's order.

    Absent and ``"unknown"`` are the same state here and are treated the same
    way: the applicant has not told us. Keeping form order rather than sorting
    means the list reads as the questions still to ask.
    """
    project_type = intake.get("project_type")
    if not isinstance(project_type, str):
        return ()
    return tuple(
        name
        for name in material_fields(project_type)
        if intake.get(name, UNKNOWN) == UNKNOWN
    )


def _citation_payload(rule: Rule) -> dict[str, Any]:
    citation = rule.citation
    return {
        "source": citation.source,
        "url": citation.url,
        "excerpt": citation.excerpt,
        "excerpt_sha256": citation.excerpt_sha256,
        "verified_on": citation.verified_on,
    }


def _matched_rule_payload(result: PathwayResult) -> dict[str, Any]:
    rule = result.rule
    return {
        "rule_id": rule.rule_id,
        "pathway": rule.pathway,
        "route_class": rule.route_class,
        "display_group": rule.display_group,
        "jurisdiction_scope": rule.jurisdiction_scope,
        "required_documents": list(rule.required_documents),
        "source_dependencies": list(rule.source_dependencies),
        "citation": _citation_payload(rule),
        # Named for what it is. `verified` used to read as "this rule is
        # correct"; it records only that its citation carries a date.
        "has_dated_source_record": result.verified,
    }


def _id_list(snapshot: Mapping[str, Any], key: str) -> list[str] | None:
    """One of the snapshot's id lists, or ``None`` when it does not carry it.

    ``or []`` was the first version of this, and it was the very defect the rest
    of this module exists to prevent: a snapshot that was supplied but does not
    carry ``changed_source_ids`` would have published an empty list, which reads
    as "nothing changed" — a finding the snapshot never reported. A key that is
    absent, null, or not a list of strings is unknown, and unknown is ``None``.
    """
    value = snapshot.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return list(value)


def source_state_summary(snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    """What the result can honestly say about the sources under it.

    ``None`` means no snapshot was supplied or one could not be read. That is
    reported as nulls plus a notice rather than as an empty summary: an empty
    ``changed_source_ids`` list looks exactly like "nothing changed", and an
    absent check is not the same finding as a clean one.

    ``available`` says only that a snapshot was read. Each field is reported
    separately, because a snapshot can be present and still not answer a
    question — and a supplied snapshot missing a field is not evidence of an
    empty answer to it.
    """
    if snapshot is None:
        return {
            "snapshot_id": None,
            "receipt_id": None,
            "receipt_status": None,
            "checked_at": None,
            "changed_source_ids": None,
            "unverifiable_source_ids": None,
            "affected_rule_ids": None,
            "available": False,
        }
    receipt = snapshot.get("receipt")
    receipt_map = receipt if isinstance(receipt, Mapping) else {}
    return {
        # The snapshot id *is* the receipt identity in this project's source
        # records; there is no separate receipt id field, so one is not invented.
        "snapshot_id": snapshot.get("snapshot_id"),
        "receipt_id": snapshot.get("snapshot_id"),
        "receipt_status": receipt_map.get("status"),
        "checked_at": snapshot.get("checked_at"),
        "changed_source_ids": _id_list(snapshot, "changed_source_ids"),
        "unverifiable_source_ids": _id_list(snapshot, "unverifiable_source_ids"),
        "affected_rule_ids": _id_list(snapshot, "affected_rule_ids"),
        "available": True,
    }


def build_result(
    *,
    intake: Mapping[str, Any],
    rules: Sequence[Rule],
    results: Sequence[PathwayResult],
    as_of: str,
    source_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Assemble the result envelope. Pure: no clock, no filesystem, no network."""
    unresolved = unresolved_facts(intake)
    boundary = "needs_staff_review" if unresolved else "candidate_rules_only"

    matched = [_matched_rule_payload(result) for result in results]
    # Withheld, not empty-by-accident: a route named while a material fact is
    # unknown is a route the encoded rules do not actually support yet.
    routes = (
        [] if unresolved else sorted({payload["route_class"] for payload in matched})
    )

    facts_payload = [
        {
            "field": name,
            "value": intake.get(name, UNKNOWN),
            "known": intake.get(name, UNKNOWN) != UNKNOWN,
            "provenance": FACT_PROVENANCE,
        }
        for name in material_fields(str(intake.get("project_type", "")))
    ]

    source = source_state_summary(source_state)
    notices: list[str] = []
    if unresolved:
        notices.append(
            "A material fact is unknown, so no candidate route is reported. "
            "Staff review is needed for: " + ", ".join(unresolved) + "."
        )
    if not source["available"]:
        notices.append(
            "No source-state snapshot was supplied, so this result says nothing "
            "about whether the cited sources have changed since they were recorded."
        )
    else:
        # Reported per field, because a supplied snapshot can still fail to
        # answer one of these, and silence about a question is not an answer of
        # "none". `unverifiable is None` and `unverifiable == []` are different
        # findings and get different sentences.
        unsaid = sorted(
            key
            for key in (
                "changed_source_ids",
                "unverifiable_source_ids",
                "affected_rule_ids",
            )
            if source[key] is None
        )
        if unsaid:
            notices.append(
                "The source-state snapshot does not record "
                + ", ".join(unsaid)
                + ", so this result says nothing about "
                + ("them." if len(unsaid) > 1 else "it.")
            )
        if source["unverifiable_source_ids"]:
            notices.append(
                "Some sources could not be fetched on the last check and are neither "
                "confirmed unchanged nor known to have changed: "
                + ", ".join(source["unverifiable_source_ids"])
                + "."
            )

    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of,
        "jurisdiction": intake.get("jurisdiction"),
        "project_type": intake.get("project_type"),
        "decision_boundary": boundary,
        "decision_boundary_statement": (
            "These are candidate rules from an encoded, cited rule set. This is "
            "not an eligibility determination, a completeness determination, or "
            "a jurisdiction approval."
        ),
        "facts": facts_payload,
        "unresolved_facts": list(unresolved),
        "matched_rules": matched,
        "candidate_routes": routes,
        "source_state": source,
        "rules_fingerprint": rules_fingerprint(rules),
        "notices": notices,
    }


# --- the published schemas, generated from the definitions above -------------


def _string_enum(values: Iterable[str], description: str) -> dict[str, Any]:
    return {"type": "string", "enum": list(values), "description": description}


def facts_schema() -> dict[str, Any]:
    """The intake document an integrator writes, from ``ai.facts``."""
    properties: dict[str, Any] = {
        "project_type": _string_enum(
            PROJECT_TYPES, "The kind of project being screened."
        ),
        "jurisdiction": {
            "type": "string",
            "minLength": 1,
            "description": (
                "Jurisdiction slug. Rules scoped 'statewide' apply to every "
                "jurisdiction; others apply only to the slug they name."
            ),
        },
    }
    for field in FACT_FIELDS:
        properties[field.name] = _string_enum(
            field.values,
            f"{field.meaning} Read only for project types: "
            f"{', '.join(field.applies_to)}. "
            f"'{UNKNOWN}' means the applicant did not answer, which withholds "
            "candidate routes rather than defaulting the answer.",
        )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{_SCHEMA_BASE}/facts.schema.json",
        "title": "Permit Bearings screening facts",
        "description": (
            "Applicant-asserted facts for one project. Every value is asserted "
            "by whoever wrote the file; nothing here is verified against a "
            "parcel record, a zoning map, or a permit history."
        ),
        "type": "object",
        "required": list(_REQUIRED_NON_FACT_FIELDS),
        "additionalProperties": False,
        "properties": properties,
    }


def rule_schema() -> dict[str, Any]:
    """One record in ``data/rules/*.json``, from the loader's own key sets."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{_SCHEMA_BASE}/rule.schema.json",
        "title": "Permit Bearings rule record",
        "description": (
            "Rules are data, not code: each record carries its own citation. An "
            "uncited rule is a schema error, not a softer answer."
        ),
        "type": "object",
        "required": [
            "rule_id",
            "pathway",
            "route_class",
            "jurisdiction_scope",
            "criteria",
            "citation",
            "source_dependencies",
            "display_group",
        ],
        "additionalProperties": False,
        "properties": {
            "rule_id": {"type": "string", "minLength": 1},
            "pathway": {"type": "string", "minLength": 1},
            "route_class": _string_enum(ROUTE_CLASSES, "How the route is decided."),
            "jurisdiction_scope": {
                "type": "string",
                "description": "'statewide', or a jurisdiction slug.",
            },
            "display_group": _string_enum(
                DISPLAY_GROUPS, "Where the rule is presented in a result."
            ),
            "criteria": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["field", "op", "value"],
                    "additionalProperties": False,
                    "properties": {
                        "field": {"type": "string"},
                        "op": _string_enum(
                            SUPPORTED_OPERATORS,
                            "Comparison the matcher applies.",
                        ),
                        "value": {},
                    },
                },
            },
            "citation": {
                "type": "object",
                "required": ["source", "url"],
                "additionalProperties": False,
                "properties": {
                    "source": {"type": "string", "minLength": 1},
                    "url": {"type": "string", "minLength": 1},
                    "excerpt": {"type": ["string", "null"]},
                    "excerpt_sha256": {"type": ["string", "null"]},
                    "verified_on": {
                        "type": ["string", "null"],
                        "description": (
                            "ISO date the source evidence carries. Null means no "
                            "dated source record -- not that the rule is wrong, "
                            "and not that it is current."
                        ),
                    },
                },
            },
            "source_dependencies": {"type": "array", "items": {"type": "string"}},
            "required_documents": {"type": "array", "items": {"type": "string"}},
            "notes": {"type": "string"},
        },
    }


def result_schema() -> dict[str, Any]:
    """The envelope :func:`build_result` produces."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{_SCHEMA_BASE}/result.schema.json",
        "title": "Permit Bearings screening result",
        "description": (
            "One screening result and the boundary it was computed inside. A "
            "consumer that drops 'decision_boundary', 'unresolved_facts' or "
            "'source_state' is reporting something this project does not claim."
        ),
        "type": "object",
        "required": [
            "schema_version",
            "as_of",
            "jurisdiction",
            "project_type",
            "decision_boundary",
            "decision_boundary_statement",
            "facts",
            "unresolved_facts",
            "matched_rules",
            "candidate_routes",
            "source_state",
            "rules_fingerprint",
            "notices",
        ],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": SCHEMA_VERSION},
            "as_of": {"type": "string", "description": "ISO date the run used."},
            "jurisdiction": {"type": "string"},
            "project_type": _string_enum(PROJECT_TYPES, "The project screened."),
            "decision_boundary": _string_enum(
                DECISION_BOUNDARIES,
                "'needs_staff_review' whenever a material fact is unknown.",
            ),
            "decision_boundary_statement": {"type": "string"},
            "facts": {
                "type": "array",
                "description": "The material facts for this project type, in form order.",
                "items": {
                    "type": "object",
                    "required": ["field", "value", "known", "provenance"],
                    "additionalProperties": False,
                    "properties": {
                        "field": _string_enum(FACT_NAMES_SORTED, "Fact name."),
                        "value": {"type": "string"},
                        "known": {
                            "type": "boolean",
                            "description": "False when the applicant did not answer.",
                        },
                        "provenance": {"type": "string", "const": FACT_PROVENANCE},
                    },
                },
            },
            "unresolved_facts": {"type": "array", "items": {"type": "string"}},
            "matched_rules": {
                "type": "array",
                "description": (
                    "Every rule whose criteria the intake satisfies, including "
                    "rules with no dated source record. There is no ranking "
                    "field: the order is the rule set's, not a preference."
                ),
                "items": {
                    "type": "object",
                    "required": [
                        "rule_id",
                        "pathway",
                        "route_class",
                        "display_group",
                        "jurisdiction_scope",
                        "required_documents",
                        "source_dependencies",
                        "citation",
                        "has_dated_source_record",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "rule_id": {"type": "string"},
                        "pathway": {"type": "string"},
                        "route_class": _string_enum(ROUTE_CLASSES, "Route class."),
                        "display_group": _string_enum(DISPLAY_GROUPS, "Group."),
                        "jurisdiction_scope": {"type": "string"},
                        "required_documents": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "source_dependencies": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "citation": {"type": "object"},
                        "has_dated_source_record": {"type": "boolean"},
                    },
                },
            },
            "candidate_routes": {
                "type": "array",
                "description": (
                    "Empty whenever 'decision_boundary' is 'needs_staff_review': "
                    "withheld, not absent. Unordered by preference."
                ),
                "items": _string_enum(ROUTE_CLASSES, "Route class."),
            },
            "source_state": {
                "type": "object",
                "required": [
                    "snapshot_id",
                    "receipt_id",
                    "receipt_status",
                    "checked_at",
                    "changed_source_ids",
                    "unverifiable_source_ids",
                    "affected_rule_ids",
                    "available",
                ],
                "additionalProperties": False,
                "properties": {
                    "snapshot_id": {"type": ["string", "null"]},
                    "receipt_id": {"type": ["string", "null"]},
                    "receipt_status": {"type": ["string", "null"]},
                    "checked_at": {"type": ["string", "null"]},
                    "changed_source_ids": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "unverifiable_source_ids": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "affected_rule_ids": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "available": {
                        "type": "boolean",
                        "description": (
                            "False when no snapshot was supplied. Every other "
                            "field is then null, so a consumer cannot read an "
                            "unchecked run as a clean one."
                        ),
                    },
                },
            },
            "rules_fingerprint": {
                "type": "string",
                "pattern": "^sha256:[0-9a-f]{64}$",
                "description": "Digest of the parsed rule set this result used.",
            },
            "notices": {"type": "array", "items": {"type": "string"}},
        },
    }


SCHEMAS: dict[str, Any] = {
    "facts.schema.json": facts_schema,
    "rule.schema.json": rule_schema,
    "result.schema.json": result_schema,
}


def render_schema(name: str) -> str:
    """The committed bytes for one schema: two-space JSON with a trailing newline."""
    if name not in SCHEMAS:
        raise KeyError(name)
    return json.dumps(SCHEMAS[name](), indent=2, sort_keys=False) + "\n"


__all__ = [
    "DECISION_BOUNDARIES",
    "FACT_PROVENANCE",
    "SCHEMAS",
    "SCHEMA_VERSION",
    "FactsDocumentError",
    "build_result",
    "facts_schema",
    "render_schema",
    "result_schema",
    "rule_schema",
    "rules_fingerprint",
    "source_state_summary",
    "unresolved_facts",
    "validate_facts_document",
]
