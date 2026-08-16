"""Strict source-change approval, publication, and rollback receipts.

The re-verification decision ledger is intentionally not a release mechanism.
This module adds three separate evidence records around it.  Validation is
read-only: it never adopts a source-state receipt, clears a browser hold,
changes a rule, runs Git, deploys a build, or performs a rollback.

Committed templates remain ``not_run`` and may keep every evidence binding
null.  A bound prepared set can be generated only from an open, validated
worklist and its complete decision-ledger shape.  A completed approval further
requires every decision entry to be resolved; publication and rollback each
require their own later receipt and a separately validated reviewed
source-state snapshot.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import urlsplit

from .harness.runner import load_golden
from .harness.watch import load_sources
from .review_queue import (
    DECISION_DISPOSITIONS,
    DECISION_STATUSES,
    ReadinessReviewContext,
    ReviewDecision,
    ReviewDecisionLedger,
    ReviewWorklist,
    build_review_worklist,
)
from .screening import load_rules
from .source_state import (
    SourceStateSnapshot,
    source_state_fingerprint,
    validate_source_state_snapshot,
)

RECEIPT_SCHEMA_VERSION = 1
MAX_RECEIPT_BYTES = 262_144
APPROVAL_STATUSES = ("not_run", "complete")
APPROVAL_OUTCOMES = ("approved_for_publication", "rejected")
PUBLICATION_STATUSES = ("not_run", "complete")
ROLLBACK_STATUSES = ("not_run", "complete")
HOLD_STATES = ("clear_in_source_state", "retained_in_source_state")
ROLLBACK_REASONS = (
    "controlled_rehearsal",
    "content_defect",
    "deployment_verification_failure",
    "functional_regression",
)
SOURCE_RESOLUTIONS = ("adopt_observed", "restore_recorded", "retain_hold")

APPROVAL_CLAIM_BOUNDARY = (
    "This receipt is evidence metadata only. It does not clear a source-review "
    "hold, adopt source state, approve legal meaning, publish a build, or "
    "authenticate the declared reviewer authority or external evidence."
)
PUBLICATION_CLAIM_BOUNDARY = (
    "This receipt records separately verified publication evidence. Validation "
    "does not mutate the repository, adopt source state, deploy, or clear a hold; "
    "hold state is derived from the separately supplied published source receipt, "
    "and Git, the deployment URL, and external receipt IDs are not authenticated."
)
ROLLBACK_CLAIM_BOUNDARY = (
    "This receipt records separately verified rollback evidence. Validation does "
    "not run or authenticate Git, inspect the live deployment, deploy, restore "
    "data, authenticate external receipt IDs, or change source-review holds."
)

APPROVAL_EFFECTS: Mapping[str, bool] = MappingProxyType(
    {
        "decision_ledger_clears_source_hold": False,
        "decision_ledger_publishes": False,
        "validator_authenticates_external_evidence": False,
        "receipt_clears_source_hold": False,
        "receipt_publishes": False,
    }
)
PUBLICATION_EFFECTS: Mapping[str, bool] = MappingProxyType(
    {
        "validator_adopts_source_state": False,
        "validator_authenticates_external_evidence": False,
        "validator_clears_source_hold": False,
        "validator_deploys": False,
        "validator_mutates_repository": False,
    }
)
ROLLBACK_EFFECTS: Mapping[str, bool] = MappingProxyType(
    {
        "validator_authenticates_external_evidence": False,
        "validator_deploys": False,
        "validator_mutates_repository": False,
        "validator_restores_data": False,
    }
)
TEMPLATE_FINGERPRINTS_V1: Mapping[str, str] = MappingProxyType(
    {
        "approval": "sha256:7c17aa6ddb7969b4023f8ea9ee4a48f6c4172ae46a2cd1735fff7951d006b365",
        "publication": "sha256:73b41f1c37d2572b2e048af3f4c6d6013025a49d4f18d9409701e0e5a26621bd",
        "rollback": "sha256:125dd8dcbf6e5cc9333ad48cdc2436981a52a13b571eaac5e5535542c07d2e7c",
    }
)

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_OWNER_CODE = re.compile(r"^[A-Z][A-Z0-9_-]{1,15}$")
_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_INVALID_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")
_PLACEHOLDER_IDENTIFIERS = {
    "na",
    "none",
    "notapplicable",
    "not-run",
    "not_run",
    "notrun",
    "pending",
    "placeholder",
    "tbd",
    "todo",
    "unassigned",
    "unknown",
}


def _fingerprint(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


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


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise ValueError(f"receipt uses non-finite JSON value {value}")


def _load_json(path: Path) -> dict[str, Any]:
    descriptor = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"{path}: receipt input must be a regular file")
        if metadata.st_size > MAX_RECEIPT_BYTES:
            raise ValueError(
                f"{path}: receipt exceeds the {MAX_RECEIPT_BYTES}-byte limit"
            )
        with os.fdopen(descriptor, "rb", closefd=True) as source:
            descriptor = -1
            raw_bytes = source.read(MAX_RECEIPT_BYTES + 1)
    except ValueError:
        raise
    except OSError as error:
        raise ValueError(f"{path}: receipt could not be loaded") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw_bytes) > MAX_RECEIPT_BYTES:
        raise ValueError(f"{path}: receipt exceeds the {MAX_RECEIPT_BYTES}-byte limit")
    try:
        encoded = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"{path}: receipt is not valid UTF-8") from error
    try:
        raw = json.loads(
            encoded,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite_constant,
        )
    except (json.JSONDecodeError, RecursionError) as error:
        raise ValueError(f"{path}: receipt could not be loaded") from error
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return raw


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field}: expected a stable identifier")
    return value


def _optional_identifier(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _identifier(value, field)


def _evidence_identifier(value: Any, field: str) -> str:
    identifier = _identifier(value, field)
    if _contains_placeholder(identifier):
        raise ValueError(f"{field}: placeholder evidence identifiers are not allowed")
    return identifier


def _contains_placeholder(value: str) -> bool:
    normalized = re.sub(r"[-_.]", "", value.lower())
    tokens = {token for token in re.split(r"[-_.]", value.lower()) if token}
    return normalized in _PLACEHOLDER_IDENTIFIERS or bool(
        tokens & _PLACEHOLDER_IDENTIFIERS
    )


def _optional_evidence_identifier(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _evidence_identifier(value, field)


def _optional_fingerprint(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _FINGERPRINT.fullmatch(value):
        raise ValueError(f"{field}: expected a SHA-256 fingerprint or null")
    return value


def _choice(value: Any, allowed: tuple[str, ...], field: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{field}: expected one of {', '.join(allowed)}")
    return value


def _optional_choice(value: Any, allowed: tuple[str, ...], field: str) -> str | None:
    if value is None:
        return None
    return _choice(value, allowed, field)


def _owner_code(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _OWNER_CODE.fullmatch(value):
        raise ValueError(f"{field}: expected an opaque uppercase owner code or null")
    if _contains_placeholder(value):
        raise ValueError(f"{field}: placeholder owner codes are not allowed")
    return value


def _validation_now(value: datetime | None) -> datetime:
    now = value or datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise ValueError("validation time must be timezone-aware UTC")
    return now.astimezone(UTC)


def _timestamp(
    value: Any,
    field: str,
    *,
    now: datetime,
) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field}: expected a whole-second UTC timestamp or null")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError(f"{field}: invalid UTC timestamp") from error
    if parsed.tzinfo != UTC or parsed.microsecond or _timestamp_text(parsed) != value:
        raise ValueError(f"{field}: expected a whole-second UTC timestamp")
    if parsed > now:
        raise ValueError(f"{field}: future timestamps are not allowed")
    return parsed


def _timestamp_text(parsed: datetime | None) -> str | None:
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ") if parsed is not None else None


def _https_url(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(character.isspace() or ord(character) < 0x20 for character in value)
        or "\x7f" in value
        or "\\" in value
        or _INVALID_PERCENT_ESCAPE.search(value)
    ):
        raise ValueError(f"{field}: expected an HTTPS URL or null")
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError as error:
        raise ValueError(f"{field}: expected an HTTPS URL or null") from error
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.hostname != parsed.hostname.strip(".")
        or ".." in parsed.hostname
    ):
        raise ValueError(
            f"{field}: expected an HTTPS URL without credentials or fragment"
        )
    return value


def _optional_commit(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _COMMIT_SHA.fullmatch(value):
        raise ValueError(f"{field}: expected a full lowercase commit SHA or null")
    return value


def _receipt_ids(value: Any, field: str) -> tuple[str, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field}: expected a non-empty list or null")
    result = tuple(
        _evidence_identifier(item, f"{field}[{index}]")
        for index, item in enumerate(value)
    )
    if list(result) != sorted(result) or len(result) != len(set(result)):
        raise ValueError(f"{field}: expected sorted unique receipt IDs")
    return result


def _source_resolutions(value: Any) -> tuple[SourceResolution, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        raise ValueError(
            "decision.source_resolutions: expected a non-empty list or null"
        )
    resolutions: list[SourceResolution] = []
    for index, item in enumerate(value):
        field = f"decision.source_resolutions[{index}]"
        raw = _exact_keys(
            item,
            {
                "source_id",
                "source_record_fingerprint",
                "resolution",
                "target_sha256",
            },
            field,
        )
        source_id = _identifier(raw["source_id"], f"{field}.source_id")
        fingerprint = _optional_fingerprint(
            raw["source_record_fingerprint"],
            f"{field}.source_record_fingerprint",
        )
        if fingerprint is None:
            raise ValueError(f"{field}.source_record_fingerprint: value is required")
        resolution = _choice(
            raw["resolution"], SOURCE_RESOLUTIONS, f"{field}.resolution"
        )
        target = raw["target_sha256"]
        if target is not None and (
            not isinstance(target, str) or not _SHA256.fullmatch(target)
        ):
            raise ValueError(f"{field}.target_sha256: expected SHA-256 or null")
        if (resolution == "retain_hold") != (target is None):
            raise ValueError(
                f"{field}: retain_hold requires a null target; other resolutions "
                "require an exact target digest"
            )
        resolutions.append(SourceResolution(source_id, fingerprint, resolution, target))
    source_ids = [item.source_id for item in resolutions]
    if source_ids != sorted(source_ids) or len(source_ids) != len(set(source_ids)):
        raise ValueError(
            "decision.source_resolutions: expected one sorted record per source"
        )
    return tuple(resolutions)


def _validate_source_resolution_context(
    resolutions: tuple[SourceResolution, ...],
    context: ReleaseContext,
) -> None:
    changed = {source.source_id: source for source in context.worklist.changed_sources}
    source_items = {
        item.target_id: item
        for item in context.worklist.items
        if item.item_type == "source_reverification"
    }
    if [item.source_id for item in resolutions] != sorted(changed):
        raise ValueError(
            "decision.source_resolutions must cover every changed source exactly once"
        )
    for resolution in resolutions:
        source = changed[resolution.source_id]
        if (
            resolution.source_id not in source_items
            or resolution.source_record_fingerprint
            != source_items[resolution.source_id].target_fingerprint
        ):
            raise ValueError(
                "decision.source_resolutions source record fingerprint does not match"
            )
        expected = {
            "adopt_observed": source.observed_sha256,
            "restore_recorded": source.recorded_sha256,
            "retain_hold": None,
        }[resolution.resolution]
        if resolution.target_sha256 != expected:
            raise ValueError(
                "decision.source_resolutions target digest does not match its "
                "explicit resolution"
            )


@dataclass(frozen=True)
class ReleaseBinding:
    source_snapshot_id: str | None
    source_snapshot_fingerprint: str | None
    worklist_id: str | None
    worklist_fingerprint: str | None
    decision_ledger_fingerprint: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "source_snapshot_id": self.source_snapshot_id,
            "source_snapshot_fingerprint": self.source_snapshot_fingerprint,
            "worklist_id": self.worklist_id,
            "worklist_fingerprint": self.worklist_fingerprint,
            "decision_ledger_fingerprint": self.decision_ledger_fingerprint,
        }

    def is_empty(self) -> bool:
        return all(value is None for value in self.to_dict().values())

    def is_complete(self) -> bool:
        return all(value is not None for value in self.to_dict().values())


@dataclass(frozen=True)
class ReceiptReference:
    receipt_id: str | None
    receipt_fingerprint: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "receipt_id": self.receipt_id,
            "receipt_fingerprint": self.receipt_fingerprint,
        }

    def is_empty(self) -> bool:
        return self.receipt_id is None and self.receipt_fingerprint is None

    def is_complete(self) -> bool:
        return self.receipt_id is not None and self.receipt_fingerprint is not None


@dataclass(frozen=True)
class ReleaseContext:
    snapshot: SourceStateSnapshot
    worklist: ReviewWorklist
    decisions: ReviewDecisionLedger
    binding: ReleaseBinding
    sources_path: Path
    rules_path: Path
    golden_path: Path
    readiness_contexts: tuple[ReadinessReviewContext, ...]
    as_of: date | None
    input_fingerprints: tuple[str, str, str]


@dataclass(frozen=True)
class SourceResolution:
    source_id: str
    source_record_fingerprint: str
    resolution: str
    target_sha256: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "source_id": self.source_id,
            "source_record_fingerprint": self.source_record_fingerprint,
            "resolution": self.resolution,
            "target_sha256": self.target_sha256,
        }


@dataclass(frozen=True)
class ApprovalReceipt:
    receipt_id: str
    status: str
    binding: ReleaseBinding
    outcome: str | None
    reviewer_code: str | None
    authority_receipt_id: str | None
    decided_at: str | None
    evidence_receipt_ids: tuple[str, ...] | None
    source_resolutions: tuple[SourceResolution, ...] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "receipt_type": "source_change_approval",
            "receipt_id": self.receipt_id,
            "status": self.status,
            "claim_boundary": APPROVAL_CLAIM_BOUNDARY,
            "release_binding": self.binding.to_dict(),
            "decision": {
                "outcome": self.outcome,
                "reviewer_code": self.reviewer_code,
                "authority_receipt_id": self.authority_receipt_id,
                "decided_at": self.decided_at,
                "evidence_receipt_ids": (
                    list(self.evidence_receipt_ids)
                    if self.evidence_receipt_ids is not None
                    else None
                ),
                "source_resolutions": (
                    [resolution.to_dict() for resolution in self.source_resolutions]
                    if self.source_resolutions is not None
                    else None
                ),
            },
            "effects": dict(APPROVAL_EFFECTS),
        }

    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


@dataclass(frozen=True)
class PublicationReceipt:
    receipt_id: str
    status: str
    binding: ReleaseBinding
    approval: ReceiptReference
    actor_code: str | None
    started_at: str | None
    completed_at: str | None
    baseline_commit_sha: str | None
    published_commit_sha: str | None
    published_url: str | None
    published_source_snapshot_id: str | None
    published_source_snapshot_fingerprint: str | None
    hold_state: str | None
    verification_receipt_id: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "receipt_type": "source_change_publication",
            "receipt_id": self.receipt_id,
            "status": self.status,
            "claim_boundary": PUBLICATION_CLAIM_BOUNDARY,
            "release_binding": self.binding.to_dict(),
            "approval_receipt": self.approval.to_dict(),
            "publication": {
                "actor_code": self.actor_code,
                "started_at": self.started_at,
                "completed_at": self.completed_at,
                "baseline_commit_sha": self.baseline_commit_sha,
                "published_commit_sha": self.published_commit_sha,
                "published_url": self.published_url,
                "published_source_snapshot_id": self.published_source_snapshot_id,
                "published_source_snapshot_fingerprint": (
                    self.published_source_snapshot_fingerprint
                ),
                "hold_state": self.hold_state,
                "verification_receipt_id": self.verification_receipt_id,
            },
            "effects": dict(PUBLICATION_EFFECTS),
        }

    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


@dataclass(frozen=True)
class RollbackReceipt:
    receipt_id: str
    status: str
    binding: ReleaseBinding
    publication: ReceiptReference
    actor_code: str | None
    triggered_at: str | None
    completed_at: str | None
    reason: str | None
    restored_commit_sha: str | None
    restored_url: str | None
    restored_source_snapshot_id: str | None
    restored_source_snapshot_fingerprint: str | None
    hold_state: str | None
    verification_receipt_id: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "receipt_type": "source_change_rollback",
            "receipt_id": self.receipt_id,
            "status": self.status,
            "claim_boundary": ROLLBACK_CLAIM_BOUNDARY,
            "release_binding": self.binding.to_dict(),
            "publication_receipt": self.publication.to_dict(),
            "rollback": {
                "actor_code": self.actor_code,
                "triggered_at": self.triggered_at,
                "completed_at": self.completed_at,
                "reason": self.reason,
                "restored_commit_sha": self.restored_commit_sha,
                "restored_url": self.restored_url,
                "restored_source_snapshot_id": self.restored_source_snapshot_id,
                "restored_source_snapshot_fingerprint": (
                    self.restored_source_snapshot_fingerprint
                ),
                "hold_state": self.hold_state,
                "verification_receipt_id": self.verification_receipt_id,
            },
            "effects": dict(ROLLBACK_EFFECTS),
        }

    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


def build_release_context(
    snapshot: SourceStateSnapshot,
    worklist: ReviewWorklist,
    decisions: ReviewDecisionLedger,
    *,
    sources_path: Path,
    rules_path: Path,
    golden_path: Path,
    readiness_contexts: tuple[ReadinessReviewContext, ...] = (),
    as_of: date | None = None,
) -> ReleaseContext:
    """Re-derive and bind exact artifacts without interpreting publication."""

    canonical_sources_path = _canonical_input_path(sources_path, "sources_path")
    canonical_rules_path = _canonical_input_path(rules_path, "rules_path")
    canonical_golden_path = _canonical_input_path(golden_path, "golden_path")
    input_fingerprints = _input_fingerprints(
        canonical_sources_path,
        canonical_rules_path,
        canonical_golden_path,
    )
    canonical_snapshot = validate_source_state_snapshot(
        snapshot,
        canonical_sources_path,
        canonical_rules_path,
        canonical_golden_path,
    )
    sources = load_sources(canonical_sources_path, today=as_of)
    rules = load_rules(canonical_rules_path, today=as_of)
    golden_cases = load_golden(canonical_golden_path, rules)
    canonical_worklist = build_review_worklist(
        canonical_snapshot,
        sources,
        rules,
        golden_cases,
        readiness_contexts=readiness_contexts,
    )
    if worklist.to_dict() != canonical_worklist.to_dict():
        raise ValueError("worklist does not match the canonical affected-output set")
    if input_fingerprints != _input_fingerprints(
        canonical_sources_path,
        canonical_rules_path,
        canonical_golden_path,
    ):
        raise ValueError("source, rule, or Golden input changed during validation")
    return _context_from_artifacts(
        canonical_snapshot,
        worklist,
        decisions,
        sources_path=canonical_sources_path,
        rules_path=canonical_rules_path,
        golden_path=canonical_golden_path,
        readiness_contexts=readiness_contexts,
        as_of=as_of,
        input_fingerprints=input_fingerprints,
    )


def _canonical_input_path(path: Path, field: str) -> Path:
    if not isinstance(path, Path):
        raise ValueError(f"{field}: expected a filesystem path")
    try:
        return path.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"{field}: input does not exist") from error


def _raw_input_fingerprint(path: Path) -> str:
    """Fingerprint the exact loader-visible bytes around context derivation."""

    if path.is_dir():
        files = sorted(
            item for item in path.glob("*.json") if item.name != "index.json"
        )
        if not files:
            raise ValueError(f"{path}: no input files found")
    else:
        files = [path]
    digest = hashlib.sha256()
    for item in files:
        try:
            relative = item.relative_to(path) if path.is_dir() else Path(item.name)
            raw = item.read_bytes()
        except OSError as error:
            raise ValueError(f"{item}: input could not be fingerprinted") from error
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return "sha256:" + digest.hexdigest()


def _input_fingerprints(
    sources_path: Path,
    rules_path: Path,
    golden_path: Path,
) -> tuple[str, str, str]:
    return (
        _raw_input_fingerprint(sources_path),
        _raw_input_fingerprint(rules_path),
        _raw_input_fingerprint(golden_path),
    )


def _context_from_artifacts(
    snapshot: SourceStateSnapshot,
    worklist: ReviewWorklist,
    decisions: ReviewDecisionLedger,
    *,
    sources_path: Path,
    rules_path: Path,
    golden_path: Path,
    readiness_contexts: tuple[ReadinessReviewContext, ...],
    as_of: date | None,
    input_fingerprints: tuple[str, str, str],
) -> ReleaseContext:
    """Recheck bindings for an already canonically derived in-process context."""

    snapshot_fingerprint = source_state_fingerprint(snapshot)
    _validate_worklist_context(snapshot, snapshot_fingerprint, worklist)
    _validate_decision_context(worklist, decisions)
    binding = ReleaseBinding(
        source_snapshot_id=snapshot.snapshot_id,
        source_snapshot_fingerprint=snapshot_fingerprint,
        worklist_id=worklist.worklist_id,
        worklist_fingerprint=worklist.fingerprint(),
        decision_ledger_fingerprint=decisions.fingerprint(),
    )
    return ReleaseContext(
        snapshot,
        worklist,
        decisions,
        binding,
        sources_path,
        rules_path,
        golden_path,
        readiness_contexts,
        as_of,
        input_fingerprints,
    )


def _validate_worklist_context(
    snapshot: SourceStateSnapshot,
    snapshot_fingerprint: str,
    worklist: ReviewWorklist,
) -> None:
    if worklist.source_snapshot_id != snapshot.snapshot_id:
        raise ValueError("worklist source snapshot ID does not match")
    if worklist.source_snapshot_fingerprint != snapshot_fingerprint:
        raise ValueError("worklist source snapshot fingerprint does not match")
    if worklist.receipt_status != snapshot.receipt.status:
        raise ValueError("worklist source receipt status does not match")
    if worklist.changed_source_ids != snapshot.changed_source_ids:
        raise ValueError("worklist changed-source IDs do not match")
    if worklist.status != "open" or not snapshot.changed_source_ids:
        raise ValueError("source release requires an open changed-source worklist")


def _validate_decision_context(
    worklist: ReviewWorklist,
    decisions: ReviewDecisionLedger,
) -> None:
    if decisions.worklist_id != worklist.worklist_id:
        raise ValueError("decision ledger worklist ID does not match")
    if decisions.worklist_fingerprint != worklist.fingerprint():
        raise ValueError("decision ledger worklist fingerprint does not match")
    items = worklist.item_map()
    decision_ids = [entry.item_id for entry in decisions.entries]
    if decision_ids != sorted(items) or len(decision_ids) != len(set(decision_ids)):
        raise ValueError("decision ledger must cover every work item exactly once")
    for entry in decisions.entries:
        if entry.item_fingerprint != items[entry.item_id].fingerprint():
            raise ValueError("decision ledger item fingerprint does not match")
        _validate_context_decision(entry)


def _validate_context_decision(entry: ReviewDecision) -> None:
    if entry.status not in DECISION_STATUSES:
        raise ValueError("decision ledger contains an invalid status")
    if entry.owner_code is not None:
        _owner_code(entry.owner_code, "decision ledger owner code")
    if entry.disposition is not None and entry.disposition not in DECISION_DISPOSITIONS:
        raise ValueError("decision ledger contains an invalid disposition")
    if entry.evidence_receipt_id is not None:
        _evidence_identifier(
            entry.evidence_receipt_id, "decision ledger evidence receipt ID"
        )
    assigned = _ledger_date(entry.assigned_on, "assigned_on")
    decided = _ledger_date(entry.decided_on, "decided_on")
    values = (
        entry.owner_code,
        entry.assigned_on,
        entry.disposition,
        entry.decided_on,
        entry.evidence_receipt_id,
    )
    if entry.status == "unassigned" and any(values):
        raise ValueError("unassigned decision ledger entry carries metadata")
    if entry.status == "assigned" and (
        entry.owner_code is None or assigned is None or any(values[2:])
    ):
        raise ValueError("assigned decision ledger entry has invalid metadata")
    if entry.status == "resolved" and (
        not all(values) or assigned is None or decided is None or decided < assigned
    ):
        raise ValueError("resolved decision ledger entry has invalid metadata")


def _ledger_date(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"decision ledger contains an invalid {field} date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"decision ledger contains an invalid {field} date") from error
    if parsed.isoformat() != value:
        raise ValueError(f"decision ledger contains an invalid {field} date")
    return parsed


def _empty_binding() -> ReleaseBinding:
    return ReleaseBinding(None, None, None, None, None)


def approval_template(
    receipt_id: str = "source-change-approval-template",
) -> ApprovalReceipt:
    return ApprovalReceipt(
        receipt_id=_identifier(receipt_id, "receipt_id"),
        status="not_run",
        binding=_empty_binding(),
        outcome=None,
        reviewer_code=None,
        authority_receipt_id=None,
        decided_at=None,
        evidence_receipt_ids=None,
        source_resolutions=None,
    )


def publication_template(
    receipt_id: str = "source-change-publication-template",
) -> PublicationReceipt:
    return PublicationReceipt(
        receipt_id=_identifier(receipt_id, "receipt_id"),
        status="not_run",
        binding=_empty_binding(),
        approval=ReceiptReference(None, None),
        actor_code=None,
        started_at=None,
        completed_at=None,
        baseline_commit_sha=None,
        published_commit_sha=None,
        published_url=None,
        published_source_snapshot_id=None,
        published_source_snapshot_fingerprint=None,
        hold_state=None,
        verification_receipt_id=None,
    )


def rollback_template(
    receipt_id: str = "source-change-rollback-template",
) -> RollbackReceipt:
    return RollbackReceipt(
        receipt_id=_identifier(receipt_id, "receipt_id"),
        status="not_run",
        binding=_empty_binding(),
        publication=ReceiptReference(None, None),
        actor_code=None,
        triggered_at=None,
        completed_at=None,
        reason=None,
        restored_commit_sha=None,
        restored_url=None,
        restored_source_snapshot_id=None,
        restored_source_snapshot_fingerprint=None,
        hold_state=None,
        verification_receipt_id=None,
    )


def prepared_receipts(
    release_id: str,
    context: ReleaseContext,
) -> tuple[ApprovalReceipt, PublicationReceipt, RollbackReceipt]:
    """Create bound ``not_run`` receipts without creating an approval claim."""

    context = _validated_context(context)
    stable_id = _evidence_identifier(release_id, "release_id")
    approval = approval_template(f"{stable_id}-approval")
    approval = ApprovalReceipt(
        receipt_id=approval.receipt_id,
        status=approval.status,
        binding=context.binding,
        outcome=None,
        reviewer_code=None,
        authority_receipt_id=None,
        decided_at=None,
        evidence_receipt_ids=None,
        source_resolutions=None,
    )
    publication = publication_template(f"{stable_id}-publication")
    publication = PublicationReceipt(
        receipt_id=publication.receipt_id,
        status=publication.status,
        binding=context.binding,
        approval=ReceiptReference(approval.receipt_id, approval.fingerprint()),
        actor_code=None,
        started_at=None,
        completed_at=None,
        baseline_commit_sha=None,
        published_commit_sha=None,
        published_url=None,
        published_source_snapshot_id=None,
        published_source_snapshot_fingerprint=None,
        hold_state=None,
        verification_receipt_id=None,
    )
    rollback = rollback_template(f"{stable_id}-rollback")
    rollback = RollbackReceipt(
        receipt_id=rollback.receipt_id,
        status=rollback.status,
        binding=context.binding,
        publication=ReceiptReference(publication.receipt_id, publication.fingerprint()),
        actor_code=None,
        triggered_at=None,
        completed_at=None,
        reason=None,
        restored_commit_sha=None,
        restored_url=None,
        restored_source_snapshot_id=None,
        restored_source_snapshot_fingerprint=None,
        hold_state=None,
        verification_receipt_id=None,
    )
    return approval, publication, rollback


def encoded_receipt(
    receipt: ApprovalReceipt | PublicationReceipt | RollbackReceipt,
) -> str:
    return (
        json.dumps(receipt.to_dict(), ensure_ascii=True, indent=2, sort_keys=True)
        + "\n"
    )


def _parse_binding(raw: Any, field: str) -> ReleaseBinding:
    record = _exact_keys(
        raw,
        {
            "source_snapshot_id",
            "source_snapshot_fingerprint",
            "worklist_id",
            "worklist_fingerprint",
            "decision_ledger_fingerprint",
        },
        field,
    )
    binding = ReleaseBinding(
        source_snapshot_id=_optional_identifier(
            record["source_snapshot_id"], f"{field}.source_snapshot_id"
        ),
        source_snapshot_fingerprint=_optional_fingerprint(
            record["source_snapshot_fingerprint"],
            f"{field}.source_snapshot_fingerprint",
        ),
        worklist_id=_optional_identifier(record["worklist_id"], f"{field}.worklist_id"),
        worklist_fingerprint=_optional_fingerprint(
            record["worklist_fingerprint"], f"{field}.worklist_fingerprint"
        ),
        decision_ledger_fingerprint=_optional_fingerprint(
            record["decision_ledger_fingerprint"],
            f"{field}.decision_ledger_fingerprint",
        ),
    )
    if not binding.is_empty() and not binding.is_complete():
        raise ValueError(f"{field}: bindings must be entirely null or complete")
    return binding


def _parse_reference(raw: Any, field: str) -> ReceiptReference:
    record = _exact_keys(raw, {"receipt_id", "receipt_fingerprint"}, field)
    reference = ReceiptReference(
        receipt_id=_optional_identifier(record["receipt_id"], f"{field}.receipt_id"),
        receipt_fingerprint=_optional_fingerprint(
            record["receipt_fingerprint"], f"{field}.receipt_fingerprint"
        ),
    )
    if not reference.is_empty() and not reference.is_complete():
        raise ValueError(
            f"{field}: receipt reference must be entirely null or complete"
        )
    return reference


def _validate_common(
    raw: dict[str, Any],
    *,
    receipt_type: str,
    claim_boundary: str,
    effects: Mapping[str, bool],
) -> tuple[str, ReleaseBinding]:
    if (
        type(raw["schema_version"]) is not int
        or raw["schema_version"] != RECEIPT_SCHEMA_VERSION
    ):
        raise ValueError(f"schema_version: expected {RECEIPT_SCHEMA_VERSION}")
    if raw["receipt_type"] != receipt_type:
        raise ValueError(f"receipt_type: expected {receipt_type}")
    if raw["claim_boundary"] != claim_boundary:
        raise ValueError(
            "claim_boundary: expected the canonical non-promoting boundary"
        )
    raw_effects = _exact_keys(raw["effects"], set(effects), "effects")
    if any(
        type(raw_effects[key]) is not bool or raw_effects[key] is not expected
        for key, expected in effects.items()
    ):
        raise ValueError(
            "effects: receipt cannot be given mutating or promoting effects"
        )
    receipt_id = _identifier(raw["receipt_id"], "receipt_id")
    return receipt_id, _parse_binding(raw["release_binding"], "release_binding")


def _validate_receipt_id_for_state(
    receipt_id: str,
    status: str,
    binding: ReleaseBinding,
) -> None:
    if status == "complete" or binding.is_complete():
        _evidence_identifier(receipt_id, "receipt_id")


def _validate_binding(
    binding: ReleaseBinding,
    context: ReleaseContext | None,
    *,
    completed: bool,
) -> None:
    if completed and context is None:
        raise ValueError("completed receipt requires exact release artifacts")
    if context is None:
        if not binding.is_empty():
            raise ValueError("bound receipt requires exact release artifacts")
        return
    validated = _validated_context(context)
    if binding != validated.binding:
        raise ValueError(
            "release binding does not match source state, worklist, and ledger"
        )


def _validated_context(context: ReleaseContext) -> ReleaseContext:
    if not isinstance(context, ReleaseContext):
        raise ValueError("release context has invalid type")
    validated = build_release_context(
        context.snapshot,
        context.worklist,
        context.decisions,
        sources_path=context.sources_path,
        rules_path=context.rules_path,
        golden_path=context.golden_path,
        readiness_contexts=context.readiness_contexts,
        as_of=context.as_of,
    )
    if context != validated:
        raise ValueError(
            "release context binding does not match source state, worklist, and ledger"
        )
    return validated


def _all_null(values: tuple[object | None, ...], field: str) -> None:
    if any(value is not None for value in values):
        raise ValueError(f"{field}: not_run receipt cannot carry execution evidence")


def _resolved_decisions(context: ReleaseContext) -> None:
    if not context.decisions.entries or any(
        entry.status != "resolved" for entry in context.decisions.entries
    ):
        raise ValueError(
            "approval requires every exact worklist decision to be resolved"
        )


def _approval_from_payload(
    payload: dict[str, Any],
    context: ReleaseContext | None,
    *,
    as_of: datetime,
    field: str,
) -> ApprovalReceipt:
    raw = _exact_keys(
        payload,
        {
            "schema_version",
            "receipt_type",
            "receipt_id",
            "status",
            "claim_boundary",
            "release_binding",
            "decision",
            "effects",
        },
        field,
    )
    receipt_id, binding = _validate_common(
        raw,
        receipt_type="source_change_approval",
        claim_boundary=APPROVAL_CLAIM_BOUNDARY,
        effects=APPROVAL_EFFECTS,
    )
    status = _choice(raw["status"], APPROVAL_STATUSES, "status")
    _validate_receipt_id_for_state(receipt_id, status, binding)
    decision = _exact_keys(
        raw["decision"],
        {
            "outcome",
            "reviewer_code",
            "authority_receipt_id",
            "decided_at",
            "evidence_receipt_ids",
            "source_resolutions",
        },
        "decision",
    )
    outcome = _optional_choice(
        decision["outcome"], APPROVAL_OUTCOMES, "decision.outcome"
    )
    reviewer_code = _owner_code(decision["reviewer_code"], "decision.reviewer_code")
    authority_receipt_id = _optional_evidence_identifier(
        decision["authority_receipt_id"], "decision.authority_receipt_id"
    )
    decided = _timestamp(decision["decided_at"], "decision.decided_at", now=as_of)
    evidence = _receipt_ids(
        decision["evidence_receipt_ids"], "decision.evidence_receipt_ids"
    )
    resolutions = _source_resolutions(decision["source_resolutions"])
    fields = (
        outcome,
        reviewer_code,
        authority_receipt_id,
        decided,
        evidence,
        resolutions,
    )
    completed = status == "complete"
    _validate_binding(binding, context, completed=completed)
    if not completed:
        _all_null(fields, "decision")
    else:
        if any(value is None for value in fields):
            raise ValueError("complete approval lacks required decision evidence")
        if context is None or decided is None:
            raise AssertionError("completed approval context was not validated")
        _resolved_decisions(context)
        if resolutions is None:
            raise AssertionError("completed approval resolutions were not validated")
        _validate_source_resolution_context(resolutions, context)
        if outcome == "rejected" and any(
            item.resolution != "retain_hold" for item in resolutions
        ):
            raise ValueError("rejected approval must retain every changed-source hold")
        snapshot_checked = datetime.fromisoformat(
            context.snapshot.checked_at[:-1] + "+00:00"
        )
        if decided < snapshot_checked:
            raise ValueError("approval cannot predate the changed-source snapshot")
        decided_date = decided.date()
        if any(
            entry.decided_on is None
            or date.fromisoformat(entry.decided_on) > decided_date
            for entry in context.decisions.entries
        ):
            raise ValueError(
                "approval date cannot precede a bound work-item decision date"
            )
    return ApprovalReceipt(
        receipt_id=receipt_id,
        status=status,
        binding=binding,
        outcome=outcome,
        reviewer_code=reviewer_code,
        authority_receipt_id=authority_receipt_id,
        decided_at=_timestamp_text(decided),
        evidence_receipt_ids=evidence,
        source_resolutions=resolutions,
    )


def load_approval_receipt(
    path: Path,
    context: ReleaseContext | None = None,
    *,
    now: datetime | None = None,
) -> ApprovalReceipt:
    return _approval_from_payload(
        _load_json(path),
        context,
        as_of=_validation_now(now),
        field=str(path),
    )


def _expected_reference(
    reference: ReceiptReference,
    receipt_id: str,
    receipt_fingerprint: str,
    field: str,
) -> None:
    if reference != ReceiptReference(receipt_id, receipt_fingerprint):
        raise ValueError(f"{field}: receipt ID or fingerprint does not match")


def _validated_transition_snapshot(
    snapshot: SourceStateSnapshot,
    context: ReleaseContext,
    *,
    sources_path: Path | None,
    rules_path: Path | None,
    golden_path: Path | None,
) -> SourceStateSnapshot:
    supplied = (sources_path, rules_path, golden_path)
    if any(path is not None for path in supplied) and not all(
        path is not None for path in supplied
    ):
        raise ValueError(
            "transition source-state validation requires sources, rules, and Golden paths"
        )
    return validate_source_state_snapshot(
        snapshot,
        sources_path or context.sources_path,
        rules_path or context.rules_path,
        golden_path or context.golden_path,
        require_reviewed=True,
    )


def _transition_observations(
    context: ReleaseContext,
    state: SourceStateSnapshot,
) -> dict[str, Any]:
    observations = {item.source_id: item for item in state.observations}
    missing = sorted(set(context.snapshot.changed_source_ids) - set(observations))
    if missing:
        raise ValueError(
            "target source state does not contain every previously changed source: "
            + ", ".join(missing)
        )
    prior_changes = {
        source_id: observations[source_id]
        for source_id in context.snapshot.changed_source_ids
    }
    unverifiable = sorted(
        item.source_id
        for item in prior_changes.values()
        if item.status == "unverifiable"
    )
    if unverifiable:
        raise ValueError(
            "target source state cannot resolve a previously changed source as "
            "unverifiable: " + ", ".join(unverifiable)
        )
    for observation in prior_changes.values():
        if observation.status == "unchanged" and (
            observation.observed_sha256 is None
            or observation.observed_sha256 != observation.recorded_sha256
        ):
            raise ValueError(
                "target source state has invalid unchanged evidence for "
                f"{observation.source_id}"
            )
        if observation.status not in ("unchanged", "changed"):
            raise ValueError(
                f"target source state has invalid evidence for {observation.source_id}"
            )
    return prior_changes


def _publication_resolution_digests(
    context: ReleaseContext,
    approval: ApprovalReceipt,
) -> dict[str, tuple[str | None, str]]:
    changed_sources = {
        source.source_id: source for source in context.worklist.changed_sources
    }
    if set(changed_sources) != set(context.snapshot.changed_source_ids):
        raise ValueError("worklist changed-source evidence is incomplete")
    if approval.source_resolutions is None:
        raise ValueError("publication requires explicit per-source resolutions")
    _validate_source_resolution_context(approval.source_resolutions, context)
    result: dict[str, tuple[str | None, str]] = {}
    for resolution in approval.source_resolutions:
        source_id = resolution.source_id
        source = changed_sources[source_id]
        observation = next(
            item
            for item in context.snapshot.observations
            if item.source_id == source_id
        )
        if (
            source.recorded_sha256 != observation.recorded_sha256
            or source.observed_sha256 != observation.observed_sha256
        ):
            raise ValueError("worklist changed-source digest evidence does not match")
        result[source_id] = (resolution.target_sha256, resolution.resolution)
    return result


def _publication_hold_state(
    context: ReleaseContext,
    approval: ApprovalReceipt,
    state: SourceStateSnapshot,
) -> str:
    observations = _transition_observations(context, state)
    expected_digests = _publication_resolution_digests(context, approval)
    retained = False
    for source_id, observation in observations.items():
        expected, resolution = expected_digests[source_id]
        if observation.status == "changed":
            retained = True
            continue
        if expected is None:
            raise ValueError(
                "publication cannot clear a source with explicit resolution "
                f"{resolution!r} for {source_id}"
            )
        if (
            observation.recorded_sha256 != expected
            or observation.observed_sha256 != expected
        ):
            raise ValueError(
                "published source digest does not match the bound source "
                f"disposition for {source_id}"
            )
    return "retained_in_source_state" if retained else "clear_in_source_state"


def _rollback_hold_state(
    context: ReleaseContext,
    state: SourceStateSnapshot,
) -> str:
    observations = _transition_observations(context, state)
    baseline = {
        source.source_id: source.recorded_sha256
        for source in context.worklist.changed_sources
    }
    if set(baseline) != set(context.snapshot.changed_source_ids):
        raise ValueError("worklist changed-source evidence is incomplete")
    retained = False
    for source_id, observation in observations.items():
        if observation.status == "changed":
            retained = True
            continue
        if (
            observation.recorded_sha256 != baseline[source_id]
            or observation.observed_sha256 != baseline[source_id]
        ):
            raise ValueError(
                f"restored source digest does not match the baseline for {source_id}"
            )
    return "retained_in_source_state" if retained else "clear_in_source_state"


@dataclass(frozen=True)
class _PublicationEvidence:
    actor: str | None
    started: datetime | None
    completed: datetime | None
    baseline_commit: str | None
    published_commit: str | None
    published_url: str | None
    published_snapshot_id: str | None
    published_snapshot_fingerprint: str | None
    hold_state: str | None
    verification_receipt_id: str | None

    def values(self) -> tuple[object | None, ...]:
        return (
            self.actor,
            self.started,
            self.completed,
            self.baseline_commit,
            self.published_commit,
            self.published_url,
            self.published_snapshot_id,
            self.published_snapshot_fingerprint,
            self.hold_state,
            self.verification_receipt_id,
        )


def _publication_evidence(
    raw: Any,
    *,
    now: datetime,
) -> _PublicationEvidence:
    publication = _exact_keys(
        raw,
        {
            "actor_code",
            "started_at",
            "completed_at",
            "baseline_commit_sha",
            "published_commit_sha",
            "published_url",
            "published_source_snapshot_id",
            "published_source_snapshot_fingerprint",
            "hold_state",
            "verification_receipt_id",
        },
        "publication",
    )
    return _PublicationEvidence(
        actor=_owner_code(publication["actor_code"], "publication.actor_code"),
        started=_timestamp(
            publication["started_at"], "publication.started_at", now=now
        ),
        completed=_timestamp(
            publication["completed_at"], "publication.completed_at", now=now
        ),
        baseline_commit=_optional_commit(
            publication["baseline_commit_sha"], "publication.baseline_commit_sha"
        ),
        published_commit=_optional_commit(
            publication["published_commit_sha"], "publication.published_commit_sha"
        ),
        published_url=_https_url(
            publication["published_url"], "publication.published_url"
        ),
        published_snapshot_id=_optional_identifier(
            publication["published_source_snapshot_id"],
            "publication.published_source_snapshot_id",
        ),
        published_snapshot_fingerprint=_optional_fingerprint(
            publication["published_source_snapshot_fingerprint"],
            "publication.published_source_snapshot_fingerprint",
        ),
        hold_state=_optional_choice(
            publication["hold_state"], HOLD_STATES, "publication.hold_state"
        ),
        verification_receipt_id=_optional_evidence_identifier(
            publication["verification_receipt_id"],
            "publication.verification_receipt_id",
        ),
    )


def _validate_optional_reference(
    reference: ReceiptReference,
    receipt: ApprovalReceipt | PublicationReceipt | None,
    field: str,
    *,
    required: bool,
) -> None:
    if reference.is_empty():
        if required:
            raise ValueError(f"bound {field} requires a complete receipt reference")
        return
    if not reference.is_complete():
        raise ValueError(f"{field}: expected a complete or null reference")
    if receipt is None:
        raise ValueError(f"bound {field} requires its referenced receipt")
    _expected_reference(reference, receipt.receipt_id, receipt.fingerprint(), field)


def _validate_publication_snapshot(
    evidence: _PublicationEvidence,
    context: ReleaseContext,
    approval: ApprovalReceipt,
    published_snapshot: SourceStateSnapshot,
    *,
    sources_path: Path | None,
    rules_path: Path | None,
    golden_path: Path | None,
) -> None:
    published_snapshot = _validated_transition_snapshot(
        published_snapshot,
        context,
        sources_path=sources_path,
        rules_path=rules_path,
        golden_path=golden_path,
    )
    if published_snapshot.receipt.status != "reviewed":
        raise ValueError("published source state must be a reviewed receipt")
    if published_snapshot.receipt.commit_sha != evidence.published_commit:
        raise ValueError("published source-state commit does not match publication")
    if published_snapshot.snapshot_id != evidence.published_snapshot_id:
        raise ValueError("published source-state snapshot ID does not match")
    expected_fingerprint = source_state_fingerprint(published_snapshot)
    if evidence.published_snapshot_fingerprint != expected_fingerprint:
        raise ValueError("published source-state fingerprint does not match")
    expected_hold = _publication_hold_state(context, approval, published_snapshot)
    if evidence.hold_state != expected_hold:
        raise ValueError("publication hold state does not match published source state")
    if evidence.completed is None:
        raise AssertionError("completed publication timestamp was not validated")
    published_checked = datetime.fromisoformat(
        published_snapshot.checked_at[:-1] + "+00:00"
    )
    changed_checked = datetime.fromisoformat(
        context.snapshot.checked_at[:-1] + "+00:00"
    )
    if published_checked < changed_checked or published_checked > evidence.completed:
        raise ValueError("published source-state chronology is invalid")


def _validate_completed_publication(
    evidence: _PublicationEvidence,
    reference: ReceiptReference,
    approval: ApprovalReceipt | None,
    context: ReleaseContext | None,
    published_snapshot: SourceStateSnapshot | None,
    *,
    published_sources_path: Path | None,
    published_rules_path: Path | None,
    published_golden_path: Path | None,
) -> None:
    if any(value is None for value in evidence.values()):
        raise ValueError("complete publication lacks required evidence")
    if approval is None or context is None or published_snapshot is None:
        raise ValueError(
            "complete publication requires approval and source-state evidence"
        )
    _expected_reference(
        reference, approval.receipt_id, approval.fingerprint(), "approval_receipt"
    )
    if approval.binding != context.binding:
        raise ValueError("approval receipt release binding does not match publication")
    if approval.status != "complete" or approval.outcome != "approved_for_publication":
        raise ValueError(
            "publication requires a completed approval-for-publication receipt"
        )
    if (
        evidence.started is None
        or evidence.completed is None
        or approval.decided_at is None
    ):
        raise AssertionError("completed publication chronology was not validated")
    approval_time = datetime.fromisoformat(approval.decided_at[:-1] + "+00:00")
    if evidence.started < approval_time or evidence.completed < evidence.started:
        raise ValueError("publication chronology is invalid")
    if evidence.baseline_commit != context.snapshot.receipt.commit_sha:
        raise ValueError("publication baseline commit does not match source receipt")
    if evidence.published_commit == evidence.baseline_commit:
        raise ValueError("published commit must differ from the baseline commit")
    _validate_publication_snapshot(
        evidence,
        context,
        approval,
        published_snapshot,
        sources_path=published_sources_path,
        rules_path=published_rules_path,
        golden_path=published_golden_path,
    )


def _publication_from_payload(
    payload: dict[str, Any],
    approval: ApprovalReceipt | None = None,
    context: ReleaseContext | None = None,
    published_snapshot: SourceStateSnapshot | None = None,
    *,
    published_sources_path: Path | None = None,
    published_rules_path: Path | None = None,
    published_golden_path: Path | None = None,
    as_of: datetime,
    field: str,
) -> PublicationReceipt:
    raw = _exact_keys(
        payload,
        {
            "schema_version",
            "receipt_type",
            "receipt_id",
            "status",
            "claim_boundary",
            "release_binding",
            "approval_receipt",
            "publication",
            "effects",
        },
        field,
    )
    receipt_id, binding = _validate_common(
        raw,
        receipt_type="source_change_publication",
        claim_boundary=PUBLICATION_CLAIM_BOUNDARY,
        effects=PUBLICATION_EFFECTS,
    )
    status = _choice(raw["status"], PUBLICATION_STATUSES, "status")
    _validate_receipt_id_for_state(receipt_id, status, binding)
    reference = _parse_reference(raw["approval_receipt"], "approval_receipt")
    evidence = _publication_evidence(raw["publication"], now=as_of)
    validated_approval = (
        _approval_from_payload(
            approval.to_dict(),
            context,
            as_of=as_of,
            field="approval_receipt",
        )
        if approval is not None
        else None
    )
    completed = status == "complete"
    _validate_binding(binding, context, completed=completed)
    if not completed:
        _all_null(evidence.values(), "publication")
        _validate_optional_reference(
            reference,
            validated_approval,
            "approval_receipt",
            required=binding.is_complete(),
        )
    else:
        _validate_completed_publication(
            evidence,
            reference,
            validated_approval,
            context,
            published_snapshot,
            published_sources_path=published_sources_path,
            published_rules_path=published_rules_path,
            published_golden_path=published_golden_path,
        )
    return PublicationReceipt(
        receipt_id=receipt_id,
        status=status,
        binding=binding,
        approval=reference,
        actor_code=evidence.actor,
        started_at=_timestamp_text(evidence.started),
        completed_at=_timestamp_text(evidence.completed),
        baseline_commit_sha=evidence.baseline_commit,
        published_commit_sha=evidence.published_commit,
        published_url=evidence.published_url,
        published_source_snapshot_id=evidence.published_snapshot_id,
        published_source_snapshot_fingerprint=evidence.published_snapshot_fingerprint,
        hold_state=evidence.hold_state,
        verification_receipt_id=evidence.verification_receipt_id,
    )


def load_publication_receipt(
    path: Path,
    approval: ApprovalReceipt | None = None,
    context: ReleaseContext | None = None,
    published_snapshot: SourceStateSnapshot | None = None,
    *,
    published_sources_path: Path | None = None,
    published_rules_path: Path | None = None,
    published_golden_path: Path | None = None,
    now: datetime | None = None,
) -> PublicationReceipt:
    return _publication_from_payload(
        _load_json(path),
        approval,
        context,
        published_snapshot,
        published_sources_path=published_sources_path,
        published_rules_path=published_rules_path,
        published_golden_path=published_golden_path,
        as_of=_validation_now(now),
        field=str(path),
    )


@dataclass(frozen=True)
class _RollbackEvidence:
    actor: str | None
    triggered: datetime | None
    completed: datetime | None
    reason: str | None
    restored_commit: str | None
    restored_url: str | None
    restored_snapshot_id: str | None
    restored_snapshot_fingerprint: str | None
    hold_state: str | None
    verification_receipt_id: str | None

    def values(self) -> tuple[object | None, ...]:
        return (
            self.actor,
            self.triggered,
            self.completed,
            self.reason,
            self.restored_commit,
            self.restored_url,
            self.restored_snapshot_id,
            self.restored_snapshot_fingerprint,
            self.hold_state,
            self.verification_receipt_id,
        )


def _rollback_evidence(raw: Any, *, now: datetime) -> _RollbackEvidence:
    rollback = _exact_keys(
        raw,
        {
            "actor_code",
            "triggered_at",
            "completed_at",
            "reason",
            "restored_commit_sha",
            "restored_url",
            "restored_source_snapshot_id",
            "restored_source_snapshot_fingerprint",
            "hold_state",
            "verification_receipt_id",
        },
        "rollback",
    )
    return _RollbackEvidence(
        actor=_owner_code(rollback["actor_code"], "rollback.actor_code"),
        triggered=_timestamp(
            rollback["triggered_at"], "rollback.triggered_at", now=now
        ),
        completed=_timestamp(
            rollback["completed_at"], "rollback.completed_at", now=now
        ),
        reason=_optional_choice(
            rollback["reason"], ROLLBACK_REASONS, "rollback.reason"
        ),
        restored_commit=_optional_commit(
            rollback["restored_commit_sha"], "rollback.restored_commit_sha"
        ),
        restored_url=_https_url(rollback["restored_url"], "rollback.restored_url"),
        restored_snapshot_id=_optional_identifier(
            rollback["restored_source_snapshot_id"],
            "rollback.restored_source_snapshot_id",
        ),
        restored_snapshot_fingerprint=_optional_fingerprint(
            rollback["restored_source_snapshot_fingerprint"],
            "rollback.restored_source_snapshot_fingerprint",
        ),
        hold_state=_optional_choice(
            rollback["hold_state"], HOLD_STATES, "rollback.hold_state"
        ),
        verification_receipt_id=_optional_evidence_identifier(
            rollback["verification_receipt_id"], "rollback.verification_receipt_id"
        ),
    )


def _validate_restored_snapshot(
    evidence: _RollbackEvidence,
    context: ReleaseContext,
    restored_snapshot: SourceStateSnapshot,
    *,
    sources_path: Path | None,
    rules_path: Path | None,
    golden_path: Path | None,
) -> None:
    restored_snapshot = _validated_transition_snapshot(
        restored_snapshot,
        context,
        sources_path=sources_path,
        rules_path=rules_path,
        golden_path=golden_path,
    )
    if restored_snapshot.receipt.status != "reviewed":
        raise ValueError("restored source state must be a reviewed receipt")
    if restored_snapshot.receipt.commit_sha != evidence.restored_commit:
        raise ValueError("restored source-state commit does not match rollback")
    if restored_snapshot.snapshot_id != evidence.restored_snapshot_id:
        raise ValueError("restored source-state snapshot ID does not match")
    expected_fingerprint = source_state_fingerprint(restored_snapshot)
    if evidence.restored_snapshot_fingerprint != expected_fingerprint:
        raise ValueError("restored source-state fingerprint does not match")
    expected_hold = _rollback_hold_state(context, restored_snapshot)
    if evidence.hold_state != expected_hold:
        raise ValueError("rollback hold state does not match restored source state")
    if evidence.hold_state != "clear_in_source_state":
        raise ValueError("rollback baseline must not retain the changed-source hold")
    if evidence.triggered is None or evidence.completed is None:
        raise AssertionError("completed rollback chronology was not validated")
    restored_checked = datetime.fromisoformat(
        restored_snapshot.checked_at[:-1] + "+00:00"
    )
    if restored_checked < evidence.triggered or restored_checked > evidence.completed:
        raise ValueError("restored source-state chronology is invalid")


def _validate_completed_rollback(
    evidence: _RollbackEvidence,
    reference: ReceiptReference,
    publication: PublicationReceipt | None,
    context: ReleaseContext | None,
    restored_snapshot: SourceStateSnapshot | None,
    *,
    restored_sources_path: Path | None,
    restored_rules_path: Path | None,
    restored_golden_path: Path | None,
) -> None:
    if any(value is None for value in evidence.values()):
        raise ValueError("complete rollback lacks required evidence")
    if publication is None or context is None or restored_snapshot is None:
        raise ValueError(
            "complete rollback requires publication and source-state evidence"
        )
    _expected_reference(
        reference,
        publication.receipt_id,
        publication.fingerprint(),
        "publication_receipt",
    )
    if publication.binding != context.binding:
        raise ValueError("publication receipt release binding does not match rollback")
    if publication.status != "complete":
        raise ValueError("rollback requires a completed publication receipt")
    if (
        evidence.triggered is None
        or evidence.completed is None
        or publication.completed_at is None
    ):
        raise AssertionError("completed rollback chronology was not validated")
    publication_time = datetime.fromisoformat(publication.completed_at[:-1] + "+00:00")
    if evidence.triggered < publication_time or evidence.completed < evidence.triggered:
        raise ValueError("rollback chronology is invalid")
    if evidence.restored_commit != publication.baseline_commit_sha:
        raise ValueError("rollback must restore the publication baseline commit")
    if evidence.restored_url != publication.published_url:
        raise ValueError("rollback must verify the same deployment URL")
    _validate_restored_snapshot(
        evidence,
        context,
        restored_snapshot,
        sources_path=restored_sources_path,
        rules_path=restored_rules_path,
        golden_path=restored_golden_path,
    )


def load_rollback_receipt(
    path: Path,
    publication: PublicationReceipt | None = None,
    context: ReleaseContext | None = None,
    restored_snapshot: SourceStateSnapshot | None = None,
    *,
    approval: ApprovalReceipt | None = None,
    published_snapshot: SourceStateSnapshot | None = None,
    published_sources_path: Path | None = None,
    published_rules_path: Path | None = None,
    published_golden_path: Path | None = None,
    restored_sources_path: Path | None = None,
    restored_rules_path: Path | None = None,
    restored_golden_path: Path | None = None,
    now: datetime | None = None,
) -> RollbackReceipt:
    as_of = _validation_now(now)
    raw = _exact_keys(
        _load_json(path),
        {
            "schema_version",
            "receipt_type",
            "receipt_id",
            "status",
            "claim_boundary",
            "release_binding",
            "publication_receipt",
            "rollback",
            "effects",
        },
        str(path),
    )
    receipt_id, binding = _validate_common(
        raw,
        receipt_type="source_change_rollback",
        claim_boundary=ROLLBACK_CLAIM_BOUNDARY,
        effects=ROLLBACK_EFFECTS,
    )
    status = _choice(raw["status"], ROLLBACK_STATUSES, "status")
    _validate_receipt_id_for_state(receipt_id, status, binding)
    reference = _parse_reference(raw["publication_receipt"], "publication_receipt")
    evidence = _rollback_evidence(raw["rollback"], now=as_of)
    validated_publication = (
        _publication_from_payload(
            publication.to_dict(),
            approval,
            context,
            published_snapshot,
            published_sources_path=published_sources_path,
            published_rules_path=published_rules_path,
            published_golden_path=published_golden_path,
            as_of=as_of,
            field="publication_receipt",
        )
        if publication is not None
        else None
    )
    completed = status == "complete"
    _validate_binding(binding, context, completed=completed)
    if not completed:
        _all_null(evidence.values(), "rollback")
        _validate_optional_reference(
            reference,
            validated_publication,
            "publication_receipt",
            required=binding.is_complete(),
        )
    else:
        _validate_completed_rollback(
            evidence,
            reference,
            validated_publication,
            context,
            restored_snapshot,
            restored_sources_path=restored_sources_path,
            restored_rules_path=restored_rules_path,
            restored_golden_path=restored_golden_path,
        )
    return RollbackReceipt(
        receipt_id=receipt_id,
        status=status,
        binding=binding,
        publication=reference,
        actor_code=evidence.actor,
        triggered_at=_timestamp_text(evidence.triggered),
        completed_at=_timestamp_text(evidence.completed),
        reason=evidence.reason,
        restored_commit_sha=evidence.restored_commit,
        restored_url=evidence.restored_url,
        restored_source_snapshot_id=evidence.restored_snapshot_id,
        restored_source_snapshot_fingerprint=evidence.restored_snapshot_fingerprint,
        hold_state=evidence.hold_state,
        verification_receipt_id=evidence.verification_receipt_id,
    )
