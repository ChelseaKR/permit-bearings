import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.screening import Citation, PathwayResult, Rule, load_rules


def _valid_rule(rule_id: str = "test-rule") -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "pathway": "Test pathway",
        "route_class": "ministerial",
        "jurisdiction_scope": "statewide",
        "criteria": [{"field": "project_type", "op": "eq", "value": "adu"}],
        "citation": {
            "source": "Test source",
            "url": "https://example.gov/source",
            "excerpt": "Supporting text.",
            "excerpt_sha256": "a" * 64,
            "verified_on": "2026-01-01",
        },
        "source_dependencies": ["test-source"],
        "display_group": "route",
        "required_documents": ["Application"],
        "notes": "Test-only rule.",
    }


def _write(tmp_path: Path, payload: Any) -> Path:
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rule_id", "Bad ID"),
        ("route_class", "automatic"),
        ("jurisdiction_scope", "Bad Scope"),
        ("display_group", "other"),
        ("source_dependencies", []),
        ("source_dependencies", ["Bad Source"]),
        ("source_dependencies", ["test-source", "test-source"]),
        ("criteria", []),
        ("citation", "not-an-object"),
        ("required_documents", "Application"),
        ("required_documents", ["Application", "Application"]),
        ("notes", ""),
    ],
)
def test_rule_schema_rejects_invalid_top_level_values(
    tmp_path: Path, field: str, value: Any
) -> None:
    record = _valid_rule()
    record[field] = value
    with pytest.raises(ValueError):
        load_rules(_write(tmp_path, [record]), today=date(2026, 7, 30))


@pytest.mark.parametrize(
    "criterion",
    [
        "not-an-object",
        {"field": "project_type", "op": "eq"},
        {"field": "project_type", "op": "eq", "value": "adu", "extra": True},
        {"field": "Bad Field", "op": "eq", "value": "adu"},
        {"field": "project_type", "op": "contains", "value": "adu"},
        {"field": "project_type", "op": "eq", "value": {"nested": True}},
        {"field": "project_type", "op": "eq", "value": " "},
        {"field": "project_type", "op": "eq", "value": 1.5},
        {"field": "project_type", "op": "in", "value": []},
        {"field": "project_type", "op": "in", "value": [["adu"]]},
        {"field": "project_type", "op": "in", "value": ["adu", " "]},
        {"field": "project_type", "op": "in", "value": ["adu", 1]},
        {"field": "project_type", "op": "in", "value": ["adu", "adu"]},
        {"field": "units", "op": "lte", "value": 1.5},
        {"field": "units", "op": "gte", "value": 2**54},
    ],
)
def test_rule_schema_rejects_invalid_criteria(tmp_path: Path, criterion: Any) -> None:
    record = _valid_rule()
    record["criteria"] = [criterion]
    with pytest.raises(ValueError):
        load_rules(_write(tmp_path, [record]), today=date(2026, 7, 30))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("url", "http://example.gov/source"),
        ("url", "https://user@example.gov/source"),
        ("excerpt_sha256", "not-a-digest"),
        ("verified_on", "2026/01/01"),
        ("verified_on", "2026-02-30"),
        ("verified_on", "2027-01-01"),
    ],
)
def test_rule_schema_rejects_invalid_citation_values(
    tmp_path: Path, field: str, value: Any
) -> None:
    record = _valid_rule()
    record["citation"][field] = value
    with pytest.raises(ValueError):
        load_rules(_write(tmp_path, [record]), today=date(2026, 7, 30))


def test_rule_schema_rejects_dated_citation_without_excerpt(tmp_path: Path) -> None:
    record = _valid_rule()
    record["citation"]["excerpt"] = None
    with pytest.raises(ValueError, match="dated evidence requires an excerpt"):
        load_rules(_write(tmp_path, [record]), today=date(2026, 7, 30))


def test_rule_loader_rejects_structural_failures(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(ValueError, match="no rule files"):
        load_rules(empty_dir)

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="could not be loaded"):
        load_rules(malformed)

    with pytest.raises(ValueError, match="expected a list"):
        load_rules(_write(tmp_path, {"rules": []}))
    with pytest.raises(ValueError, match="expected an object"):
        load_rules(_write(tmp_path, ["rule"]))


def test_rule_loader_rejects_unknown_missing_and_duplicate_records(
    tmp_path: Path,
) -> None:
    unknown = _valid_rule()
    unknown["unexpected"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        load_rules(_write(tmp_path, [unknown]))

    missing = _valid_rule()
    del missing["notes"]
    with pytest.raises(ValueError, match="missing fields"):
        load_rules(_write(tmp_path, [missing]))

    first = _valid_rule()
    duplicate = deepcopy(first)
    with pytest.raises(ValueError, match="duplicate rule ID"):
        load_rules(_write(tmp_path, [first, duplicate]))


def test_citation_currency_and_result_summary_boundaries() -> None:
    undated = Citation("Source", "https://example.gov")
    assert undated.is_stale(180, date(2026, 7, 30))
    with pytest.raises(ValueError, match="non-negative"):
        undated.is_stale(-1, date(2026, 7, 30))

    future = Citation("Source", "https://example.gov", verified_on="2026-08-01")
    assert future.is_stale(180, date(2026, 7, 30))

    rule = Rule(
        rule_id="summary-rule",
        pathway="Summary pathway",
        route_class="ministerial",
        jurisdiction_scope="statewide",
        criteria=[{"field": "project_type", "op": "unsupported", "value": "adu"}],
        citation=undated,
        source_dependencies=["source"],
        display_group="route",
    )
    assert not rule.matches({"project_type": "adu"})
    assert "NO DATED SOURCE RECORD" in PathwayResult(rule, False).summary()
