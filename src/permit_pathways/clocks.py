"""Statutory review-clock calculator.

Computes the deadlines State ADU Law and SB 9 impose on permitting
agencies, so an applicant (or staff) can see exactly where an application
stands. Encodes:

- Gov. Code § 66317(a)(2)(A): written completeness determination within
  15 BUSINESS days of receipt (ADU/JADU).
- Gov. Code § 66317(a)(2)(F): the application is DEEMED COMPLETE if no
  timely written determination is made.
- Gov. Code §§ 66317(a)(3), 66335(a)(3): approve or deny within 60
  CALENDAR days of a complete application (existing SF/MF dwelling on
  the lot); same 60-day clock for SB 9 (§§ 65852.21, 66411.7 per the
  April 2026 HCD fact sheet).

Business days exclude weekends and California state holidays (Gov. Code
§ 6700 list, as observed by state offices: Saturday holidays shift to
Friday, Sunday holidays to Monday). Jurisdictions may observe additional
local holidays — a deployment should confirm the local calendar; the
state list is the floor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

COMPLETENESS_BUSINESS_DAYS = 15   # § 66317(a)(2)(A)
DECISION_CALENDAR_DAYS = 60       # §§ 66317(a)(3), 66335(a)(3); SB 9


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    d = date(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d: date) -> date:
    if d.weekday() == 5:            # Saturday -> Friday
        return d - timedelta(days=1)
    if d.weekday() == 6:            # Sunday -> Monday
        return d + timedelta(days=1)
    return d


def ca_holidays(year: int) -> set[date]:
    """California state holidays per Gov. Code § 6700 as observed by state
    offices (including the day after Thanksgiving)."""
    thanksgiving = _nth_weekday(year, 11, 3, 4)
    fixed = [date(year, 1, 1), date(year, 3, 31), date(year, 7, 4),
             date(year, 11, 11), date(year, 12, 25)]
    floating = [
        _nth_weekday(year, 1, 0, 3),   # Martin Luther King Jr. Day
        _nth_weekday(year, 2, 0, 3),   # Presidents' Day
        _last_weekday(year, 5, 0),     # Memorial Day
        _nth_weekday(year, 9, 0, 1),   # Labor Day
        thanksgiving,
        thanksgiving + timedelta(days=1),  # day after Thanksgiving
    ]
    return {_observed(d) for d in fixed} | set(floating)


def add_business_days(start: date, days: int,
                      holidays: set[date] | None = None) -> date:
    if holidays is None:
        holidays = ca_holidays(start.year) | ca_holidays(start.year + 1)
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in holidays:
            remaining -= 1
    return current


@dataclass(frozen=True)
class ClockStatus:
    received: date
    completeness_deadline: date       # written determination due
    deemed_complete_if_silent: date   # day after deadline passes with no notice
    decision_deadline_if_complete: date

    def summary(self) -> str:
        return "\n".join([
            f"Application received:            {self.received.isoformat()}",
            f"Completeness notice due by:      {self.completeness_deadline.isoformat()}"
            "  (Gov. Code § 66317(a)(2)(A), 15 business days)",
            f"Deemed complete if no notice by: {self.deemed_complete_if_silent.isoformat()}"
            "  (Gov. Code § 66317(a)(2)(F))",
            f"Decision due (once complete):    {self.decision_deadline_if_complete.isoformat()}"
            "  (Gov. Code § 66317(a)(3), 60 days)",
        ])


def adu_clocks(received: date) -> ClockStatus:
    completeness = add_business_days(received, COMPLETENESS_BUSINESS_DAYS)
    return ClockStatus(
        received=received,
        completeness_deadline=completeness,
        deemed_complete_if_silent=completeness + timedelta(days=1),
        decision_deadline_if_complete=received + timedelta(days=DECISION_CALENDAR_DAYS),
    )
