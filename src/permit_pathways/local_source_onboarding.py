"""Strict intake contract for a future jurisdiction-owned local source layer.

The committed artifact is an empty ``not_run`` template.  A copied intake can
progress only as far as ``prepared_for_review``: this module deliberately has
no reviewed, approved, encoded, or published state.  It validates candidate
official-source metadata, exact operative-passage fingerprints, project and
parcel scope, unresolved exceptions and conflicts, open questions, and the
owners/cadence planned for later human review.

Loading this record cannot create a screening rule or establish which local
law is operative.  The screening and publication paths do not import this
module.  A separate, fingerprint-bound review and publication receipt is
required before any collected material could support a local layer.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, cast
from urllib.parse import urlsplit

from .dates import resolve_today

SCHEMA_VERSION = 1
RECORD_TYPE = "local_source_onboarding_intake"
TEMPLATE_VERSION = "1.0.0"
TEMPLATE_ID = "local-source-onboarding-template-v1"
TEMPLATE_PUBLISHED_ON = "2026-08-09"
MAX_INTAKE_BYTES = 1_048_576

RecordStatus = Literal["not_run", "collection_in_progress", "prepared_for_review"]

RECORD_STATUSES = ("not_run", "collection_in_progress", "prepared_for_review")
SOURCE_REQUIREMENT_ROLES = (
    "operative_ordinance",
    "application_form",
    "submission_checklist",
    "fee_schedule",
    "process_page",
)
SOURCE_TYPES = (
    "ordinance",
    "application_form",
    "submission_checklist",
    "fee_schedule",
    "process_page",
    "parcel_dataset",
    "other_official",
)
ROLE_SOURCE_TYPES = {
    "operative_ordinance": "ordinance",
    "application_form": "application_form",
    "submission_checklist": "submission_checklist",
    "fee_schedule": "fee_schedule",
    "process_page": "process_page",
}
CLAIM_BOUNDARY_STATEMENT = (
    "This intake inventories unreviewed candidate local sources for future "
    "authoring. It does not establish which law is operative, create or "
    "publish a local rule, prove comprehensive local coverage, determine "
    "compliance or eligibility, or record human or jurisdiction review or "
    "approval."
)
CLAIM_BOUNDARY: Mapping[str, object] = MappingProxyType(
    {
        "local_layer_status": "not_encoded",
        "creates_or_publishes_local_rule": False,
        "establishes_operative_law": False,
        "establishes_comprehensive_local_coverage": False,
        "determines_compliance_or_eligibility": False,
        "records_human_review": False,
        "records_jurisdiction_approval": False,
        "statement": CLAIM_BOUNDARY_STATEMENT,
    }
)

_STABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_VERSION = re.compile(r"^[1-9][0-9]*\.[0-9]+\.[0-9]+$")
_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")
_INVALID_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")
_OWNER_ROLE_PLACEHOLDERS = {"none", "pending", "tbd", "unassigned", "unknown"}

_ROOT_KEYS = {
    "schema_version",
    "record_type",
    "template_version",
    "onboarding_id",
    "status",
    "template_published_on",
    "project_scope",
    "parcel_scope",
    "source_requirements",
    "sources",
    "operative_passages",
    "exception_review",
    "conflict_review",
    "open_questions",
    "review_plan",
    "claim_boundary",
}
_PROJECT_SCOPE_KEYS = {
    "jurisdiction_id",
    "jurisdiction_name",
    "permit_subtype_id",
    "permit_subtype_name",
    "included_project_types",
    "excluded_project_types",
}
_PARCEL_SCOPE_KEYS = {"description", "facts", "unknown_behavior"}
_PARCEL_FACT_KEYS = {
    "fact_id",
    "label",
    "collection_method",
    "source_id",
    "source_field",
    "unresolved_behavior",
}
_SOURCE_REQUIREMENT_KEYS = {"role", "status", "source_ids"}
_SOURCE_KEYS = {
    "source_id",
    "source_type",
    "title",
    "publisher",
    "official_url",
    "content_fingerprint",
    "checked_on",
    "enacted_on",
    "effective_on",
}
_PASSAGE_KEYS = {
    "passage_id",
    "source_id",
    "locator",
    "exact_text",
    "text_fingerprint",
    "enacted_on",
    "effective_on",
    "checked_on",
}
_REVIEW_COLLECTION_KEYS = {"status", "items"}
_EXCEPTION_KEYS = {
    "exception_id",
    "candidate_summary",
    "passage_ids",
    "question_id",
}
_CONFLICT_KEYS = {
    "conflict_id",
    "candidate_summary",
    "source_ids",
    "passage_ids",
    "resolution_status",
    "question_id",
}
_QUESTION_KEYS = {
    "question_id",
    "question",
    "blocking",
    "owner_role",
    "source_ids",
    "passage_ids",
}
_REVIEW_PLAN_KEYS = {
    "status",
    "source_owner_role",
    "content_review_owner_role",
    "jurisdiction_approval_owner_role",
    "publication_owner_role",
    "reverification_cadence_days",
    "reviewer",
    "method",
    "reviewed_on",
    "reviewed_artifact_fingerprint",
    "approver",
    "approved_on",
    "approved_artifact_fingerprint",
}


@dataclass(frozen=True)
class LocalSourceOnboarding:
    """Validated summary of one local-source onboarding intake."""

    onboarding_id: str
    template_version: str
    status: RecordStatus
    template_published_on: str
    source_requirement_count: int
    collected_source_requirement_count: int
    source_count: int
    operative_passage_count: int
    parcel_fact_count: int
    open_question_count: int
    review_status: Literal["not_run"]
    local_layer_status: Literal["not_encoded"]
    validated_as_of: str
    earliest_reverification_due_on: str | None
    artifact_fingerprint: str

    @property
    def ready_for_review(self) -> bool:
        """Whether collection is complete enough to begin, not pass, review."""

        return self.status == "prepared_for_review"


@dataclass(frozen=True)
class _Source:
    source_id: str
    source_type: str
    checked_on: str
    enacted_on: str | None
    effective_on: str | None


@dataclass(frozen=True)
class _Passage:
    passage_id: str
    source_id: str


@dataclass(frozen=True)
class _ReviewPlan:
    source_owner_role: str | None
    content_review_owner_role: str | None
    jurisdiction_approval_owner_role: str | None
    publication_owner_role: str | None
    reverification_cadence_days: int | None


def artifact_fingerprint(payload: dict[str, Any]) -> str:
    """Fingerprint the complete parsed intake using canonical JSON bytes."""

    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def passage_fingerprint(exact_text: str) -> str:
    """Fingerprint the exact retained passage text, including whitespace."""

    return "sha256:" + hashlib.sha256(exact_text.encode("utf-8")).hexdigest()


def _exact_object(value: Any, expected: set[str], field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    unknown = sorted(set(value) - expected)
    if unknown:
        raise ValueError(f"{field}: unknown fields: {', '.join(unknown)}")
    missing = sorted(expected - set(value))
    if missing:
        raise ValueError(f"{field}: missing fields: {', '.join(missing)}")
    return value


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected non-blank text")
    return value.strip()


def _required_exact_text(value: Any, field: str) -> str:
    """Validate nonblank evidence text without changing its retained bytes."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected non-blank text")
    return value


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field)


def _stable_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _STABLE_ID.fullmatch(value):
        raise ValueError(f"{field}: expected a stable ID")
    return value


def _optional_stable_id(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _stable_id(value, field)


def _optional_owner_role(value: Any, field: str) -> str | None:
    owner_role = _optional_stable_id(value, field)
    if owner_role in _OWNER_ROLE_PLACEHOLDERS:
        raise ValueError(f"{field}: placeholder owner roles are not allowed")
    return owner_role


def _fingerprint(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _FINGERPRINT.fullmatch(value):
        raise ValueError(f"{field}: expected sha256:<64 lowercase hex>")
    return value


def _iso_date(
    value: Any, field: str, *, optional: bool = False
) -> tuple[str, date] | None:
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field}: expected YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field}: expected YYYY-MM-DD") from error
    if parsed.isoformat() != value:
        raise ValueError(f"{field}: expected YYYY-MM-DD")
    return value, parsed


def _https_url(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(character.isspace() or ord(character) < 0x20 for character in value)
        or "\x7f" in value
        or "\\" in value
        or _INVALID_PERCENT_ESCAPE.search(value)
    ):
        raise ValueError(
            f"{field}: expected an HTTPS URL without credentials or fragment"
        )
    url = value
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except ValueError as error:
        raise ValueError(
            f"{field}: expected an HTTPS URL without credentials or fragment"
        ) from error
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.hostname != parsed.hostname.strip(".")
        or ".." in parsed.hostname
    ):
        raise ValueError(
            f"{field}: expected an HTTPS URL without credentials or fragment"
        )
    return url


def _enum(value: Any, allowed: tuple[str, ...], field: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{field}: unsupported value {value!r}")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field}: expected a list")
    return value


def _sorted_unique_ids(value: Any, field: str) -> tuple[str, ...]:
    values = _list(value, field)
    identifiers = tuple(
        _stable_id(item, f"{field}[{index}]") for index, item in enumerate(values)
    )
    if list(identifiers) != sorted(set(identifiers)):
        raise ValueError(f"{field}: IDs must be unique and sorted")
    return identifiers


def _sorted_unique_text(value: Any, field: str) -> tuple[str, ...]:
    values = _list(value, field)
    texts = tuple(
        _required_text(item, f"{field}[{index}]") for index, item in enumerate(values)
    )
    if list(texts) != sorted(set(texts)):
        raise ValueError(f"{field}: values must be unique and sorted")
    return texts


def _unique_records(
    value: Any,
    field: str,
    id_field: str,
) -> list[dict[str, Any]]:
    records = _list(value, field)
    output: list[dict[str, Any]] = []
    identifiers: list[str] = []
    for index, item in enumerate(records):
        if not isinstance(item, dict):
            raise ValueError(f"{field}[{index}]: expected an object")
        identifier = _stable_id(item.get(id_field), f"{field}[{index}].{id_field}")
        identifiers.append(identifier)
        output.append(item)
    if identifiers != sorted(set(identifiers)):
        raise ValueError(f"{field}: {id_field} values must be unique and sorted")
    return output


def _project_scope(value: Any) -> tuple[bool, bool]:
    scope = _exact_object(value, _PROJECT_SCOPE_KEYS, "project_scope")
    jurisdiction_id = _optional_stable_id(
        scope["jurisdiction_id"], "project_scope.jurisdiction_id"
    )
    jurisdiction_name = _optional_text(
        scope["jurisdiction_name"], "project_scope.jurisdiction_name"
    )
    permit_subtype_id = _optional_stable_id(
        scope["permit_subtype_id"], "project_scope.permit_subtype_id"
    )
    permit_subtype_name = _optional_text(
        scope["permit_subtype_name"], "project_scope.permit_subtype_name"
    )
    included = _sorted_unique_text(
        scope["included_project_types"], "project_scope.included_project_types"
    )
    excluded = _sorted_unique_text(
        scope["excluded_project_types"], "project_scope.excluded_project_types"
    )
    if set(included) & set(excluded):
        raise ValueError("project_scope: included and excluded project types overlap")
    values = (
        jurisdiction_id,
        jurisdiction_name,
        permit_subtype_id,
        permit_subtype_name,
    )
    complete = all(values) and bool(included)
    return bool(complete), any(values) or bool(included) or bool(excluded)


def _source(value: dict[str, Any], index: int, *, today: date) -> _Source:
    field = f"sources[{index}]"
    record = _exact_object(value, _SOURCE_KEYS, field)
    source_id = _stable_id(record["source_id"], f"{field}.source_id")
    source_type = _enum(record["source_type"], SOURCE_TYPES, f"{field}.source_type")
    _required_text(record["title"], f"{field}.title")
    _required_text(record["publisher"], f"{field}.publisher")
    _https_url(record["official_url"], f"{field}.official_url")
    _fingerprint(record["content_fingerprint"], f"{field}.content_fingerprint")

    checked = cast(
        tuple[str, date], _iso_date(record["checked_on"], f"{field}.checked_on")
    )
    if checked[1] > today:
        raise ValueError(f"{field}.checked_on: future dates are not allowed")
    enacted = _iso_date(record["enacted_on"], f"{field}.enacted_on", optional=True)
    effective = _iso_date(
        record["effective_on"], f"{field}.effective_on", optional=True
    )
    _validate_source_dates(source_type, enacted, effective, checked, field)
    return _Source(
        source_id=source_id,
        source_type=source_type,
        checked_on=checked[0],
        enacted_on=enacted[0] if enacted else None,
        effective_on=effective[0] if effective else None,
    )


def _validate_source_dates(
    source_type: str,
    enacted: tuple[str, date] | None,
    effective: tuple[str, date] | None,
    checked: tuple[str, date],
    field: str,
) -> None:
    if source_type == "ordinance" and (enacted is None or effective is None):
        raise ValueError(
            f"{field}: ordinance sources require enacted_on and effective_on"
        )
    if source_type != "ordinance" and enacted is not None:
        raise ValueError(f"{field}.enacted_on: allowed only for ordinance sources")
    if enacted is not None and effective is not None and enacted[1] > effective[1]:
        raise ValueError(f"{field}: enacted_on must not be after effective_on")
    if enacted is not None and enacted[1] > checked[1]:
        raise ValueError(f"{field}: enacted_on must not be after checked_on")
    if effective is not None and effective[1] > checked[1]:
        raise ValueError(f"{field}: effective_on must not be after checked_on")


def _sources(value: Any, *, today: date) -> dict[str, _Source]:
    records = _unique_records(value, "sources", "source_id")
    sources: dict[str, _Source] = {}
    for index, record in enumerate(records):
        source = _source(record, index, today=today)
        sources[source.source_id] = source
    return sources


def _source_requirements(
    value: Any,
    sources: dict[str, _Source],
) -> tuple[dict[str, tuple[str, tuple[str, ...]]], set[str]]:
    records = _list(value, "source_requirements")
    if len(records) != len(SOURCE_REQUIREMENT_ROLES):
        raise ValueError(
            "source_requirements: expected one record for every required role"
        )
    result: dict[str, tuple[str, tuple[str, ...]]] = {}
    referenced: set[str] = set()
    for index, expected_role in enumerate(SOURCE_REQUIREMENT_ROLES):
        field = f"source_requirements[{index}]"
        record = _exact_object(records[index], _SOURCE_REQUIREMENT_KEYS, field)
        role = _enum(record["role"], SOURCE_REQUIREMENT_ROLES, f"{field}.role")
        if role != expected_role:
            raise ValueError(f"{field}.role: expected {expected_role!r}")
        status = _enum(
            record["status"],
            ("not_collected", "collected_unreviewed"),
            f"{field}.status",
        )
        source_ids = _sorted_unique_ids(record["source_ids"], f"{field}.source_ids")
        if (status == "not_collected") != (not source_ids):
            raise ValueError(f"{field}: status and source_ids do not agree")
        _validate_role_sources(role, source_ids, sources, field)
        referenced.update(source_ids)
        result[role] = (status, source_ids)
    return result, referenced


def _validate_role_sources(
    role: str,
    source_ids: tuple[str, ...],
    sources: dict[str, _Source],
    field: str,
) -> None:
    expected_type = ROLE_SOURCE_TYPES[role]
    for source_id in source_ids:
        source = sources.get(source_id)
        if source is None:
            raise ValueError(f"{field}: references unknown source ID {source_id!r}")
        if source.source_type != expected_type:
            raise ValueError(
                f"{field}: source {source_id!r} must have type {expected_type!r}"
            )


def _passage(
    value: dict[str, Any],
    index: int,
    sources: dict[str, _Source],
) -> _Passage:
    field = f"operative_passages[{index}]"
    record = _exact_object(value, _PASSAGE_KEYS, field)
    passage_id = _stable_id(record["passage_id"], f"{field}.passage_id")
    source_id = _stable_id(record["source_id"], f"{field}.source_id")
    source = sources.get(source_id)
    if source is None:
        raise ValueError(
            f"{field}.source_id: references unknown source ID {source_id!r}"
        )
    if source.source_type != "ordinance":
        raise ValueError(
            f"{field}.source_id: operative passage requires ordinance source"
        )
    _required_text(record["locator"], f"{field}.locator")
    exact_text = _required_exact_text(record["exact_text"], f"{field}.exact_text")
    fingerprint = _fingerprint(record["text_fingerprint"], f"{field}.text_fingerprint")
    if fingerprint != passage_fingerprint(exact_text):
        raise ValueError(f"{field}.text_fingerprint: does not match exact_text")
    _passage_date(record["enacted_on"], source.enacted_on, f"{field}.enacted_on")
    _passage_date(record["effective_on"], source.effective_on, f"{field}.effective_on")
    _passage_date(record["checked_on"], source.checked_on, f"{field}.checked_on")
    return _Passage(passage_id, source_id)


def _passage_date(value: Any, expected: str | None, field: str) -> None:
    parsed = _iso_date(value, field)
    if expected is None or cast(tuple[str, date], parsed)[0] != expected:
        raise ValueError(f"{field}: must match the linked ordinance source")


def _passages(value: Any, sources: dict[str, _Source]) -> dict[str, _Passage]:
    records = _unique_records(value, "operative_passages", "passage_id")
    passages: dict[str, _Passage] = {}
    for index, record in enumerate(records):
        passage = _passage(record, index, sources)
        passages[passage.passage_id] = passage
    return passages


def _parcel_fact(
    record: dict[str, Any],
    index: int,
    sources: dict[str, _Source],
) -> str | None:
    field = f"parcel_scope.facts[{index}]"
    value = _exact_object(record, _PARCEL_FACT_KEYS, field)
    _stable_id(value["fact_id"], f"{field}.fact_id")
    _required_text(value["label"], f"{field}.label")
    method = _enum(
        value["collection_method"],
        ("official_dataset", "applicant_assertion", "staff_confirmation"),
        f"{field}.collection_method",
    )
    source_id = _optional_stable_id(value["source_id"], f"{field}.source_id")
    source_field = _optional_text(value["source_field"], f"{field}.source_field")
    if value["unresolved_behavior"] != "route_to_staff":
        raise ValueError(f"{field}.unresolved_behavior: must be 'route_to_staff'")
    if method == "official_dataset":
        if source_id is None or source_field is None:
            raise ValueError(
                f"{field}: official_dataset requires source_id and source_field"
            )
        source = sources.get(source_id)
        if source is None or source.source_type != "parcel_dataset":
            raise ValueError(f"{field}.source_id: requires a parcel_dataset source")
        return source_id
    if source_id is not None or source_field is not None:
        raise ValueError(f"{field}: non-dataset facts cannot claim source bindings")
    return None


def _parcel_scope(
    value: Any,
    sources: dict[str, _Source],
) -> tuple[str | None, int, set[str], bool]:
    scope = _exact_object(value, _PARCEL_SCOPE_KEYS, "parcel_scope")
    description = _optional_text(scope["description"], "parcel_scope.description")
    if scope["unknown_behavior"] != "route_to_staff":
        raise ValueError("parcel_scope.unknown_behavior: must be 'route_to_staff'")
    records = _unique_records(scope["facts"], "parcel_scope.facts", "fact_id")
    referenced: set[str] = set()
    for index, record in enumerate(records):
        source_id = _parcel_fact(record, index, sources)
        if source_id is not None:
            referenced.add(source_id)
    return (
        description,
        len(records),
        referenced,
        description is not None or bool(records),
    )


def _reference_ids(
    value: Any,
    field: str,
    known: set[str],
    kind: str,
    *,
    minimum: int = 0,
) -> tuple[str, ...]:
    identifiers = _sorted_unique_ids(value, field)
    if len(identifiers) < minimum:
        raise ValueError(f"{field}: expected at least {minimum} {kind} ID(s)")
    unknown = sorted(set(identifiers) - known)
    if unknown:
        raise ValueError(f"{field}: unknown {kind} IDs: {', '.join(unknown)}")
    return identifiers


def _open_questions(
    value: Any,
    sources: dict[str, _Source],
    passages: dict[str, _Passage],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    records = _unique_records(value, "open_questions", "question_id")
    questions: dict[str, dict[str, Any]] = {}
    referenced_sources: set[str] = set()
    for index, record in enumerate(records):
        field = f"open_questions[{index}]"
        item = _exact_object(record, _QUESTION_KEYS, field)
        question_id = _stable_id(item["question_id"], f"{field}.question_id")
        _required_text(item["question"], f"{field}.question")
        if not isinstance(item["blocking"], bool):
            raise ValueError(f"{field}.blocking: expected a boolean")
        _optional_owner_role(item["owner_role"], f"{field}.owner_role")
        source_ids = _reference_ids(
            item["source_ids"], f"{field}.source_ids", set(sources), "source"
        )
        _reference_ids(
            item["passage_ids"], f"{field}.passage_ids", set(passages), "passage"
        )
        referenced_sources.update(source_ids)
        questions[question_id] = item
    return questions, referenced_sources


def _exception_review(
    value: Any,
    passages: dict[str, _Passage],
    questions: dict[str, dict[str, Any]],
) -> tuple[str, set[str]]:
    review = _exact_object(value, _REVIEW_COLLECTION_KEYS, "exception_review")
    status = _enum(
        review["status"],
        ("not_run", "collection_complete_unreviewed"),
        "exception_review.status",
    )
    records = _unique_records(review["items"], "exception_review.items", "exception_id")
    referenced_passages: set[str] = set()
    for index, record in enumerate(records):
        field = f"exception_review.items[{index}]"
        item = _exact_object(record, _EXCEPTION_KEYS, field)
        _stable_id(item["exception_id"], f"{field}.exception_id")
        _required_text(item["candidate_summary"], f"{field}.candidate_summary")
        passage_ids = _reference_ids(
            item["passage_ids"],
            f"{field}.passage_ids",
            set(passages),
            "passage",
            minimum=1,
        )
        _question_reference(item["question_id"], questions, f"{field}.question_id")
        referenced_passages.update(passage_ids)
    if status == "not_run" and records:
        raise ValueError("exception_review: not_run cannot contain items")
    return status, referenced_passages


def _conflict_review(
    value: Any,
    sources: dict[str, _Source],
    passages: dict[str, _Passage],
    questions: dict[str, dict[str, Any]],
) -> tuple[str, set[str]]:
    review = _exact_object(value, _REVIEW_COLLECTION_KEYS, "conflict_review")
    status = _enum(
        review["status"],
        ("not_run", "collection_complete_unreviewed"),
        "conflict_review.status",
    )
    records = _unique_records(review["items"], "conflict_review.items", "conflict_id")
    referenced_sources: set[str] = set()
    for index, record in enumerate(records):
        field = f"conflict_review.items[{index}]"
        item = _exact_object(record, _CONFLICT_KEYS, field)
        _stable_id(item["conflict_id"], f"{field}.conflict_id")
        _required_text(item["candidate_summary"], f"{field}.candidate_summary")
        source_ids = _reference_ids(
            item["source_ids"], f"{field}.source_ids", set(sources), "source", minimum=2
        )
        _reference_ids(
            item["passage_ids"], f"{field}.passage_ids", set(passages), "passage"
        )
        if item["resolution_status"] != "unresolved":
            raise ValueError(f"{field}.resolution_status: must remain 'unresolved'")
        _question_reference(item["question_id"], questions, f"{field}.question_id")
        referenced_sources.update(source_ids)
    if status == "not_run" and records:
        raise ValueError("conflict_review: not_run cannot contain items")
    return status, referenced_sources


def _question_reference(
    value: Any,
    questions: dict[str, dict[str, Any]],
    field: str,
) -> None:
    question_id = _stable_id(value, field)
    if question_id not in questions:
        raise ValueError(f"{field}: references unknown open question {question_id!r}")


def _review_plan(value: Any) -> _ReviewPlan:
    field = "review_plan"
    plan = _exact_object(value, _REVIEW_PLAN_KEYS, field)
    if plan["status"] != "not_run":
        raise ValueError("review_plan.status: onboarding intake must remain 'not_run'")
    owners = (
        _optional_owner_role(plan["source_owner_role"], f"{field}.source_owner_role"),
        _optional_owner_role(
            plan["content_review_owner_role"],
            f"{field}.content_review_owner_role",
        ),
        _optional_owner_role(
            plan["jurisdiction_approval_owner_role"],
            f"{field}.jurisdiction_approval_owner_role",
        ),
        _optional_owner_role(
            plan["publication_owner_role"], f"{field}.publication_owner_role"
        ),
    )
    cadence = plan["reverification_cadence_days"]
    if cadence is not None and (
        isinstance(cadence, bool)
        or not isinstance(cadence, int)
        or not 1 <= cadence <= 366
    ):
        raise ValueError(
            f"{field}.reverification_cadence_days: expected an integer from 1 to 366"
        )
    evidence_fields = (
        "reviewer",
        "method",
        "reviewed_on",
        "reviewed_artifact_fingerprint",
        "approver",
        "approved_on",
        "approved_artifact_fingerprint",
    )
    if any(plan[name] is not None for name in evidence_fields):
        raise ValueError(
            "review_plan: onboarding intake cannot record completed review or approval evidence"
        )
    return _ReviewPlan(*owners, cadence)


def _claim_boundary(value: Any) -> None:
    boundary = _exact_object(value, set(CLAIM_BOUNDARY), "claim_boundary")
    exact = all(
        type(boundary[key]) is type(expected) and boundary[key] == expected
        for key, expected in CLAIM_BOUNDARY.items()
    )
    if not exact:
        raise ValueError(
            "claim_boundary: must preserve the not-encoded, unreviewed, "
            "non-approval boundary"
        )


def _validate_not_run(
    project_started: bool,
    parcel_description: str | None,
    parcel_fact_count: int,
    requirements: dict[str, tuple[str, tuple[str, ...]]],
    sources: dict[str, _Source],
    passages: dict[str, _Passage],
    exception_status: str,
    conflict_status: str,
    questions: dict[str, dict[str, Any]],
    review_plan: _ReviewPlan,
) -> None:
    owner_values = (
        review_plan.source_owner_role,
        review_plan.content_review_owner_role,
        review_plan.jurisdiction_approval_owner_role,
        review_plan.publication_owner_role,
        review_plan.reverification_cadence_days,
    )
    if project_started or parcel_description is not None or parcel_fact_count:
        raise ValueError("not_run template cannot contain project or parcel scope")
    if sources or passages or questions:
        raise ValueError("not_run template cannot contain collected source material")
    if any(status != "not_collected" for status, _ in requirements.values()):
        raise ValueError("not_run template cannot mark a source requirement collected")
    if exception_status != "not_run" or conflict_status != "not_run":
        raise ValueError(
            "not_run template cannot claim exception or conflict collection"
        )
    if any(value is not None for value in owner_values):
        raise ValueError(
            "not_run template review ownership and cadence must remain null"
        )


def _validate_progress(
    project_started: bool,
    parcel_started: bool,
    sources: dict[str, _Source],
    passages: dict[str, _Passage],
    questions: dict[str, dict[str, Any]],
    review_plan: _ReviewPlan,
) -> None:
    owner_started = any(
        value is not None
        for value in (
            review_plan.source_owner_role,
            review_plan.content_review_owner_role,
            review_plan.jurisdiction_approval_owner_role,
            review_plan.publication_owner_role,
            review_plan.reverification_cadence_days,
        )
    )
    if not any(
        (
            project_started,
            parcel_started,
            bool(sources),
            bool(passages),
            bool(questions),
            owner_started,
        )
    ):
        raise ValueError("collection_in_progress must contain collected intake work")


def _validate_prepared(
    onboarding_id: str,
    project_complete: bool,
    parcel_description: str | None,
    requirements: dict[str, tuple[str, tuple[str, ...]]],
    sources: dict[str, _Source],
    passages: dict[str, _Passage],
    exception_status: str,
    conflict_status: str,
    questions: dict[str, dict[str, Any]],
    review_plan: _ReviewPlan,
    referenced_sources: set[str],
) -> None:
    if onboarding_id == TEMPLATE_ID:
        raise ValueError("prepared intake must assign a distinct stable onboarding_id")
    if not project_complete:
        raise ValueError("prepared intake requires complete project_scope")
    if parcel_description is None:
        raise ValueError("prepared intake requires a parcel_scope description")
    if any(status != "collected_unreviewed" for status, _ in requirements.values()):
        raise ValueError(
            "prepared intake requires every source role collected_unreviewed"
        )
    if not passages:
        raise ValueError("prepared intake requires at least one operative passage")
    ordinance_ids = set(requirements["operative_ordinance"][1])
    passage_source_ids = {passage.source_id for passage in passages.values()}
    if ordinance_ids != passage_source_ids:
        raise ValueError(
            "prepared intake requires operative passages to use exactly the "
            "operative_ordinance source role"
        )
    if exception_status != "collection_complete_unreviewed":
        raise ValueError("prepared intake requires unreviewed exception collection")
    if conflict_status != "collection_complete_unreviewed":
        raise ValueError("prepared intake requires unreviewed conflict collection")
    _validate_prepared_ownership(questions, review_plan)
    if set(sources) != referenced_sources:
        raise ValueError("prepared intake cannot contain unreferenced source records")


def _validate_prepared_ownership(
    questions: dict[str, dict[str, Any]],
    review_plan: _ReviewPlan,
) -> None:
    if any(question["owner_role"] is None for question in questions.values()):
        raise ValueError(
            "prepared intake requires an owner_role for every open question"
        )
    owner_values = (
        review_plan.source_owner_role,
        review_plan.content_review_owner_role,
        review_plan.jurisdiction_approval_owner_role,
        review_plan.publication_owner_role,
        review_plan.reverification_cadence_days,
    )
    if not all(value is not None for value in owner_values):
        raise ValueError(
            "prepared intake requires accountable owner role IDs and cadence"
        )


def _validate_prepared_currency(
    sources: dict[str, _Source],
    review_plan: _ReviewPlan,
    today: date,
) -> str:
    cadence = cast(int, review_plan.reverification_cadence_days)
    stale_ids = sorted(
        source.source_id
        for source in sources.values()
        if (today - date.fromisoformat(source.checked_on)).days > cadence
    )
    if stale_ids:
        raise ValueError(
            "prepared intake has source checks outside the planned cadence: "
            + ", ".join(stale_ids)
        )
    return min(
        date.fromisoformat(source.checked_on) + timedelta(days=cadence)
        for source in sources.values()
    ).isoformat()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise ValueError(f"local-source onboarding data uses non-finite JSON value {value}")


def _load_payload(path: Path) -> dict[str, Any]:
    try:
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("local-source onboarding input must be a regular file")
        if metadata.st_size > MAX_INTAKE_BYTES:
            raise ValueError(
                "local-source onboarding data exceeds the 1048576-byte limit"
            )
        with path.open("rb") as stream:
            raw_bytes = stream.read(MAX_INTAKE_BYTES + 1)
    except ValueError:
        raise
    except OSError as error:
        raise ValueError(
            f"local-source onboarding data could not be read: {error}"
        ) from error
    if len(raw_bytes) > MAX_INTAKE_BYTES:
        raise ValueError("local-source onboarding data exceeds the 1048576-byte limit")
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("local-source onboarding data is not valid UTF-8") from error
    try:
        payload = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite_constant,
        )
    except (json.JSONDecodeError, RecursionError) as error:
        raise ValueError(
            f"local-source onboarding data is invalid JSON: {error}"
        ) from error
    if not isinstance(payload, dict):
        raise ValueError("local-source onboarding root: expected an object")
    return payload


def load_local_source_onboarding(
    path: Path,
    *,
    today: date | None = None,
) -> LocalSourceOnboarding:
    """Load and strictly validate a local-source onboarding intake.

    The maximum accepted lifecycle state is ``prepared_for_review``.  That
    state means only that the required candidate inputs and review plan are
    present; all review and approval evidence fields remain null.
    """

    as_of = resolve_today(today)
    payload = _load_payload(path)
    root = _exact_object(payload, _ROOT_KEYS, "root")
    if (
        type(root["schema_version"]) is not int
        or root["schema_version"] != SCHEMA_VERSION
    ):
        raise ValueError(f"schema_version: expected {SCHEMA_VERSION}")
    if root["record_type"] != RECORD_TYPE:
        raise ValueError(f"record_type: expected {RECORD_TYPE!r}")
    version = root["template_version"]
    if (
        not isinstance(version, str)
        or version != TEMPLATE_VERSION
        or not _VERSION.fullmatch(version)
    ):
        raise ValueError(f"template_version: expected {TEMPLATE_VERSION!r}")
    onboarding_id = _stable_id(root["onboarding_id"], "onboarding_id")
    status = _enum(root["status"], RECORD_STATUSES, "status")
    published = cast(
        tuple[str, date],
        _iso_date(root["template_published_on"], "template_published_on"),
    )
    if published[0] != TEMPLATE_PUBLISHED_ON:
        raise ValueError(f"template_published_on: expected {TEMPLATE_PUBLISHED_ON!r}")
    if published[1] > as_of:
        raise ValueError("template_published_on: future dates are not allowed")

    project_complete, project_started = _project_scope(root["project_scope"])
    sources = _sources(root["sources"], today=as_of)
    requirements, role_sources = _source_requirements(
        root["source_requirements"], sources
    )
    passages = _passages(root["operative_passages"], sources)
    parcel_description, parcel_fact_count, parcel_sources, parcel_started = (
        _parcel_scope(root["parcel_scope"], sources)
    )
    questions, question_sources = _open_questions(
        root["open_questions"], sources, passages
    )
    exception_status, _ = _exception_review(
        root["exception_review"], passages, questions
    )
    conflict_status, conflict_sources = _conflict_review(
        root["conflict_review"], sources, passages, questions
    )
    review_plan = _review_plan(root["review_plan"])
    _claim_boundary(root["claim_boundary"])

    earliest_reverification_due_on = None
    if status == "not_run":
        _validate_not_run(
            project_started,
            parcel_description,
            parcel_fact_count,
            requirements,
            sources,
            passages,
            exception_status,
            conflict_status,
            questions,
            review_plan,
        )
    elif status == "collection_in_progress":
        if onboarding_id == TEMPLATE_ID:
            raise ValueError(
                "active intake must assign a distinct stable onboarding_id"
            )
        _validate_progress(
            project_started,
            parcel_started,
            sources,
            passages,
            questions,
            review_plan,
        )
    else:
        referenced_sources = (
            role_sources | parcel_sources | question_sources | conflict_sources
        )
        referenced_sources.update(passage.source_id for passage in passages.values())
        _validate_prepared(
            onboarding_id,
            project_complete,
            parcel_description,
            requirements,
            sources,
            passages,
            exception_status,
            conflict_status,
            questions,
            review_plan,
            referenced_sources,
        )
        earliest_reverification_due_on = _validate_prepared_currency(
            sources, review_plan, as_of
        )

    collected = sum(
        status_value == "collected_unreviewed"
        for status_value, _ in requirements.values()
    )
    return LocalSourceOnboarding(
        onboarding_id=onboarding_id,
        template_version=version,
        status=cast(RecordStatus, status),
        template_published_on=published[0],
        source_requirement_count=len(SOURCE_REQUIREMENT_ROLES),
        collected_source_requirement_count=collected,
        source_count=len(sources),
        operative_passage_count=len(passages),
        parcel_fact_count=parcel_fact_count,
        open_question_count=len(questions),
        review_status="not_run",
        local_layer_status="not_encoded",
        validated_as_of=as_of.isoformat(),
        earliest_reverification_due_on=earliest_reverification_due_on,
        artifact_fingerprint=artifact_fingerprint(payload),
    )
