import json
from pathlib import Path

import pytest

from permit_pathways.conformance import load_checks, scan

DATA = Path(__file__).parent.parent / "data" / "conformance"
VALIDATION = json.loads((DATA / "hcd-validation-santa-clara.json").read_text())


@pytest.fixture()
def checks():
    return load_checks(DATA / "checks.json")


def test_scanner_rederives_each_hcd_finding(checks):
    # Every ordinance provision HCD quoted in its June 2025 Santa Clara
    # County findings letter must trigger the corresponding check.
    for provision in VALIDATION["provisions"]:
        found = {f.check.check_id for f in scan(provision["text"], checks)}
        missing = set(provision["expected_checks"]) - found
        assert not missing, (
            f"{provision['hcd_finding']}: scanner missed {missing}"
        )


def test_full_letter_corpus_yields_all_expected_checks(checks):
    corpus = "\n\n".join(p["text"] for p in VALIDATION["provisions"])
    found = {f.check.check_id for f in scan(corpus, checks)}
    expected = {c for p in VALIDATION["provisions"] for c in p["expected_checks"]}
    assert expected <= found


def test_conformant_control_text_is_quiet(checks):
    findings = scan(VALIDATION["control"]["text"], checks)
    assert findings == [], [f.check.check_id for f in findings]


def test_current_sb9_section_never_flagged_as_stale(checks):
    # § 65852.21 is current SB 9 law and must not trip the SB 477
    # stale-citation screen aimed at §§ 65852.2/.22/.26.
    text = "Pursuant to Government Code Section 65852.21, subdivision (a)."
    assert scan(text, checks) == []


def test_finding_summary_carries_state_law_and_precedent(checks):
    findings = scan(VALIDATION["provisions"][0]["text"], checks)
    summary = findings[0].summary()
    assert "SB 477" in summary
    assert "Santa Clara" in summary


def test_committed_scan_results_are_valid(checks):
    import json
    results_dir = DATA / "results"
    index = json.loads((results_dir / "index.json").read_text())
    check_ids = {c.check_id for c in checks}
    registry_slugs = {
        j["slug"] for j in json.loads(
            (DATA.parent / "jurisdictions" / "registry.json").read_text()
        )["jurisdictions"]}
    assert index, "at least one ordinance scan is committed"
    for slug, meta in index.items():
        assert slug in registry_slugs
        rec = json.loads((results_dir / f"{slug}.json").read_text())
        assert rec["source"]["url"]
        assert len(rec["findings"]) == meta["findings"]
        for f in rec["findings"]:
            assert f["check_id"] in check_ids


def test_san_diego_scan_reproduces():
    from permit_pathways.conformance import scan_file
    root = Path(__file__).parent.parent
    findings = scan_file(root / "corpus" / "ordinances" / "san-diego.txt",
                         DATA / "checks.json")
    # One review flag: the 1,200 sq ft detached-ADU size cap — the same
    # failure pattern as HCD's Santa Clara County Finding 7.
    assert [f.check.check_id for f in findings] == ["size-cap-conflict"]
