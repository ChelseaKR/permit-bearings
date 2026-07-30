"""Deterministic pathway screening.

Rules are data, not code: each rule is a JSON record carrying its own
citation and verification status. The engine never emits a result whose
rule lacks a citation — an uncited rule is a schema error, not a softer
answer.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .dates import resolve_today

ROUTE_CLASSES = ("ministerial", "discretionary", "mixed")
DISPLAY_GROUPS = ("route", "standard", "local_process")
SUPPORTED_OPERATORS = ("eq", "in", "lte", "gte")
JS_MAX_SAFE_INTEGER = (2**53) - 1

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_FIELD_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_SHA256 = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
_RULE_KEYS = {
    "rule_id",
    "pathway",
    "route_class",
    "jurisdiction_scope",
    "criteria",
    "citation",
    "source_dependencies",
    "display_group",
    "required_documents",
    "notes",
}
_CITATION_KEYS = {
    "source",
    "url",
    "excerpt",
    "excerpt_sha256",
    "verified_on",
}
_CRITERION_KEYS = {"field", "op", "value"}


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, bool)) or _is_safe_integer(value)


def _is_safe_integer(value: Any) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and -JS_MAX_SAFE_INTEGER <= value <= JS_MAX_SAFE_INTEGER
    )


def _reject_noncanonical_number(value: Any, field: str) -> None:
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and not _is_safe_integer(value)
    ):
        raise ValueError(
            f"{field}: numeric criteria must be integers within the "
            "JavaScript safe-integer range"
        )


def _same_scalar(left: Any, right: Any) -> bool:
    """JSON-scalar equality without Python's ``True == 1`` coercion."""

    if _is_number(left) and _is_number(right):
        return bool(left == right)
    return type(left) is type(right) and left == right


def _criterion_matches(actual: Any, operator: str, expected: Any) -> bool:
    # Missing and explicit null intake values never satisfy a concrete
    # criterion. A rule may accept the literal string "unknown" explicitly.
    if actual is None:
        return False
    if operator == "eq":
        return _same_scalar(actual, expected)
    if operator == "in":
        return any(_same_scalar(actual, candidate) for candidate in expected)
    if operator == "lte":
        return _is_number(actual) and actual <= expected
    if operator == "gte":
        return _is_number(actual) and actual >= expected
    # Loading rejects unsupported operators, but fail closed if a Rule is
    # constructed directly in application code.
    return False


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected non-blank text")
    return value.strip()


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field)


def _exact_keys(record: dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(record) - allowed)
    if unknown:
        raise ValueError(f"{field}: unknown fields: {', '.join(unknown)}")


def _parse_iso_date(
    value: Any,
    field: str,
    *,
    today: date,
    optional: bool = False,
) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise ValueError(f"{field}: expected YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field}: invalid date {value!r}") from error
    if parsed > today:
        raise ValueError(f"{field}: future dates are not allowed")
    return value


def _validate_criterion(
    record: Any,
    *,
    rule_id: str,
    index: int,
) -> dict[str, Any]:
    field = f"{rule_id}.criteria[{index}]"
    if not isinstance(record, dict):
        raise ValueError(f"{field}: expected an object")
    _exact_keys(record, _CRITERION_KEYS, field)
    missing = sorted(_CRITERION_KEYS - set(record))
    if missing:
        raise ValueError(f"{field}: missing fields: {', '.join(missing)}")

    intake_field = _required_text(record["field"], f"{field}.field")
    if not _FIELD_NAME.fullmatch(intake_field):
        raise ValueError(f"{field}.field: expected a stable snake_case name")
    operator = _required_text(record["op"], f"{field}.op")
    if operator not in SUPPORTED_OPERATORS:
        raise ValueError(f"{field}.op: unsupported operator {operator!r}")
    value = record["value"]
    if operator == "eq":
        _reject_noncanonical_number(value, f"{field}.value")
        if not _is_scalar(value):
            raise ValueError(f"{field}.value: eq requires a JSON scalar")
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"{field}.value: expected non-blank text")
    elif operator == "in":
        if not isinstance(value, list) or not value:
            raise ValueError(f"{field}.value: in requires a non-empty list")
        for item in value:
            _reject_noncanonical_number(item, f"{field}.value")
        if any(not _is_scalar(item) for item in value):
            raise ValueError(f"{field}.value: in values must be JSON scalars")
        if any(isinstance(item, str) and not item.strip() for item in value):
            raise ValueError(f"{field}.value: in values cannot be blank")
        first = value[0]
        if any(
            not ((_is_number(first) and _is_number(item)) or type(first) is type(item))
            for item in value[1:]
        ):
            raise ValueError(f"{field}.value: in values must have one type")
        if any(
            _same_scalar(item, prior)
            for position, item in enumerate(value)
            for prior in value[:position]
        ):
            raise ValueError(f"{field}.value: in values must be unique")
    elif not _is_safe_integer(value):
        raise ValueError(
            f"{field}.value: {operator} requires an integer within the "
            "JavaScript safe-integer range"
        )
    return {"field": intake_field, "op": operator, "value": value}


@dataclass(frozen=True)
class Citation:
    """The source a rule encodes. `verified_on` records the date attached to
    its source evidence; it does not identify a reviewer or jurisdiction
    approval. The harness reports records without a date separately."""

    source: str  # e.g. "Gov. Code § 66321(b)(3)" or an HCD document title
    url: str
    excerpt: str | None = None  # supporting source text recorded for the rule
    excerpt_sha256: str | None = None
    verified_on: str | None = None  # ISO date of last verification against source

    @property
    def is_verified(self) -> bool:
        return self.verified_on is not None

    def is_stale(self, max_age_days: int, today: date) -> bool:
        if max_age_days < 0:
            raise ValueError("max_age_days must be non-negative")
        if self.verified_on is None:
            return True
        verified = date.fromisoformat(self.verified_on)
        age_days = (today - verified).days
        # Future dates are rejected by ``load_rules``. Treat directly
        # constructed future citations as stale rather than current.
        return age_days < 0 or age_days > max_age_days


@dataclass(frozen=True)
class Rule:
    rule_id: str
    pathway: str  # e.g. "ADU ministerial approval"
    route_class: str  # ministerial | discretionary | mixed
    jurisdiction_scope: str  # "statewide" or a jurisdiction slug
    criteria: list[dict[str, Any]]  # [{"field", "op", "value"}, ...]
    citation: Citation
    source_dependencies: list[str]
    display_group: str
    required_documents: list[str] = field(default_factory=list)
    notes: str = ""

    def matches(self, intake: dict[str, Any]) -> bool:
        for c in self.criteria:
            if not _criterion_matches(
                intake.get(c["field"]),
                c.get("op", ""),
                c.get("value"),
            ):
                return False
        return True


@dataclass(frozen=True)
class PathwayResult:
    rule: Rule
    verified: bool

    def summary(self) -> str:
        badge = "dated source record" if self.verified else "NO DATED SOURCE RECORD"
        return (
            f"{self.rule.pathway} ({self.rule.route_class}) — "
            f"{self.rule.citation.source} [{badge}]"
        )


def load_rules(path: Path, *, today: date | None = None) -> list[Rule]:
    """Load rules from a JSON file, or from every *.json file in a
    directory (sorted by filename: statewide plus per-jurisdiction files)."""
    as_of = resolve_today(today)
    files = (
        sorted(p for p in path.glob("*.json") if p.name != "index.json")
        if path.is_dir()
        else [path]
    )
    if not files:
        raise ValueError(f"{path}: no rule files found")

    rules: list[Rule] = []
    seen: set[str] = set()
    for file_path in files:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"{file_path}: rule data could not be loaded") from error
        if not isinstance(payload, list):
            raise ValueError(f"{file_path}: expected a list of rules")
        for index, record in enumerate(payload):
            record_field = f"{file_path.name}[{index}]"
            if not isinstance(record, dict):
                raise ValueError(f"{record_field}: expected an object")
            _exact_keys(record, _RULE_KEYS, record_field)
            missing = sorted(_RULE_KEYS - set(record))
            if missing:
                raise ValueError(
                    f"{record_field}: missing fields: {', '.join(missing)}"
                )

            rule_id = _required_text(record["rule_id"], f"{record_field}.rule_id")
            if not _IDENTIFIER.fullmatch(rule_id):
                raise ValueError(f"{record_field}.rule_id: invalid stable ID")
            if rule_id in seen:
                raise ValueError(f"{rule_id}: duplicate rule ID")
            seen.add(rule_id)

            pathway = _required_text(record["pathway"], f"{rule_id}.pathway")
            route_class = _required_text(
                record["route_class"], f"{rule_id}.route_class"
            )
            if route_class not in ROUTE_CLASSES:
                raise ValueError(f"{rule_id}: unknown route_class {route_class!r}")
            jurisdiction_scope = _required_text(
                record["jurisdiction_scope"],
                f"{rule_id}.jurisdiction_scope",
            )
            if not _IDENTIFIER.fullmatch(jurisdiction_scope):
                raise ValueError(f"{rule_id}.jurisdiction_scope: invalid stable ID")
            display_group = _required_text(
                record["display_group"], f"{rule_id}.display_group"
            )
            if display_group not in DISPLAY_GROUPS:
                raise ValueError(
                    f"{rule_id}.display_group: unknown value {display_group!r}"
                )

            dependencies = record["source_dependencies"]
            if not isinstance(dependencies, list) or not dependencies:
                raise ValueError(
                    f"{rule_id}.source_dependencies: expected a non-empty list"
                )
            source_dependencies = [
                _required_text(source_id, f"{rule_id}.source_dependencies[{position}]")
                for position, source_id in enumerate(dependencies)
            ]
            if any(
                not _IDENTIFIER.fullmatch(source_id)
                for source_id in source_dependencies
            ):
                raise ValueError(
                    f"{rule_id}.source_dependencies: invalid stable source ID"
                )
            if len(source_dependencies) != len(set(source_dependencies)):
                raise ValueError(f"{rule_id}.source_dependencies: duplicate source ID")

            criteria_payload = record["criteria"]
            if not isinstance(criteria_payload, list) or not criteria_payload:
                raise ValueError(f"{rule_id}.criteria: expected a non-empty list")
            criteria = [
                _validate_criterion(item, rule_id=rule_id, index=position)
                for position, item in enumerate(criteria_payload)
            ]

            citation_payload = record["citation"]
            if not isinstance(citation_payload, dict):
                raise ValueError(f"{rule_id}.citation: expected an object")
            _exact_keys(citation_payload, _CITATION_KEYS, f"{rule_id}.citation")
            citation_missing = {"source", "url", "excerpt", "verified_on"} - set(
                citation_payload
            )
            if citation_missing:
                raise ValueError(
                    f"{rule_id}.citation: missing fields: "
                    + ", ".join(sorted(citation_missing))
                )
            source = _required_text(
                citation_payload["source"], f"{rule_id}.citation.source"
            )
            url = _required_text(citation_payload["url"], f"{rule_id}.citation.url")
            parsed_url = urlsplit(url)
            if (
                parsed_url.scheme != "https"
                or not parsed_url.hostname
                or parsed_url.username is not None
                or parsed_url.password is not None
            ):
                raise ValueError(f"{rule_id}.citation.url: expected HTTPS URL")
            excerpt = _optional_text(
                citation_payload.get("excerpt"), f"{rule_id}.citation.excerpt"
            )
            excerpt_sha256 = _optional_text(
                citation_payload.get("excerpt_sha256"),
                f"{rule_id}.citation.excerpt_sha256",
            )
            if excerpt_sha256 and not _SHA256.fullmatch(excerpt_sha256):
                raise ValueError(
                    f"{rule_id}.citation.excerpt_sha256: invalid SHA-256 digest"
                )
            verified_on = _parse_iso_date(
                citation_payload["verified_on"],
                f"{rule_id}.citation.verified_on",
                today=as_of,
                optional=True,
            )
            if verified_on is not None and excerpt is None:
                raise ValueError(
                    f"{rule_id}.citation: dated evidence requires an excerpt"
                )
            citation = Citation(
                source=source,
                url=url,
                excerpt=excerpt,
                excerpt_sha256=excerpt_sha256,
                verified_on=verified_on,
            )

            documents_payload = record["required_documents"]
            if not isinstance(documents_payload, list):
                raise ValueError(f"{rule_id}.required_documents: expected a list")
            required_documents = [
                _required_text(document, f"{rule_id}.required_documents[{position}]")
                for position, document in enumerate(documents_payload)
            ]
            if len(required_documents) != len(set(required_documents)):
                raise ValueError(f"{rule_id}.required_documents: duplicate item")
            notes = _required_text(record["notes"], f"{rule_id}.notes")

            rules.append(
                Rule(
                    rule_id=rule_id,
                    pathway=pathway,
                    route_class=route_class,
                    jurisdiction_scope=jurisdiction_scope,
                    criteria=criteria,
                    citation=citation,
                    source_dependencies=source_dependencies,
                    display_group=display_group,
                    required_documents=required_documents,
                    notes=notes,
                )
            )
    return rules


def screen(intake: dict[str, Any], rules: list[Rule]) -> list[PathwayResult]:
    """Return candidate pathways for a structured intake. Results from
    rules without dated source evidence are still returned — flagged, never
    hidden — because hiding them would misrepresent coverage."""
    jurisdiction = intake.get("jurisdiction")
    applicable = [
        r for r in rules if r.jurisdiction_scope in ("statewide", jurisdiction)
    ]
    return [
        PathwayResult(rule=r, verified=r.citation.is_verified)
        for r in applicable
        if r.matches(intake)
    ]
