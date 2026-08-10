"""Strict evidence record for bounded program availability.

This module records whether the official City of Woodland program page lists
any preapproved ADU plans.  It is intentionally isolated from screening and
readiness evaluation: loading the record cannot create a candidate route or
make the synthetic Woodland workflow applicable.

The current record is a future-state simulation boundary.  ``plans_not_listed``
means only that no plan was identified on the official page on the recorded
check date.  It is not evidence that the program is unavailable forever, and
it is never a favorable applicability fact.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urlsplit

from .dates import resolve_today

SCHEMA_VERSION = 1
MAX_RECORD_BYTES = 256 * 1024
PROGRAM_ID = "woodland-preapproved-adu-plan-program"
SOURCE_ID = "woodland-preapproved-adu-program-page"
WORKFLOW_ID = "woodland-preapproved-detached-adu"
JURISDICTION = "woodland"
OFFICIAL_PROGRAM_URL = (
    "https://www.cityofwoodland.gov/1616/Preapproved-ADU-Plan-Program"
)
OFFICIAL_EXCERPT = "Preapproved ADU List: Coming soon!"
MAX_RECHECK_INTERVAL_DAYS = 31
BOUNDARY = (
    "No currently listed City of Woodland preapproved ADU plan was identified "
    "on the checked program page. This future-state simulation is not evidence "
    "that a plan is available; real workflow applicability must be confirmed "
    "with the City before use."
)
WOODLAND_AVAILABILITY_POLICY = "woodland-preapproved-adu-plans-not-listed-v1"
GENERIC_PROTOTYPE_AVAILABILITY_POLICY = "prototype-generic-plans-not-listed-v1"
GENERIC_PROTOTYPE_BOUNDARY = (
    "No currently listed plan was identified on the checked official program "
    "page. This prototype observation is not evidence that a plan is available "
    "or that this workflow applies; applicability must be confirmed with the "
    "responsible jurisdiction before use."
)
GENERIC_PROTOTYPE_EXCERPT = "No plans are listed on this prototype page."
SUPPORTED_AVAILABILITY_POLICIES = (
    GENERIC_PROTOTYPE_AVAILABILITY_POLICY,
    WOODLAND_AVAILABILITY_POLICY,
)

AvailabilityMode = Literal["future_state_simulation"]
AvailabilityStatus = Literal["plans_not_listed"]
MonitoringStatus = Literal["manual_date_bound"]

_STABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = {"schema_version", "availability"}
_AVAILABILITY_KEYS = {
    "program_id",
    "workflow_id",
    "jurisdiction",
    "mode",
    "status",
    "monitoring_status",
    "source",
    "boundary",
}
_SOURCE_KEYS = {
    "source_id",
    "url",
    "label",
    "checked_on",
    "recheck_due_on",
    "excerpt",
    "excerpt_sha256",
}


@dataclass(frozen=True)
class AvailabilitySource:
    """Official page evidence attached to one availability observation."""

    source_id: str
    url: str
    label: str
    checked_on: str
    recheck_due_on: str
    excerpt: str
    excerpt_sha256: str


@dataclass(frozen=True)
class ProgramAvailability:
    """One bounded program-availability observation."""

    program_id: str
    workflow_id: str
    jurisdiction: str
    mode: AvailabilityMode
    status: AvailabilityStatus
    monitoring_status: MonitoringStatus
    source: AvailabilitySource
    boundary: str


def normalize_excerpt(value: str) -> str:
    """Normalize source copy before fingerprinting.

    NFKC normalization and whitespace collapsing make the fingerprint stable
    across presentation-only spacing changes while preserving punctuation and
    words that affect the observation's meaning.
    """

    return " ".join(unicodedata.normalize("NFKC", value).split())


def excerpt_fingerprint(value: str) -> str:
    """Return the canonical SHA-256 fingerprint for a source excerpt."""

    normalized = normalize_excerpt(value)
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _exact_keys(record: dict[str, Any], expected: set[str], field: str) -> None:
    unknown = sorted(set(record) - expected)
    if unknown:
        raise ValueError(f"{field}: unknown fields: {', '.join(unknown)}")
    missing = sorted(expected - set(record))
    if missing:
        raise ValueError(f"{field}: missing fields: {', '.join(missing)}")


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(
            f"{field}: expected non-blank text without surrounding whitespace"
        )
    return value


class _DuplicateKeyError(ValueError):
    """Raised before an ambiguous JSON object can replace an earlier key."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    record: dict[str, Any] = {}
    for key, value in pairs:
        if key in record:
            raise _DuplicateKeyError(key)
        record[key] = value
    return record


def _reject_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant {value!r} is not allowed")


def _load_json(path: Path) -> Any:
    try:
        metadata = path.stat()
        if metadata.st_size > MAX_RECORD_BYTES:
            raise ValueError(f"file exceeds {MAX_RECORD_BYTES} bytes")
        with path.open("rb") as stream:
            raw = stream.read(MAX_RECORD_BYTES + 1)
        if len(raw) > MAX_RECORD_BYTES:
            raise ValueError(f"file exceeds {MAX_RECORD_BYTES} bytes")
        text = raw.decode("utf-8")
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        _DuplicateKeyError,
        RecursionError,
        ValueError,
    ) as error:
        raise ValueError(
            f"{path}: program-availability data could not be loaded"
        ) from error


def _stable_id(value: Any, field: str) -> str:
    identifier = _required_text(value, field)
    if not _STABLE_ID.fullmatch(identifier):
        raise ValueError(f"{field}: expected a stable ID")
    return identifier


def _iso_date(value: Any, field: str) -> tuple[str, date]:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise ValueError(f"{field}: expected YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field}: invalid ISO date {value!r}") from error
    return value, parsed


def _safe_https_url(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or any(ord(character) <= 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError(f"{field}: expected HTTPS URL")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ValueError(f"{field}: expected HTTPS URL") from error
    if not hostname:
        raise ValueError(f"{field}: expected HTTPS URL")
    labels = hostname.split(".")
    canonical_hostname = bool(
        hostname.isascii()
        and hostname == hostname.lower()
        and len(labels) >= 2
        and labels[-1].isalpha()
        and all(
            label
            and len(label) <= 63
            and re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
            for label in labels
        )
    )
    if (
        parsed.scheme != "https"
        or not canonical_hostname
        or parsed.netloc != hostname
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/")
        or parsed.path.startswith("//")
        or parsed.path == "/"
        or "\\" in parsed.path
        or f"https://{hostname}{parsed.path}" != value
    ):
        raise ValueError(f"{field}: expected HTTPS URL")
    return value


def _validate_policy_source_binding(
    *,
    policy: str,
    program_id: str,
    source_id: str,
    url: str,
    excerpt: str,
) -> None:
    field = "availability.source"
    if policy == WOODLAND_AVAILABILITY_POLICY:
        if source_id != SOURCE_ID:
            raise ValueError(f"{field}.source_id: expected {SOURCE_ID!r}")
        if excerpt != OFFICIAL_EXCERPT:
            raise ValueError(
                f"{field}.excerpt: must match the plans_not_listed observation"
            )
        if url != OFFICIAL_PROGRAM_URL:
            raise ValueError(f"{field}.url: expected the official Woodland program URL")
        return

    if source_id != f"{program_id}-page":
        raise ValueError(
            f"{field}.source_id: generic policy requires {program_id!r} source binding"
        )
    if excerpt != GENERIC_PROTOTYPE_EXCERPT:
        raise ValueError(
            f"{field}.excerpt: must match the generic plans_not_listed observation"
        )
    if urlsplit(url).path != f"/{program_id}":
        raise ValueError(
            f"{field}.url: generic policy requires the exact program-ID path"
        )


def _source(
    record: Any,
    *,
    today: date,
    policy: str,
    program_id: str,
) -> AvailabilitySource:
    field = "availability.source"
    if not isinstance(record, dict):
        raise ValueError(f"{field}: expected an object")
    _exact_keys(record, _SOURCE_KEYS, field)

    source_id = _stable_id(record["source_id"], f"{field}.source_id")

    checked_on, checked_date = _iso_date(record["checked_on"], f"{field}.checked_on")
    if checked_date > today:
        raise ValueError(f"{field}.checked_on: future dates are not allowed")
    recheck_due_on, recheck_date = _iso_date(
        record["recheck_due_on"], f"{field}.recheck_due_on"
    )
    if recheck_date <= checked_date:
        raise ValueError(f"{field}.recheck_due_on: must be after checked_on")
    if (recheck_date - checked_date).days > MAX_RECHECK_INTERVAL_DAYS:
        raise ValueError(
            f"{field}.recheck_due_on: must be within "
            f"{MAX_RECHECK_INTERVAL_DAYS} days of checked_on"
        )

    excerpt = _required_text(record["excerpt"], f"{field}.excerpt")
    url = _safe_https_url(record["url"], f"{field}.url")
    _validate_policy_source_binding(
        policy=policy,
        program_id=program_id,
        source_id=source_id,
        url=url,
        excerpt=excerpt,
    )

    fingerprint = _required_text(record["excerpt_sha256"], f"{field}.excerpt_sha256")
    if not _FINGERPRINT.fullmatch(fingerprint):
        raise ValueError(f"{field}.excerpt_sha256: invalid SHA-256 fingerprint")
    if fingerprint != excerpt_fingerprint(excerpt):
        raise ValueError(
            f"{field}.excerpt_sha256: does not match the normalized excerpt"
        )

    return AvailabilitySource(
        source_id=source_id,
        url=url,
        label=_required_text(record["label"], f"{field}.label"),
        checked_on=checked_on,
        recheck_due_on=recheck_due_on,
        excerpt=excerpt,
        excerpt_sha256=fingerprint,
    )


def _availability(
    record: Any,
    *,
    today: date,
    policy: str,
) -> ProgramAvailability:
    field = "availability"
    if not isinstance(record, dict):
        raise ValueError(f"{field}: expected an object")
    _exact_keys(record, _AVAILABILITY_KEYS, field)

    program_id = _stable_id(record["program_id"], f"{field}.program_id")
    if policy == WOODLAND_AVAILABILITY_POLICY and program_id != PROGRAM_ID:
        raise ValueError(f"{field}.program_id: expected {PROGRAM_ID!r}")
    workflow_id = _stable_id(record["workflow_id"], f"{field}.workflow_id")
    if policy == WOODLAND_AVAILABILITY_POLICY and workflow_id != WORKFLOW_ID:
        raise ValueError(f"{field}.workflow_id: expected {WORKFLOW_ID!r}")
    jurisdiction = _stable_id(record["jurisdiction"], f"{field}.jurisdiction")
    if policy == WOODLAND_AVAILABILITY_POLICY and jurisdiction != JURISDICTION:
        raise ValueError(f"{field}.jurisdiction: expected {JURISDICTION!r}")

    mode = _required_text(record["mode"], f"{field}.mode")
    if mode != "future_state_simulation":
        raise ValueError(f"{field}.mode: unsupported value {mode!r}")
    status = _required_text(record["status"], f"{field}.status")
    if status != "plans_not_listed":
        raise ValueError(f"{field}.status: unsupported value {status!r}")
    monitoring = _required_text(
        record["monitoring_status"], f"{field}.monitoring_status"
    )
    if monitoring != "manual_date_bound":
        raise ValueError(f"{field}.monitoring_status: unsupported value {monitoring!r}")
    boundary = _required_text(record["boundary"], f"{field}.boundary")
    expected_boundary = (
        BOUNDARY
        if policy == WOODLAND_AVAILABILITY_POLICY
        else GENERIC_PROTOTYPE_BOUNDARY
    )
    if boundary != expected_boundary:
        raise ValueError(
            f"{field}.boundary: must preserve the {policy!r} "
            "no-listed-plan and applicability-confirmation boundary"
        )

    return ProgramAvailability(
        program_id=program_id,
        workflow_id=workflow_id,
        jurisdiction=jurisdiction,
        mode=cast(AvailabilityMode, mode),
        status=cast(AvailabilityStatus, status),
        monitoring_status=cast(MonitoringStatus, monitoring),
        source=_source(
            record["source"],
            today=today,
            policy=policy,
            program_id=program_id,
        ),
        boundary=boundary,
    )


def load_program_availability(
    path: Path,
    *,
    today: date | None = None,
    policy: str = WOODLAND_AVAILABILITY_POLICY,
) -> ProgramAvailability:
    """Load one strict, source-bound program-availability record.

    The default policy retains the exact Woodland source and wording checks.
    The generic policy exists only to exercise registered prototype workflows;
    it still requires the same conservative status, monitoring window, excerpt
    fingerprint, and a fixed non-applicability boundary.
    """

    if policy not in SUPPORTED_AVAILABILITY_POLICIES:
        raise ValueError(f"availability policy: unsupported value {policy!r}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected an object")
    _exact_keys(payload, _TOP_LEVEL_KEYS, "program-availability record")
    schema_version = payload["schema_version"]
    if type(schema_version) is not int or schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"schema_version must be {SCHEMA_VERSION}; got {schema_version!r}"
        )
    return _availability(
        payload["availability"],
        today=resolve_today(today),
        policy=policy,
    )
