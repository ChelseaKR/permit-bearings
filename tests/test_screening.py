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


ADU_GENERIC = {
    "adu-ministerial-review", "adu-protected-minimum", "adu-height-standards",
    "adu-size-allowances", "adu-parking-limits", "adu-no-owner-occupancy-rental",
    "adu-conversion-exemptions",
}


def test_adu_intake_matches_adu_rules(rules):
    results = screen(ADU_INTAKE, rules)
    assert {r.rule.rule_id for r in results} == ADU_GENERIC


def test_unpermitted_flag_adds_legalization_pathway(rules):
    results = screen({**ADU_INTAKE, "unpermitted_existing": True}, rules)
    assert {r.rule.rule_id for r in results} == ADU_GENERIC | {
        "adu-unpermitted-legalization"
    }


def test_multifamily_lot_adds_66323_allowances(rules):
    results = screen({**ADU_INTAKE, "dwelling_type": "multifamily"}, rules)
    assert {r.rule.rule_id for r in results} == ADU_GENERIC | {
        "adu-multifamily-66323"
    }


def test_statewide_rules_have_dated_source_evidence_and_citations(rules):
    for rule in rules:
        if rule.jurisdiction_scope == "statewide":
            assert rule.citation.is_verified, rule.rule_id
            assert rule.citation.excerpt, rule.rule_id
    results = screen(ADU_INTAKE, rules)
    assert all(r.verified for r in results)
    assert "dated source record" in results[0].summary()


def test_davis_record_is_flagged_without_dated_source_evidence(rules):
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
