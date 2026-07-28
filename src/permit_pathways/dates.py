"""Shared calendar-date defaults.

Currency checks compare date-only source metadata. Resolve an omitted date
against UTC so the Python and browser runtimes do not disagree near midnight
in the host machine's local timezone.
"""

from __future__ import annotations

from datetime import date, datetime, timezone


def utc_today() -> date:
    """Return the current UTC calendar date."""

    return datetime.now(timezone.utc).date()


def resolve_today(value: date | None) -> date:
    """Use an injected date when supplied, otherwise the UTC calendar date."""

    return value if value is not None else utc_today()
