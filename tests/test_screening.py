from pathlib import Path

import pytest

from permit_pathways.screening import load_rules, screen

RULES = Path(__file__).parent.parent / "data" / "rules"

ADU_INTAKE = {
    "project_type": "adu",
    "has_primary_dwelling": True,
    "jurisdiction": "example-city",
}


@pytest.fixture()
def rules():
    return load_rules(RULES)


def test_adu_intake_matches_adu_rules(rules):
    results = screen(ADU_INTAKE, rules)
    assert {r.rule.rule_id for r in results} == {
        "adu-ministerial-review",
        "adu-protected-minimum",
        "adu-height-standards",
    }


def test_statewide_rules_are_verified_and_cited(rules):
    for rule in rules:
        if rule.jurisdiction_scope == "statewide":
            assert rule.citation.is_verified, rule.rule_id
            assert rule.citation.excerpt, rule.rule_id
    results = screen(ADU_INTAKE, rules)
    assert all(r.verified for r in results)
    assert "verified" in results[0].summary()


def test_davis_intake_includes_local_layer_flagged_unverified(rules):
    results = screen({**ADU_INTAKE, "jurisdiction": "davis"}, rules)
    by_id = {r.rule.rule_id: r for r in results}
    assert "davis-local-adu-process" in by_id
    assert not by_id["davis-local-adu-process"].verified


def test_sb9_exclusion_screens_out_tenant_occupied(rules):
    intake = {
        "project_type": "two_unit",
        "zone_class": "single_family_residential",
        "in_urbanized_area": True,
        "demolishes_protected_housing": False,
        "tenant_occupied_last_3_years": True,
        "in_historic_district": False,
        "on_protected_site": False,
        "jurisdiction": "example-city",
    }
    assert screen(intake, rules) == []


def test_non_matching_intake_returns_nothing(rules):
    assert screen({"project_type": "hotel", "jurisdiction": "example-city"}, rules) == []
