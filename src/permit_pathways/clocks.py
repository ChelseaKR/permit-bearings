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

California state holidays are not modeled — business days here exclude
weekends only, which is the conservative (earlier) reading for the
agency's deadline. A production deployment should load the jurisdiction's
observed-holiday calendar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

COMPLETENESS_BUSINESS_DAYS = 15   # § 66317(a)(2)(A)
DECISION_CALENDAR_DAYS = 60       # §§ 66317(a)(3), 66335(a)(3); SB 9


def add_business_days(start: date, days: int) -> date:
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
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
