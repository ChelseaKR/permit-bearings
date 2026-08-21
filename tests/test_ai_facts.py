"""The AI intake vocabulary must be exactly the matcher's vocabulary."""

from __future__ import annotations

import json
import re
from pathlib import Path

from permit_pathways.ai import facts
from permit_pathways.beta_operations import BROWSER_MEMORY_FIELDS

ROOT = Path(__file__).resolve().parents[1]


def _rule_criteria_fields() -> set[str]:
    names: set[str] = set()
    for path in sorted((ROOT / "data" / "rules").glob("*.json")):
        if path.name == "index.json":
            continue
        for rule in json.loads(path.read_text(encoding="utf-8")):
            for criterion in rule["criteria"]:
                names.add(criterion["field"])
    return names


def _rule_criteria_values() -> dict[str, set[str]]:
    values: dict[str, set[str]] = {}
    for path in sorted((ROOT / "data" / "rules").glob("*.json")):
        if path.name == "index.json":
            continue
        for rule in json.loads(path.read_text(encoding="utf-8")):
            for criterion in rule["criteria"]:
                bucket = values.setdefault(criterion["field"], set())
                raw = criterion["value"]
                bucket.update(raw if isinstance(raw, list) else [raw])
    return values


def test_every_rule_criterion_field_is_in_the_vocabulary() -> None:
    vocabulary = set(facts.FACT_NAMES) | {"project_type", "jurisdiction"}
    assert _rule_criteria_fields() <= vocabulary


def test_every_rule_criterion_value_is_an_allowed_value() -> None:
    for field, values in _rule_criteria_values().items():
        if field == "jurisdiction":
            continue
        assert values <= set(facts.allowed_values(field)), field


def test_vocabulary_matches_the_pinned_browser_memory_fields() -> None:
    browser_facts = set(BROWSER_MEMORY_FIELDS) - {
        "jurisdiction_name",
        "journey_applicability",
    }
    assert browser_facts == set(facts.FACT_NAMES) | {"project_type", "jurisdiction"}


def test_material_fields_match_the_browser_form() -> None:
    source = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")

    def js_list(name: str) -> list[str]:
        match = re.search(rf"const {name} = \[(.*?)\];", source, re.S)
        assert match, name
        return re.findall(r'"([a-z0-9_]+)"', match.group(1))

    base = js_list("SB9_BASE_FIELDS")
    two_unit = js_list("SB9_TWO_UNIT_FIELDS")
    lot_split = js_list("SB9_LOT_SPLIT_FIELDS")
    assert list(facts.material_fields("adu")) == [
        "primary_dwelling_status",
        "adu_project_form",
        "unpermitted_existing",
    ]
    assert list(facts.material_fields("jadu")) == [
        "primary_dwelling_status",
        "unpermitted_existing",
    ]
    assert set(facts.material_fields("two_unit")) == set(base + two_unit)
    assert set(facts.material_fields("lot_split")) == set(base + lot_split)
    assert facts.material_fields("garage") == ()


def test_browser_option_values_match_allowed_values() -> None:
    source = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")

    def option_values(name: str) -> list[str]:
        match = re.search(rf"{name}: \[(.*?)\n    \]", source, re.S)
        assert match, name
        return re.findall(r'\["([a-z_]+)",', match.group(1))

    assert option_values("primaryOptions") == list(facts.PRIMARY_DWELLING_VALUES)
    assert option_values("aduFormOptions") == list(facts.ADU_FORM_VALUES)
    tri = re.search(r'tri: \[\["yes","Yes"\],\["no","No"\],\["unknown"', source)
    assert tri is not None
    assert facts.TRI_STATE == ("yes", "no", "unknown")


def test_unknown_is_always_allowed_and_never_concrete() -> None:
    for field in facts.FACT_FIELDS:
        assert facts.UNKNOWN in field.values
        assert facts.UNKNOWN not in field.concrete_values
        assert field.meaning
    assert facts.allowed_values("project_type") == facts.PROJECT_TYPES
    assert facts.allowed_values("nonsense") == ()
