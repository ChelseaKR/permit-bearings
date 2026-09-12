"""The frozen clock the suite shares with the attestation it exercises.

``data/availability/woodland-preapproved-adu-program.json`` is a human
attestation: a person opened the City of Woodland program page on a stated
day and wrote down what it said. It carries ``checked_on`` and a
``recheck_due_on`` thirty days later, and the beta gate blocks once today is
past that deadline. Renewing it is meant to be a data edit: someone looks at
the page again and two dates move.

It was not one. Twenty-one test files pinned a literal "today", all of them
earlier than any date a real renewal could carry, and
``load_program_availability`` refuses a record whose ``checked_on`` is in the
future. So the first renewal the record ever needed turned most of the suite
red, and the thirty-day recheck control had never once been satisfiable.

This module reads the attested dates out of the record itself. A test that
loads the real record freezes its clock from here, so the clock moves when the
attestation does and the renewal goes back to being two edited dates.

Nothing here relaxes a check. ``checked_on`` after the clock is still refused,
a record past ``recheck_due_on`` still blocks the gate, and the excerpt
fingerprint is still compared byte for byte. ``expired_clock`` exists so a
test can prove the expiry still fires rather than assuming it.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

#: The committed attestation every derived clock is read from.
ATTESTATION_RECORD = (
    REPOSITORY_ROOT / "data" / "availability" / "woodland-preapproved-adu-program.json"
)


class UnreadableAttestation(RuntimeError):
    """Raised instead of falling back to a date nobody attested to.

    A clock guessed from a record that could not be read would let the suite
    stay green over an attestation it never opened.
    """


def attested_dates(record: Path = ATTESTATION_RECORD) -> tuple[date, date]:
    """Return the record's own ``(checked_on, recheck_due_on)`` pair."""

    try:
        payload = json.loads(record.read_text(encoding="utf-8"))
        source = payload["availability"]["source"]
        checked_on = date.fromisoformat(source["checked_on"])
        recheck_due_on = date.fromisoformat(source["recheck_due_on"])
    except (OSError, TypeError, KeyError, ValueError) as error:
        raise UnreadableAttestation(
            f"{record}: the attested check dates could not be read, so no test "
            "clock can be derived from them"
        ) from error
    if recheck_due_on <= checked_on:
        raise UnreadableAttestation(
            f"{record}: recheck_due_on {recheck_due_on.isoformat()} is not after "
            f"checked_on {checked_on.isoformat()}, so the record has no window"
        )
    return checked_on, recheck_due_on


def attested_on(record: Path = ATTESTATION_RECORD) -> date:
    """The day a person states they looked at the official program page."""

    return attested_dates(record)[0]


def recheck_due_on(record: Path = ATTESTATION_RECORD) -> date:
    """The day after which the attestation stops counting as current."""

    return attested_dates(record)[1]


def frozen_today(
    *,
    not_before: date | None = None,
    record: Path = ATTESTATION_RECORD,
) -> date:
    """A deterministic "today" inside the attestation's own window.

    ``not_before`` lets a test keep a later anchor its other fixtures need;
    the result is never earlier than the attestation and never past its
    recheck deadline, and a ``not_before`` that cannot satisfy both is an
    error rather than a clock that quietly expires the record.
    """

    checked_on, deadline = attested_dates(record)
    today = checked_on if not_before is None else max(checked_on, not_before)
    if today > deadline:
        raise UnreadableAttestation(
            f"{record}: a clock at {today.isoformat()} is past the attestation's "
            f"recheck deadline {deadline.isoformat()}; re-check the page rather "
            "than moving the clock"
        )
    return today


def pre_attestation_clock(
    *,
    days: int = 1,
    record: Path = ATTESTATION_RECORD,
) -> date:
    """A clock before the attestation, where its ``checked_on`` is the future."""

    if days < 1:
        raise ValueError("days must be at least 1 to precede the attestation")
    return attested_on(record) - timedelta(days=days)


def expired_clock(
    *,
    days: int = 1,
    record: Path = ATTESTATION_RECORD,
) -> date:
    """A clock past the recheck deadline, where the attestation has expired."""

    if days < 1:
        raise ValueError("days must be at least 1 to pass the recheck deadline")
    return recheck_due_on(record) + timedelta(days=days)
