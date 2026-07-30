from datetime import date
from pathlib import Path

from permit_pathways.harness import verify_rules

DATA = Path(__file__).parent.parent / "data"
RULES = DATA / "rules"
GOLDEN = DATA / "golden" / "example.json"
AS_OF = date(2026, 7, 28)


def test_report_is_honest_about_the_unverified_davis_rule():
    report = verify_rules(RULES, GOLDEN, today=AS_OF)
    # Davis's code host blocks automated retrieval, so its local rule ships
    # unverified by design — and the harness must therefore refuse to call
    # the rule base trustworthy, even though every golden case passes.
    assert report.unverified == ["davis-local-adu-process"]
    assert report.stale == []
    assert len(report.verified) == 18
    assert report.golden_failed == []
    assert not report.trustworthy


def test_changed_source_flips_dependent_rules_to_stale():
    # Rehearse a legislative amendment touching Gov. Code § 66321
    # (ADU size/setback/height standards): both dependent rules must go
    # stale; unrelated rules stay verified.
    report = verify_rules(RULES, GOLDEN, today=AS_OF, changed_sources=["ca-gov-66321"])
    assert set(report.stale) == {
        "adu-protected-minimum",
        "adu-height-standards",
        "adu-size-allowances",
        "adu-multifamily-66323",
        "adu-multifamily-proposed-66323",
    }
    assert "sb9-two-unit-ministerial" in report.verified
    assert not report.trustworthy


def test_verification_goes_stale_after_max_age():
    report = verify_rules(RULES, GOLDEN, today=date(2027, 7, 27))
    assert report.verified == []
    assert len(report.stale) == 18


def test_jurisdiction_layers_ride_on_the_statewide_base():
    report = verify_rules(RULES, GOLDEN, today=AS_OF)
    assert {
        "davis-new-detached-adu-local-layer",
        "woodland-new-detached-adu-local-layer",
    } <= set(report.golden_passed)
