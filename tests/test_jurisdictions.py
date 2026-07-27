from pathlib import Path

import pytest

from permit_pathways.jurisdictions import coverage, load_registry
from permit_pathways.screening import load_rules, screen

DATA = Path(__file__).parent.parent / "data"


@pytest.fixture()
def registry():
    return load_registry(DATA / "jurisdictions" / "registry.json",
                         DATA / "rules",
                         DATA / "jurisdictions" / "hcd-letters.json")


def test_full_statewide_coverage(registry):
    cov = coverage(registry)
    assert cov.cities == 482
    assert cov.counties == 58
    assert cov.total == 540
    assert cov.local_layers == 2       # davis, woodland
    assert cov.with_hcd_letters >= 7


def test_slugs_are_unique(registry):
    slugs = [j.slug for j in registry]
    assert len(slugs) == len(set(slugs))


def test_local_layer_flags(registry):
    by_slug = {j.slug: j for j in registry}
    assert by_slug["davis"].has_local_layer
    assert by_slug["woodland"].has_local_layer
    assert not by_slug["san-francisco"].has_local_layer
    assert by_slug["santa-clara-county"].hcd_letters


def test_statewide_rules_apply_to_any_registry_jurisdiction(registry):
    # Any jurisdiction in the registry — even with no local layer — gets
    # the full statewide baseline from the screening engine.
    rules = load_rules(DATA / "rules")
    intake = {"project_type": "adu", "has_primary_dwelling": True,
              "jurisdiction": "eureka"}
    results = screen(intake, rules)
    assert len(results) == 7
    assert all(r.rule.jurisdiction_scope == "statewide" for r in results)
