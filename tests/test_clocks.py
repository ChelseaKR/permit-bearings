from datetime import date

from permit_pathways.clocks import add_business_days, adu_clocks


def test_business_days_skip_weekends():
    # Mon 2026-08-03 + 5 business days = Mon 2026-08-10
    assert add_business_days(date(2026, 8, 3), 5) == date(2026, 8, 10)


def test_adu_clock_deadlines():
    # Received Mon 2026-08-03: 15 business days later is Mon 2026-08-24.
    status = adu_clocks(date(2026, 8, 3))
    assert status.completeness_deadline == date(2026, 8, 24)
    assert status.deemed_complete_if_silent == date(2026, 8, 25)
    assert status.decision_deadline_if_complete == date(2026, 10, 2)
    summary = status.summary()
    assert "66317(a)(2)(A)" in summary
    assert "Deemed complete" in summary
