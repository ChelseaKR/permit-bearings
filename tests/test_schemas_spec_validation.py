"""The published schemas, checked by a spec-complete validator (CQ-49).

`tests/test_screening_contract.py` validates with a small in-repo checker that
refuses any keyword it does not enforce. This file adds the independent check:
the `jsonschema` library's Draft 2020-12 validator, which implements the whole
specification. Each committed schema must itself be a valid 2020-12 schema,
and the documents the project publishes must validate against it. If the
in-repo checker and the reference implementation ever disagree, one of these
two files fails.

The negative controls at the end break one document each and assert the
validator rejects it, so a validator that accepts everything cannot pass here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from permit_pathways.screening import load_rules, screen
from permit_pathways.screening_contract import SCHEMAS, build_result

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
RULES_DIR = ROOT / "data" / "rules"


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _rule_records() -> list[dict[str, Any]]:
    records = []
    for path in sorted(RULES_DIR.glob("*.json")):
        if path.name != "index.json":
            records.extend(json.loads(path.read_text(encoding="utf-8")))
    return records


def _golden_intakes() -> list[dict[str, Any]]:
    cases = json.loads((ROOT / "data" / "golden" / "example.json").read_text("utf-8"))
    return [case["intake"] for case in cases]


def _result(intake: dict[str, Any]) -> dict[str, Any]:
    rules = load_rules(RULES_DIR)
    return build_result(
        intake=intake,
        rules=rules,
        results=screen(intake, rules),
        as_of="2026-09-06",
        source_state=None,
    )


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_each_published_schema_is_a_valid_draft_2020_12_schema(name: str) -> None:
    _validator(name)


def test_every_committed_rule_validates() -> None:
    validator = _validator("rule.schema.json")
    records = _rule_records()
    assert len(records) >= 19, f"only {len(records)} rule records were found"
    for record in records:
        errors = [e.message for e in validator.iter_errors(record)]
        assert not errors, (record.get("rule_id"), errors)


def test_every_golden_intake_validates_as_a_facts_document() -> None:
    validator = _validator("facts.schema.json")
    intakes = _golden_intakes()
    assert intakes
    for intake in intakes:
        errors = [e.message for e in validator.iter_errors(intake)]
        assert not errors, errors


def test_the_result_for_every_golden_intake_validates() -> None:
    validator = _validator("result.schema.json")
    for intake in _golden_intakes():
        errors = [e.message for e in validator.iter_errors(_result(intake))]
        assert not errors, errors


# --- negative controls -----------------------------------------------------


def test_negative_control_a_rule_without_its_citation_is_rejected() -> None:
    record = dict(_rule_records()[0])
    assert "citation" in record
    del record["citation"]
    assert not _validator("rule.schema.json").is_valid(record)


def test_negative_control_an_unknown_fact_value_is_rejected() -> None:
    intake = dict(_golden_intakes()[0])
    intake["project_type"] = "not-a-project-type"
    assert not _validator("facts.schema.json").is_valid(intake)


def test_negative_control_a_ranking_field_on_a_result_is_rejected() -> None:
    result = _result(_golden_intakes()[0])
    result["rank"] = 1
    assert not _validator("result.schema.json").is_valid(result)
