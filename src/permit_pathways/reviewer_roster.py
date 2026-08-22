"""Reviewer roster binding named humans to dated conflict-of-interest attestations.

A ``human_reviewed`` or ``jurisdiction_approved`` ledger claim names a
reviewer, but until now nothing structurally connected that name to an
attested, current human. This module supplies that connection:

- the committed roster template at the repository root declares the review
  roles this repository recognizes and which verification level each role
  may support;
- each member record maps one opaque member ID and one reviewer name to one
  role and one dated conflict-of-interest attestation;
- an attestation older than :data:`COI_ATTESTATION_MAX_AGE_DAYS`, or dated in
  the future, makes its member invalid at strict load time.

The roster never changes which rules match an intake and never promotes a
level by itself. It is a gate consumed by strict ledger loading: when a
caller supplies a roster, every promoted ledger entry must name a reviewer
who is currently an attested member of a role supporting that level. Public
surfaces must use :meth:`ReviewerRoster.public_summary`, which reports
aggregate counts only and never member names or IDs.

The committed template carries zero members because no real review exists.
Adding a member without a real, dated attestation would be fabrication, not
configuration.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .dates import resolve_today

ROSTER_SCHEMA_VERSION = 1
COI_ATTESTATION_MAX_AGE_DAYS = 365
SUPPORTED_LEVELS = ("human_reviewed", "jurisdiction_approved")

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_ROLE_KEYS = {"role_id", "level"}
_MEMBER_KEYS = {"member_id", "reviewer_name", "role_id", "coi_attested_on"}
_TOP_LEVEL_KEYS = {"schema_version", "roles", "members"}


@dataclass(frozen=True)
class RosterRole:
    """One review role and the single verification level it may support."""

    role_id: str
    level: str


@dataclass(frozen=True)
class RosterMember:
    """One attested human mapped to one role by exact reviewer name."""

    member_id: str
    reviewer_name: str
    role_id: str
    coi_attested_on: str


@dataclass(frozen=True)
class ReviewerRoster:
    """A validated roster: roles plus attested members, aggregate-only out."""

    roles: tuple[RosterRole, ...]
    members: tuple[RosterMember, ...]

    def _role_levels(self) -> dict[str, str]:
        return {role.role_id: role.level for role in self.roles}

    def allows(
        self,
        reviewer_name: str | None,
        level: str,
        *,
        today: date | None = None,
    ) -> bool:
        """Return True only for a currently attested member of a matching role.

        Matching is exact on the stripped reviewer name recorded in the
        ledger entry. An attestation expires once
        :data:`COI_ATTESTATION_MAX_AGE_DAYS` elapse; expiry fails closed.
        """

        if not reviewer_name or level not in SUPPORTED_LEVELS:
            return False
        as_of = resolve_today(today)
        role_levels = self._role_levels()
        covering_roles = {
            role_id for role_id, supported in role_levels.items() if supported == level
        }
        for member in self.members:
            if member.reviewer_name != reviewer_name.strip():
                continue
            if member.role_id not in covering_roles:
                continue
            attested = date.fromisoformat(member.coi_attested_on)
            if 0 <= (as_of - attested).days <= COI_ATTESTATION_MAX_AGE_DAYS:
                return True
        return False

    def public_summary(self) -> str:
        """Aggregate counts only; never member names, IDs, or dates."""

        active = len({member.member_id for member in self.members})
        return f"{len(self.roles)} roster role(s); {active} attested reviewer(s) active"


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected non-blank text")
    return value.strip()


def _identifier(value: Any, field: str) -> str:
    text = _required_text(value, field)
    if not _IDENTIFIER.fullmatch(text):
        raise ValueError(f"{field}: expected a stable lowercase identifier")
    return text


def _attested_date(value: Any, field: str, *, today: date) -> str:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise ValueError(f"{field}: expected YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field}: invalid ISO date {value!r}") from error
    if parsed > today:
        raise ValueError(f"{field}: future dates are not allowed")
    if (today - parsed).days > COI_ATTESTATION_MAX_AGE_DAYS:
        raise ValueError(
            f"{field}: conflict-of-interest attestation is older than "
            f"{COI_ATTESTATION_MAX_AGE_DAYS} days and must be renewed"
        )
    return value


def _exact_keys(value: Any, expected: set[str], field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    unknown = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    if unknown:
        raise ValueError(f"{field}: unknown fields: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{field}: missing fields: {', '.join(missing)}")
    return value


def _roles(raw: Any, today: date) -> tuple[RosterRole, ...]:
    if not isinstance(raw, list):
        raise ValueError("roles: expected a list")
    roles: list[RosterRole] = []
    seen: set[str] = set()
    covered: set[str] = set()
    for index, record in enumerate(raw):
        field = f"roles[{index}]"
        data = _exact_keys(record, _ROLE_KEYS, field)
        role_id = _identifier(data["role_id"], f"{field}.role_id")
        if role_id in seen:
            raise ValueError(f"{field}: duplicate role ID {role_id!r}")
        seen.add(role_id)
        level = _required_text(data["level"], f"{field}.level")
        if level not in SUPPORTED_LEVELS:
            raise ValueError(f"{field}.level: unsupported value {level!r}")
        covered.add(level)
        roles.append(RosterRole(role_id=role_id, level=level))
    missing_levels = sorted(set(SUPPORTED_LEVELS) - covered)
    if missing_levels:
        raise ValueError(
            "roles: no role supports required level(s): " + ", ".join(missing_levels)
        )
    return tuple(roles)


def _members(
    raw: Any,
    roles: tuple[RosterRole, ...],
    today: date,
) -> tuple[RosterMember, ...]:
    if not isinstance(raw, list):
        raise ValueError("members: expected a list")
    known_roles = {role.role_id for role in roles}
    members: list[RosterMember] = []
    seen_ids: set[str] = set()
    seen_names: set[tuple[str, str]] = set()
    for index, record in enumerate(raw):
        field = f"members[{index}]"
        data = _exact_keys(record, _MEMBER_KEYS, field)
        member_id = _identifier(data["member_id"], f"{field}.member_id")
        if member_id in seen_ids:
            raise ValueError(f"{field}: duplicate member ID {member_id!r}")
        seen_ids.add(member_id)
        reviewer_name = _required_text(data["reviewer_name"], f"{field}.reviewer_name")
        role_id = _identifier(data["role_id"], f"{field}.role_id")
        if role_id not in known_roles:
            raise ValueError(f"{field}.role_id: references undeclared role {role_id!r}")
        pair = (reviewer_name, role_id)
        if pair in seen_names:
            raise ValueError(f"{field}: duplicate reviewer name for role {role_id!r}")
        seen_names.add(pair)
        coi_attested_on = _attested_date(
            data["coi_attested_on"], f"{field}.coi_attested_on", today=today
        )
        members.append(
            RosterMember(
                member_id=member_id,
                reviewer_name=reviewer_name,
                role_id=role_id,
                coi_attested_on=coi_attested_on,
            )
        )
    return tuple(members)


def load_reviewer_roster(
    path: Path,
    *,
    today: date | None = None,
) -> ReviewerRoster:
    """Strictly load and validate the reviewer roster at ``path``.

    The committed template is valid with zero members: an empty roster means
    no promotion can be gated through it, which is exactly today's honest
    state (zero named reviews, zero jurisdiction approvals).
    """

    as_of = resolve_today(today)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"reviewer roster could not be loaded: {error}") from error
    record = _exact_keys(payload, _TOP_LEVEL_KEYS, str(path))
    if record["schema_version"] != ROSTER_SCHEMA_VERSION:
        raise ValueError(
            f"{path}.schema_version: expected {ROSTER_SCHEMA_VERSION}; "
            f"got {record['schema_version']!r}"
        )
    roles = _roles(record["roles"], as_of)
    members = _members(record["members"], roles, as_of)
    return ReviewerRoster(roles=roles, members=members)


def maybe_load_reviewer_roster(
    path: Path, *, today: date | None = None
) -> ReviewerRoster | None:
    """Load the roster when it exists; return None when it does not.

    Callers that require the gate must treat None explicitly rather than
    silently skipping enforcement.
    """

    if not path.exists():
        return None
    return load_reviewer_roster(path, today=today)
