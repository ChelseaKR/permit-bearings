from pathlib import Path

import pytest

from permit_pathways.screening import load_rules, screen

RULES = Path(__file__).parent.parent / "data" / "rules" / "statewide.json"


@pytest.fixture()
def rules():
    return load_rules(RULES)


def test_adu_intake_matches_adu_pathway(rules):
    results = screen(
        {"project_type": "adu", "on_existing_residential_lot": True,
         "jurisdiction": "example-city"},
        rules,
    )
    assert [r.rule.rule_id for r in results] == ["adu-ministerial-placeholder"]


def test_non_matching_intake_returns_nothing(rules):
    results = screen(
        {"project_type": "hotel", "jurisdiction": "example-city"}, rules
    )
    assert results == []


def test_placeholder_rules_surface_as_unverified(rules):
    results = screen(
        {"project_type": "adu", "on_existing_residential_lot": True,
         "jurisdiction": "example-city"},
        rules,
    )
    assert all(not r.verified for r in results)
    assert "UNVERIFIED" in results[0].summary()
