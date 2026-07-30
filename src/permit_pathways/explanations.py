"""Versioned plain-language explanations for deterministic screening results.

The explanation layer is deliberately separate from the rule engine. Rules
decide which records match; this module only validates and loads display copy
linked to those records by stable ``rule_id``. A missing or invalid
explanation must never change a screening result.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

from .dates import resolve_today
from .screening import DISPLAY_GROUPS, Rule

SCHEMA_VERSION = 1
REVIEW_STATUSES = (
    "prototype_review_pending",
    "human_reviewed",
    "jurisdiction_approved",
)
TRANSLATION_STATUSES = (
    "machine_draft",
    "human_reviewed",
    "jurisdiction_approved",
)
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class Review:
    status: str
    reviewer: str | None
    reviewed_on: str | None
    method: str | None
    reviewed_version: str | None
    content_fingerprint: str | None


@dataclass(frozen=True)
class Highlight:
    label: str
    text: str


@dataclass(frozen=True)
class HighlightGroup:
    title: str
    items: tuple[Highlight, ...]


@dataclass(frozen=True)
class LocalizedExplanation:
    title: str
    summary: str
    next_steps: tuple[str, ...]
    confirm_with_staff: tuple[str, ...]
    highlights: HighlightGroup | None = None
    translation_status: str | None = None
    reviewer: str | None = None
    reviewed_on: str | None = None
    method: str | None = None
    reviewed_version: str | None = None
    content_fingerprint: str | None = None


@dataclass(frozen=True)
class PlainLanguageExplanation:
    version: str
    source_rule_id: str
    source_verified_on: str | None
    citation_fingerprint: str
    rule_fingerprint: str
    display_group: str
    drafted_by: str
    updated_on: str
    review: Review
    en: LocalizedExplanation
    es: LocalizedExplanation | None

    def localized(self, language: str) -> LocalizedExplanation:
        """Return requested display copy, falling back to English."""

        return self.es if language == "es" and self.es is not None else self.en

    def localized_language(self, language: str) -> str:
        """Return the language actually used by :meth:`localized`."""

        return "es" if language == "es" and self.es is not None else "en"


def citation_fingerprint(rule: Rule) -> str:
    """Hash the normalized citation fields an explanation was checked against."""

    citation = rule.citation
    payload = json.dumps(
        {
            "excerpt": citation.excerpt,
            "excerpt_sha256": citation.excerpt_sha256,
            "source": citation.source,
            "url": citation.url,
            "verified_on": citation.verified_on,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def rule_fingerprint(rule: Rule) -> str:
    """Hash every rule field that can affect explanation meaning."""

    payload = json.dumps(
        {
            "citation": {
                "excerpt": rule.citation.excerpt,
                "excerpt_sha256": rule.citation.excerpt_sha256,
                "source": rule.citation.source,
                "url": rule.citation.url,
                "verified_on": rule.citation.verified_on,
            },
            "criteria": rule.criteria,
            "jurisdiction_scope": rule.jurisdiction_scope,
            "notes": rule.notes,
            "pathway": rule.pathway,
            "required_documents": rule.required_documents,
            "route_class": rule.route_class,
            "rule_id": rule.rule_id,
            "source_dependencies": rule.source_dependencies,
            "display_group": rule.display_group,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def localized_content_fingerprint(
    version: str,
    language: str,
    localized: LocalizedExplanation,
) -> str:
    """Bind a review claim to the exact localized copy that was reviewed."""

    highlights = None
    if localized.highlights is not None:
        highlights = {
            "title": localized.highlights.title,
            "items": [
                {"label": item.label, "text": item.text}
                for item in localized.highlights.items
            ],
        }
    payload = json.dumps(
        {
            "confirm_with_staff": list(localized.confirm_with_staff),
            "highlights": highlights,
            "language": language,
            "next_steps": list(localized.next_steps),
            "summary": localized.summary,
            "title": localized.title,
            "version": version,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


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


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected non-blank text or null")
    return value.strip()


def _required_text(value: Any, field: str) -> str:
    text = _optional_text(value, field)
    if text is None:
        raise ValueError(f"{field}: expected non-blank text")
    return text


def _text_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field}: expected a non-empty list")
    return tuple(
        _required_text(item, f"{field}[{index}]") for index, item in enumerate(value)
    )


def _highlights(value: Any, field: str) -> HighlightGroup | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object or null")
    title = _required_text(value.get("title"), f"{field}.title")
    items = value.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError(f"{field}.items: expected a non-empty list")
    parsed: list[Highlight] = []
    for index, item in enumerate(items):
        item_field = f"{field}.items[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{item_field}: expected an object")
        parsed.append(
            Highlight(
                label=_required_text(item.get("label"), f"{item_field}.label"),
                text=_required_text(item.get("text"), f"{item_field}.text"),
            )
        )
    return HighlightGroup(title=title, items=tuple(parsed))


def _review(  # noqa: C901 — WVR-007
    record: Any,
    rule_id: str,
    version: str,
    updated_on: str,
    expected_content_fingerprint: str,
    today: date,
) -> Review:
    field = f"{rule_id}.review"
    if not isinstance(record, dict):
        raise ValueError(f"{field}: expected an object")
    status = _required_text(record.get("status"), f"{field}.status")
    if status not in REVIEW_STATUSES:
        raise ValueError(f"{field}.status: unknown value {status!r}")
    reviewer = _optional_text(record.get("reviewer"), f"{field}.reviewer")
    reviewed_on = _iso_date(
        record.get("reviewed_on"),
        f"{field}.reviewed_on",
        today=today,
        optional=True,
    )
    method = _optional_text(record.get("method"), f"{field}.method")
    reviewed_version = _optional_text(
        record.get("reviewed_version"), f"{field}.reviewed_version"
    )
    content_fingerprint = _optional_text(
        record.get("content_fingerprint"), f"{field}.content_fingerprint"
    )
    metadata = (
        reviewer,
        reviewed_on,
        method,
        reviewed_version,
        content_fingerprint,
    )
    if status == "prototype_review_pending" and any(metadata):
        raise ValueError(f"{field}: pending review cannot claim reviewer metadata")
    core_metadata = (reviewer, reviewed_on, method, reviewed_version)
    if status != "prototype_review_pending" and not all(core_metadata):
        raise ValueError(
            f"{field}: completed review requires reviewer, date, method, "
            f"and reviewed_version"
        )
    if status != "prototype_review_pending":
        reviewed_on_value = cast(str, reviewed_on)
        if reviewed_version != version:
            raise ValueError(
                f"{field}: reviewed_version must match explanation version"
            )
        if reviewed_on_value < updated_on:
            raise ValueError(
                f"{field}: review date predates the explanation update date"
            )
        if content_fingerprint is None:
            raise ValueError(f"{field}: completed review requires content_fingerprint")
        if not _FINGERPRINT.fullmatch(content_fingerprint):
            raise ValueError(f"{field}.content_fingerprint: invalid SHA-256")
        if content_fingerprint != expected_content_fingerprint:
            raise ValueError(
                f"{field}: content_fingerprint does not match English copy"
            )
    return Review(
        status,
        reviewer,
        reviewed_on,
        method,
        reviewed_version,
        content_fingerprint,
    )


def _localized(  # noqa: C901 — WVR-007
    record: Any,
    rule_id: str,
    language: str,
    version: str,
    updated_on: str,
    today: date,
) -> LocalizedExplanation:
    field = f"{rule_id}.{language}"
    if not isinstance(record, dict):
        raise ValueError(f"{field}: expected an object")
    translation_status = None
    reviewer = None
    reviewed_on = None
    method = None
    reviewed_version = None
    content_fingerprint = None

    title = _required_text(record.get("title"), f"{field}.title")
    summary = _required_text(record.get("summary"), f"{field}.summary")
    next_steps = _text_list(record.get("next_steps"), f"{field}.next_steps")
    confirm_with_staff = _text_list(
        record.get("confirm_with_staff"), f"{field}.confirm_with_staff"
    )
    highlights = _highlights(record.get("highlights"), f"{field}.highlights")
    localized = LocalizedExplanation(
        title=title,
        summary=summary,
        next_steps=next_steps,
        confirm_with_staff=confirm_with_staff,
        highlights=highlights,
    )

    if language == "es":
        translation_status = _required_text(
            record.get("translation_status"), f"{field}.translation_status"
        )
        if translation_status not in TRANSLATION_STATUSES:
            raise ValueError(
                f"{field}.translation_status: unknown value {translation_status!r}"
            )
        reviewer = _optional_text(record.get("reviewer"), f"{field}.reviewer")
        reviewed_on = _iso_date(
            record.get("reviewed_on"),
            f"{field}.reviewed_on",
            today=today,
            optional=True,
        )
        method = _optional_text(record.get("method"), f"{field}.method")
        reviewed_version = _optional_text(
            record.get("reviewed_version"), f"{field}.reviewed_version"
        )
        content_fingerprint = _optional_text(
            record.get("content_fingerprint"),
            f"{field}.content_fingerprint",
        )
        metadata = (
            reviewer,
            reviewed_on,
            method,
            reviewed_version,
            content_fingerprint,
        )
        if translation_status == "machine_draft" and any(metadata):
            raise ValueError(
                f"{field}: machine draft cannot claim translation review metadata"
            )
        core_metadata = (reviewer, reviewed_on, method, reviewed_version)
        if translation_status != "machine_draft" and not all(core_metadata):
            raise ValueError(
                f"{field}: reviewed translation requires reviewer, date, method, "
                f"and reviewed_version"
            )
        if translation_status != "machine_draft":
            reviewed_on_value = cast(str, reviewed_on)
            if reviewed_version != version:
                raise ValueError(
                    f"{field}: reviewed_version must match explanation version"
                )
            if reviewed_on_value < updated_on:
                raise ValueError(
                    f"{field}: review date predates the explanation update date"
                )
            if content_fingerprint is None:
                raise ValueError(
                    f"{field}: reviewed translation requires content_fingerprint"
                )
            if not _FINGERPRINT.fullmatch(content_fingerprint):
                raise ValueError(f"{field}.content_fingerprint: invalid SHA-256")
            expected = localized_content_fingerprint(version, language, localized)
            if content_fingerprint != expected:
                raise ValueError(
                    f"{field}: content_fingerprint does not match translated copy"
                )
    return LocalizedExplanation(
        title=title,
        summary=summary,
        next_steps=next_steps,
        confirm_with_staff=confirm_with_staff,
        highlights=highlights,
        translation_status=translation_status,
        reviewer=reviewer,
        reviewed_on=reviewed_on,
        method=method,
        reviewed_version=reviewed_version,
        content_fingerprint=content_fingerprint,
    )


def load_explanations(  # noqa: C901 — WVR-007
    path: Path,
    rules: list[Rule],
    *,
    require_complete: bool = True,
    strict: bool = True,
    today: date | None = None,
) -> dict[str, PlainLanguageExplanation]:
    """Load and validate display copy against the canonical rule set.

    Strict mode catches duplicate, orphaned, missing, citation-drifted, and
    source-date-drifted records. Display runtimes may use ``strict=False`` to
    discard invalid records individually and fall back from invalid Spanish
    copy to English. Neither mode participates in matching.
    """

    as_of = resolve_today(today)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        if strict:
            raise ValueError(
                f"plain-language data could not be loaded: {error}"
            ) from error
        return {}
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        got = payload.get("schema_version") if isinstance(payload, dict) else None
        schema_error = ValueError(
            f"plain-language schema_version must be {SCHEMA_VERSION}; got {got!r}"
        )
        if strict:
            raise schema_error
        return {}
    records = payload.get("entries")
    if not isinstance(records, list):
        if strict:
            raise ValueError("plain-language entries: expected a list")
        return {}

    rules_by_id = {rule.rule_id: rule for rule in rules}
    if len(rules_by_id) != len(rules):
        if strict:
            raise ValueError("canonical rule set contains duplicate rule IDs")
        return {}

    explanations: dict[str, PlainLanguageExplanation] = {}
    seen: set[str] = set()
    blocked: set[str] = set()
    for index, record in enumerate(records):
        try:
            if not isinstance(record, dict):
                raise ValueError(f"entries[{index}]: expected an object")
            rule_id = _required_text(
                record.get("source_rule_id"),
                f"entries[{index}].source_rule_id",
            )
        except ValueError:
            if strict:
                raise
            continue

        if rule_id in seen:
            if strict:
                raise ValueError(f"{rule_id}: duplicate plain-language explanation")
            explanations.pop(rule_id, None)
            blocked.add(rule_id)
            continue
        seen.add(rule_id)
        if rule_id in blocked:
            continue

        try:
            rule = rules_by_id.get(rule_id)
            if rule is None:
                raise ValueError(f"{rule_id}: explanation references an unknown rule")

            version = _required_text(record.get("version"), f"{rule_id}.version")
            if not _SEMVER.fullmatch(version):
                raise ValueError(f"{rule_id}.version: expected semantic version")
            source_verified_on = _iso_date(
                record.get("source_verified_on"),
                f"{rule_id}.source_verified_on",
                today=as_of,
                optional=True,
            )
            if source_verified_on != rule.citation.verified_on:
                raise ValueError(
                    f"{rule_id}: explanation source date {source_verified_on!r} "
                    f"does not match rule source date "
                    f"{rule.citation.verified_on!r}"
                )
            fingerprint = _required_text(
                record.get("citation_fingerprint"),
                f"{rule_id}.citation_fingerprint",
            )
            expected_fingerprint = citation_fingerprint(rule)
            if fingerprint != expected_fingerprint:
                raise ValueError(
                    f"{rule_id}: citation fingerprint does not match linked rule"
                )
            full_rule_fingerprint = _required_text(
                record.get("rule_fingerprint"),
                f"{rule_id}.rule_fingerprint",
            )
            expected_rule_fingerprint = rule_fingerprint(rule)
            if full_rule_fingerprint != expected_rule_fingerprint:
                raise ValueError(
                    f"{rule_id}: rule fingerprint does not match linked rule"
                )
            display_group = _required_text(
                record.get("display_group"), f"{rule_id}.display_group"
            )
            if display_group not in DISPLAY_GROUPS:
                raise ValueError(
                    f"{rule_id}.display_group: unknown value {display_group!r}"
                )
            if display_group != rule.display_group:
                raise ValueError(f"{rule_id}.display_group: does not match linked rule")
            drafted_by = _required_text(
                record.get("drafted_by"), f"{rule_id}.drafted_by"
            )
            if drafted_by != "ai_assisted":
                raise ValueError(
                    f"{rule_id}.drafted_by: expected 'ai_assisted', got {drafted_by!r}"
                )

            updated_on = _iso_date(
                record.get("updated_on"),
                f"{rule_id}.updated_on",
                today=as_of,
            )
            updated_on_value = cast(str, updated_on)
            if source_verified_on and updated_on_value < source_verified_on:
                raise ValueError(
                    f"{rule_id}: explanation update date {updated_on!r} "
                    f"predates linked source date {source_verified_on!r}"
                )
            english = _localized(
                record.get("en"),
                rule_id,
                "en",
                version,
                updated_on_value,
                as_of,
            )
            english_fingerprint = localized_content_fingerprint(version, "en", english)
            review = _review(
                record.get("review"),
                rule_id,
                version,
                updated_on_value,
                english_fingerprint,
                as_of,
            )
            try:
                spanish = _localized(
                    record.get("es"),
                    rule_id,
                    "es",
                    version,
                    updated_on_value,
                    as_of,
                )
            except ValueError:
                if strict:
                    raise
                spanish = None

            explanation = PlainLanguageExplanation(
                version=version,
                source_rule_id=rule_id,
                source_verified_on=source_verified_on,
                citation_fingerprint=fingerprint,
                rule_fingerprint=full_rule_fingerprint,
                display_group=display_group,
                drafted_by=drafted_by,
                updated_on=updated_on_value,
                review=review,
                en=english,
                es=spanish,
            )
        except ValueError:
            if strict:
                raise
            continue
        explanations[rule_id] = explanation

    if require_complete and strict:
        missing = sorted(set(rules_by_id) - set(explanations))
        if missing:
            raise ValueError(
                "plain-language explanations missing rule IDs: " + ", ".join(missing)
            )
    return explanations
