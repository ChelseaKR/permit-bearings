from datetime import date

import pytest

from permit_pathways.clocks import (
    add_business_days,
    adu_clocks,
    completeness_deadline,
)


def test_business_days_require_and_use_the_agency_calendar():
    assert add_business_days(date(2026, 8, 3), 5, set()) == date(2026, 8, 10)
    assert add_business_days(
        date(2026, 8, 3),
        5,
        {date(2026, 8, 7)},
    ) == date(2026, 8, 11)
    with pytest.raises(TypeError):
        add_business_days(date(2026, 8, 3), 5)


def test_completeness_deadline_is_unknown_without_agency_closures():
    deadline = completeness_deadline(date(2026, 8, 3))
    assert deadline.status == "unknown"
    assert deadline.date is None
    assert "agency" in deadline.reason

    status = adu_clocks(date(2026, 8, 3))
    assert status.completeness_notice.status == "unknown"
    assert status.deemed_complete_if_silent.status == "unknown"
    assert status.decision_if_complete.status == "unknown"


def test_exact_dates_require_explicit_calendar_and_project_conditions():
    status = adu_clocks(
        date(2026, 8, 3),
        set(),
        complete_on_receipt=True,
        existing_dwelling=True,
    )
    assert status.completeness_notice.date == date(2026, 8, 24)
    assert status.deemed_complete_if_silent.date == date(2026, 8, 25)
    assert status.decision_if_complete.date == date(2026, 10, 2)
    assert "Completeness notice deadline: 2026-08-24" in status.summary()


def test_saturday_closure_is_not_invented_as_a_friday_closure():
    # The supplied agency calendar contains only the actual Saturday closure.
    # The calculator must not manufacture a Friday observance.
    assert add_business_days(
        date(2026, 6, 29),
        5,
        {date(2026, 7, 4)},
    ) == date(2026, 7, 6)
    assert add_business_days(
        date(2026, 6, 29),
        5,
        {date(2026, 7, 3)},
    ) == date(2026, 7, 7)


def test_60_day_clock_does_not_assume_completeness_or_existing_dwelling():
    no_completion = adu_clocks(
        date(2026, 8, 3),
        set(),
        existing_dwelling=True,
    )
    assert no_completion.decision_if_complete.status == "unknown"
    assert "complete-application date" in no_completion.decision_if_complete.reason

    no_existing_dwelling = adu_clocks(
        date(2026, 8, 3),
        set(),
        complete_on_receipt=True,
    )
    assert no_existing_dwelling.decision_if_complete.status == "unknown"
    assert "existing" in no_existing_dwelling.decision_if_complete.reason
