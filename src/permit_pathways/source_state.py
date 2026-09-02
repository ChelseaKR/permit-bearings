"""Versioned source-watch snapshots and exact dependency impact.

The watcher is deliberately ephemeral.  This module turns one completed run
into a portable receipt that can be reviewed and committed separately from the
historical rule, journey, and readiness records.  Only sources that were
fetched and whose digest changed make dependents stale; an unverifiable fetch
remains a warning and never becomes evidence of changed law.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urlsplit

from .harness.runner import load_golden
from .harness.watch import (
    UNVERIFIABLE_KINDS,
    SourceRecord,
    UnverifiableKind,
    WatchResult,
    load_sources,
)
from .screening import load_rules

SourceWatchStatus = Literal["unchanged", "changed", "unverifiable"]
ReceiptStatus = Literal["proposed", "reviewed"]

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_SNAPSHOT_ID = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_SOURCE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_TOP_LEVEL_KEYS = {
    "affected_golden_case_ids",
    "affected_rule_ids",
    "changed_source_ids",
    "checked_at",
    "observations",
    "receipt",
    "schema_version",
    "snapshot_id",
    "source_registry_sha256",
    "unaffected_golden_case_ids",
    "unaffected_rule_ids",
    "unverifiable_source_ids",
}
_OBSERVATION_KEYS = {
    "last_verified_on",
    "observed_sha256",
    "reason",
    "recorded_sha256",
    "source_id",
    "status",
}
# Present exactly on an unverifiable observation and absent everywhere else,
# so a receipt written before this field existed stays byte-identical and
# keeps its fingerprint. A fetched observation carrying the key is rejected
# rather than ignored.
_UNVERIFIABLE_KIND_KEY = "unverifiable_kind"
_RECEIPT_KEYS = {"commit_sha", "method", "run_url", "status"}


@dataclass(frozen=True)
class SourceObservation:
    source_id: str
    status: SourceWatchStatus
    recorded_sha256: str
    observed_sha256: str | None
    last_verified_on: str
    reason: str | None
    # Set only when ``status`` is ``unverifiable``. ``transport`` means the
    # fetch got no authoritative answer; ``not_found`` means the server
    # answered that no document is published at that address. Neither is
    # evidence that the law changed, and neither stales a dependent rule.
    unverifiable_kind: UnverifiableKind | None = None

    @property
    def is_not_found(self) -> bool:
        return self.status == "unverifiable" and self.unverifiable_kind == "not_found"

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "last_verified_on": self.last_verified_on,
            "observed_sha256": self.observed_sha256,
            "reason": self.reason,
            "recorded_sha256": self.recorded_sha256,
            "source_id": self.source_id,
            "status": self.status,
        }
        if self.unverifiable_kind is not None:
            payload[_UNVERIFIABLE_KIND_KEY] = self.unverifiable_kind
        return payload


@dataclass(frozen=True)
class SourceStateReceipt:
    status: ReceiptStatus
    method: str
    run_url: str
    commit_sha: str


@dataclass(frozen=True)
class SourceStateSnapshot:
    schema_version: int
    snapshot_id: str
    checked_at: str
    source_registry_sha256: str
    receipt: SourceStateReceipt
    observations: tuple[SourceObservation, ...]
    changed_source_ids: tuple[str, ...]
    unverifiable_source_ids: tuple[str, ...]
    affected_rule_ids: tuple[str, ...]
    unaffected_rule_ids: tuple[str, ...]
    affected_golden_case_ids: tuple[str, ...]
    unaffected_golden_case_ids: tuple[str, ...]

    @property
    def not_found_source_ids(self) -> tuple[str, ...]:
        """Watched sources whose published address answered "no document".

        Derived from the observations rather than stored as its own receipt
        field, so no committed receipt has to change to gain the reading.
        """

        return tuple(
            sorted(item.source_id for item in self.observations if item.is_not_found)
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["observations"] = [
            observation.to_dict() for observation in self.observations
        ]
        for field_name in (
            "changed_source_ids",
            "unverifiable_source_ids",
            "affected_rule_ids",
            "unaffected_rule_ids",
            "affected_golden_case_ids",
            "unaffected_golden_case_ids",
        ):
            payload[field_name] = list(getattr(self, field_name))
        return payload


def source_state_fingerprint(snapshot: SourceStateSnapshot) -> str:
    """Return the canonical semantic fingerprint for one validated snapshot."""

    encoded = json.dumps(
        snapshot.to_dict(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def source_registry_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _checked_at(value: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("checked_at: expected a UTC RFC3339 timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError("checked_at: invalid RFC3339 timestamp") from error
    if parsed.tzinfo != UTC or parsed.microsecond:
        raise ValueError("checked_at: expected whole-second UTC timestamp")
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _https_url(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}: expected HTTPS URL")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(f"{field}: expected HTTPS URL")
    return value


def _exact_string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field}: expected a list of strings")
    if value != sorted(value) or len(value) != len(set(value)):
        raise ValueError(f"{field}: expected sorted unique values")
    return tuple(value)


def _impact(
    rules_path: Path,
    golden_path: Path,
    changed_source_ids: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    changed = set(changed_source_ids)
    rules = load_rules(rules_path)
    affected_rules = tuple(
        sorted(
            rule.rule_id
            for rule in rules
            if changed.intersection(rule.source_dependencies)
        )
    )
    affected_rule_set = set(affected_rules)
    unaffected_rules = tuple(
        sorted(rule.rule_id for rule in rules if rule.rule_id not in affected_rule_set)
    )
    golden = load_golden(golden_path, rules)
    affected_cases = tuple(
        sorted(
            case.case_id
            for case in golden
            if affected_rule_set.intersection(case.rule_dependency_ids)
        )
    )
    affected_case_set = set(affected_cases)
    unaffected_cases = tuple(
        sorted(case.case_id for case in golden if case.case_id not in affected_case_set)
    )
    return affected_rules, unaffected_rules, affected_cases, unaffected_cases


def _source_state_receipt(
    status: ReceiptStatus,
    method: Any,
    run_url: Any,
    commit_sha: Any,
) -> SourceStateReceipt:
    if status not in ("proposed", "reviewed"):
        raise ValueError("receipt.status: expected proposed or reviewed")
    if not isinstance(method, str) or not method.strip():
        raise ValueError("receipt.method: expected non-blank text")
    if not isinstance(commit_sha, str) or not _COMMIT_SHA.fullmatch(commit_sha):
        raise ValueError("receipt.commit_sha: expected full lowercase commit SHA")
    return SourceStateReceipt(
        status=status,
        method=method.strip(),
        run_url=_https_url(run_url, "receipt.run_url"),
        commit_sha=commit_sha,
    )


def _watched_sources(sources_path: Path) -> dict[str, SourceRecord]:
    return {
        source_id: source
        for source_id, source in load_sources(sources_path).items()
        if source.watch
    }


def _validate_watch_classification(
    watch: WatchResult,
    watched: dict[str, SourceRecord],
) -> None:
    unchanged = set(watch.unchanged)
    changed = set(watch.changed)
    unverifiable = set(watch.unverifiable)
    if unchanged | changed | unverifiable != set(watched):
        raise ValueError("watch result must classify every watched source exactly once")
    if unchanged & changed or unchanged & unverifiable or changed & unverifiable:
        raise ValueError("watch result classifications overlap")


def _observation_from_watch(
    source_id: str,
    source: SourceRecord,
    watch: WatchResult,
) -> SourceObservation:
    if source.sha256 is None or source.fetched_on is None:
        raise ValueError(f"{source_id}: watched source lacks recorded evidence")
    failure = watch.unverifiable.get(source_id)
    if failure is not None:
        return SourceObservation(
            source_id=source_id,
            status="unverifiable",
            recorded_sha256=source.sha256,
            observed_sha256=None,
            last_verified_on=source.fetched_on,
            reason=failure.reason,
            unverifiable_kind=failure.kind,
        )
    observed = watch.observed_digests.get(source_id)
    if observed is None:
        observed = source.sha256 if source_id in watch.unchanged else None
    if observed is None or not _SHA256.fullmatch(observed):
        raise ValueError(f"{source_id}: fetched source lacks observed digest")
    status: SourceWatchStatus = "changed" if source_id in watch.changed else "unchanged"
    if (status == "unchanged") != (observed == source.sha256):
        raise ValueError(f"{source_id}: status contradicts observed digest")
    return SourceObservation(
        source_id=source_id,
        status=status,
        recorded_sha256=source.sha256,
        observed_sha256=observed,
        last_verified_on=source.fetched_on,
        reason=None,
    )


def build_source_state_snapshot(
    watch: WatchResult,
    sources_path: Path,
    rules_path: Path,
    golden_path: Path,
    *,
    snapshot_id: str,
    checked_at: str,
    receipt_status: ReceiptStatus,
    method: str,
    run_url: str,
    commit_sha: str,
) -> SourceStateSnapshot:
    """Build a strict snapshot from one completed watcher result."""

    if not _SNAPSHOT_ID.fullmatch(snapshot_id):
        raise ValueError("snapshot_id: invalid stable ID")
    checked = _checked_at(checked_at)
    receipt = _source_state_receipt(
        receipt_status,
        method,
        run_url,
        commit_sha,
    )
    watched = _watched_sources(sources_path)
    _validate_watch_classification(watch, watched)
    observations = tuple(
        _observation_from_watch(source_id, watched[source_id], watch)
        for source_id in sorted(watched)
    )

    changed = tuple(sorted(watch.changed))
    unverifiable = tuple(sorted(watch.unverifiable))
    affected, unaffected, affected_cases, unaffected_cases = _impact(
        rules_path,
        golden_path,
        changed,
    )
    return SourceStateSnapshot(
        schema_version=1,
        snapshot_id=snapshot_id,
        checked_at=checked,
        source_registry_sha256=source_registry_sha256(sources_path),
        receipt=receipt,
        observations=observations,
        changed_source_ids=changed,
        unverifiable_source_ids=unverifiable,
        affected_rule_ids=affected,
        unaffected_rule_ids=unaffected,
        affected_golden_case_ids=affected_cases,
        unaffected_golden_case_ids=unaffected_cases,
    )


def _load_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"{path}: source-state snapshot could not be loaded"
        ) from error
    if not isinstance(payload, dict) or set(payload) != _TOP_LEVEL_KEYS:
        raise ValueError(f"{path}: source-state snapshot has invalid fields")
    return payload


def _snapshot_header(
    payload: dict[str, Any],
    sources_path: Path,
) -> tuple[str, str, str]:
    if payload.get("schema_version") != 1:
        raise ValueError("schema_version: expected 1")
    snapshot_id = payload.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not _SNAPSHOT_ID.fullmatch(snapshot_id):
        raise ValueError("snapshot_id: invalid stable ID")
    checked_value = payload.get("checked_at")
    if not isinstance(checked_value, str):
        raise ValueError("checked_at: expected text")
    checked = _checked_at(checked_value)
    expected_digest = source_registry_sha256(sources_path)
    if payload.get("source_registry_sha256") != expected_digest:
        raise ValueError(
            "source_registry_sha256: snapshot does not bind current registry"
        )
    return snapshot_id, checked, expected_digest


def _load_receipt(
    payload: dict[str, Any],
    *,
    require_reviewed: bool,
) -> SourceStateReceipt:
    raw = payload.get("receipt")
    if not isinstance(raw, dict) or set(raw) != _RECEIPT_KEYS:
        raise ValueError("receipt: invalid fields")
    status = raw.get("status")
    if status not in ("proposed", "reviewed"):
        raise ValueError("receipt.status: expected proposed or reviewed")
    if require_reviewed and status != "reviewed":
        raise ValueError("receipt.status: public bundle requires reviewed snapshot")
    return _source_state_receipt(
        cast(ReceiptStatus, status),
        raw.get("method"),
        raw.get("run_url"),
        raw.get("commit_sha"),
    )


def _validate_observation_evidence(
    source_id: str,
    status: Any,
    recorded: Any,
    observed: Any,
    reason: Any,
) -> None:
    if status == "unverifiable":
        if observed is not None or not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"{source_id}: invalid unverifiable evidence")
        return
    if not isinstance(observed, str) or not _SHA256.fullmatch(observed):
        raise ValueError(f"{source_id}: invalid observed digest")
    if reason is not None:
        raise ValueError(f"{source_id}: fetched observation cannot have reason")
    if (status == "unchanged") != (observed == recorded):
        raise ValueError(f"{source_id}: status contradicts observed digest")


def _observation_kind(source_id: str, raw: dict[str, Any], status: Any) -> Any:
    """Read the fetch-failure kind, which every unverifiable row must carry.

    An unverifiable observation with no kind cannot be rendered honestly:
    the reader has no way to tell a certificate failure from a citation
    whose published address is gone. Fail closed rather than guess one.
    """

    kind = raw.get(_UNVERIFIABLE_KIND_KEY)
    if status != "unverifiable":
        if _UNVERIFIABLE_KIND_KEY in raw:
            raise ValueError(f"{source_id}: fetched observation cannot have a kind")
        return None
    if kind not in UNVERIFIABLE_KINDS:
        raise ValueError(f"{source_id}: unverifiable observation needs a valid kind")
    return kind


def _load_observation(
    raw: Any,
    watched: dict[str, SourceRecord],
) -> SourceObservation:
    if not isinstance(raw, dict) or not set(raw) <= (
        _OBSERVATION_KEYS | {_UNVERIFIABLE_KIND_KEY}
    ):
        raise ValueError("observations: invalid fields")
    if not set(raw) >= _OBSERVATION_KEYS:
        raise ValueError("observations: invalid fields")
    source_id = raw.get("source_id")
    if not isinstance(source_id, str) or not _SOURCE_ID.fullmatch(source_id):
        raise ValueError("observations.source_id: invalid stable ID")
    source = watched.get(source_id)
    if source is None or source.sha256 is None or source.fetched_on is None:
        raise ValueError(f"{source_id}: unknown or unwatched source")
    status = raw.get("status")
    if status not in ("unchanged", "changed", "unverifiable"):
        raise ValueError(f"{source_id}.status: invalid state")
    recorded = raw.get("recorded_sha256")
    observed = raw.get("observed_sha256")
    reason = raw.get("reason")
    if recorded != source.sha256 or raw.get("last_verified_on") != source.fetched_on:
        raise ValueError(f"{source_id}: recorded evidence drifted")
    _validate_observation_evidence(source_id, status, recorded, observed, reason)
    kind = _observation_kind(source_id, raw, status)
    return SourceObservation(
        source_id=source_id,
        status=cast(SourceWatchStatus, status),
        recorded_sha256=cast(str, recorded),
        observed_sha256=observed,
        last_verified_on=source.fetched_on,
        reason=reason,
        unverifiable_kind=cast("UnverifiableKind | None", kind),
    )


def _load_observations(
    payload: dict[str, Any],
    watched: dict[str, SourceRecord],
) -> tuple[SourceObservation, ...]:
    raw = payload.get("observations")
    if not isinstance(raw, list):
        raise ValueError("observations: expected list")
    observations = tuple(_load_observation(item, watched) for item in raw)
    if [item.source_id for item in observations] != sorted(watched):
        raise ValueError("observations: expected one sorted record per watched source")
    return observations


def _source_state_summaries(
    payload: dict[str, Any],
    observations: tuple[SourceObservation, ...],
    rules_path: Path,
    golden_path: Path,
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    changed = tuple(item.source_id for item in observations if item.status == "changed")
    unverifiable = tuple(
        item.source_id for item in observations if item.status == "unverifiable"
    )
    if (
        _exact_string_list(payload.get("changed_source_ids"), "changed_source_ids")
        != changed
    ):
        raise ValueError("source-state summary contradicts observations")
    if (
        _exact_string_list(
            payload.get("unverifiable_source_ids"),
            "unverifiable_source_ids",
        )
        != unverifiable
    ):
        raise ValueError("source-state summary contradicts observations")
    impact = _impact(rules_path, golden_path, changed)
    fields = (
        "affected_rule_ids",
        "unaffected_rule_ids",
        "affected_golden_case_ids",
        "unaffected_golden_case_ids",
    )
    for field, expected in zip(fields, impact, strict=True):
        if _exact_string_list(payload.get(field), field) != expected:
            raise ValueError(f"{field}: dependency impact drifted")
    return changed, unverifiable, *impact


def load_source_state_snapshot(
    path: Path,
    sources_path: Path,
    rules_path: Path,
    golden_path: Path,
    *,
    require_reviewed: bool = False,
) -> SourceStateSnapshot:
    """Load and re-derive a snapshot's exact dependency impact."""

    payload = _load_payload(path)
    return validate_source_state_payload(
        payload,
        sources_path,
        rules_path,
        golden_path,
        require_reviewed=require_reviewed,
    )


def validate_source_state_payload(
    payload: dict[str, Any],
    sources_path: Path,
    rules_path: Path,
    golden_path: Path,
    *,
    require_reviewed: bool = False,
) -> SourceStateSnapshot:
    """Re-derive a source-state payload against one explicit corpus."""

    if set(payload) != _TOP_LEVEL_KEYS:
        raise ValueError("source-state snapshot has invalid fields")
    snapshot_id, checked, expected_digest = _snapshot_header(payload, sources_path)
    receipt = _load_receipt(payload, require_reviewed=require_reviewed)
    observations = _load_observations(payload, _watched_sources(sources_path))
    (
        changed,
        unverifiable,
        affected,
        unaffected,
        affected_cases,
        unaffected_cases,
    ) = _source_state_summaries(payload, observations, rules_path, golden_path)

    return SourceStateSnapshot(
        schema_version=1,
        snapshot_id=snapshot_id,
        checked_at=checked,
        source_registry_sha256=expected_digest,
        receipt=receipt,
        observations=observations,
        changed_source_ids=changed,
        unverifiable_source_ids=unverifiable,
        affected_rule_ids=affected,
        unaffected_rule_ids=unaffected,
        affected_golden_case_ids=affected_cases,
        unaffected_golden_case_ids=unaffected_cases,
    )


def validate_source_state_snapshot(
    snapshot: SourceStateSnapshot,
    sources_path: Path,
    rules_path: Path,
    golden_path: Path,
    *,
    require_reviewed: bool = False,
) -> SourceStateSnapshot:
    """Re-derive a caller-supplied snapshot instead of trusting its dataclass."""

    if not isinstance(snapshot, SourceStateSnapshot):
        raise ValueError("source-state snapshot has invalid type")
    return validate_source_state_payload(
        snapshot.to_dict(),
        sources_path,
        rules_path,
        golden_path,
        require_reviewed=require_reviewed,
    )


def encoded_source_state(snapshot: SourceStateSnapshot) -> str:
    return (
        json.dumps(
            snapshot.to_dict(),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


@dataclass(frozen=True)
class WithdrawnCitation:
    """One published rule citation whose address answered "no document".

    This is a finding about the *link*, never about the law. The excerpt,
    the retained local copy, and the recorded hash all still stand, and the
    rule keeps whatever status its own review dates give it. What changed
    is that a reader who follows the citation gets nothing, so the citation
    must stop being presented as a working link.
    """

    rule_id: str
    source_id: str
    source_label: str
    url: str
    last_verified_on: str
    reason: str

    def describe(self) -> str:
        return (
            f"{self.rule_id}: cited source {self.source_id} answered "
            f"{self.reason} at its published address; the retained copy last "
            f"confirmed {self.last_verified_on} still stands, and no rule was "
            "marked stale, but the printed link does not resolve"
        )


def withdrawn_citations(
    snapshot: SourceStateSnapshot,
    sources_path: Path,
    rules_path: Path,
) -> tuple[WithdrawnCitation, ...]:
    """Return every rule whose own citation URL is recorded ``not_found``.

    A rule can also *depend* on a withdrawn source without citing it; that
    is a weaker finding and is deliberately not reported here, because the
    applicant-facing promise is about the one link the result card prints.
    """

    not_found = {
        item.source_id: item for item in snapshot.observations if item.is_not_found
    }
    if not not_found:
        return ()
    sources = load_sources(sources_path)
    by_url = {source.url: source for source in sources.values()}
    findings = [
        WithdrawnCitation(
            rule_id=rule.rule_id,
            source_id=source.source_id,
            source_label=source.label,
            url=source.url,
            last_verified_on=not_found[source.source_id].last_verified_on,
            reason=cast(str, not_found[source.source_id].reason),
        )
        for rule in load_rules(rules_path)
        if (source := by_url.get(rule.citation.url)) is not None
        and source.source_id in not_found
    ]
    return tuple(sorted(findings, key=lambda item: (item.rule_id, item.source_id)))
