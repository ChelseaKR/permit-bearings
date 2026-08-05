"""Explicit verification-level ledger bound to published rule citations.

``Citation.verified_on`` (see :mod:`permit_pathways.screening`) records that
dated source evidence exists for a rule. It does not say who reviewed the
interpretation or whether a jurisdiction accepted it. AGENTS.md's evidence
rules ask for explicit levels on top of that baseline:

- ``machine_linked`` — the implicit floor for every rule: a machine confirmed
  a dated source citation is linked. No named person has reviewed the
  interpretation. A rule with no ledger entry is ``machine_linked`` by
  default.
- ``human_reviewed`` — a named reviewer compared the rule's criteria and
  citation against the source and recorded how and when.
- ``jurisdiction_approved`` — a jurisdiction accepted the interpretation.

This module never changes which rules match an intake: :mod:`screening`
does not import it, and nothing here filters or reorders screening results.
A promoted level binds to the exact citation fingerprint it was checked
against (:func:`permit_pathways.explanations.citation_fingerprint`); editing
a rule's citation without re-reviewing it is a data-integrity error caught
at strict load time, the same way explanation copy is bound to its rule.
Even an unchanged, correctly bound review ages out: :func:`effective_status`
fails a stale ``human_reviewed`` or ``jurisdiction_approved`` claim closed
back to ``machine_linked`` once its review window elapses, exactly as
``Citation.is_stale`` does for the underlying source date.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

from .dates import resolve_today
from .explanations import citation_fingerprint
from .harness.runner import DEFAULT_MAX_AGE_DAYS
from .screening import Rule

SCHEMA_VERSION = 1
VERIFICATION_LEVELS = ("machine_linked", "human_reviewed", "jurisdiction_approved")
_REVIEWED_LEVELS = ("human_reviewed", "jurisdiction_approved")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")
_ENTRY_KEYS = {
    "rule_id",
    "level",
    "reviewer",
    "method",
    "reviewed_on",
    "reviewed_citation_fingerprint",
}


@dataclass(frozen=True)
class RuleVerification:
    """One ledger entry as recorded, before any staleness check."""

    rule_id: str
    level: str
    reviewer: str | None
    method: str | None
    reviewed_on: str | None
    reviewed_citation_fingerprint: str | None


@dataclass(frozen=True)
class EffectiveVerification:
    """The level actually in force for a rule as of a given date.

    ``recorded_level`` preserves the ledger's own claim for audit even when
    ``level`` has failed closed to ``machine_linked`` because the review
    window elapsed.
    """

    level: str
    recorded_level: str
    stale: bool
    reason: str | None


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected non-blank text")
    return value.strip()


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field)


def _iso_date(
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
        raise ValueError(f"{field}: invalid ISO date {value!r}") from error
    if parsed > today:
        raise ValueError(f"{field}: future dates are not allowed")
    return value


def _rule_index(rules: list[Rule]) -> dict[str, Rule]:
    index: dict[str, Rule] = {}
    for rule in rules:
        if rule.rule_id in index:
            raise ValueError("canonical rule set contains duplicate rule IDs")
        index[rule.rule_id] = rule
    return index


def _reviewed_metadata(
    record: dict[str, Any],
    field: str,
    today: date,
) -> tuple[str | None, str | None, str | None, str | None]:
    reviewer = _optional_text(record.get("reviewer"), f"{field}.reviewer")
    method = _optional_text(record.get("method"), f"{field}.method")
    reviewed_on = _iso_date(
        record.get("reviewed_on"), f"{field}.reviewed_on", today=today, optional=True
    )
    fingerprint = _optional_text(
        record.get("reviewed_citation_fingerprint"),
        f"{field}.reviewed_citation_fingerprint",
    )
    return reviewer, method, reviewed_on, fingerprint


def _validate_reviewed_level(
    metadata: tuple[str | None, str | None, str | None, str | None],
    field: str,
    level: str,
    rule: Rule,
) -> None:
    reviewer, method, reviewed_on, fingerprint = metadata
    if not all((reviewer, method, reviewed_on, fingerprint)):
        raise ValueError(
            f"{field}: {level} requires reviewer, method, reviewed_on, and "
            "reviewed_citation_fingerprint"
        )
    if not rule.citation.is_verified:
        raise ValueError(
            f"{field}: {level} requires the rule to carry a dated source citation"
        )
    reviewed_on_value = cast(str, reviewed_on)
    source_verified_on = cast(str, rule.citation.verified_on)
    if reviewed_on_value < source_verified_on:
        raise ValueError(
            f"{field}: reviewed_on {reviewed_on_value!r} predates the rule's "
            f"source date {source_verified_on!r}"
        )
    fingerprint_value = cast(str, fingerprint)
    if not _FINGERPRINT.fullmatch(fingerprint_value):
        raise ValueError(f"{field}.reviewed_citation_fingerprint: invalid SHA-256")
    expected = citation_fingerprint(rule)
    if fingerprint_value != expected:
        raise ValueError(
            f"{field}: reviewed_citation_fingerprint does not match the "
            "rule's current citation"
        )


def _entry(
    record: Any,
    index: int,
    rules_by_id: dict[str, Rule],
    today: date,
) -> RuleVerification:
    field = f"entries[{index}]"
    if not isinstance(record, dict):
        raise ValueError(f"{field}: expected an object")
    unknown = sorted(set(record) - _ENTRY_KEYS)
    if unknown:
        raise ValueError(f"{field}: unknown fields: {', '.join(unknown)}")
    missing = sorted(_ENTRY_KEYS - set(record))
    if missing:
        raise ValueError(f"{field}: missing fields: {', '.join(missing)}")

    rule_id = _required_text(record["rule_id"], f"{field}.rule_id")
    rule = rules_by_id.get(rule_id)
    if rule is None:
        raise ValueError(f"{field}: references unknown rule ID {rule_id!r}")

    level = _required_text(record["level"], f"{field}.level")
    if level not in VERIFICATION_LEVELS:
        raise ValueError(f"{field}.level: unknown value {level!r}")

    metadata = _reviewed_metadata(record, field, today)
    if level == "machine_linked":
        if any(metadata):
            raise ValueError(f"{field}: machine_linked cannot claim reviewer metadata")
    else:
        _validate_reviewed_level(metadata, field, level, rule)

    reviewer, method, reviewed_on, fingerprint = metadata
    return RuleVerification(rule_id, level, reviewer, method, reviewed_on, fingerprint)


def _records(path: Path, strict: bool) -> list[Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        if strict:
            raise ValueError(
                f"rule-verification data could not be loaded: {error}"
            ) from error
        return None
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        got = payload.get("schema_version") if isinstance(payload, dict) else None
        schema_error = ValueError(
            f"rule-verification schema_version must be {SCHEMA_VERSION}; got {got!r}"
        )
        if strict:
            raise schema_error
        return None
    entries = payload.get("entries")
    if not isinstance(entries, list):
        if strict:
            raise ValueError("rule-verification entries: expected a list")
        return None
    return entries


def load_rule_verifications(
    path: Path,
    rules: list[Rule],
    *,
    require_complete: bool = True,
    strict: bool = True,
    today: date | None = None,
) -> dict[str, RuleVerification]:
    """Load and validate the verification-level ledger against canonical rules.

    A ledger entry never changes screening. Strict mode (used by tests and
    the build) catches duplicate, orphaned, unauthorized-metadata,
    citation-drifted, and pre-dated entries. Display or staff tooling may
    use ``strict=False`` to drop invalid entries individually; a rule with
    no valid entry is simply absent from the returned mapping and callers
    should treat that as the ``machine_linked`` floor, exactly as
    :func:`effective_status` does.
    """

    as_of = resolve_today(today)
    records = _records(path, strict)
    if records is None:
        return {}
    rules_by_id = _rule_index(rules)

    ledger: dict[str, RuleVerification] = {}
    seen: set[str] = set()
    for index, record in enumerate(records):
        try:
            entry = _entry(record, index, rules_by_id, as_of)
        except ValueError:
            if strict:
                raise
            continue
        if entry.rule_id in seen:
            if strict:
                raise ValueError(f"{entry.rule_id}: duplicate rule-verification entry")
            ledger.pop(entry.rule_id, None)
            continue
        seen.add(entry.rule_id)
        ledger[entry.rule_id] = entry

    if require_complete and strict:
        missing = sorted(set(rules_by_id) - set(ledger))
        if missing:
            raise ValueError(
                "rule-verification ledger missing rule IDs: " + ", ".join(missing)
            )
    return ledger


def effective_status(
    rule: Rule,
    ledger: dict[str, RuleVerification],
    *,
    today: date | None = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> EffectiveVerification:
    """Return the verification level actually in force for ``rule`` today.

    A rule absent from the ledger is ``machine_linked`` by default. A
    recorded ``human_reviewed`` or ``jurisdiction_approved`` level fails
    closed back to ``machine_linked`` once ``reviewed_on`` ages past
    ``max_age_days`` — the ledger keeps the original claim for audit, but
    display and staff tooling must call this function rather than read
    ``RuleVerification.level`` directly.
    """

    if max_age_days < 0:
        raise ValueError("max_age_days must be non-negative")
    as_of = resolve_today(today)
    entry = ledger.get(rule.rule_id)
    if entry is None or entry.level == "machine_linked":
        recorded = entry.level if entry is not None else "machine_linked"
        return EffectiveVerification("machine_linked", recorded, False, None)

    reviewed_on = cast(str, entry.reviewed_on)
    reviewed = date.fromisoformat(reviewed_on)
    age_days = (as_of - reviewed).days
    if age_days < 0:
        raise ValueError(f"{rule.rule_id}: reviewed_on is in the future")
    if age_days > max_age_days:
        return EffectiveVerification(
            "machine_linked",
            entry.level,
            True,
            f"{entry.level} review window elapsed; re-verify",
        )
    return EffectiveVerification(entry.level, entry.level, False, None)
