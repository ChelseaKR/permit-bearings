"""Shared calendar-date defaults.

Currency checks compare date-only source metadata. Resolve an omitted date
against UTC so the Python and browser runtimes do not disagree near midnight
in the host machine's local timezone.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

#: How long a dated source record stays inside the review window.
#:
#: This is the single definition. Every Python runtime imports it, and
#: ``assets/demo.js`` mirrors it as ``MAX_AGE_DAYS``; a contract test asserts
#: the two agree so the browser and the servers cannot drift apart silently.
SOURCE_REVIEW_WINDOW_DAYS = 180  # roughly one legislative cycle between re-checks


def utc_today() -> date:
    """Return the current UTC calendar date."""

    return datetime.now(UTC).date()


def resolve_today(value: date | None) -> date:
    """Use an injected date when supplied, otherwise the UTC calendar date."""

    return value if value is not None else utc_today()
