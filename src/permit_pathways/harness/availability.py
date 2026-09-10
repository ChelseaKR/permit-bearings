"""Advance notice for program-availability records whose reading is about to lapse.

A program-availability record under ``data/availability/`` says that a person
opened a jurisdiction's page on ``checked_on`` and read what its ``excerpt``
says. ``recheck_due_on`` is the date that reading stops counting. Once it
passes, the beta gate appends a reference-currency blocker and the packet
journey closes -- correctly, and with no warning of any kind beforehand.

Measured on 2026-09-09, which is why this module exists: the weekly
``Source currency watch`` ran at 2026-09-07T15:10Z, exited 0 in 21 seconds, and
said nothing about a deadline 33 hours away, because none of its five signals
reads ``data/availability/`` at all. ``grep -rn 'program_availability'
src/permit_pathways/harness/`` returned nothing. A clean report over a record
that was never examined is this repository's own named failure mode, and the
harness argues against it in terms one file over: ``changed_sources`` prints
``not_checked`` rather than ``0`` precisely so a run that checked nothing cannot
look like a run that found nothing.

**The lead time is derived from the workflow's own schedule, not chosen.** A
watch cannot cover a deadline that falls between two of its runs, so the notice
has to reach one interval ahead. That interval is read out of
``.github/workflows/currency.yml`` by walking its cron a year forward and taking
the **longest** gap between consecutive fires -- longest, not nominal, because a
schedule may fire unevenly and a lead time short by a day is a lead time that
misses one deadline in seven. Nothing here hard-codes ``7``: change the cron to
fortnightly and the notice widens with it.

This module reports. It does not renew anything and it does not decide anything:
``monitoring_status: "manual_date_bound"`` means the observation is a human
attestation, and an automated fetch must never write ``checked_on``.

**Why this does not call ``program_availability.load_program_availability``.**
That loader is the product's strict one: it enforces a named policy, refuses a
future ``checked_on``, refuses a window wider than
``MAX_RECHECK_INTERVAL_DAYS``, and raises. Those are the right rules for the
thing that decides whether a packet may be built, and the wrong ones for a
watch, which must be able to say "this record's reading lapses on Tuesday" about
a record that is currently invalid for some other reason, and must not go blind
to a second jurisdiction whose record does not fit the Woodland policy. So this
reader is deliberately tolerant -- and a test in ``tests/test_availability_watch.py``
holds the two dates it reads to the strict loader's own, so the second reader
cannot drift into reading a different record from the one the product enforces.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

import json

#: Where the workflow that runs this watch declares its own schedule.
WATCH_WORKFLOW_PATH = Path(".github") / "workflows" / "currency.yml"

#: How far ahead the cron is walked when measuring its longest gap. A year
#: covers every field shape the schedule can take, including day-of-month
#: schedules whose gap depends on which month it is.
_CRON_HORIZON_DAYS = 366


@dataclass(frozen=True)
class AvailabilityRecord:
    """One committed program-availability record, and when its reading lapses."""

    path: Path
    program_id: str
    recheck_due_on: date
    checked_on: date

    def days_remaining(self, today: date) -> int:
        """Days until the reading lapses; negative once it already has."""

        return (self.recheck_due_on - today).days


@dataclass(frozen=True)
class AvailabilityWatch:
    """What this run could say about the committed availability records.

    ``records`` is the denominator and ``due`` the numerator, and both are
    printed. A count of due records means nothing without the population it was
    drawn from: "0 due" over a directory that could not be read is the sentence
    this module exists to stop being printed.
    """

    records: tuple[AvailabilityRecord, ...]
    due: tuple[AvailabilityRecord, ...]
    lead_days: int | None
    unreadable: tuple[Path, ...]

    @property
    def checked(self) -> bool:
        """Whether a number was earned at all.

        Without a lead time the question "is this due inside the next watch
        interval" has no answer -- there is no known next interval. Without a
        readable directory there is no population. Either way the signal says
        ``not_checked`` rather than ``0``.
        """

        return self.lead_days is not None and not self.unreadable


def _resolve_bounds(body: str, names: dict[str, int]) -> tuple[int, int] | None:
    """The inclusive range one cron term admits, or ``None`` if it is unreadable.

    A wildcard is not a range and is handled by the caller; anything this cannot
    read returns ``None`` rather than a guess, so an expression this module does
    not understand can never widen a lead time by accident.
    """

    resolved: list[int] = []
    for token in body.split("-"):
        key = token.strip().lower()
        if key in names:
            resolved.append(names[key])
        elif key.isdigit():
            resolved.append(int(key))
        else:
            return None
    if len(resolved) == 1:
        return resolved[0], resolved[0]
    if len(resolved) == 2:
        return resolved[0], resolved[1]
    return None


def _cron_term_matches(part: str, value: int, names: dict[str, int]) -> bool:
    """Whether one comma-separated cron term admits ``value``."""

    body = part
    step = 1
    if "/" in part:
        body, _, step_text = part.partition("/")
        if not step_text.isdigit() or int(step_text) < 1:
            return False
        step = int(step_text)
    if body.strip() in {"*", "?"}:
        return (value % step) == 0
    bounds = _resolve_bounds(body, names)
    if bounds is None:
        return False
    low, high = bounds
    return low <= value <= high and ((value - low) % step) == 0


def _cron_field_matches(field: str, value: int, *, names: dict[str, int]) -> bool:
    """Whether one cron field admits ``value``. Supports ``*``, lists, steps, ranges."""

    return any(_cron_term_matches(part, value, names) for part in field.split(","))


_MONTH_NAMES = {
    name: index
    for index, name in enumerate(
        [
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        ],
        start=1,
    )
}
_DAY_NAMES = {
    name: index
    for index, name in enumerate(
        ["sun", "mon", "tue", "wed", "thu", "fri", "sat"],
    )
}


def _cron_fires_on(expression: str, day: date) -> bool:
    """Whether a five-field cron fires at least once on ``day``.

    Only the three date fields decide this; the minute and hour fields decide
    *when* on that day, which the gap between calendar days does not depend on.
    GitHub's cron follows the POSIX rule that a day-of-month and a day-of-week
    restriction are ORed when both are restricted, and that is honoured here
    because getting it backwards makes a fortnightly schedule read as daily.
    """

    fields = expression.split()
    if len(fields) != 5:
        return False
    _minute, _hour, dom, month, dow = fields
    if not _cron_field_matches(month, day.month, names=_MONTH_NAMES):
        return False
    weekday = (day.weekday() + 1) % 7  # cron: Sunday is 0
    dom_restricted = dom.strip() not in {"*", "?"}
    dow_restricted = dow.strip() not in {"*", "?"}
    dom_hit = _cron_field_matches(dom, day.day, names={})
    dow_hit = _cron_field_matches(dow, weekday, names=_DAY_NAMES)
    if dom_restricted and dow_restricted:
        return dom_hit or dow_hit
    if dom_restricted:
        return dom_hit
    if dow_restricted:
        return dow_hit
    return True


def _schedule_expressions(workflow_text: str) -> list[str]:
    """Every ``cron:`` expression in a workflow file, read without a YAML parser.

    PyYAML reads a bare ``on:`` as the boolean ``True`` (YAML 1.1), so
    ``workflow["on"]`` over a file that plainly declares triggers returns
    ``None`` -- absence rendered as a value inside the reader. The three lines
    below cannot make that mistake, and this file's grammar for the key is
    fixed by GitHub.
    """

    expressions = []
    for line in workflow_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- cron:") and not stripped.startswith("cron:"):
            continue
        _, _, value = stripped.partition("cron:")
        value = value.split("#", 1)[0].strip()
        if value[:1] in {'"', "'"} and value[-1:] == value[:1]:
            value = value[1:-1]
        if value:
            expressions.append(value)
    return expressions


def watch_interval_days(
    workflow_path: Path, *, today: date | None = None
) -> int | None:
    """The longest gap, in days, between two consecutive fires of the schedule.

    ``None`` when the workflow cannot be read or declares no usable schedule.
    That is not ``0`` and not a default: a run that does not know when it will
    next happen cannot say whether a deadline falls before then.
    """

    try:
        text = workflow_path.read_text(encoding="utf-8")
    except OSError:
        return None
    expressions = _schedule_expressions(text)
    if not expressions:
        return None
    start = today if today is not None else date(2026, 1, 1)
    fires = [
        start + timedelta(days=offset)
        for offset in range(_CRON_HORIZON_DAYS)
        if any(
            _cron_fires_on(expression, start + timedelta(days=offset))
            for expression in expressions
        )
    ]
    if len(fires) < 2:
        return None
    return max((later - earlier).days for earlier, later in pairwise(fires))


def _iter_record_paths(directory: Path) -> Iterator[Path]:
    yield from sorted(directory.glob("*.json"))


def load_availability_records(
    directory: Path,
) -> tuple[list[AvailabilityRecord], list[Path]]:
    """Read every committed availability record, and name the ones that would not.

    A file that cannot be parsed is returned in the second list rather than
    skipped. A record silently dropped is a record reported as not due.
    """

    records: list[AvailabilityRecord] = []
    unreadable: list[Path] = []
    if not directory.is_dir():
        return records, unreadable
    for path in _iter_record_paths(directory):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            availability = payload["availability"]
            source = availability["source"]
            records.append(
                AvailabilityRecord(
                    path=path,
                    program_id=str(availability["program_id"]),
                    checked_on=date.fromisoformat(str(source["checked_on"])),
                    recheck_due_on=date.fromisoformat(str(source["recheck_due_on"])),
                )
            )
        except (OSError, ValueError, KeyError, TypeError):
            unreadable.append(path)
    return records, unreadable


def watch_availability(
    directory: Path,
    *,
    today: date,
    workflow_path: Path,
) -> AvailabilityWatch:
    """Which committed readings lapse before the next run of this watch."""

    records, unreadable = load_availability_records(directory)
    lead_days = watch_interval_days(workflow_path, today=today)
    if lead_days is None:
        due: tuple[AvailabilityRecord, ...] = ()
    else:
        horizon = today + timedelta(days=lead_days)
        due = tuple(record for record in records if record.recheck_due_on <= horizon)
    return AvailabilityWatch(
        records=tuple(records),
        due=due,
        lead_days=lead_days,
        unreadable=tuple(unreadable),
    )


def availability_note(watch: AvailabilityWatch, *, today: date, root: Path) -> str:
    """The human half of the signal: which record, which date, how many days."""

    lines: list[str] = []
    for path in watch.unreadable:
        lines.append(
            f"  UNREADABLE: {_relative(path, root)} — this run cannot say whether "
            "its reading has lapsed."
        )
    if watch.lead_days is None and not watch.unreadable:
        lines.append(
            f"  NOT CHECKED: no usable schedule was found in "
            f"{_relative(WATCH_WORKFLOW_PATH, root)}, so there is no next watch "
            "interval to measure a deadline against."
        )
    for record in watch.due:
        remaining = record.days_remaining(today)
        if remaining < 0:
            state = f"LAPSED {abs(remaining)} day(s) ago"
        elif remaining == 0:
            state = "lapses today"
        else:
            state = f"lapses in {remaining} day(s)"
        lines.append(
            f"  {state}: {_relative(record.path, root)} "
            f"(checked_on {record.checked_on}, recheck_due_on "
            f"{record.recheck_due_on}). Renewing it is a person opening the "
            "recorded page and attesting to what it says; an automated fetch "
            "must not write checked_on."
        )
    if not lines:
        return ""
    header = (
        "\nprogram availability readings due before the next watch"
        f" (lead {watch.lead_days} day(s), derived from"
        f" {_relative(WATCH_WORKFLOW_PATH, root)}):"
        if watch.lead_days is not None
        else "\nprogram availability readings:"
    )
    return header + "\n" + "\n".join(lines)


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def signal_values(watch: AvailabilityWatch, *, not_checked: str) -> tuple[str, str]:
    """``(due, records)`` for the machine-readable line.

    Two numbers, always both: the count of readings about to lapse, and the
    count of readings this run could examine at all. A numerator without its
    denominator cannot distinguish a clean directory from an unread one.
    """

    if not watch.checked:
        return not_checked, not_checked
    return str(len(watch.due)), str(len(watch.records))
