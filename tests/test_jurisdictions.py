from pathlib import Path

import pytest

from permit_pathways.jurisdictions import coverage, load_registry
from permit_pathways.screening import load_rules, screen

DATA = Path(__file__).parent.parent / "data"


@pytest.fixture()
def registry():
    return load_registry(
        DATA / "jurisdictions" / "registry.json",
        DATA / "rules",
        DATA / "jurisdictions" / "hcd-letters.json",
    )


def test_full_statewide_coverage(registry):
    cov = coverage(registry)
    assert cov.cities == 483
    assert cov.counties == 58
    assert cov.total == 541
    assert cov.local_layers == 2  # davis, woodland
    # Full HAU letter dataset: 469 jurisdictions have letter history.
    assert cov.with_hcd_letters >= 400


def test_full_hau_dataset_is_complete_and_matched(registry):
    import json

    data = json.loads((DATA / "jurisdictions" / "hcd-letters.json").read_text())
    assert data["letter_count"] == 1309
    assert data["_unmatched"] == {}
    # The Santa Clara County findings letter used to validate the
    # conformance scanner appears in HCD's own dataset.
    urls = [r["url"] or "" for r in data["letters"]["santa-clara-county"]]
    assert any("santa-clara-cou-adu-sb-9-findings" in u for u in urls)


def test_slugs_are_unique(registry):
    slugs = [j.slug for j in registry]
    assert len(slugs) == len(set(slugs))


def test_local_layer_flags(registry):
    by_slug = {j.slug: j for j in registry}
    assert by_slug["mountain-house"].county == "San Joaquin County"
    assert by_slug["davis"].has_local_layer
    assert by_slug["woodland"].has_local_layer
    assert not by_slug["san-francisco"].has_local_layer
    assert by_slug["santa-clara-county"].hcd_letters


def test_statewide_rules_apply_to_any_registry_jurisdiction(registry):
    # Any jurisdiction in the registry — even with no local layer — gets
    # the full statewide baseline from the screening engine.
    rules = load_rules(DATA / "rules")
    intake = {
        "project_type": "adu",
        "primary_dwelling_status": "existing_single_family",
        "adu_project_form": "new_detached",
        "unpermitted_existing": "no",
        "jurisdiction": "eureka",
    }
    results = screen(intake, rules)
    assert {result.rule.rule_id for result in results} == {
        "adu-ministerial-review",
        "adu-protected-minimum",
        "adu-height-standards",
        "adu-size-allowances",
        "adu-parking-limits",
        "adu-no-owner-occupancy-rental",
    }
    assert all(r.rule.jurisdiction_scope == "statewide" for r in results)
