from pathlib import Path

import pytest

from permit_pathways.screening import load_rules, screen

RULES = Path(__file__).parent.parent / "data" / "rules"

ADU_INTAKE = {
    "project_type": "adu",
    "primary_dwelling_status": "existing_single_family",
    "adu_project_form": "new_detached",
    "unpermitted_existing": "no",
    "jurisdiction": "example-city",
}

ADU_GENERIC_SINGLE_FAMILY = {
    "adu-ministerial-review",
    "adu-protected-minimum",
    "adu-height-standards",
    "adu-size-allowances",
    "adu-parking-limits",
    "adu-no-owner-occupancy-rental",
}


@pytest.fixture()
def rules():
    return load_rules(RULES)


def ids(results):
    return {result.rule.rule_id for result in results}


def sb9_intake(project_type: str, **updates):
    intake = {
        "project_type": project_type,
        "sf_zone": "yes",
        "in_urbanized_area": "yes",
        "demolishes_protected_housing": "no",
        "tenant_occupied_last_3_years": "no",
        "ellis_withdrawal_last_15_years": "no",
        "on_protected_site": "no",
        "jurisdiction": "example-city",
    }
    if project_type == "two_unit":
        intake.update(
            {
                "two_unit_contributing_historic_location": "no",
                "two_unit_individually_listed_historic_property": "no",
            }
        )
    if project_type == "lot_split":
        intake.update(
            {
                "lot_split_on_historic_landmark_site": "no",
                "lot_split_alters_historic_district_resource": "no",
                "parcel_created_by_sb9_split": "no",
                "adjacent_sb9_split_same_actor": "no",
                "proposed_lot_ratio_compliant": "yes",
                "proposed_lot_size_compliant": "yes",
            }
        )
    intake.update(updates)
    return intake


def test_new_detached_adu_does_not_match_conversion_rule(rules):
    assert ids(screen(ADU_INTAKE, rules)) == ADU_GENERIC_SINGLE_FAMILY


@pytest.mark.parametrize("project_form", ["conversion", "same_footprint_rebuild"])
def test_conversion_rule_requires_an_explicit_qualifying_project_form(
    rules, project_form
):
    intake = {**ADU_INTAKE, "adu_project_form": project_form}
    assert ids(screen(intake, rules)) == ADU_GENERIC_SINGLE_FAMILY | {
        "adu-conversion-exemptions"
    }


@pytest.mark.parametrize("project_form", ["new_detached", "new_attached", "unknown"])
def test_nonconversion_and_unknown_forms_do_not_receive_conversion_exemptions(
    rules, project_form
):
    intake = {**ADU_INTAKE, "adu_project_form": project_form}
    assert "adu-conversion-exemptions" not in ids(screen(intake, rules))


def test_unpermitted_adu_and_jadu_have_separate_legalization_routes(rules):
    adu = {
        **ADU_INTAKE,
        "adu_project_form": "conversion",
        "unpermitted_existing": "yes",
    }
    assert "adu-unpermitted-legalization" in ids(screen(adu, rules))
    assert "jadu-unpermitted-legalization" not in ids(screen(adu, rules))

    jadu = {
        "project_type": "jadu",
        "primary_dwelling_status": "existing_single_family",
        "unpermitted_existing": "yes",
        "jurisdiction": "example-city",
    }
    assert ids(screen(jadu, rules)) == {
        "jadu-standards",
        "jadu-ministerial-review",
        "jadu-unpermitted-legalization",
    }


def test_existing_and_proposed_multifamily_branches_do_not_conflate(rules):
    existing = {
        **ADU_INTAKE,
        "primary_dwelling_status": "existing_multifamily",
    }
    proposed = {
        **ADU_INTAKE,
        "primary_dwelling_status": "proposed_multifamily",
    }
    assert "adu-multifamily-66323" in ids(screen(existing, rules))
    assert "adu-multifamily-proposed-66323" not in ids(screen(existing, rules))
    assert "adu-multifamily-proposed-66323" in ids(screen(proposed, rules))
    assert "adu-multifamily-66323" not in ids(screen(proposed, rules))


@pytest.mark.parametrize(
    "primary_status",
    ["unknown", "none", None],
)
def test_missing_or_unknown_primary_dwelling_status_fails_closed(rules, primary_status):
    intake = {**ADU_INTAKE}
    if primary_status is None:
        intake.pop("primary_dwelling_status")
    else:
        intake["primary_dwelling_status"] = primary_status
    assert screen(intake, rules) == []


def test_jadu_requires_an_existing_or_proposed_single_family_home(rules):
    base = {
        "project_type": "jadu",
        "unpermitted_existing": "no",
        "jurisdiction": "example-city",
    }
    for status in ("existing_single_family", "proposed_single_family"):
        assert ids(screen({**base, "primary_dwelling_status": status}, rules)) == {
            "jadu-standards",
            "jadu-ministerial-review",
        }
    for status in (
        "existing_multifamily",
        "proposed_multifamily",
        "none",
        "unknown",
    ):
        assert screen({**base, "primary_dwelling_status": status}, rules) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("sf_zone", "unknown"),
        ("in_urbanized_area", "unknown"),
        ("demolishes_protected_housing", "unknown"),
        ("tenant_occupied_last_3_years", "yes"),
        ("ellis_withdrawal_last_15_years", "yes"),
        ("ellis_withdrawal_last_15_years", "unknown"),
        ("two_unit_contributing_historic_location", "yes"),
        ("two_unit_contributing_historic_location", "unknown"),
        ("two_unit_individually_listed_historic_property", "yes"),
        ("two_unit_individually_listed_historic_property", "unknown"),
        ("on_protected_site", "yes"),
    ],
)
def test_two_unit_route_fails_closed_on_each_exclusion_or_unknown(rules, field, value):
    assert screen(sb9_intake("two_unit", **{field: value}), rules) == []


def test_two_unit_route_matches_only_after_all_material_facts_are_explicit(rules):
    assert ids(screen(sb9_intake("two_unit"), rules)) == {
        "sb9-two-unit-ministerial",
        "sb9-adu-interaction",
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("parcel_created_by_sb9_split", "yes"),
        ("parcel_created_by_sb9_split", "unknown"),
        ("adjacent_sb9_split_same_actor", "yes"),
        ("adjacent_sb9_split_same_actor", "unknown"),
        ("lot_split_on_historic_landmark_site", "yes"),
        ("lot_split_on_historic_landmark_site", "unknown"),
        ("lot_split_alters_historic_district_resource", "yes"),
        ("lot_split_alters_historic_district_resource", "unknown"),
        ("proposed_lot_ratio_compliant", "no"),
        ("proposed_lot_ratio_compliant", "unknown"),
        ("proposed_lot_size_compliant", "no"),
        ("proposed_lot_size_compliant", "unknown"),
    ],
)
def test_lot_split_route_fails_closed_on_each_lot_specific_fact(rules, field, value):
    assert screen(sb9_intake("lot_split", **{field: value}), rules) == []


def test_lot_split_boundary_case_matches_both_route_and_interaction(rules):
    # The intake facts represent the exact statutory boundaries:
    # one result is 40%, and both result parcels meet either the 1,200-sq-ft
    # minimum or a verified smaller minimum in a current local ordinance.
    assert ids(screen(sb9_intake("lot_split"), rules)) == {
        "sb9-urban-lot-split",
        "sb9-lot-split-adu-interaction",
    }


def test_sb9_rules_use_route_specific_historic_fields(rules):
    sb9_fields = {
        criterion["field"]
        for rule in rules
        if rule.rule_id.startswith("sb9-")
        for criterion in rule.criteria
    }
    assert "in_historic_district" not in sb9_fields
    assert "individually_listed_historic" not in sb9_fields


def test_statewide_rules_have_canonical_metadata_and_dated_evidence(rules):
    for rule in rules:
        assert rule.display_group in {"route", "standard", "local_process"}
        assert rule.source_dependencies, rule.rule_id
        if rule.jurisdiction_scope == "statewide":
            assert rule.citation.is_verified, rule.rule_id
            assert rule.citation.excerpt, rule.rule_id


def test_davis_record_is_bounded_to_published_categories_and_dated_evidence(rules):
    results = screen({**ADU_INTAKE, "jurisdiction": "davis"}, rules)
    by_id = {result.rule.rule_id: result for result in results}
    assert "davis-local-adu-process" in by_id
    davis = by_id["davis-local-adu-process"]
    assert davis.verified
    assert davis.rule.route_class == "mixed"
    assert davis.rule.source_dependencies == [
        "davis-adu-handout-2026",
        "hcd-davis-adu-ta-2025",
    ]
    assert davis.rule.required_documents == []
    assert "does not determine which category applies" in davis.rule.notes
    assert "may be outdated, noncompliant, or null and void" in davis.rule.notes


def test_nonmatching_intake_returns_nothing(rules):
    assert (
        screen({"project_type": "hotel", "jurisdiction": "example-city"}, rules) == []
    )
