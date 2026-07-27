from datetime import date
from pathlib import Path

from permit_pathways.harness import verify_rules

DATA = Path(__file__).parent.parent / "data"


def test_report_flags_placeholder_rules_and_passes_golden():
    report = verify_rules(
        DATA / "rules" / "statewide.json",
        DATA / "golden" / "example.json",
        today=date(2026, 7, 27),
    )
    # Placeholder rules have never been verified against their sources,
    # so the harness must refuse to call the rule base trustworthy.
    assert set(report.unverified) == {
        "adu-ministerial-placeholder",
        "sb9-two-unit-placeholder",
    }
    assert not report.trustworthy
    # But the golden pathway expectations themselves hold.
    assert report.golden_failed == []
    assert set(report.golden_passed) == {"adu-basic", "sb9-duplex"}
