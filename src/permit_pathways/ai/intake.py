"""Natural-language intake: the model structures input; it does not decide.

Given an applicant's free-text description, ask the model for a draft of the
structured facts in :mod:`permit_pathways.ai.facts` — and nothing outside
that vocabulary — with a verbatim quote from the applicant's text supporting
each value. The service then re-checks every value against the allowed list
and every quote against the text, downgrading anything unsupported to
``unknown``. Fields the text did not answer stay ``unknown`` and are reported
as "could not tell from what you wrote". The result is a draft for the
applicant to confirm in the existing form; the matcher never sees it.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

from . import facts
from .corpus import normalize_for_match
from .provider import Provider, ProviderError

PROMPT_VERSION = "intake-v1"
MAX_TEXT_CHARS = 4000
MAX_OUTPUT_TOKENS = 2500
LANGUAGES = ("en", "es")
STATUS_EXTRACTED = "extracted"
STATUS_UNKNOWN = "unknown"
STATUS_NOT_APPLICABLE = "not_applicable"
STATUS_DOWNGRADED = "downgraded"


class IntakeError(ValueError):
    """The request or the model output could not be used."""


@dataclass(frozen=True)
class ExtractedField:
    name: str
    value: str
    status: str
    quote: str | None
    note: str | None


@dataclass(frozen=True)
class ExtractedJurisdiction:
    text: str | None
    slug: str | None
    name: str | None
    status: str
    quote: str | None
    candidates: tuple[str, ...]


@dataclass(frozen=True)
class IntakeExtraction:
    language: str
    detected_language: str
    project_type: ExtractedField
    jurisdiction: ExtractedJurisdiction
    fields: tuple[ExtractedField, ...]
    unanswered: tuple[str, ...]
    unmapped_details: tuple[str, ...]
    provider: str
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def draft_intake(self) -> dict[str, str]:
        """The form-shaped draft: confirmed-looking, but a draft until the
        applicant submits it. ``unknown`` stays ``unknown``."""
        draft = {"project_type": self.project_type.value}
        if self.jurisdiction.slug:
            draft["jurisdiction"] = self.jurisdiction.slug
        for f in self.fields:
            if f.status != STATUS_NOT_APPLICABLE:
                draft[f.name] = f.value
        return draft


_SYSTEM_PROMPT = """You extract structured facts from a homeowner's or builder's description of a California housing project so that a separate, deterministic screening tool can run on them. You do not decide anything, do not give advice, and do not evaluate eligibility.

Rules you must follow:
1. Every value you return must be one of the allowed values for that field. Use "unknown" whenever the description does not state the fact or states it ambiguously.
2. For every value other than "unknown", copy the exact words from the description that support it into "quote". The quote must be a verbatim substring of the description. If you cannot quote supporting words, return "unknown" and an empty quote ("").
3. Never infer a fact that the description does not state: do not assume zoning, historic status, tenant history, rent restrictions, protected-site conditions, lot-size compliance, urbanized status, or permit history from how typical projects usually are. Ordinary-meaning readings are fine: "backyard cottage" is a new detached ADU; "convert my garage" is a conversion; "my house" is an existing single-family home; "a unit inside my house" is a junior ADU only if the description says it is small and inside the home.
4. The description may be in English or Spanish. Return field values in the allowed English tokens regardless of the input language.
5. "jurisdiction_name": the city or county named in the description, copied as written (for example "Davis" or "Yolo County"), with "quote" the words it came from. Empty strings if none is named. Do not guess a city from a street, neighborhood, or region.
6. "unmapped_details": verbatim quotes of concrete details the applicant gave that no field captures (for example a lot size, unit size, or a nearby bus stop). Quotes only; no paraphrase, no interpretation.
7. Fields that do not apply to the project type should still be present with "unknown".
"""


def _vocabulary_block() -> str:
    lines = [
        "Fields and allowed values:",
        f"- project_type: {', '.join(facts.PROJECT_TYPES)}, unknown. "
        "adu = accessory dwelling unit (backyard cottage, garage conversion, attached or "
        "detached second unit); jadu = junior ADU, a small unit inside the existing "
        "home; two_unit = two homes on one single-family lot under SB 9; lot_split = "
        "splitting one lot into two parcels under SB 9.",
    ]
    for f in facts.FACT_FIELDS:
        lines.append(
            f"- {f.name} (applies to {', '.join(f.applies_to)}): "
            f"{', '.join(f.values)}. {f.meaning}"
        )
    return "\n".join(lines)


def extraction_schema() -> dict[str, Any]:
    def field_schema(values: tuple[str, ...]) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "value": {"type": "string", "enum": list(values)},
                "quote": {"type": "string"},
            },
            "required": ["value", "quote"],
            "additionalProperties": False,
        }

    properties: dict[str, Any] = {
        "detected_language": {"type": "string", "enum": ["en", "es", "other"]},
        "project_type": field_schema((*facts.PROJECT_TYPES, facts.UNKNOWN)),
        "jurisdiction_name": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "quote": {"type": "string"},
            },
            "required": ["value", "quote"],
            "additionalProperties": False,
        },
        "unmapped_details": {"type": "array", "items": {"type": "string"}},
    }
    for f in facts.FACT_FIELDS:
        properties[f.name] = field_schema(f.values)
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def system_prompt() -> str:
    return f"{_SYSTEM_PROMPT}\n{_vocabulary_block()}"


def user_prompt(text: str) -> str:
    return (
        "Project description (verbatim; quote from it exactly):\n<description>\n"
        f"{text}\n</description>"
    )


def _quote_supports(quote: str | None, text: str) -> bool:
    if not quote or not quote.strip():
        return False
    needle = normalize_for_match(quote)
    return len(needle) >= 3 and needle in normalize_for_match(text)


def _clean_text(text: str) -> str:
    cleaned = unicodedata.normalize("NFC", text).replace("\x00", "").strip()
    if not cleaned:
        raise IntakeError("the description is empty")
    if len(cleaned) > MAX_TEXT_CHARS:
        raise IntakeError(f"the description is longer than {MAX_TEXT_CHARS} characters")
    return cleaned


def _parse(completion_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(completion_text)
    except ValueError as exc:
        raise IntakeError("the model did not return JSON") from exc
    if not isinstance(parsed, dict):
        raise IntakeError("the model did not return a JSON object")
    return parsed


def _field_from(
    name: str, raw: Any, text: str, *, applicable: bool, values: tuple[str, ...]
) -> ExtractedField:
    if not applicable:
        return ExtractedField(name, facts.UNKNOWN, STATUS_NOT_APPLICABLE, None, None)
    if not isinstance(raw, dict):
        return ExtractedField(
            name, facts.UNKNOWN, STATUS_UNKNOWN, None, "no field returned"
        )
    value = raw.get("value")
    quote = raw.get("quote")
    quote_text = quote.strip() if isinstance(quote, str) and quote.strip() else None
    if not isinstance(value, str) or value not in values:
        return ExtractedField(
            name,
            facts.UNKNOWN,
            STATUS_DOWNGRADED,
            None,
            "value outside the allowed list",
        )
    if value == facts.UNKNOWN:
        return ExtractedField(name, facts.UNKNOWN, STATUS_UNKNOWN, None, None)
    if not _quote_supports(quote_text, text):
        return ExtractedField(
            name,
            facts.UNKNOWN,
            STATUS_DOWNGRADED,
            None,
            "the supporting quote was missing or does not occur in the description",
        )
    return ExtractedField(name, value, STATUS_EXTRACTED, quote_text, None)


_NAME_NOISE = re.compile(
    r"^(?:the\s+)?(?:city|town|county|ciudad|condado)\s+(?:of|de)\s+", re.I
)


def normalize_jurisdiction_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    value = value.strip().strip(".,;:")
    value = _NAME_NOISE.sub("", value)
    value = re.sub(r"\s+", " ", value)
    return value.casefold()


@dataclass(frozen=True)
class JurisdictionEntry:
    slug: str
    name: str
    kind: str


def load_jurisdictions(
    records: Iterable[Mapping[str, Any]],
) -> tuple[JurisdictionEntry, ...]:
    return tuple(
        JurisdictionEntry(str(r["slug"]), str(r["name"]), str(r["kind"]))
        for r in records
    )


def resolve_jurisdiction(
    raw: Any, text: str, registry: tuple[JurisdictionEntry, ...]
) -> ExtractedJurisdiction:
    if not isinstance(raw, dict) or not isinstance(raw.get("value"), str):
        return ExtractedJurisdiction(None, None, None, STATUS_UNKNOWN, None, ())
    value = raw["value"].strip()
    quote_raw = raw.get("quote")
    quote = (
        quote_raw.strip() if isinstance(quote_raw, str) and quote_raw.strip() else None
    )
    if not value:
        return ExtractedJurisdiction(None, None, None, STATUS_UNKNOWN, None, ())
    if not _quote_supports(quote, text) and not _quote_supports(value, text):
        return ExtractedJurisdiction(value, None, None, STATUS_DOWNGRADED, None, ())
    wanted = normalize_jurisdiction_name(value)
    wants_county = bool(re.search(r"\b(county|condado)\b", value, re.I))
    exact = [e for e in registry if normalize_jurisdiction_name(e.name) == wanted]
    if not exact and wants_county:
        base = re.sub(r"\b(county|condado)\b", "", wanted).strip()
        exact = [
            e
            for e in registry
            if e.kind == "county"
            and normalize_jurisdiction_name(e.name) == f"{base} county"
        ]
    if len(exact) == 1:
        entry = exact[0]
        return ExtractedJurisdiction(
            value, entry.slug, entry.name, STATUS_EXTRACTED, quote or value, ()
        )
    partial = [
        e.name
        for e in registry
        if wanted and wanted in normalize_jurisdiction_name(e.name)
    ][:5]
    return ExtractedJurisdiction(value, None, None, "unresolved", quote, tuple(partial))


def extract_intake(
    text: str,
    *,
    language: str,
    provider: Provider,
    registry: tuple[JurisdictionEntry, ...],
) -> IntakeExtraction:
    if language not in LANGUAGES:
        raise IntakeError(f"language must be one of {', '.join(LANGUAGES)}")
    cleaned = _clean_text(text)
    completion = provider.complete_json(
        system=system_prompt(),
        user=user_prompt(cleaned),
        schema=extraction_schema(),
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    parsed = _parse(completion.text)
    project_type = _field_from(
        "project_type",
        parsed.get("project_type"),
        cleaned,
        applicable=True,
        values=(*facts.PROJECT_TYPES, facts.UNKNOWN),
    )
    material = set(facts.material_fields(project_type.value))
    fields = tuple(
        _field_from(
            f.name,
            parsed.get(f.name),
            cleaned,
            applicable=f.name in material,
            values=f.values,
        )
        for f in facts.FACT_FIELDS
    )
    jurisdiction = resolve_jurisdiction(
        parsed.get("jurisdiction_name"), cleaned, registry
    )
    unanswered = [
        f.name for f in fields if f.status in {STATUS_UNKNOWN, STATUS_DOWNGRADED}
    ]
    if project_type.value == facts.UNKNOWN:
        unanswered.insert(0, "project_type")
    if jurisdiction.slug is None:
        unanswered.append("jurisdiction")
    details = parsed.get("unmapped_details")
    unmapped = tuple(
        d
        for d in (details if isinstance(details, list) else [])
        if isinstance(d, str) and _quote_supports(d, cleaned)
    )
    detected = parsed.get("detected_language")
    return IntakeExtraction(
        language=language,
        detected_language=detected if detected in {"en", "es", "other"} else "other",
        project_type=project_type,
        jurisdiction=jurisdiction,
        fields=fields,
        unanswered=tuple(unanswered),
        unmapped_details=unmapped,
        provider=completion.provider,
        model=completion.model,
        prompt_version=PROMPT_VERSION,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
    )


__all__ = [
    "ExtractedField",
    "ExtractedJurisdiction",
    "IntakeError",
    "IntakeExtraction",
    "JurisdictionEntry",
    "ProviderError",
    "extract_intake",
    "extraction_schema",
    "load_jurisdictions",
    "resolve_jurisdiction",
    "system_prompt",
]
