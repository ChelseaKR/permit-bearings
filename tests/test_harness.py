from datetime import date
from pathlib import Path

from permit_pathways.harness import verify_rules

DATA = Path(__file__).parent.parent / "data"
RULES = DATA / "rules" / "statewide.json"
GOLDEN = DATA / "golden" / "example.json"
AS_OF = date(2026, 7, 27)


def test_current_rule_base_is_trustworthy():
    report = verify_rules(RULES, GOLDEN, today=AS_OF)
    assert report.unverified == []
    assert report.stale == []
    assert report.golden_failed == []
    assert report.trustworthy


def test_changed_source_flips_dependent_rules_to_stale():
    # Rehearse a legislative amendment touching Gov. Code § 66321
    # (ADU size/setback/height standards): both dependent rules must go
    # stale; unrelated rules stay verified.
    report = verify_rules(RULES, GOLDEN, today=AS_OF,
                          changed_sources=["66321"])
    assert set(report.stale) == {"adu-protected-minimum", "adu-height-standards"}
    assert "sb9-two-unit-ministerial" in report.verified
    assert not report.trustworthy


def test_verification_goes_stale_after_max_age():
    report = verify_rules(RULES, GOLDEN, today=date(2027, 7, 27))
    assert report.verified == []
    assert len(report.stale) == 6
