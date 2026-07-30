"""Conservative statutory review-clock calculations.

Gov. Code §§ 66317(a)(2) and 66335(a)(2) use a 15-business-day
completeness-notice period. The relevant agency calendar controls which
weekdays are full-day closures. A statewide holiday approximation is not an
agency calendar, so this module returns an explicit unknown state unless a
deployment supplies that calendar.

The 60-calendar-day ADU decision clock is separately conditioned on a
complete application and an existing qualifying dwelling. The helper never
silently treats the receipt date as the completion date.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal, cast

COMPLETENESS_BUSINESS_DAYS = 15
DECISION_CALENDAR_DAYS = 60


@dataclass(frozen=True)
class CalendarDeadline:
    """A deadline with an explicit exact-or-unknown evidence state."""

    status: Literal["unknown", "exact"]
    date: date | None
    reason: str

    def __post_init__(self) -> None:
        if self.status not in ("unknown", "exact"):
            raise ValueError(f"unknown deadline status {self.status!r}")
        if self.status == "exact" and self.date is None:
            raise ValueError("exact deadline requires a date")
        if self.status == "unknown" and self.date is not None:
            raise ValueError("unknown deadline cannot carry a date")
        if not self.reason.strip():
            raise ValueError("deadline reason cannot be blank")


def add_business_days(
    start: date,
    days: int,
    agency_closures: set[date],
) -> date:
    """Add weekdays using an explicitly supplied agency closure calendar."""

    if days < 0:
        raise ValueError("days must be non-negative")
    if not isinstance(agency_closures, set) or any(
        not isinstance(closure, date) for closure in agency_closures
    ):
        raise ValueError("agency_closures must be a set of dates")
    current = start
    remaining = days
    while remaining:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in agency_closures:
            remaining -= 1
    return current


def completeness_deadline(
    received: date,
    agency_closures: set[date] | None = None,
) -> CalendarDeadline:
    """Return an exact deadline only with the relevant agency calendar."""

    if agency_closures is None:
        return CalendarDeadline(
            status="unknown",
            date=None,
            reason=(
                "Exact date requires the permitting agency's full-day closure calendar."
            ),
        )
    return CalendarDeadline(
        status="exact",
        date=add_business_days(
            received,
            COMPLETENESS_BUSINESS_DAYS,
            agency_closures,
        ),
        reason=(
            "Calculated from weekends and the supplied agency full-day "
            "closure calendar."
        ),
    )


@dataclass(frozen=True)
class ClockStatus:
    received: date
    completeness_notice: CalendarDeadline
    deemed_complete_if_silent: CalendarDeadline
    decision_if_complete: CalendarDeadline

    @property
    def completeness_deadline(self) -> CalendarDeadline:
        """Compatibility name with an explicit deadline state."""

        return self.completeness_notice

    @property
    def decision_deadline_if_complete(self) -> CalendarDeadline:
        """Compatibility name with an explicit deadline state."""

        return self.decision_if_complete

    def summary(self) -> str:
        def line(label: str, deadline: CalendarDeadline) -> str:
            value = (
                cast(date, deadline.date).isoformat()
                if deadline.status == "exact"
                else "unknown"
            )
            return f"{label}: {value} — {deadline.reason}"

        return "\n".join(
            [
                f"Application received: {self.received.isoformat()}",
                line("Completeness notice deadline", self.completeness_notice),
                line(
                    "Deemed complete if no timely notice",
                    self.deemed_complete_if_silent,
                ),
                line(
                    "60-day decision deadline",
                    self.decision_if_complete,
                ),
            ]
        )


def adu_clocks(
    received: date,
    agency_closures: set[date] | None = None,
    *,
    complete_on_receipt: bool = False,
    existing_dwelling: bool = False,
) -> ClockStatus:
    """Calculate only deadlines supported by supplied project facts.

    ``complete_on_receipt`` must be explicitly true before the receipt date
    is used as the complete-application date. A correction or resubmittal
    workflow needs its recorded completion event and should calculate
    ``complete_date + 60 days`` directly.
    """

    completeness = completeness_deadline(received, agency_closures)
    if completeness.status == "exact":
        completeness_date = cast(date, completeness.date)
        deemed = CalendarDeadline(
            status="exact",
            date=completeness_date + timedelta(days=1),
            reason=(
                "The application is deemed complete after the timely-notice "
                "deadline passes without a notice."
            ),
        )
    else:
        deemed = CalendarDeadline(
            status="unknown",
            date=None,
            reason=(
                "This date cannot be shown until the completeness-notice "
                "deadline is known."
            ),
        )

    if not complete_on_receipt:
        decision = CalendarDeadline(
            status="unknown",
            date=None,
            reason=(
                "A recorded complete-application date is required before "
                "the 60-day clock can be calculated."
            ),
        )
    elif not existing_dwelling:
        decision = CalendarDeadline(
            status="unknown",
            date=None,
            reason=(
                "The encoded 60-day ADU clock applies only when an existing "
                "single-family or multifamily dwelling is on the lot."
            ),
        )
    else:
        decision = CalendarDeadline(
            status="exact",
            date=received + timedelta(days=DECISION_CALENDAR_DAYS),
            reason=(
                "Calculated from the asserted complete-on-receipt date and "
                "existing-dwelling condition."
            ),
        )

    return ClockStatus(
        received=received,
        completeness_notice=completeness,
        deemed_complete_if_silent=deemed,
        decision_if_complete=decision,
    )
