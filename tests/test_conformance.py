import json
from pathlib import Path

import pytest

from permit_pathways.conformance import Check, load_checks, main, scan

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
        assert not missing, f"{provision['hcd_finding']}: scanner missed {missing}"


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


def test_lawful_proposed_multifamily_two_adu_cap_is_not_flagged(checks):
    text = (
        "On a lot with a proposed multifamily dwelling, no more than two "
        "detached accessory dwelling units are allowed."
    )
    assert "unit-count-undercount" not in {
        finding.check.check_id for finding in scan(text, checks)
    }


def test_privacy_word_alone_is_not_treated_as_subjective(checks):
    text = (
        "For an accessory dwelling unit, a privacy window shall have a "
        "minimum sill height of five feet above finished floor."
    )
    assert "subjective-design-standard" not in {
        finding.check.check_id for finding in scan(text, checks)
    }


def test_qualitative_privacy_language_remains_a_review_signal(checks):
    text = (
        "An accessory dwelling unit shall preserve the privacy of neighboring "
        "properties."
    )
    assert "subjective-design-standard" in {
        finding.check.check_id for finding in scan(text, checks)
    }


def test_height_check_describes_roof_pitch_as_transit_specific(checks):
    check = next(
        check for check in checks if check.check_id == "height-cap-below-state"
    )
    assert "transit branch" in check.state_law
    assert "multistory-multifamily branch does not carry" in check.explanation


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
        j["slug"]
        for j in json.loads(
            (DATA.parent / "jurisdictions" / "registry.json").read_text()
        )["jurisdictions"]
    }
    assert index, "at least one ordinance scan is committed"
    for slug, meta in index.items():
        assert slug in registry_slugs
        rec = json.loads((results_dir / f"{slug}.json").read_text())
        assert rec["source"]["url"]
        assert len(rec["findings"]) == meta["findings"]
        for f in rec["findings"]:
            assert f["check_id"] in check_ids


def test_no_published_finding_disagrees_with_the_check_that_produced_it(checks):
    """No published text may disagree with `checks.json`.

    Each result denormalises `title`, `state_law` and `hcd_precedent` out of
    the check it matched. Editing a check without rescanning leaves a dated,
    jurisdiction-named artifact stating something the checks no longer say —
    which is what happened between 2026-07-27 and 2026-07-28, and what the
    browser served afterwards. Shape validation does not catch it: the
    finding count and check IDs stayed correct the whole time.
    """
    by_id = {check.check_id: check for check in checks}
    results_dir = DATA / "results"
    published = sorted(results_dir.glob("*.json"))
    compared = 0
    for path in published:
        if path.name == "index.json":
            continue
        record = json.loads(path.read_text())
        for finding in record["findings"]:
            check = by_id[finding["check_id"]]
            assert finding["title"] == check.title, path.name
            assert finding["state_law"] == check.state_law, path.name
            assert finding["hcd_precedent"] == check.hcd_precedent, path.name
            assert finding["severity"] == check.severity, path.name
            compared += 1
    assert compared, "at least one published finding is compared"


def test_published_scan_artifacts_match_a_fresh_scan():
    """The whole artifact, not just its denormalised strings.

    `--check` is the gate wired into `make bundle-check`; this runs the same
    derivation under pytest so the parity failure is visible in the test run
    too. Each committed `scanned_on` is reused, so a date is never reported
    as drift.
    """
    from scripts.scan_ordinances import build_results, committed_scan_dates

    dates = committed_scan_dates()
    assert dates, "at least one ordinance scan is committed"
    expected = build_results(lambda slug: dates[slug])
    for path, content in expected.items():
        assert path.exists(), f"{path.name}: published result missing"
        assert path.read_text() == content, (
            f"{path.name}: published artifact differs from a fresh scan of the "
            f"committed corpus; rerun scripts/scan_ordinances.py <date>"
        )


def test_scan_check_mode_fails_when_a_published_result_drifts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The gate must fail on drift, not merely run.

    This is the exact 2026-07-28 edit: `state_law` rewritten in
    `checks.json` while the published result keeps the old wording. The
    finding set, severity and excerpt are untouched, so a shape check still
    passes and only a parity check catches it.
    """
    from scripts.scan_ordinances import check_published

    staged = tmp_path / "results"
    staged.mkdir()
    for path in (DATA / "results").glob("*.json"):
        (staged / path.name).write_text(path.read_text())
    assert check_published(staged) == 0, capsys.readouterr().out
    capsys.readouterr()

    published = staged / "san-diego.json"
    stale = json.loads(published.read_text())
    stale["findings"][0]["state_law"] = "the superseded 2026-07-27 wording"
    published.write_text(json.dumps(stale, indent=1) + "\n")

    assert check_published(staged) == 1
    output = capsys.readouterr().out
    assert "drifted" in output
    assert "findings[0].state_law" in output


def test_san_diego_scan_reproduces():
    from permit_pathways.conformance import scan_file

    root = Path(__file__).parent.parent
    findings = scan_file(
        root / "corpus" / "ordinances" / "san-diego.txt", DATA / "checks.json"
    )
    # One review flag: the 1,200 sq ft detached-ADU size cap — the same
    # failure pattern as HCD's Santa Clara County Finding 7.
    assert [f.check.check_id for f in findings] == ["size-cap-conflict"]


def test_exclusion_context_and_duplicate_span_controls() -> None:
    excluded = Check(
        check_id="excluded",
        title="Excluded match",
        severity="review",
        patterns=[r"65852"],
        state_law="State law",
        explanation="Explanation",
        hcd_precedent="Precedent",
        exclude_patterns=[r"Section 65852\.21"],
    )
    assert scan("Section 65852.21", [excluded]) == []

    contextual = Check(
        check_id="contextual",
        title="Contextual match",
        severity="review",
        patterns=[r"1,200 square feet", r"square feet"],
        state_law="State law",
        explanation="Explanation",
        hcd_precedent="Precedent",
        context_patterns=[r"accessory dwelling"],
    )
    assert scan("A warehouse may be 1,200 square feet.", [contextual]) == []
    findings = scan(
        "An accessory dwelling unit may be limited to 1,200 square feet.",
        [contextual],
    )
    assert len(findings) == 1
    assert findings[0].check.check_id == "contextual"


def test_conformance_cli_reports_quiet_and_flagged_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checks_path = tmp_path / "checks.json"
    checks_path.write_text(
        json.dumps(
            [
                {
                    "check_id": "height",
                    "title": "Height cap",
                    "severity": "definite",
                    "patterns": ["sixteen feet"],
                    "state_law": "State law permits more.",
                    "explanation": "Review the cap.",
                    "hcd_precedent": "Example precedent.",
                }
            ]
        )
    )

    ordinance = tmp_path / "ordinance.txt"
    ordinance.write_text("No candidate language.", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["permit_pathways.conformance", str(ordinance), "--checks", str(checks_path)],
    )
    assert main() == 0
    assert "No candidate provisions flagged" in capsys.readouterr().out

    ordinance.write_text("The maximum height is sixteen feet.", encoding="utf-8")
    assert main() == 2
    output = capsys.readouterr().out
    assert "1 provision(s) flagged" in output
    assert "[FINDING] Height cap" in output
