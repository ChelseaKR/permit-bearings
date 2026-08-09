from pathlib import Path

import pytest

from permit_pathways.jurisdictions import (
    COVERAGE_INDEX_SCHEMA_VERSION,
    build_coverage_index,
    coverage,
    load_registry,
)
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
    # Full HAU letter dataset: 470 jurisdictions have letter history.
    assert cov.with_hcd_letters == 470


def test_full_hau_dataset_is_complete_and_matched(registry):
    import json

    data = json.loads((DATA / "jurisdictions" / "hcd-letters.json").read_text())
    assert data["letter_count"] == 1314
    assert data["retrieved_on"] == "2026-08-03"
    assert data["_unmatched"] == {}
    # The Santa Clara County findings letter used to validate the
    # conformance scanner appears in HCD's own dataset.
    urls = [r["url"] or "" for r in data["letters"]["santa-clara-county"]]
    assert any("santa-clara-cou-adu-sb-9-findings" in u for u in urls)
    # The refresh added Grover Beach to the statewide coverage surface.
    assert data["letters"]["grover-beach"][0]["hau_number"] == "HAU0003468"


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


def test_coverage_index_keeps_statewide_and_local_coverage_separate(registry):
    index = build_coverage_index(
        DATA / "jurisdictions" / "registry.json",
        DATA / "rules",
        DATA / "jurisdictions" / "hcd-letters.json",
    )

    assert index["schema_version"] == COVERAGE_INDEX_SCHEMA_VERSION
    assert len(index["statewide_rule_ids"]) == 17
    assert index["statewide_rule_ids"] == sorted(index["statewide_rule_ids"])
    assert set(index["profiles"]) == {jurisdiction.slug for jurisdiction in registry}
    by_slug = {jurisdiction.slug: jurisdiction for jurisdiction in registry}
    assert index["profiles"]["davis"] == {
        "local_rule_ids": ["davis-local-adu-process"],
        "hcd_record_count": len(by_slug["davis"].hcd_letters),
    }
    assert index["profiles"]["woodland"] == {
        "local_rule_ids": ["woodland-adu-ordinance-2026"],
        "hcd_record_count": len(by_slug["woodland"].hcd_letters),
    }
    assert index["profiles"]["eureka"]["local_rule_ids"] == []
    assert set(index["hcd_dataset"]) == {
        "retrieved_on",
        "letter_count",
        "source",
        "statewide_record_count",
        "unmatched_record_count",
    }
    assert index["hcd_dataset"]["retrieved_on"] == "2026-08-03"
    assert index["hcd_dataset"]["letter_count"] == 1314
    assert index["hcd_dataset"]["statewide_record_count"] == 2
    assert index["hcd_dataset"]["unmatched_record_count"] == 0


def test_coverage_index_rejects_unknown_local_rule_scope(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        '{"jurisdictions":[{"slug":"known-city","name":"Known City",'
        '"kind":"city","county":"Example County"}]}',
        encoding="utf-8",
    )
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "local.json").write_text(
        '[{"rule_id":"unknown-scope-rule","jurisdiction_scope":"missing-city"}]',
        encoding="utf-8",
    )
    letters_path = tmp_path / "hcd-letters.json"
    letters_path.write_text(
        '{"retrieved_on":"2026-08-03","letter_count":0,'
        '"source":"Official test dataset","letters":{},'
        '"_statewide":[],"_unmatched":{}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"unknown local rule scope.*missing-city"):
        build_coverage_index(registry_path, rules_dir, letters_path)
    with pytest.raises(ValueError, match=r"unknown local rule scope.*missing-city"):
        load_registry(registry_path, rules_dir, letters_path)


@pytest.mark.parametrize(
    ("retrieved_on", "message"),
    [
        ("not-a-date", "expected an ISO calendar date"),
        ("9999-01-01", "cannot be in the future"),
    ],
)
def test_coverage_index_rejects_invalid_hcd_retrieval_date(
    tmp_path, retrieved_on, message
):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        '{"jurisdictions":[{"slug":"known-city","name":"Known City",'
        '"kind":"city","county":"Example County"}]}',
        encoding="utf-8",
    )
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "statewide.json").write_text(
        '[{"rule_id":"statewide-rule","jurisdiction_scope":"statewide"}]',
        encoding="utf-8",
    )
    letters_path = tmp_path / "hcd-letters.json"
    letters_path.write_text(
        f'{{"retrieved_on":"{retrieved_on}","letter_count":0,'
        '"source":"Official test dataset","letters":{},'
        '"_statewide":[],"_unmatched":{}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=message):
        build_coverage_index(registry_path, rules_dir, letters_path)
