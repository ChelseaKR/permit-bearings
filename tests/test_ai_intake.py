"""Intake extraction: allowed values only, quote-bound, absence stays absence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.ai import facts
from permit_pathways.ai.intake import (
    MAX_TEXT_CHARS,
    STATUS_DOWNGRADED,
    STATUS_EXTRACTED,
    STATUS_NOT_APPLICABLE,
    STATUS_UNKNOWN,
    IntakeError,
    JurisdictionEntry,
    extract_intake,
    extraction_schema,
    load_jurisdictions,
    normalize_jurisdiction_name,
    resolve_jurisdiction,
    system_prompt,
)
from permit_pathways.ai.provider import ScriptedProvider

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = load_jurisdictions(
    json.loads(
        (ROOT / "data" / "jurisdictions" / "registry.json").read_text(encoding="utf-8")
    )["jurisdictions"]
)
TEXT = (
    "I want to build a 600 sq ft detached unit behind my house in Davis, "
    "lot is 5,000 sq ft, there's a bus stop two blocks away."
)


def _payload(**overrides: Any) -> str:
    base: dict[str, Any] = {
        "detected_language": "en",
        "project_type": {"value": "adu", "quote": "build a 600 sq ft detached unit"},
        "jurisdiction_name": {"value": "Davis", "quote": "in Davis"},
        "unmapped_details": [
            "lot is 5,000 sq ft",
            "a bus stop two blocks away",
            "not in text",
        ],
    }
    for field in facts.FACT_FIELDS:
        base[field.name] = {"value": "unknown", "quote": ""}
    base["primary_dwelling_status"] = {
        "value": "existing_single_family",
        "quote": "behind my house",
    }
    base["adu_project_form"] = {"value": "new_detached", "quote": "detached unit"}
    base.update(overrides)
    return json.dumps(base)


def test_schema_has_no_union_typed_parameters_and_covers_every_field() -> None:
    schema = extraction_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "detected_language",
        "project_type",
        "jurisdiction_name",
        "unmapped_details",
        *facts.FACT_NAMES,
    }
    encoded = json.dumps(schema)
    assert "anyOf" not in encoded and '"null"' not in encoded
    assert schema["properties"]["project_type"]["properties"]["value"]["enum"] == [
        *facts.PROJECT_TYPES,
        "unknown",
    ]
    prompt = system_prompt()
    assert "never infer" in prompt.lower() or "Never infer" in prompt
    assert all(field.name in prompt for field in facts.FACT_FIELDS)


def test_extraction_keeps_supported_values_and_reports_unknowns() -> None:
    provider = ScriptedProvider([_payload()])
    result = extract_intake(TEXT, language="en", provider=provider, registry=REGISTRY)
    assert result.project_type.value == "adu"
    assert result.project_type.status == STATUS_EXTRACTED
    assert (
        result.jurisdiction.slug == "davis"
        and result.jurisdiction.status == STATUS_EXTRACTED
    )
    by_name = {f.name: f for f in result.fields}
    assert by_name["primary_dwelling_status"].value == "existing_single_family"
    assert by_name["adu_project_form"].quote == "detached unit"
    assert by_name["unpermitted_existing"].status == STATUS_UNKNOWN
    assert by_name["sf_zone"].status == STATUS_NOT_APPLICABLE
    assert result.unanswered == ("unpermitted_existing",)
    assert result.unmapped_details == (
        "lot is 5,000 sq ft",
        "a bus stop two blocks away",
    )
    assert result.draft_intake() == {
        "project_type": "adu",
        "jurisdiction": "davis",
        "primary_dwelling_status": "existing_single_family",
        "adu_project_form": "new_detached",
        "unpermitted_existing": "unknown",
    }
    assert result.prompt_version == "intake-v1" and result.provider == "scripted"
    assert result.to_dict()["detected_language"] == "en"
    assert provider.calls[0].user.startswith("Project description")
    assert TEXT in provider.calls[0].user


def test_value_without_a_verbatim_quote_is_downgraded_to_unknown() -> None:
    provider = ScriptedProvider(
        [
            _payload(
                unpermitted_existing={"value": "no", "quote": "built with permits"},
                adu_project_form={"value": "new_detached", "quote": ""},
            )
        ]
    )
    result = extract_intake(TEXT, language="en", provider=provider, registry=REGISTRY)
    by_name = {f.name: f for f in result.fields}
    assert by_name["unpermitted_existing"].value == "unknown"
    assert by_name["unpermitted_existing"].status == STATUS_DOWNGRADED
    assert "does not occur" in str(by_name["unpermitted_existing"].note)
    assert by_name["adu_project_form"].status == STATUS_DOWNGRADED
    assert (
        "adu_project_form" in result.unanswered
        and "unpermitted_existing" in result.unanswered
    )


def test_value_outside_the_allowed_list_is_downgraded() -> None:
    provider = ScriptedProvider(
        [_payload(adu_project_form={"value": "tiny_home", "quote": "detached unit"})]
    )
    result = extract_intake(TEXT, language="en", provider=provider, registry=REGISTRY)
    field = next(f for f in result.fields if f.name == "adu_project_form")
    assert field.status == STATUS_DOWNGRADED and field.value == "unknown"
    assert field.note == "value outside the allowed list"


def test_unknown_project_type_makes_every_field_not_applicable() -> None:
    provider = ScriptedProvider(
        [
            _payload(
                project_type={"value": "unknown", "quote": ""},
                jurisdiction_name={"value": "", "quote": ""},
            )
        ]
    )
    result = extract_intake(TEXT, language="es", provider=provider, registry=REGISTRY)
    assert result.project_type.value == "unknown"
    assert all(f.status == STATUS_NOT_APPLICABLE for f in result.fields)
    assert (
        result.unanswered[0] == "project_type"
        and result.unanswered[-1] == "jurisdiction"
    )
    assert result.draft_intake() == {"project_type": "unknown"}
    assert result.jurisdiction.status == STATUS_UNKNOWN


def test_missing_or_malformed_field_objects_become_unknown() -> None:
    payload = json.loads(_payload())
    payload["unpermitted_existing"] = "no"
    del payload["primary_dwelling_status"]
    provider = ScriptedProvider([json.dumps(payload)])
    result = extract_intake(TEXT, language="en", provider=provider, registry=REGISTRY)
    by_name = {f.name: f for f in result.fields}
    assert by_name["unpermitted_existing"].note == "no field returned"
    assert by_name["primary_dwelling_status"].status == STATUS_UNKNOWN


@pytest.mark.parametrize(
    ("text", "message"),
    [("   ", "empty"), ("x" * (MAX_TEXT_CHARS + 1), "longer than")],
)
def test_rejects_empty_or_oversized_descriptions(text: str, message: str) -> None:
    with pytest.raises(IntakeError, match=message):
        extract_intake(
            text, language="en", provider=ScriptedProvider([]), registry=REGISTRY
        )


def test_rejects_unknown_language_and_non_json_output() -> None:
    with pytest.raises(IntakeError, match="language"):
        extract_intake(
            TEXT, language="fr", provider=ScriptedProvider([]), registry=REGISTRY
        )
    with pytest.raises(IntakeError, match="did not return JSON"):
        extract_intake(
            TEXT,
            language="en",
            provider=ScriptedProvider(["not json"]),
            registry=REGISTRY,
        )
    with pytest.raises(IntakeError, match="JSON object"):
        extract_intake(
            TEXT, language="en", provider=ScriptedProvider(["[1]"]), registry=REGISTRY
        )


def test_jurisdiction_resolution_handles_cities_counties_and_ambiguity() -> None:
    text = "My house is in the City of Davis, in Yolo County, near Sacramento."
    davis = resolve_jurisdiction(
        {"value": "City of Davis", "quote": "City of Davis"}, text, REGISTRY
    )
    assert (davis.slug, davis.name, davis.status) == (
        "davis",
        "Davis",
        STATUS_EXTRACTED,
    )
    county = resolve_jurisdiction(
        {"value": "Yolo County", "quote": "Yolo County"}, text, REGISTRY
    )
    assert county.slug == "yolo-county"
    condado = resolve_jurisdiction(
        {"value": "Condado de Yolo", "quote": "Condado de Yolo"},
        "Vivo en el Condado de Yolo.",
        REGISTRY,
    )
    assert condado.slug == "yolo-county"
    unsupported = resolve_jurisdiction(
        {"value": "Fresno", "quote": "Fresno"}, text, REGISTRY
    )
    assert unsupported.status == STATUS_DOWNGRADED and unsupported.slug is None
    partial = resolve_jurisdiction(
        {"value": "San", "quote": "San"}, "I live in San something.", REGISTRY
    )
    assert (
        partial.status == "unresolved" and partial.candidates and partial.slug is None
    )
    assert resolve_jurisdiction(None, text, REGISTRY).status == STATUS_UNKNOWN
    assert (
        resolve_jurisdiction({"value": "  ", "quote": ""}, text, REGISTRY).status
        == STATUS_UNKNOWN
    )
    assert normalize_jurisdiction_name("The County of Yolo.") == "yolo"


def test_jurisdiction_entries_are_plain_records() -> None:
    entries = load_jurisdictions([{"slug": "x-city", "name": "X City", "kind": "city"}])
    assert entries == (JurisdictionEntry("x-city", "X City", "city"),)
