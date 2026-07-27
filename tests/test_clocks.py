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


def test_ca_holidays_2026():
    from permit_pathways.clocks import ca_holidays
    h = ca_holidays(2026)
    assert date(2026, 1, 1) in h            # New Year's (Thursday)
    assert date(2026, 1, 19) in h           # MLK Day, 3rd Monday
    assert date(2026, 3, 31) in h           # Cesar Chavez Day
    assert date(2026, 5, 25) in h           # Memorial Day, last Monday
    assert date(2026, 7, 3) in h            # July 4 is Saturday -> observed Friday
    assert date(2026, 11, 26) in h and date(2026, 11, 27) in h  # Thanksgiving + day after
    assert date(2026, 12, 25) in h          # Christmas (Friday)


def test_business_days_skip_holidays():
    from permit_pathways.clocks import add_business_days
    # Received Thu 2026-12-24. Excluding weekends, Christmas (Fri 12/25),
    # New Year's (Fri 1/1), and MLK Day (Mon 1/18), the 15th business day
    # is Tue 2027-01-19.
    assert add_business_days(date(2026, 12, 24), 15) == date(2027, 1, 19)
