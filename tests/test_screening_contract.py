"""The published contract around the matcher: the schemas and the envelope.

Two things are being held here.

*The schemas cannot drift from the code.* They are generated from
``ai.facts`` and ``screening``'s own definitions, so a new fact field or a new
route class moves the schema; the committed files under ``schemas/`` are then
compared byte for byte, and a stale one fails.

*The envelope cannot publish an absence as a value.* An unanswered material
fact withholds every candidate route and says so; a missing source snapshot
reports nulls and a notice rather than an empty summary that reads like a clean
check.

The schema checker below is deliberately small and deliberately guarded. A
hand-rolled validator's real failure mode is not rejecting something valid --
it is *passing* a document because it silently ignored a keyword it does not
implement. ``test_the_checker_understands_every_keyword_the_schemas_use`` walks
the committed schemas and fails on any keyword the checker cannot enforce, so
the checker cannot go quiet as the schemas grow.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.ai.facts import FACT_FIELDS, PROJECT_TYPES
from permit_pathways.screening import Citation, Rule, load_rules, screen
from permit_pathways.screening_contract import (
    DECISION_BOUNDARIES,
    SCHEMA_VERSION,
    SCHEMAS,
    FactsDocumentError,
    build_result,
    render_schema,
    rules_fingerprint,
    source_state_summary,
    unresolved_facts,
    validate_facts_document,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
RULES_DIR = ROOT / "data" / "rules"

#: Every keyword the checker below actually enforces. A schema using anything
#: else is a silent hole, so the guard test fails instead.
_UNDERSTOOD = {
    "$schema",
    "$id",
    "title",
    "description",
    "type",
    "required",
    "additionalProperties",
    "properties",
    "items",
    "enum",
    "const",
    "pattern",
    "minLength",
}

_TYPES: dict[str, Any] = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "boolean": bool,
}


def _check_type(value: Any, expected: Any, path: str, errors: list[str]) -> bool:
    names = expected if isinstance(expected, list) else [expected]
    for name in names:
        if name == "null":
            if value is None:
                return True
            continue
        python_type = _TYPES[name]
        if python_type is int and isinstance(value, bool):
            continue
        if python_type is not bool and isinstance(value, bool):
            continue
        if isinstance(value, python_type):
            return True
    errors.append(f"{path}: expected {expected}, got {type(value).__name__}")
    return False


def _scalar_errors(instance: Any, schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in {schema['enum']}")
    if not isinstance(instance, str):
        return errors
    if "pattern" in schema and not re.search(schema["pattern"], instance):
        errors.append(f"{path}: {instance!r} does not match {schema['pattern']}")
    if "minLength" in schema and len(instance) < schema["minLength"]:
        errors.append(f"{path}: shorter than {schema['minLength']}")
    return errors


def _object_errors(
    instance: dict[str, Any], schema: dict[str, Any], path: str
) -> list[str]:
    errors: list[str] = []
    for name in schema.get("required", []):
        if name not in instance:
            errors.append(f"{path}: missing required {name!r}")
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        for name in instance:
            if name not in properties:
                errors.append(f"{path}: unexpected property {name!r}")
    for name, value in instance.items():
        if name in properties:
            errors.extend(validate(value, properties[name], f"{path}.{name}"))
    return errors


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """A checker for exactly the keyword subset these schemas use."""
    errors: list[str] = []
    if "type" in schema and not _check_type(instance, schema["type"], path, errors):
        return errors
    errors.extend(_scalar_errors(instance, schema, path))
    if isinstance(instance, dict):
        errors.extend(_object_errors(instance, schema, path))
    if isinstance(instance, list) and "items" in schema:
        for index, value in enumerate(instance):
            errors.extend(validate(value, schema["items"], f"{path}[{index}]"))
    return errors


def _keywords(node: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        found |= set(node)
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                for child in value.values():
                    found |= _keywords(child)
            elif key not in {"enum", "const", "required"}:
                found |= _keywords(value)
    elif isinstance(node, list):
        for value in node:
            found |= _keywords(value)
    return found


def _committed(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _adu_facts(**overrides: str) -> dict[str, Any]:
    facts = {
        "project_type": "adu",
        "jurisdiction": "davis",
        "primary_dwelling_status": "existing_single_family",
        "adu_project_form": "new_detached",
        "unpermitted_existing": "no",
    }
    facts.update(overrides)
    return facts


def _result(facts: dict[str, Any], snapshot: dict[str, Any] | None = None) -> dict:
    rules = load_rules(RULES_DIR)
    return build_result(
        intake=facts,
        rules=rules,
        results=screen(facts, rules),
        as_of="2026-09-06",
        source_state=snapshot,
    )


# --- the schemas are generated, not maintained -------------------------------


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_the_committed_schema_is_what_the_code_generates(name: str) -> None:
    """Regenerate and compare. A schema edited by hand fails here."""
    committed = (SCHEMA_DIR / name).read_text(encoding="utf-8")
    assert committed == render_schema(name), (
        f"schemas/{name} is stale; regenerate with `python scripts/gen_schemas.py`"
    )


def test_the_checker_understands_every_keyword_the_schemas_use() -> None:
    """The hole a hand-rolled validator actually falls into.

    Rejecting a valid document is loud. Accepting an invalid one because a
    keyword was ignored is silent, and it is the failure that makes a
    "validated against the schema" claim worthless.
    """
    used: set[str] = set()
    for name in SCHEMAS:
        used |= _keywords(_committed(name))
    assert used <= _UNDERSTOOD, (
        f"schema keywords the checker ignores: {used - _UNDERSTOOD}"
    )


def test_the_facts_schema_names_every_fact_the_matcher_reads() -> None:
    """A fact added to the vocabulary must reach the published schema."""
    schema = _committed("facts.schema.json")
    assert set(schema["properties"]) == {"project_type", "jurisdiction"} | {
        field.name for field in FACT_FIELDS
    }
    assert schema["properties"]["project_type"]["enum"] == list(PROJECT_TYPES)
    for field in FACT_FIELDS:
        assert schema["properties"][field.name]["enum"] == list(field.values)


def test_every_committed_rule_validates_against_the_published_rule_schema() -> None:
    rule_schema = _committed("rule.schema.json")
    checked = 0
    for path in sorted(RULES_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        for index, record in enumerate(json.loads(path.read_text(encoding="utf-8"))):
            errors = validate(record, rule_schema, f"{path.name}[{index}]")
            assert not errors, errors
            checked += 1
    # A loop over an empty corpus passes without checking anything.
    assert checked >= 19, f"only {checked} rule records were checked"


def test_every_golden_intake_validates_against_the_published_facts_schema() -> None:
    """The corpus the browser is held to is also a corpus of valid facts files."""
    facts_schema = _committed("facts.schema.json")
    cases = json.loads(
        (ROOT / "data" / "golden" / "example.json").read_text(encoding="utf-8")
    )
    assert len(cases) == 29, "the golden corpus changed size; check the parity tests"
    for case in cases:
        errors = validate(case["intake"], facts_schema, case["case_id"])
        assert not errors, errors


# --- the envelope ------------------------------------------------------------


def test_a_complete_intake_produces_a_result_that_validates() -> None:
    result = _result(_adu_facts())
    assert not validate(result, _committed("result.schema.json"))
    assert result["decision_boundary"] == "candidate_rules_only"
    assert result["candidate_routes"], "a complete intake should name its route classes"
    assert result["matched_rules"]


def test_an_unanswered_material_fact_withholds_every_candidate_route() -> None:
    """The dominant defect, in its natural habitat.

    `unpermitted_existing: unknown` is not `no`. A route derived from rules
    matched under an unanswered question would be a route the encoded rules do
    not support yet, printed with the same confidence as one they do.
    """
    result = _result(_adu_facts(unpermitted_existing="unknown"))
    assert not validate(result, _committed("result.schema.json"))
    assert result["decision_boundary"] == "needs_staff_review"
    assert result["candidate_routes"] == []
    assert result["unresolved_facts"] == ["unpermitted_existing"]
    assert any("unpermitted_existing" in notice for notice in result["notices"])
    # Matched rules are still reported: hiding them would misrepresent coverage.
    assert result["matched_rules"]


def test_a_fact_left_out_entirely_is_the_same_state_as_unknown() -> None:
    facts = _adu_facts()
    del facts["adu_project_form"]
    assert unresolved_facts(facts) == ("adu_project_form",)
    assert _result(facts)["candidate_routes"] == []


def test_no_snapshot_is_reported_as_no_check_not_as_a_clean_check() -> None:
    """An empty `changed_source_ids` list reads exactly like "nothing changed"."""
    summary = source_state_summary(None)
    assert summary["available"] is False
    assert summary["snapshot_id"] is None
    assert summary["receipt_id"] is None
    assert summary["changed_source_ids"] is None, (
        "an unchecked run is not an empty list"
    )
    assert summary["unverifiable_source_ids"] is None

    result = _result(_adu_facts(), snapshot=None)
    assert any("says nothing about whether" in notice for notice in result["notices"])


def test_a_source_that_could_not_be_fetched_is_named_not_folded_into_unchanged() -> (
    None
):
    snapshot = {
        "snapshot_id": "source-watch-1",
        "checked_at": "2026-09-01T00:00:00Z",
        "receipt": {"status": "reviewed"},
        "changed_source_ids": [],
        "unverifiable_source_ids": ["davis-adu-handout-2026"],
        "affected_rule_ids": [],
    }
    result = _result(_adu_facts(), snapshot=snapshot)
    assert result["source_state"]["unverifiable_source_ids"] == [
        "davis-adu-handout-2026"
    ]
    assert any("could not be fetched" in notice for notice in result["notices"])


def test_the_result_carries_no_ranking_field() -> None:
    """Ordering is the rule set's, not a preference. The schema is closed, so a
    ranking field added later fails the checker rather than reaching a consumer."""
    result = _result(_adu_facts())
    schema = _committed("result.schema.json")
    assert schema["additionalProperties"] is False
    assert "rank" not in json.dumps(result)
    assert "score" not in json.dumps(result)


def test_the_schema_version_is_pinned_to_its_literal() -> None:
    """A property test cannot catch a wrong constant; this publishes a number."""
    assert SCHEMA_VERSION == 1
    assert (
        _committed("result.schema.json")["properties"]["schema_version"]["const"] == 1
    )
    assert DECISION_BOUNDARIES == ("candidate_rules_only", "needs_staff_review")


# --- the rule-set fingerprint ------------------------------------------------


def _rule(rule_id: str, value: str = "adu") -> Rule:
    return Rule(
        rule_id=rule_id,
        pathway="p",
        route_class="ministerial",
        jurisdiction_scope="statewide",
        criteria=[{"field": "project_type", "op": "eq", "value": value}],
        citation=Citation(source="s", url="u"),
        source_dependencies=[],
        display_group="route",
    )


def test_the_fingerprint_moves_when_a_criterion_moves() -> None:
    before = rules_fingerprint([_rule("a"), _rule("b")])
    after = rules_fingerprint([_rule("a"), _rule("b", value="jadu")])
    assert before != after


def test_the_fingerprint_does_not_move_when_rule_order_does() -> None:
    assert rules_fingerprint([_rule("a"), _rule("b")]) == rules_fingerprint(
        [_rule("b"), _rule("a")]
    )


def test_the_fingerprint_is_a_sha256_string() -> None:
    fingerprint = rules_fingerprint([_rule("a")])
    assert fingerprint.startswith("sha256:")
    assert len(fingerprint) == len("sha256:") + 64


# --- fail-closed input validation --------------------------------------------


def test_an_unknown_value_names_the_field_and_what_it_accepts() -> None:
    with pytest.raises(FactsDocumentError) as caught:
        validate_facts_document(
            {**_adu_facts(), "project_type": "adu", "sf_zone": "maybe"}
        )
    reasons = " ".join(caught.value.reasons)
    assert "sf_zone" in reasons
    assert "'yes', 'no', 'unknown'" in reasons.replace('"', "'")


def test_an_unknown_field_is_refused_rather_than_ignored() -> None:
    with pytest.raises(FactsDocumentError) as caught:
        validate_facts_document({**_adu_facts(), "lot_has_a_nice_view": "yes"})
    assert "lot_has_a_nice_view" in " ".join(caught.value.reasons)


def test_a_fact_that_does_not_apply_to_this_project_type_is_refused() -> None:
    with pytest.raises(FactsDocumentError) as caught:
        validate_facts_document({**_adu_facts(), "sf_zone": "yes"})
    assert "not read for project_type" in " ".join(caught.value.reasons)


def test_every_reason_is_reported_not_only_the_first() -> None:
    with pytest.raises(FactsDocumentError) as caught:
        validate_facts_document({"project_type": "shed", "adu_project_form": "wrong"})
    assert len(caught.value.reasons) >= 3
