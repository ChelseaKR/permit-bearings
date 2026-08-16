"""Strict pilot-neutral aggregate gate for a future limited beta.

The committed record is intentionally a planning artifact.  It binds existing
specialized ledgers and recomputes their current conservative state, but schema
version 1 cannot record a tested beta, an approval, or a partner decision.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

from .beta_operations import load_beta_operations_readiness
from .conformance_evaluation import load_evaluation_manifest
from .dates import resolve_today
from .journey import load_journey_config, resolve_journey
from .program_availability import load_program_availability
from .readiness import load_and_evaluate_readiness
from .rule_verification import effective_status, level_coverage, load_rule_verifications
from .screening import load_rules
from .source_state import load_source_state_snapshot
from .workflow_registry import load_workflow_registry

SCHEMA_VERSION = 1
GATE_ID = "limited-beta-aggregate-v1"
GATE_VERSION = "1.0.0"
RECORD_STATUS = "prepared"
BETA_STATUS = "not_run"
DEFAULT_RECORD_PATH = Path("data/validation/pilot-beta-gate.json")
MAX_RECORD_BYTES = 256 * 1024
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_SNAPSHOT_FILE_BYTES = 16 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 40 * 1024 * 1024
WORKFLOW_REGISTRY_PATH = "data/workflows/registry.json"

CLAIM_BOUNDARY = (
    "PREPARED AGGREGATE / TESTED BETA NOT RUN. This record recomputes the "
    "current conservative gate state from bound repository artifacts. It is "
    "not evidence of an active pilot, deployed beta, human or jurisdiction "
    "review, applicant research, accessibility or language approval, partner "
    "acceptance, privacy/security/records approval, completed rehearsal, "
    "application completeness, compliance, eligibility, permit approval, or "
    "statewide local coverage. A passing or decision-bearing gate requires a "
    "separately reviewed execution schema and external receipts."
)

EXPORT_BOUNDARY_CLAIM = (
    "This aggregate record, its validator, and any future filled execution "
    "record are outside public/synthetic evidence export profiles v1 and v2. "
    "Profile validity is portability-mechanism evidence only, not jurisdiction "
    "ownership, offboarding acceptance, or beta evidence."
)

_STABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_TOKEN_ID = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:[-_.][A-Za-z0-9]+)*$")
_SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")
_RAW_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_TOP_LEVEL_KEYS = {
    "aggregate",
    "artifact_bindings",
    "beta_status",
    "claim_boundary",
    "derived_gates",
    "export_boundary",
    "gate_id",
    "gate_version",
    "pilot_scope",
    "prepared_on",
    "prototype_reference",
    "record_status",
    "schema_version",
}
_PILOT_SCOPE_KEYS = {
    "active_source_package_id",
    "deployment_url",
    "frozen_commit_sha",
    "jurisdiction_id",
    "permit_subtype_id",
    "review_owner_role",
    "source_owner_role",
    "sponsor_role",
    "status",
    "workflow_id",
    "workflow_version",
}
_REFERENCE_KEYS = {
    "classification",
    "counts_as_active_pilot",
    "fact_envelope_fingerprint",
    "journey_fingerprint",
    "journey_id",
    "journey_version",
    "readiness_packet_fingerprint",
    "readiness_packet_id",
    "readiness_workflow_fingerprint",
    "readiness_workflow_id",
    "screening_case_fingerprint",
    "screening_case_id",
}
_BINDING_KEYS = {"artifact_id", "path", "sha256"}
_GATE_KEYS = {"artifact_ids", "gate_id", "reason_code", "status"}
_AGGREGATE_KEYS = {
    "artifact_set_fingerprint",
    "blocking_gate_ids",
    "changed_source_count",
    "not_run_gate_count",
    "prepared_gate_count",
    "reference_currency_blocker_ids",
    "stale_rule_count",
    "status",
    "supports_deployment_approval_claim",
    "supports_human_review_claim",
    "supports_partner_acceptance_claim",
    "supports_statewide_beta_claim",
    "supports_tested_beta_claim",
    "unverifiable_source_count",
    "unverified_rule_count",
}
_EXPORT_BOUNDARY_KEYS = {
    "claim",
    "future_profile_review_status",
    "gate_path",
    "inclusion_status",
    "profile_id",
    "profile_path",
}

_ARTIFACT_PATHS = {
    "beta_operations": "data/validation/beta-operations-readiness.json",
    "content_review": "data/validation/woodland-content-review.json",
    "external_evidence_gate": "data/validation/woodland-flagship-gate.json",
    "heldout_evaluation": "data/conformance/evaluations/heldout-v1/manifest.json",
    "manual_evidence": "data/validation/woodland-manual-evidence.json",
    "participant_sessions": "data/validation/woodland-participant-sessions.json",
    "public_synthetic_export": "data/export/public-synthetic-evidence-v1.json",
    "reference_journey": (
        "data/journeys/generated/woodland-preapproved-detached-adu.json"
    ),
    "reference_packet": (
        "data/readiness/generated/woodland-preapproved-adu-evidence.json"
    ),
    "rule_verification": "data/validation/rule-verification.json",
    "source_change_rehearsal": (
        "data/validation/woodland-source-change-rehearsal.json"
    ),
    "source_state": "data/source-status/current.json",
}
_ARTIFACT_IDS = tuple(sorted(_ARTIFACT_PATHS))
_EXPORT_PROFILE_ID = "permit-bearings-public-synthetic-evidence-v1"
_EXPORT_PROFILE_V2_ID = "permit-bearings-public-synthetic-evidence-v2"
_EXPORT_PROFILE_V2_PATH = "data/export/public-synthetic-evidence-v2.json"
_EXPORT_PROFILE_V2_SHA256 = (
    "sha256:d70d33b67a48c854d0ba9f2e1ac924243481a27080836aed54a5c958dc724aef"
)
_EXPORT_EXCLUDED_PATHS = {
    DEFAULT_RECORD_PATH.as_posix(),
    "src/permit_pathways/beta_gate.py",
    "src/permit_pathways/beta_gate_cli.py",
    "tests/test_beta_gate.py",
}

# These planning ledgers are deliberately immutable in aggregate schema v1.
# Pinning their independent raw bytes prevents a coordinated rewrite of a
# favorable nested result, disclaimer, or aggregate plus the binding digest.
# Executed evidence belongs in a separately reviewed execution schema.
_NOT_RUN_ARTIFACT_SHA256 = {
    "beta_operations": (
        "sha256:858dad1191fd070eab4d3c2c168d77b6c61ac45553d0e968d4070e22075bf394"
    ),
    "content_review": (
        "sha256:7110471ca09e6919dad42ef47990286f5530ba993d8840214a4f6e432b9d6abe"
    ),
    "external_evidence_gate": (
        "sha256:88f43375a80b0a0e02177e3605706c4e5251854cd00c94a0b18e42c773a33a7f"
    ),
    "heldout_evaluation": (
        "sha256:816bb414a09edbc024a2be7780761a1a2abb5f6cb2464c56e5790b58ad79e7b2"
    ),
    "manual_evidence": (
        "sha256:db1c41cf2752f1517a608e2ae6523cc5cf5b53099bd0413458aee1da0004d8d9"
    ),
    "participant_sessions": (
        "sha256:28e564adf81ec942f7a74a5cb849972f9607c4701ce8921673e644924028ab0f"
    ),
    "public_synthetic_export": (
        "sha256:2e5153f1dae2f7b660dcae156ed2d0f84480eff7a02a163fa8426a5272314e9e"
    ),
    "source_change_rehearsal": (
        "sha256:f28de3e2d86022ec61e6c73bbc98b64a658543886d98344e69063cd3d3c7d1f1"
    ),
}

_ARTIFACT_TOP_LEVEL_KEYS = {
    "beta_operations": {
        "approvals",
        "architecture_decision_path",
        "boundary",
        "claim_boundary",
        "controls",
        "decision_status",
        "deployment",
        "document_bindings",
        "export_boundary",
        "prepared_on",
        "record_id",
        "record_version",
        "records_boundary",
        "runbook_path",
        "schema_version",
        "status",
    },
    "content_review": {
        "artifact_lock",
        "baseline_provenance",
        "cross_cutting_checks",
        "gate",
        "prepared_on",
        "record_type",
        "reviewer_slots",
        "rows",
        "schema_version",
        "scoring_key_version",
        "status",
        "thresholds",
    },
    "external_evidence_gate": {
        "answer_key",
        "artifact_lock",
        "claim_boundary",
        "decision",
        "evidence_ledgers",
        "external_evidence",
        "gate_id",
        "prepared_on",
        "recruitment",
        "schema_version",
        "status",
        "thresholds",
    },
    "heldout_evaluation": {
        "claim_boundary",
        "coverage_contract",
        "development_source_exclusions",
        "evaluation_id",
        "external_blockers",
        "freeze",
        "inputs",
        "output",
        "raw_count_fields",
        "reference_labels",
        "scanner",
        "schema_version",
        "scoring_unit",
        "status",
    },
    "manual_evidence": {
        "artifact_lock",
        "claim_boundary",
        "manual_checks",
        "prepared_on",
        "privacy_protocol",
        "record_id",
        "record_version",
        "schema_version",
        "scope",
        "spanish_review_protocol",
        "spanish_semantic_reviews",
        "status",
    },
    "participant_sessions": {
        "aggregate",
        "artifact_lock",
        "claim_boundary",
        "prepared_on",
        "privacy_protocol",
        "record_id",
        "record_version",
        "schema_version",
        "scorecard_version",
        "scorecards",
        "status",
    },
    "public_synthetic_export": {
        "entries",
        "package",
        "public_state_assertions",
        "schema_version",
        "scope",
    },
    "reference_journey": {
        "applicability_facts",
        "applicability_status",
        "boundary",
        "candidate_route_rule_ids",
        "candidate_routes",
        "editable_applicability_fact_ids",
        "fact_envelope",
        "fact_envelope_fingerprint",
        "journey_fingerprint",
        "journey_id",
        "label",
        "readiness_evidence_manifest",
        "readiness_packet_fingerprint",
        "readiness_packet_id",
        "readiness_workflow_fingerprint",
        "readiness_workflow_id",
        "route_source_review_due_on",
        "route_source_status",
        "route_source_status_as_of",
        "schema_version",
        "screening_case_fingerprint",
        "screening_case_id",
        "screening_expected_rule_ids",
        "screening_intake",
        "status",
        "synthetic",
        "version",
    },
    "reference_packet": {
        "applicability_status",
        "boundary",
        "counts",
        "evaluated_on",
        "facts",
        "findings",
        "inventory",
        "manifest_type",
        "overall_status",
        "packet_fingerprint",
        "packet_id",
        "schema_version",
        "source_bindings",
        "source_review_due_on",
        "source_status",
        "source_status_as_of",
        "staff_questions",
        "synthetic",
        "workflow_fingerprint",
        "workflow_id",
    },
    "rule_verification": {"entries", "schema_version"},
    "source_change_rehearsal": {
        "aggregate",
        "artifact_lock",
        "claim_boundary",
        "execution",
        "expected_impact",
        "observed_impact",
        "partner_burden_decision",
        "prepared_on",
        "publication_receipt",
        "record_id",
        "record_version",
        "schema_version",
        "simulation_contract",
        "stages",
        "status",
        "timing",
    },
    "source_state": {
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
    },
}

_GATE_CONTRACTS: dict[str, tuple[tuple[str, ...], str]] = {
    "active_scope": ((), "pilot_scope_not_selected"),
    "applicant_evidence": (
        ("participant_sessions",),
        "participant_sessions_not_run",
    ),
    "content_authority": (("content_review",), "content_review_not_run"),
    "deterministic_evaluation": (
        ("heldout_evaluation", "source_state"),
        "heldout_evaluation_not_run",
    ),
    "frozen_artifact": (
        ("external_evidence_gate", "source_state"),
        "artifact_lock_not_run",
    ),
    "human_access": (("manual_evidence",), "manual_access_checks_not_run"),
    "language": (("manual_evidence",), "language_reviews_not_run"),
    "maintainability": (
        ("source_change_rehearsal",),
        "source_change_rehearsal_not_run",
    ),
    "ownership_export": (
        ("public_synthetic_export",),
        "partner_ownership_acceptance_not_run",
    ),
    "packet_behavior": (
        ("reference_journey", "reference_packet"),
        "synthetic_reference_is_not_pilot_evidence",
    ),
    "partner_decision": (
        ("external_evidence_gate",),
        "partner_and_decision_receipts_absent",
    ),
    "privacy_records_security": (
        ("beta_operations",),
        "operations_package_not_approved",
    ),
    "problem_evidence": (
        ("participant_sessions",),
        "problem_evidence_sessions_not_run",
    ),
    "review_levels": (
        ("rule_verification", "source_state"),
        "reachable_human_review_not_established",
    ),
}


class _DuplicateKey(ValueError):
    """Raised before a duplicate JSON key can replace evidence."""


@dataclass(frozen=True)
class ArtifactBinding:
    """One raw-byte-bound repository artifact."""

    artifact_id: str
    path: str
    sha256: str
    raw: bytes
    payload: dict[str, Any]


@dataclass(frozen=True)
class BetaGateSummary:
    """Conservative result from validating and recomputing the gate."""

    gate_id: str
    gate_version: str
    prepared_on: str
    record_status: str
    beta_status: str
    artifact_count: int
    artifact_set_fingerprint: str
    not_run_gate_count: int
    blocking_gate_ids: tuple[str, ...]
    rule_count: int
    machine_linked_rule_count: int
    stale_rule_count: int
    unverified_rule_count: int
    changed_source_count: int
    unverifiable_source_count: int
    reference_currency_blocker_ids: tuple[str, ...]
    record_sha256: str

    def to_dict(self) -> dict[str, Any]:
        """Return stable machine-readable CLI output."""

        return {
            "artifact_count": self.artifact_count,
            "artifact_set_fingerprint": self.artifact_set_fingerprint,
            "beta_status": self.beta_status,
            "blocking_gate_ids": list(self.blocking_gate_ids),
            "changed_source_count": self.changed_source_count,
            "gate_id": self.gate_id,
            "gate_version": self.gate_version,
            "machine_linked_rule_count": self.machine_linked_rule_count,
            "not_run_gate_count": self.not_run_gate_count,
            "prepared_on": self.prepared_on,
            "record_sha256": self.record_sha256,
            "record_status": self.record_status,
            "reference_currency_blocker_ids": list(self.reference_currency_blocker_ids),
            "rule_count": self.rule_count,
            "stale_rule_count": self.stale_rule_count,
            "supports_deployment_approval_claim": False,
            "supports_human_review_claim": False,
            "supports_partner_acceptance_claim": False,
            "supports_statewide_beta_claim": False,
            "supports_tested_beta_claim": False,
            "unverifiable_source_count": self.unverifiable_source_count,
            "unverified_rule_count": self.unverified_rule_count,
        }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"unsupported JSON constant {value!r}")


def _decode_json(raw: bytes, field: str, *, maximum: int) -> dict[str, Any]:
    if len(raw) > maximum:
        raise ValueError(f"{field}: exceeds byte limit")
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        _DuplicateKey,
        RecursionError,
        ValueError,
    ) as error:
        raise ValueError(f"{field}: expected strict UTF-8 JSON") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{field}: expected an object")
    return payload


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    return value


def _array(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field}: expected an array")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field}: expected non-blank trimmed text")
    if all(unicodedata.category(character)[0] in ("C", "Z") for character in value):
        raise ValueError(f"{field}: expected non-blank trimmed text")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], field: str) -> None:
    unknown = sorted(set(value) - expected)
    if unknown:
        raise ValueError(f"{field}: unknown fields: {', '.join(unknown)}")
    missing = sorted(expected - set(value))
    if missing:
        raise ValueError(f"{field}: missing fields: {', '.join(missing)}")


def _strict_equal(value: Any, expected: Any) -> bool:
    if type(value) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(value) == set(expected) and all(
            _strict_equal(value[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(value) == len(expected) and all(
            _strict_equal(item, other)
            for item, other in zip(value, expected, strict=True)
        )
    return bool(value == expected)


def _exact(value: Any, expected: Any, field: str) -> None:
    if not _strict_equal(value, expected):
        raise ValueError(f"{field}: expected {expected!r}")


def _stable_id(value: Any, field: str) -> str:
    identifier = _text(value, field)
    if not _STABLE_ID.fullmatch(identifier):
        raise ValueError(f"{field}: expected a stable identifier")
    return identifier


def _token_id(value: Any, field: str) -> str:
    identifier = _text(value, field)
    if not _TOKEN_ID.fullmatch(identifier):
        raise ValueError(f"{field}: expected a stable token")
    return identifier


def _semver(value: Any, field: str) -> str:
    version = _text(value, field)
    if not _SEMVER.fullmatch(version):
        raise ValueError(f"{field}: expected a semantic version")
    return version


def _fingerprint(value: Any, field: str) -> str:
    fingerprint = _text(value, field)
    if not _FINGERPRINT.fullmatch(fingerprint):
        raise ValueError(f"{field}: expected sha256:<64 lowercase hex>")
    return fingerprint


def _prepared_on(value: Any, *, today: date) -> str:
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        raise ValueError("prepared_on: expected YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("prepared_on: invalid date") from error
    if parsed > today:
        raise ValueError("prepared_on: future dates are not allowed")
    return value


def _iso_date_value(value: Any, field: str) -> date:
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        raise ValueError(f"{field}: expected YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field}: invalid date") from error
    if parsed.isoformat() != value:
        raise ValueError(f"{field}: expected an exact ISO date")
    return parsed


def _canonical_relative_path(value: Any, field: str) -> str:
    relative = _text(value, field)
    pure = PurePosixPath(relative)
    if (
        pure.is_absolute()
        or not pure.parts
        or ".." in pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
        or "\\" in relative
        or str(pure) != relative
    ):
        raise ValueError(f"{field}: expected a canonical repository-relative path")
    return relative


def _repository_root(path: Path) -> Path:
    lexical = Path(os.path.abspath(path))
    for candidate in reversed((lexical, *lexical.parents[:-1])):
        try:
            if candidate.is_symlink():
                raise ValueError(
                    f"{path}: symbolic-link repository roots are not allowed"
                )
        except OSError as error:
            raise ValueError(
                f"{path}: repository root could not be inspected"
            ) from error
    try:
        root = lexical.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"{path}: repository root could not be resolved") from error
    if not root.is_dir():
        raise ValueError(f"{path}: repository root must be a directory")
    return root


def _is_canonical_record(path: Path, root: Path) -> bool:
    specified = path if path.is_absolute() else root / path
    lexical = Path(os.path.abspath(specified))
    return lexical == root / DEFAULT_RECORD_PATH


def _read_repository_file(
    root: Path,
    relative: str,
    field: str,
    *,
    maximum: int,
) -> bytes:
    """Read one regular file through no-follow descriptors anchored at ``root``."""

    canonical = _canonical_relative_path(relative, field)
    parts = PurePosixPath(canonical).parts
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptors: list[int] = []
    try:
        directory_fd = os.open(root, directory_flags)
        descriptors.append(directory_fd)
        for part in parts[:-1]:
            directory_fd = os.open(
                part,
                directory_flags,
                dir_fd=directory_fd,
            )
            descriptors.append(directory_fd)
        file_fd = os.open(parts[-1], file_flags, dir_fd=directory_fd)
        descriptors.append(file_fd)
        metadata = os.fstat(file_fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"{field}: expected a regular file")
        if metadata.st_nlink != 1:
            raise ValueError(f"{field}: linked files are not allowed")
        if metadata.st_size > maximum:
            raise ValueError(f"{field}: exceeds byte limit")
        chunks: list[bytes] = []
        total = 0
        while chunk := os.read(file_fd, 64 * 1024):
            total += len(chunk)
            if total > maximum:
                raise ValueError(f"{field}: exceeds byte limit")
            chunks.append(chunk)
        return b"".join(chunks)
    except OSError as error:
        raise ValueError(
            f"{field}: expected a regular file without symbolic links or aliases"
        ) from error
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _read_external_record(path: Path) -> tuple[dict[str, Any], bytes]:
    """Read an explicit test/draft record once without following any links."""

    lexical = Path(os.path.abspath(path))
    parts = lexical.parts[1:]
    descriptors: list[int] = []
    try:
        directory_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        descriptors.append(directory_fd)
        for part in parts[:-1]:
            directory_fd = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            descriptors.append(directory_fd)
        file_fd = os.open(
            parts[-1],
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=directory_fd,
        )
        descriptors.append(file_fd)
        metadata = os.fstat(file_fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("aggregate gate: expected a regular file")
        if metadata.st_nlink != 1:
            raise ValueError("aggregate gate: linked files are not allowed")
        if metadata.st_size > MAX_RECORD_BYTES:
            raise ValueError("aggregate gate: exceeds byte limit")
        chunks: list[bytes] = []
        total = 0
        while chunk := os.read(file_fd, 64 * 1024):
            total += len(chunk)
            if total > MAX_RECORD_BYTES:
                raise ValueError("aggregate gate: exceeds byte limit")
            chunks.append(chunk)
        raw = b"".join(chunks)
    except OSError as error:
        raise ValueError(
            "aggregate gate: expected a regular file without symbolic-link ancestors"
        ) from error
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    return _decode_json(raw, "aggregate gate", maximum=MAX_RECORD_BYTES), raw


def _capture_repository_tree(  # noqa: C901
    root: Path,
    relative: str,
) -> tuple[dict[str, bytes], set[str]]:
    """Capture a complete repository subtree through no-follow descriptors.

    Each regular file is opened exactly once. Directories and files are
    inventoried by canonical relative path; any linked or special entry fails
    closed before specialized loaders see a private snapshot.
    """

    base = _canonical_relative_path(relative, "snapshot tree")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptors: list[int] = []
    payloads: dict[str, bytes] = {}
    directories: set[str] = {base}
    total = 0

    def visit(directory_fd: int, prefix: str) -> None:  # noqa: C901
        nonlocal total
        try:
            names = sorted(os.listdir(directory_fd))
        except OSError as error:
            raise ValueError(f"snapshot tree {prefix}: could not be listed") from error
        for name in names:
            if not name or name in {".", ".."} or "/" in name or "\\" in name:
                raise ValueError(f"snapshot tree {prefix}: unsafe entry name")
            child = f"{prefix}/{name}"
            try:
                metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except OSError as error:
                raise ValueError(
                    f"snapshot tree {child}: could not be inspected"
                ) from error
            if stat.S_ISDIR(metadata.st_mode):
                try:
                    child_fd = os.open(name, directory_flags, dir_fd=directory_fd)
                except OSError as error:
                    raise ValueError(
                        f"snapshot tree {child}: linked directories are not allowed"
                    ) from error
                descriptors.append(child_fd)
                directories.add(child)
                visit(child_fd, child)
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError(
                    f"snapshot tree {child}: symbolic links and special files "
                    "are not allowed"
                )
            try:
                file_fd = os.open(
                    name,
                    os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                    dir_fd=directory_fd,
                )
                descriptors.append(file_fd)
                opened = os.fstat(file_fd)
                if not stat.S_ISREG(opened.st_mode):
                    raise ValueError(f"snapshot tree {child}: expected a regular file")
                if opened.st_nlink != 1:
                    raise ValueError(
                        f"snapshot tree {child}: linked files are not allowed"
                    )
                if opened.st_size > MAX_SNAPSHOT_FILE_BYTES:
                    raise ValueError(f"snapshot tree {child}: exceeds byte limit")
                chunks: list[bytes] = []
                count = 0
                while chunk := os.read(file_fd, 64 * 1024):
                    count += len(chunk)
                    total += len(chunk)
                    if count > MAX_SNAPSHOT_FILE_BYTES or total > MAX_SNAPSHOT_BYTES:
                        raise ValueError(
                            "repository snapshot exceeds aggregate byte limit"
                        )
                    chunks.append(chunk)
                payloads[child] = b"".join(chunks)
            except OSError as error:
                raise ValueError(
                    f"snapshot tree {child}: linked files are not allowed"
                ) from error

    try:
        root_fd = os.open(
            root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
        )
        descriptors.append(root_fd)
        directory_fd = root_fd
        for part in PurePosixPath(base).parts:
            directory_fd = os.open(part, directory_flags, dir_fd=directory_fd)
            descriptors.append(directory_fd)
        visit(directory_fd, base)
    except OSError as error:
        raise ValueError(f"snapshot tree {base}: could not be opened") from error
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    return payloads, directories


def _sha256(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def artifact_set_fingerprint(rows: list[dict[str, Any]]) -> str:
    """Fingerprint the exact ordered binding registry."""

    encoded = json.dumps(
        rows,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _sha256(encoded)


def _load_bindings(
    value: Any,
    captured: dict[str, bytes],
) -> dict[str, ArtifactBinding]:
    rows = _array(value, "artifact_bindings")
    observed_ids: list[str] = []
    observed_paths: list[str] = []
    bindings: dict[str, ArtifactBinding] = {}
    for index, item in enumerate(rows):
        field = f"artifact_bindings[{index}]"
        record = _object(item, field)
        _exact_keys(record, _BINDING_KEYS, field)
        artifact_id = _stable_id(record["artifact_id"], f"{field}.artifact_id")
        observed_ids.append(artifact_id)
        if artifact_id not in _ARTIFACT_PATHS:
            raise ValueError(f"{field}.artifact_id: unsupported artifact role")
        relative = _canonical_relative_path(record["path"], f"{field}.path")
        _exact(relative, _ARTIFACT_PATHS[artifact_id], f"{field}.path")
        observed_paths.append(relative)
        expected_sha = _fingerprint(record["sha256"], f"{field}.sha256")
        try:
            raw = captured[relative]
        except KeyError as error:
            raise ValueError(f"{field}.path: bound artifact is missing") from error
        if len(raw) > MAX_ARTIFACT_BYTES:
            raise ValueError(f"{field}.path: exceeds byte limit")
        actual_sha = _sha256(raw)
        if actual_sha != expected_sha:
            raise ValueError(f"{field}.sha256: bound artifact bytes drifted")
        payload = _decode_json(raw, relative, maximum=MAX_ARTIFACT_BYTES)
        _exact_keys(
            payload,
            _ARTIFACT_TOP_LEVEL_KEYS[artifact_id],
            f"{artifact_id} artifact",
        )
        bindings[artifact_id] = ArtifactBinding(
            artifact_id=artifact_id,
            path=relative,
            sha256=expected_sha,
            raw=raw,
            payload=payload,
        )
    if observed_ids != list(_ARTIFACT_IDS):
        raise ValueError(
            "artifact_bindings: expected the exact sorted artifact registry"
        )
    if len(observed_paths) != len(set(observed_paths)):
        raise ValueError("artifact_bindings: duplicate paths are not allowed")
    return bindings


def _validate_not_run_pins(bindings: dict[str, ArtifactBinding]) -> None:
    for artifact_id, pinned in sorted(_NOT_RUN_ARTIFACT_SHA256.items()):
        _exact(
            bindings[artifact_id].sha256,
            pinned,
            f"{artifact_id} immutable not-run nested schema and bytes",
        )


def _snapshot_dependency_paths(
    bindings: dict[str, ArtifactBinding],
) -> tuple[str, ...]:
    paths = {binding.path for binding in bindings.values()}

    profile = bindings["public_synthetic_export"].payload
    entries = _array(profile["entries"], "export profile.entries")
    exported_paths: set[str] = set()
    for index, item in enumerate(entries):
        entry = _object(item, f"export profile.entries[{index}]")
        exported_paths.add(
            _canonical_relative_path(
                entry.get("path"), f"export profile.entries[{index}].path"
            )
        )
    forbidden = sorted(exported_paths.intersection(_EXPORT_EXCLUDED_PATHS))
    if forbidden:
        raise ValueError(
            "export profile v1 includes beta-gate files: " + ", ".join(forbidden)
        )
    paths.update(exported_paths)

    evaluation = bindings["heldout_evaluation"].payload
    scanner = _object(evaluation["scanner"], "heldout evaluation.scanner")
    for field in ("scanner_path", "checks_path", "evaluator_path"):
        paths.add(
            _canonical_relative_path(
                scanner.get(field), f"heldout evaluation.scanner.{field}"
            )
        )

    operations = bindings["beta_operations"].payload
    for field in ("architecture_decision_path", "runbook_path"):
        paths.add(
            _canonical_relative_path(operations[field], f"beta operations.{field}")
        )
    for index, item in enumerate(
        _array(operations["document_bindings"], "beta operations.document_bindings")
    ):
        document = _object(item, f"beta operations.document_bindings[{index}]")
        paths.add(
            _canonical_relative_path(
                document.get("path"),
                f"beta operations.document_bindings[{index}].path",
            )
        )
    for control_index, item in enumerate(
        _array(operations["controls"], "beta operations.controls")
    ):
        control = _object(item, f"beta operations.controls[{control_index}]")
        for path_index, path in enumerate(
            _array(
                control.get("evidence_paths"),
                f"beta operations.controls[{control_index}].evidence_paths",
            )
        ):
            paths.add(
                _canonical_relative_path(
                    path,
                    "beta operations.controls"
                    f"[{control_index}].evidence_paths[{path_index}]",
                )
            )

    return tuple(sorted(paths))


@contextmanager
def _repository_snapshot(  # noqa: C901
    root: Path,
    bindings: dict[str, ArtifactBinding],
    data_payloads: dict[str, bytes],
    data_directories: set[str],
) -> Iterator[tuple[Path, dict[str, bytes], set[str]]]:
    """Capture every direct and transitive validation input exactly once."""

    payloads = dict(data_payloads)
    for binding in bindings.values():
        if (
            binding.path.startswith("data/")
            and payloads.get(binding.path) != binding.raw
        ):
            raise ValueError(f"{binding.path}: captured binding bytes disagree")
        payloads.setdefault(binding.path, binding.raw)
    total = sum(len(raw) for raw in payloads.values())
    if total > MAX_SNAPSHOT_BYTES:
        raise ValueError("repository snapshot exceeds aggregate byte limit")
    for relative in _snapshot_dependency_paths(bindings):
        if relative in payloads:
            continue
        raw = _read_repository_file(
            root,
            relative,
            f"snapshot dependency {relative}",
            maximum=MAX_SNAPSHOT_FILE_BYTES,
        )
        total += len(raw)
        if total > MAX_SNAPSHOT_BYTES:
            raise ValueError("repository snapshot exceeds aggregate byte limit")
        payloads[relative] = raw

    with tempfile.TemporaryDirectory(prefix="permit-beta-gate-snapshot-") as directory:
        snapshot = Path(directory).resolve()
        for relative in sorted(
            data_directories, key=lambda item: (item.count("/"), item)
        ):
            (snapshot / PurePosixPath(relative)).mkdir(parents=True, exist_ok=True)
        for relative, raw in payloads.items():
            target = snapshot / PurePosixPath(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            target.chmod(0o400)
        expected_directories = set(data_directories)
        for relative in payloads:
            parent = PurePosixPath(relative).parent
            while str(parent) != ".":
                expected_directories.add(str(parent))
                parent = parent.parent
        yield snapshot, payloads, expected_directories


def _assert_snapshot_unchanged(  # noqa: C901
    snapshot: Path,
    payloads: dict[str, bytes],
    directories: set[str],
) -> None:
    observed_payloads, observed_directories = _capture_repository_tree(snapshot, "data")
    if observed_directories != {
        item for item in directories if item.startswith("data")
    }:
        raise ValueError(
            "snapshot integrity: validator changed the data directory tree"
        )
    if set(observed_payloads) != {
        item for item in payloads if item.startswith("data/")
    }:
        raise ValueError("snapshot integrity: validator added or removed a data file")
    for relative, expected in payloads.items():
        actual = _read_repository_file(
            snapshot,
            relative,
            f"snapshot integrity {relative}",
            maximum=MAX_SNAPSHOT_FILE_BYTES,
        )
        if actual != expected:
            raise ValueError(f"snapshot integrity {relative}: validator mutated input")

    # Inspect non-data dependencies as well so a validator cannot add a sibling
    # beside a captured source, test, or documentation input without detection.
    observed_all_files: set[str] = set()
    observed_all_directories: set[str] = set()
    for current, dir_names, file_names in os.walk(snapshot, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(snapshot).as_posix()
        if relative_dir != ".":
            observed_all_directories.add(relative_dir)
        for name in dir_names:
            candidate = current_path / name
            if candidate.is_symlink():
                raise ValueError("snapshot integrity: validator added a symbolic link")
        for name in file_names:
            candidate = current_path / name
            if candidate.is_symlink() or not candidate.is_file():
                raise ValueError("snapshot integrity: validator added a special file")
            observed_all_files.add(candidate.relative_to(snapshot).as_posix())
    if observed_all_files != set(payloads):
        raise ValueError(
            "snapshot integrity: validator changed snapshot file membership"
        )
    if observed_all_directories != directories:
        raise ValueError(
            "snapshot integrity: validator changed snapshot directory membership"
        )


def _validate_pilot_scope(value: Any) -> None:
    scope = _object(value, "pilot_scope")
    _exact_keys(scope, _PILOT_SCOPE_KEYS, "pilot_scope")
    _exact(scope["status"], "not_run", "pilot_scope.status")
    for field in _PILOT_SCOPE_KEYS - {"status"}:
        _exact(scope[field], None, f"pilot_scope.{field}")


def _validate_reference(value: Any) -> dict[str, Any]:
    reference = _object(value, "prototype_reference")
    _exact_keys(reference, _REFERENCE_KEYS, "prototype_reference")
    _exact(
        reference["classification"],
        "synthetic_future_state_prototype_only",
        "prototype_reference.classification",
    )
    _exact(
        reference["counts_as_active_pilot"],
        False,
        "prototype_reference.counts_as_active_pilot",
    )
    for field in (
        "journey_id",
        "screening_case_id",
        "readiness_workflow_id",
        "readiness_packet_id",
    ):
        _stable_id(reference[field], f"prototype_reference.{field}")
    _semver(reference["journey_version"], "prototype_reference.journey_version")
    for field in _REFERENCE_KEYS:
        if field.endswith("_fingerprint"):
            _fingerprint(reference[field], f"prototype_reference.{field}")
    return reference


def _null_fields(record: dict[str, Any], fields: set[str], prefix: str) -> None:
    for field in fields:
        _exact(record.get(field), None, f"{prefix}.{field}")


def _all_numbers_zero(value: Any, field: str) -> None:
    if isinstance(value, bool):
        raise ValueError(f"{field}: booleans are not counts")
    if isinstance(value, float):
        raise ValueError(f"{field}: counts must be integers")
    if isinstance(value, int):
        if value != 0:
            raise ValueError(f"{field}: unexecuted count must be zero")
        return
    elif isinstance(value, dict):
        for key, item in value.items():
            _all_numbers_zero(item, f"{field}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _all_numbers_zero(item, f"{field}[{index}]")
    else:
        raise ValueError(f"{field}: expected an unexecuted zero count")


def _validate_external_gate(payload: dict[str, Any]) -> None:
    _exact(payload["schema_version"], 1, "external gate.schema_version")
    _stable_id(payload["gate_id"], "external gate.gate_id")
    _exact(payload["status"], "pending", "external gate.status")
    lock = _object(payload["artifact_lock"], "external gate.artifact_lock")
    _exact_keys(
        lock,
        {
            "lock_id",
            "status",
            "commit_sha",
            "deployed_url",
            "frozen_on",
            "frozen_by_code",
            "protocol_version",
            "source_snapshot_id",
            "source_snapshot_receipt_id",
            "answer_key_version",
            "thresholds_version",
            "journey_id",
            "journey_version",
            "journey_fingerprint",
            "fact_envelope_fingerprint",
            "screening_case_id",
            "screening_case_fingerprint",
            "readiness_workflow_id",
            "readiness_workflow_fingerprint",
            "readiness_packet_id",
            "readiness_packet_fingerprint",
            "sample_urls",
            "source_snapshot",
            "internal_dry_run",
        },
        "external gate.artifact_lock",
    )
    _exact(lock.get("status"), "not_run", "external gate.artifact_lock.status")
    _null_fields(
        lock,
        {
            "commit_sha",
            "deployed_url",
            "frozen_by_code",
            "frozen_on",
            "source_snapshot_receipt_id",
        },
        "external gate.artifact_lock",
    )
    for index, item in enumerate(
        _array(lock["source_snapshot"], "artifact_lock.source_snapshot")
    ):
        entry = _object(item, f"artifact_lock.source_snapshot[{index}]")
        _exact_keys(
            entry,
            {"source_id", "sha256", "recorded_on"},
            f"artifact_lock.source_snapshot[{index}]",
        )
        _stable_id(
            entry["source_id"], f"artifact_lock.source_snapshot[{index}].source_id"
        )
        digest = _text(
            entry["sha256"], f"artifact_lock.source_snapshot[{index}].sha256"
        )
        if not _RAW_SHA256.fullmatch(digest):
            raise ValueError(
                f"artifact_lock.source_snapshot[{index}].sha256: expected lowercase SHA-256"
            )
        _iso_date_value(
            entry["recorded_on"], f"artifact_lock.source_snapshot[{index}].recorded_on"
        )
    dry_run = _object(
        lock.get("internal_dry_run"), "external gate.artifact_lock.internal_dry_run"
    )
    _exact(
        dry_run.get("status"),
        "not_run",
        "external gate.artifact_lock.internal_dry_run.status",
    )
    _null_fields(
        dry_run,
        set(dry_run) - {"status"},
        "external gate.artifact_lock.internal_dry_run",
    )
    recruitment = _object(payload["recruitment"], "external gate.recruitment")
    _exact(recruitment.get("status"), "pending", "external gate.recruitment.status")
    _all_numbers_zero(
        {key: item for key, item in recruitment.items() if key != "status"},
        "external gate.recruitment",
    )
    external = _object(payload["external_evidence"], "external gate.external_evidence")
    partner = _object(external.get("partner_gate"), "external partner gate")
    _exact_keys(
        partner,
        {
            "gate_version",
            "status",
            "artifact_lock_id",
            "tested_commit_sha",
            "journey_id",
            "journey_version",
            "qualifying_written_next_steps",
            "partner_category",
            "next_step_type",
            "owner_role",
            "due_on",
            "written_on",
            "private_evidence_receipt_id",
            "receipt_verified_on",
            "receipt_verified_by_code",
            "institutional_authorization",
        },
        "external partner gate",
    )
    _semver(partner["gate_version"], "external partner gate.gate_version")
    _exact(partner.get("status"), "pending", "external partner gate.status")
    _exact(
        partner.get("qualifying_written_next_steps"),
        0,
        "external partner gate.qualifying_written_next_steps",
    )
    _exact(
        partner.get("institutional_authorization"),
        "not_established",
        "external partner gate.institutional_authorization",
    )
    _null_fields(
        partner,
        {
            "due_on",
            "next_step_type",
            "owner_role",
            "partner_category",
            "private_evidence_receipt_id",
            "receipt_verified_by_code",
            "receipt_verified_on",
            "tested_commit_sha",
            "written_on",
        },
        "external partner gate",
    )
    decision = _object(payload["decision"], "external gate.decision")
    _exact_keys(
        decision,
        {
            "status",
            "decided_on",
            "decision_owner_code",
            "evaluated_on",
            "evaluation_receipt_id",
            "failure_reasons",
            "recommendation",
            "tested_commit_sha",
            "bounded_public_claim",
            "permitted_recommendations",
        },
        "external gate.decision",
    )
    _exact(decision.get("status"), "pending", "external gate.decision.status")
    _null_fields(
        decision,
        {
            "decided_on",
            "decision_owner_code",
            "evaluated_on",
            "evaluation_receipt_id",
            "failure_reasons",
            "recommendation",
            "tested_commit_sha",
        },
        "external gate.decision",
    )
    _text(
        decision["bounded_public_claim"], "external gate.decision.bounded_public_claim"
    )
    _exact(
        decision["permitted_recommendations"],
        ["proceed", "extend", "pivot", "stop"],
        "external gate.decision.permitted_recommendations",
    )


def _validate_content_review(payload: dict[str, Any]) -> None:
    _exact(payload["schema_version"], 2, "content review.schema_version")
    _stable_id(payload["record_type"], "content review.record_type")
    _exact(
        payload["status"],
        "prepared_not_executed",
        "content review.status",
    )
    lock = _object(payload["artifact_lock"], "content review.artifact_lock")
    _exact_keys(
        lock,
        {
            "status",
            "execution_commit",
            "deployed_url",
            "frozen_on",
            "freeze_owner_code",
            "content_bindings",
        },
        "content review.artifact_lock",
    )
    _exact(lock.get("status"), "pending", "content review.artifact_lock.status")
    _null_fields(
        lock,
        {"deployed_url", "execution_commit", "freeze_owner_code", "frozen_on"},
        "content review.artifact_lock",
    )
    slots = _array(payload["reviewer_slots"], "content review.reviewer_slots")
    if len(slots) != 2:
        raise ValueError("content review.reviewer_slots: expected two slots")
    for index, item in enumerate(slots):
        slot = _object(item, f"content review.reviewer_slots[{index}]")
        _exact(
            slot.get("status"),
            "not_run",
            f"content review.reviewer_slots[{index}].status",
        )
        _null_fields(
            slot,
            {
                "independence_attested",
                "method",
                "qualification_summary",
                "reviewed_execution_commit",
                "reviewed_on",
                "reviewer",
            },
            f"content review.reviewer_slots[{index}]",
        )
    for collection_name in ("rows", "cross_cutting_checks"):
        for index, item in enumerate(_array(payload[collection_name], collection_name)):
            row = _object(item, f"{collection_name}[{index}]")
            _null_fields(
                row,
                {"reviewer_1", "reviewer_2", "synthesis"},
                f"{collection_name}[{index}]",
            )
    gate = _object(payload["gate"], "content review.gate")
    _exact_keys(
        gate,
        {
            "status",
            "reviewers_completed",
            "rows_completed",
            "cross_cutting_checks_completed",
            "all_disagreements_resolved",
            "disagreement_count",
            "eligible_for_applicant_testing",
            "initial_agreement_count",
            "known_blocking_content_defects",
        },
        "content review.gate",
    )
    _exact(gate.get("status"), "not_run", "content review.gate.status")
    _exact(
        gate.get("reviewers_completed"), 0, "content review.gate.reviewers_completed"
    )
    _exact(gate.get("rows_completed"), 0, "content review.gate.rows_completed")
    _exact(
        gate.get("cross_cutting_checks_completed"),
        0,
        "content review.gate.cross_cutting_checks_completed",
    )
    _null_fields(
        gate,
        {
            "all_disagreements_resolved",
            "disagreement_count",
            "eligible_for_applicant_testing",
            "initial_agreement_count",
            "known_blocking_content_defects",
        },
        "content review.gate",
    )


def _validate_participants(payload: dict[str, Any]) -> None:
    _exact(payload["schema_version"], 1, "participant ledger.schema_version")
    _stable_id(payload["record_id"], "participant ledger.record_id")
    _semver(payload["record_version"], "participant ledger.record_version")
    _exact(
        payload["status"],
        "prepared_not_executed",
        "participant ledger.status",
    )
    lock = _object(payload["artifact_lock"], "participant ledger.artifact_lock")
    _exact_keys(
        lock,
        {
            "lock_id",
            "status",
            "commit_sha",
            "deployed_url",
            "frozen_on",
            "frozen_by_code",
            "source_snapshot_id",
            "source_snapshot_receipt_id",
            "protocol_version",
            "answer_key_version",
            "thresholds_version",
            "journey_id",
            "journey_version",
            "journey_fingerprint",
            "screening_case_id",
            "screening_case_fingerprint",
            "fact_envelope_fingerprint",
            "readiness_workflow_id",
            "readiness_workflow_fingerprint",
            "readiness_packet_id",
            "readiness_packet_fingerprint",
            "landing_path",
            "sample_entry_path",
            "valid_journey_path",
        },
        "participant ledger.artifact_lock",
    )
    _exact(lock.get("status"), "not_run", "participant ledger.artifact_lock.status")
    _null_fields(
        lock,
        {
            "commit_sha",
            "deployed_url",
            "frozen_by_code",
            "frozen_on",
            "source_snapshot_receipt_id",
        },
        "participant ledger.artifact_lock",
    )
    scorecards = _array(payload["scorecards"], "participant ledger.scorecards")
    if len(scorecards) != 6:
        raise ValueError("participant ledger.scorecards: expected six slots")
    observed_ids: list[str] = []
    for index, item in enumerate(scorecards):
        card = _object(item, f"participant ledger.scorecards[{index}]")
        observed_ids.append(_token_id(card.get("scorecard_id"), "scorecard_id"))
        _exact(card.get("status"), "not_run", f"scorecards[{index}].status")
        artifact_receipt = _object(
            card.get("artifact_receipt"), f"scorecards[{index}].artifact_receipt"
        )
        _null_fields(
            artifact_receipt,
            {
                "artifact_verification_receipt_id",
                "artifact_verified_by_code",
                "artifact_verified_on",
                "commit_sha",
                "deployed_url",
            },
            f"scorecards[{index}].artifact_receipt",
        )
        for nested in (
            "cohort_eligibility",
            "deidentified_synthesis",
            "receipts",
            "session",
        ):
            record = _object(card.get(nested), f"scorecards[{index}].{nested}")
            _null_fields(record, set(record), f"scorecards[{index}].{nested}")
        for nested in (
            "critical_incident",
            "final_safety_readback",
            "packet_task",
            "route_task",
        ):
            _exact(
                _object(card.get(nested), f"scorecards[{index}].{nested}").get(
                    "status"
                ),
                "not_run",
                f"scorecards[{index}].{nested}.status",
            )
            _null_fields(
                _object(card[nested], f"scorecards[{index}].{nested}"),
                set(_object(card[nested], f"scorecards[{index}].{nested}"))
                - {"status"},
                f"scorecards[{index}].{nested}",
            )
    if observed_ids != [f"P{number:02d}" for number in range(1, 7)]:
        raise ValueError("participant ledger.scorecards: unexpected slot registry")
    aggregate = _object(payload["aggregate"], "participant ledger.aggregate")
    _exact(aggregate.get("status"), "not_run", "participant ledger.aggregate.status")
    _exact(
        aggregate.get("sessions_completed"),
        0,
        "participant ledger.aggregate.sessions_completed",
    )
    for field in (
        "participants_with_small_jurisdiction_experience_completed",
        "practitioners_completed",
        "primary_beneficiaries_completed",
        "primary_with_preapproved_plan_exposure_completed",
        "primary_with_recent_attempt_completed",
    ):
        _exact(aggregate.get(field), 0, f"participant ledger.aggregate.{field}")
    _null_fields(
        aggregate,
        set(aggregate)
        - {
            "participants_with_small_jurisdiction_experience_completed",
            "practitioners_completed",
            "primary_beneficiaries_completed",
            "primary_with_preapproved_plan_exposure_completed",
            "primary_with_recent_attempt_completed",
            "sessions_completed",
            "status",
        },
        "participant ledger.aggregate",
    )
    privacy = _object(
        payload["privacy_protocol"], "participant ledger.privacy_protocol"
    )
    _exact(
        privacy.get("status"),
        "not_run",
        "participant ledger.privacy_protocol.status",
    )
    _null_fields(
        privacy,
        {"execution_confirmation", "privacy_review_receipt_id"},
        "participant ledger.privacy_protocol",
    )


def _validate_manual(payload: dict[str, Any]) -> None:
    _exact(payload["schema_version"], 1, "manual ledger.schema_version")
    _stable_id(payload["record_id"], "manual ledger.record_id")
    _semver(payload["record_version"], "manual ledger.record_version")
    _exact(
        payload["status"],
        "prepared_not_executed",
        "manual ledger.status",
    )
    lock = _object(payload["artifact_lock"], "manual ledger.artifact_lock")
    _exact_keys(
        lock,
        {
            "execution_status",
            "tested_commit",
            "deployed_url",
            "sample_entry_path",
            "valid_journey_path",
            "journey_id",
            "journey_version",
            "journey_fingerprint",
            "screening_case_id",
            "screening_case_fingerprint",
            "fact_envelope_fingerprint",
            "readiness_workflow_id",
            "readiness_workflow_fingerprint",
            "readiness_packet_id",
            "readiness_packet_fingerprint",
            "route_source_status_as_of",
            "route_source_review_due_on",
        },
        "manual ledger.artifact_lock",
    )
    _exact(
        lock.get("execution_status"),
        "not_run",
        "manual ledger.artifact_lock.execution_status",
    )
    _null_fields(
        lock,
        {"deployed_url", "tested_commit"},
        "manual ledger.artifact_lock",
    )
    checks = _array(payload["manual_checks"], "manual ledger.manual_checks")
    check_ids: list[str] = []
    for index, item in enumerate(checks):
        check = _object(item, f"manual ledger.manual_checks[{index}]")
        check_ids.append(_token_id(check.get("check_id"), "manual check.check_id"))
        _exact(check.get("result"), "not_run", f"manual_checks[{index}].result")
        _null_fields(
            check,
            {"evidence", "execution", "reviewer", "signoff"},
            f"manual_checks[{index}]",
        )
    if len(check_ids) != 22 or len(check_ids) != len(set(check_ids)):
        raise ValueError("manual ledger.manual_checks: expected 22 unique checks")
    if "ES-USABILITY-JOURNEY" not in check_ids:
        raise ValueError("manual ledger.manual_checks: Spanish usability check missing")
    rows = _array(
        payload["spanish_semantic_reviews"],
        "manual ledger.spanish_semantic_reviews",
    )
    rule_ids: list[str] = []
    for index, item in enumerate(rows):
        row = _object(item, f"spanish_semantic_reviews[{index}]")
        rule_ids.append(_stable_id(row.get("source_rule_id"), "source_rule_id"))
        _exact(
            row.get("result"),
            "not_run",
            f"spanish_semantic_reviews[{index}].result",
        )
        _null_fields(
            row,
            {"evidence", "method", "reviewed_on", "reviewer", "signoff"},
            f"spanish_semantic_reviews[{index}]",
        )
    if len(rule_ids) != 19 or len(rule_ids) != len(set(rule_ids)):
        raise ValueError(
            "manual ledger.spanish_semantic_reviews: expected 19 unique rows"
        )
    privacy = _object(payload["privacy_protocol"], "manual ledger.privacy_protocol")
    _exact(privacy.get("status"), "not_run", "manual ledger.privacy_protocol.status")
    _null_fields(
        privacy,
        {"evidence", "execution_confirmation", "reviewer", "signoff"},
        "manual ledger.privacy_protocol",
    )


def _validate_rehearsal(payload: dict[str, Any]) -> None:
    _exact(payload["schema_version"], 1, "rehearsal.schema_version")
    _stable_id(payload["record_id"], "rehearsal.record_id")
    _semver(payload["record_version"], "rehearsal.record_version")
    _exact(
        payload["status"],
        "prepared_not_executed",
        "rehearsal.status",
    )
    lock = _object(payload["artifact_lock"], "rehearsal.artifact_lock")
    _exact_keys(
        lock,
        {
            "lock_id",
            "status",
            "baseline_commit_sha",
            "baseline_deployed_url",
            "source_snapshot_id",
            "source_snapshot_receipt_id",
            "journey_id",
            "journey_version",
            "journey_fingerprint",
            "readiness_workflow_id",
            "readiness_workflow_fingerprint",
            "readiness_packet_id",
            "readiness_packet_fingerprint",
        },
        "rehearsal.artifact_lock",
    )
    _exact(lock.get("status"), "not_run", "rehearsal.artifact_lock.status")
    _null_fields(
        lock,
        {
            "baseline_commit_sha",
            "baseline_deployed_url",
            "source_snapshot_receipt_id",
        },
        "rehearsal.artifact_lock",
    )
    simulation = _object(
        payload["simulation_contract"], "rehearsal.simulation_contract"
    )
    _exact_keys(
        simulation,
        {
            "change_kind",
            "must_not_be_described_as_change_in_law",
            "target_source_id",
            "target_source_url",
            "baseline_sha256",
            "baseline_recorded_on",
            "simulated_changed_sha256",
            "changed_fixture_receipt_id",
            "detection_method",
            "readiness_command_argv",
            "expected_source_state",
            "expected_fail_closed_behavior",
        },
        "rehearsal.simulation_contract",
    )
    _stable_id(simulation["change_kind"], "rehearsal.simulation_contract.change_kind")
    _exact(
        simulation["must_not_be_described_as_change_in_law"],
        True,
        "rehearsal.simulation_contract.must_not_be_described_as_change_in_law",
    )
    _stable_id(
        simulation["target_source_id"], "rehearsal.simulation_contract.target_source_id"
    )
    _text(
        simulation["target_source_url"],
        "rehearsal.simulation_contract.target_source_url",
    )
    baseline_sha256 = _text(
        simulation["baseline_sha256"], "rehearsal.simulation_contract.baseline_sha256"
    )
    if not _RAW_SHA256.fullmatch(baseline_sha256):
        raise ValueError(
            "rehearsal.simulation_contract.baseline_sha256: expected lowercase SHA-256"
        )
    _iso_date_value(
        simulation["baseline_recorded_on"],
        "rehearsal.simulation_contract.baseline_recorded_on",
    )
    _null_fields(
        simulation,
        {"simulated_changed_sha256", "changed_fixture_receipt_id"},
        "rehearsal.simulation_contract",
    )
    _text(
        simulation["detection_method"], "rehearsal.simulation_contract.detection_method"
    )
    argv = _array(
        simulation["readiness_command_argv"],
        "rehearsal.simulation_contract.readiness_command_argv",
    )
    for index, token in enumerate(argv):
        _text(
            token,
            f"rehearsal.simulation_contract.readiness_command_argv[{index}]",
        )
    _stable_id(
        simulation["expected_source_state"],
        "rehearsal.simulation_contract.expected_source_state",
    )
    _stable_id(
        simulation["expected_fail_closed_behavior"],
        "rehearsal.simulation_contract.expected_fail_closed_behavior",
    )
    stages = _array(payload["stages"], "rehearsal.stages")
    for index, item in enumerate(stages):
        stage = _object(item, f"rehearsal.stages[{index}]")
        _exact(stage.get("status"), "not_run", f"rehearsal.stages[{index}].status")
        _null_fields(
            stage,
            set(stage) - {"stage_id", "status"},
            f"rehearsal.stages[{index}]",
        )
    aggregate = _object(payload["aggregate"], "rehearsal.aggregate")
    _exact_keys(
        aggregate,
        {
            "status",
            "stages_completed",
            "rehearsals_completed",
            "affected_requirements_confirmed",
            "unaffected_controls_confirmed",
            "defects_found",
            "human_owner_recorded",
            "republication_verified",
            "acceptable_burden",
            "acceptable_burden_decided_by_partner",
        },
        "rehearsal.aggregate",
    )
    _exact(aggregate.get("status"), "not_run", "rehearsal.aggregate.status")
    _exact(aggregate.get("stages_completed"), 0, "rehearsal.aggregate.stages_completed")
    _exact(
        aggregate.get("rehearsals_completed"),
        0,
        "rehearsal.aggregate.rehearsals_completed",
    )
    _null_fields(
        aggregate,
        {
            "affected_requirements_confirmed",
            "unaffected_controls_confirmed",
            "defects_found",
            "human_owner_recorded",
            "republication_verified",
            "acceptable_burden",
            "acceptable_burden_decided_by_partner",
        },
        "rehearsal.aggregate",
    )
    partner = _object(
        payload["partner_burden_decision"], "rehearsal.partner_burden_decision"
    )
    _exact(partner.get("status"), "pending", "partner_burden_decision.status")
    _null_fields(
        partner,
        set(partner) - {"status"},
        "rehearsal.partner_burden_decision",
    )
    field_keys = {
        "execution": {
            "rehearsal_started_at",
            "rehearsal_completed_at",
            "maintainer_code",
            "reviewer_code",
            "human_owner_role",
            "privacy_review_receipt_id",
            "protocol_deviations",
        },
        "publication_receipt": {
            "approval_receipt_id",
            "republished_commit_sha",
            "republished_url",
            "republished_source_sha256",
            "verification_receipt_id",
            "rollback_receipt_id",
        },
    }
    for field, expected_keys in field_keys.items():
        record = _object(payload[field], f"rehearsal.{field}")
        _exact_keys(record, expected_keys, f"rehearsal.{field}")
        _null_fields(record, set(record), f"rehearsal.{field}")
    observed = _object(payload["observed_impact"], "rehearsal.observed_impact")
    _exact_keys(
        observed,
        {
            "detected_source_state",
            "detected_sha256",
            "affected_requirement_ids",
            "affected_action_requirement_ids",
            "affected_record_paths",
            "unaffected_control_ids",
            "dispositions",
            "blocking_defects_found",
        },
        "rehearsal.observed_impact",
    )
    _null_fields(observed, set(observed), "rehearsal.observed_impact")
    timing = _object(payload["timing"], "rehearsal.timing")
    _exact_keys(
        timing,
        {"elapsed_minutes", "maintainer_active_minutes", "reviewer_active_minutes"},
        "rehearsal.timing",
    )
    _null_fields(timing, set(timing), "rehearsal.timing")


def _validate_reference_artifacts(
    journey: dict[str, Any], packet: dict[str, Any]
) -> None:
    _exact(journey["schema_version"], 1, "reference journey.schema_version")
    _exact(journey["status"], "prototype", "reference journey.status")
    _exact(journey["synthetic"], True, "reference journey.synthetic")
    _text(journey["boundary"], "reference journey.boundary")
    _exact(packet["schema_version"], 1, "reference packet.schema_version")
    _exact(packet["synthetic"], True, "reference packet.synthetic")
    _exact(
        packet["manifest_type"],
        "prototype_packet_presence",
        "reference packet.manifest_type",
    )
    _exact(packet["overall_status"], "known_gaps", "reference packet.overall_status")
    _text(packet["boundary"], "reference packet.boundary")
    _exact(
        journey["readiness_evidence_manifest"],
        packet,
        "reference journey.readiness_evidence_manifest",
    )


def _validate_rule_tree(snapshot_payloads: dict[str, bytes]) -> None:
    try:
        raw = snapshot_payloads["data/rules/index.json"]
    except KeyError as error:
        raise ValueError("rule manifest: missing from repository snapshot") from error
    manifest = _decode_json(raw, "rule manifest", maximum=MAX_ARTIFACT_BYTES)
    _exact_keys(manifest, {"schema_version", "files"}, "rule manifest")
    _exact(manifest["schema_version"], 1, "rule manifest.schema_version")
    declared = _array(manifest["files"], "rule manifest.files")
    if any(
        not isinstance(item, str)
        or PurePosixPath(item).name != item
        or not item.endswith(".json")
        or item == "index.json"
        for item in declared
    ):
        raise ValueError("rule manifest.files: expected canonical JSON filenames")
    if declared != sorted(declared) or len(declared) != len(set(declared)):
        raise ValueError("rule manifest.files: expected sorted unique filenames")
    rules_directory = PurePosixPath("data/rules")
    actual = sorted(
        PurePosixPath(relative).name
        for relative in snapshot_payloads
        if PurePosixPath(relative).parent == rules_directory
        and PurePosixPath(relative).name != "index.json"
    )
    _exact(actual, declared, "rule manifest exact directory membership")


def _validate_canonical_reference_outputs(
    snapshot: Path,
    bindings: dict[str, ArtifactBinding],
    rules: list[Any],
    source_state: Any,
    *,
    today: date,
) -> None:
    """Rebuild the synthetic packet/journey and availability answer key."""

    registry = load_workflow_registry(
        snapshot / WORKFLOW_REGISTRY_PATH,
        root=snapshot,
        validate_inventory=True,
    )
    entry = registry.select()
    _exact(
        entry.artifacts.readiness_evidence.path,
        bindings["reference_packet"].path,
        "workflow registry readiness output",
    )
    _exact(
        entry.artifacts.journey_evidence.path,
        bindings["reference_journey"].path,
        "workflow registry journey output",
    )
    packet_input_raw = _read_repository_file(
        snapshot,
        entry.artifacts.readiness_packet.path,
        "registered readiness packet",
        maximum=MAX_ARTIFACT_BYTES,
    )
    packet_input = _decode_json(
        packet_input_raw,
        "registered readiness packet",
        maximum=MAX_ARTIFACT_BYTES,
    )
    try:
        evaluated_on = date.fromisoformat(packet_input["packet"]["evaluated_on"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "registered readiness packet.evaluated_on: invalid date"
        ) from error
    workflow, packet, readiness = load_and_evaluate_readiness(
        entry.artifacts.readiness_workflow.resolve(snapshot),
        entry.artifacts.readiness_packet.resolve(snapshot),
        snapshot / "data/sources.json",
        today=evaluated_on,
        changed_source_ids=set(source_state.changed_source_ids),
    )
    if (
        workflow.workflow_id != entry.workflow_id
        or packet.workflow_id != entry.workflow_id
        or packet.packet_id != entry.packet_id
        or workflow.jurisdiction != entry.jurisdiction
        or packet.jurisdiction != entry.jurisdiction
    ):
        raise ValueError("registered readiness identity does not match")
    expected_packet = readiness.to_manifest(workflow, packet)
    _exact(
        bindings["reference_packet"].payload,
        expected_packet,
        "reference packet canonical recomputation",
    )

    config = load_journey_config(entry.artifacts.journey.resolve(snapshot))
    if config.journey_id != entry.journey_id:
        raise ValueError("registered journey identity does not match")
    expected_journey = resolve_journey(
        config,
        snapshot / "data/golden/example.json",
        rules,
        workflow,
        packet,
        readiness,
    )
    _exact(
        bindings["reference_journey"].payload,
        expected_journey,
        "reference journey canonical recomputation",
    )

    availability = load_program_availability(
        entry.artifacts.program_availability.resolve(snapshot),
        today=today,
        policy=entry.availability_policy,
    )
    if (
        availability.workflow_id != entry.workflow_id
        or availability.program_id != entry.program_id
        or availability.jurisdiction != entry.jurisdiction
    ):
        raise ValueError("registered program availability identity does not match")
    source = asdict(availability.source)
    expected_answer = {
        "checked_on": source["checked_on"],
        "excerpt": source["excerpt"],
        "excerpt_sha256": source["excerpt_sha256"],
        "mode": availability.mode,
        "program_id": availability.program_id,
        "recheck_due_on": source["recheck_due_on"],
        "source_id": source["source_id"],
        "status": availability.status,
    }
    answer_key = _object(
        bindings["external_evidence_gate"].payload["answer_key"],
        "external gate.answer_key",
    )
    _exact(
        answer_key.get("program_availability"),
        expected_answer,
        "external gate.answer_key.program_availability",
    )

    adopted = {observation.source_id for observation in source_state.observations}
    dependencies = {binding.source_id for binding in workflow.source_bindings} | {
        source_id
        for route in expected_journey["candidate_routes"]
        for source_id in route["source_dependencies"]
    }
    missing = sorted(dependencies - adopted)
    if missing:
        raise ValueError(
            "reference outputs use source dependencies absent from adopted source "
            "state: " + ", ".join(missing)
        )


def _reference_fields(
    reference: dict[str, Any],
    payload: dict[str, Any],
    prefix: str,
    *,
    journey_version_field: str = "journey_version",
) -> None:
    for field in _REFERENCE_KEYS - {"classification", "counts_as_active_pilot"}:
        payload_field = journey_version_field if field == "journey_version" else field
        _exact(payload.get(payload_field), reference[field], f"{prefix}.{field}")


def _validate_shared_lock_contract(
    external_lock: dict[str, Any],
    participant_lock: dict[str, Any],
    rehearsal_lock: dict[str, Any],
    participants: dict[str, Any],
) -> None:
    for field in (
        "lock_id",
        "protocol_version",
        "answer_key_version",
        "thresholds_version",
        "source_snapshot_id",
    ):
        _exact(
            participant_lock.get(field),
            external_lock.get(field),
            f"participant ledger.artifact_lock.{field}",
        )
    for field in ("lock_id", "source_snapshot_id"):
        _exact(
            rehearsal_lock.get(field),
            external_lock.get(field),
            f"rehearsal.artifact_lock.{field}",
        )
    sample_urls = _object(external_lock.get("sample_urls"), "artifact lock.sample_urls")
    for participant_field, sample_field in (
        ("landing_path", "landing"),
        ("sample_entry_path", "journey_start"),
        ("valid_journey_path", "packet_result"),
    ):
        _exact(
            participant_lock.get(participant_field),
            sample_urls.get(sample_field),
            f"participant ledger.artifact_lock.{participant_field}",
        )
    for index, item in enumerate(
        _array(participants["scorecards"], "participant ledger.scorecards")
    ):
        receipt = _object(
            _object(item, f"participant ledger.scorecards[{index}]").get(
                "artifact_receipt"
            ),
            f"participant ledger.scorecards[{index}].artifact_receipt",
        )
        _exact(
            receipt.get("lock_id"),
            external_lock.get("lock_id"),
            f"participant ledger.scorecards[{index}].artifact_receipt.lock_id",
        )
        _exact(
            receipt.get("source_snapshot_id"),
            external_lock.get("source_snapshot_id"),
            "participant ledger.scorecards"
            f"[{index}].artifact_receipt.source_snapshot_id",
        )


def _validate_cross_bindings(
    bindings: dict[str, ArtifactBinding], reference: dict[str, Any]
) -> None:
    external = bindings["external_evidence_gate"].payload
    content = bindings["content_review"].payload
    participants = bindings["participant_sessions"].payload
    manual = bindings["manual_evidence"].payload
    rehearsal = bindings["source_change_rehearsal"].payload
    journey = bindings["reference_journey"].payload
    packet = bindings["reference_packet"].payload

    _reference_fields(
        reference,
        journey,
        "reference journey",
        journey_version_field="version",
    )
    _exact(
        packet.get("workflow_id"),
        reference["readiness_workflow_id"],
        "packet.workflow_id",
    )
    _exact(
        packet.get("workflow_fingerprint"),
        reference["readiness_workflow_fingerprint"],
        "packet.workflow_fingerprint",
    )
    _exact(
        packet.get("packet_id"), reference["readiness_packet_id"], "packet.packet_id"
    )
    _exact(
        packet.get("packet_fingerprint"),
        reference["readiness_packet_fingerprint"],
        "packet.packet_fingerprint",
    )
    external_lock = _object(external["artifact_lock"], "external gate.artifact_lock")
    participant_lock = _object(
        participants["artifact_lock"], "participant ledger.artifact_lock"
    )
    manual_lock = _object(manual["artifact_lock"], "manual ledger.artifact_lock")
    _reference_fields(reference, external_lock, "external gate.artifact_lock")
    for artifact_name, artifact_lock in (
        ("participant ledger", participant_lock),
        ("manual ledger", manual_lock),
    ):
        _reference_fields(
            reference,
            artifact_lock,
            f"{artifact_name}.artifact_lock",
        )
    rehearsal_lock = _object(rehearsal["artifact_lock"], "rehearsal.artifact_lock")
    for field in (
        "journey_id",
        "journey_version",
        "journey_fingerprint",
        "readiness_workflow_id",
        "readiness_workflow_fingerprint",
        "readiness_packet_id",
        "readiness_packet_fingerprint",
    ):
        _exact(rehearsal_lock.get(field), reference[field], f"rehearsal.{field}")

    _validate_shared_lock_contract(
        external_lock,
        participant_lock,
        rehearsal_lock,
        participants,
    )
    content_bindings = _object(
        _object(content["artifact_lock"], "content review.artifact_lock").get(
            "content_bindings"
        ),
        "content review.content_bindings",
    )
    for content_field, reference_field in (
        ("workflow_id", "readiness_workflow_id"),
        ("workflow_fingerprint", "readiness_workflow_fingerprint"),
        ("journey_id", "journey_id"),
        ("journey_version", "journey_version"),
        ("journey_fingerprint", "journey_fingerprint"),
    ):
        _exact(
            content_bindings.get(content_field),
            reference[reference_field],
            f"content review.content_bindings.{content_field}",
        )
    _exact(
        _object(
            content["baseline_provenance"], "content review.baseline_provenance"
        ).get("content_bindings"),
        content_bindings,
        "content review.baseline_provenance.content_bindings",
    )
    answer_key = _object(external["answer_key"], "external gate.answer_key")
    _exact(
        answer_key.get("action_content_fingerprint"),
        content_bindings.get("remedy_content_fingerprint"),
        "external gate.answer_key.action_content_fingerprint",
    )
    _exact(
        answer_key.get("route_source_status_as_of"),
        journey.get("route_source_status_as_of"),
        "external gate.answer_key.route_source_status_as_of",
    )
    _exact(
        answer_key.get("route_source_review_due_on"),
        journey.get("route_source_review_due_on"),
        "external gate.answer_key.route_source_review_due_on",
    )
    _exact(
        manual_lock.get("route_source_status_as_of"),
        journey.get("route_source_status_as_of"),
        "manual ledger.artifact_lock.route_source_status_as_of",
    )
    _exact(
        manual_lock.get("route_source_review_due_on"),
        journey.get("route_source_review_due_on"),
        "manual ledger.artifact_lock.route_source_review_due_on",
    )
    _exact(
        answer_key.get("readiness_source_status_as_of"),
        packet.get("source_status_as_of"),
        "external gate.answer_key.readiness_source_status_as_of",
    )
    _exact(
        answer_key.get("readiness_source_review_due_on"),
        packet.get("source_review_due_on"),
        "external gate.answer_key.readiness_source_review_due_on",
    )

    external_thresholds = _object(external["thresholds"], "external gate.thresholds")
    external_content = _object(
        external_thresholds.get("content_authority"),
        "external gate.thresholds.content_authority",
    )
    content_thresholds = _object(content["thresholds"], "content review.thresholds")
    for external_field, content_field in (
        ("independent_reviewers_required", "independent_reviewers_required"),
        ("requirements_reviewed_per_reviewer", "requirements_total"),
        ("minimum_initial_agreement", "initial_agreement_minimum"),
        (
            "known_blocking_content_defects_allowed",
            "known_blocking_content_defects_maximum",
        ),
        (
            "all_disagreements_must_be_resolved",
            "resolve_every_disagreement_before_applicant_testing",
        ),
    ):
        _exact(
            external_content.get(external_field),
            content_thresholds.get(content_field),
            f"external gate.thresholds.content_authority.{external_field}",
        )
    content_rows = _array(content["rows"], "content review.rows")
    _exact(
        len(content_rows),
        content_thresholds.get("requirements_total"),
        "content review.rows count",
    )
    packet_inventory = _array(packet["inventory"], "reference packet.inventory")
    content_requirement_ids = sorted(
        _stable_id(
            _object(item, "content review row").get("requirement_id"),
            "content review row.requirement_id",
        )
        for item in content_rows
    )
    packet_requirement_ids = sorted(
        _stable_id(
            _object(item, "reference packet inventory row").get("requirement_id"),
            "reference packet inventory row.requirement_id",
        )
        for item in packet_inventory
    )
    _exact(
        content_requirement_ids,
        packet_requirement_ids,
        "content review requirement coverage",
    )
    cohort_thresholds = _object(
        external_thresholds.get("cohort"), "external gate.thresholds.cohort"
    )
    _exact(
        cohort_thresholds.get("sessions_required"),
        len(_array(participants["scorecards"], "participant ledger.scorecards")),
        "external gate.thresholds.cohort.sessions_required",
    )
    _exact(
        cohort_thresholds.get("single_frozen_version_required"),
        True,
        "external gate.thresholds.cohort.single_frozen_version_required",
    )

    ledger_refs = _object(
        external["evidence_ledgers"], "external gate.evidence_ledgers"
    )
    expected_refs = {
        "content_authority_review": (
            "content_review",
            content["record_type"],
            content["schema_version"],
        ),
        "manual_and_language_evidence": (
            "manual_evidence",
            manual["record_id"],
            manual["record_version"],
        ),
        "participant_sessions": (
            "participant_sessions",
            participants["record_id"],
            participants["record_version"],
        ),
        "source_change_rehearsal": (
            "source_change_rehearsal",
            rehearsal["record_id"],
            rehearsal["record_version"],
        ),
    }
    if set(ledger_refs) != set(expected_refs):
        raise ValueError("external gate.evidence_ledgers: unexpected ledger registry")
    for role, (artifact_id, record_id, version) in expected_refs.items():
        record = _object(ledger_refs[role], f"external gate.evidence_ledgers.{role}")
        _exact_keys(record, {"path", "record_id", "record_version"}, role)
        _exact(record["path"], bindings[artifact_id].path, f"{role}.path")
        _exact(record["record_id"], record_id, f"{role}.record_id")
        _exact(record["record_version"], version, f"{role}.record_version")

    partner = _object(
        _object(external["external_evidence"], "external evidence").get("partner_gate"),
        "partner gate",
    )
    _exact(partner.get("journey_id"), reference["journey_id"], "partner journey_id")
    _exact(
        partner.get("journey_version"),
        reference["journey_version"],
        "partner journey_version",
    )
    _exact(
        partner.get("artifact_lock_id"),
        _object(external["artifact_lock"], "artifact lock").get("lock_id"),
        "partner artifact_lock_id",
    )


def _reference_currency_blockers(
    bindings: dict[str, ArtifactBinding], *, today: date
) -> tuple[str, ...]:
    journey = bindings["reference_journey"].payload
    packet = bindings["reference_packet"].payload
    external = bindings["external_evidence_gate"].payload
    answer_key = _object(external["answer_key"], "external gate.answer_key")
    program = _object(
        answer_key.get("program_availability"),
        "external gate.answer_key.program_availability",
    )

    blockers: list[str] = []
    route_due = _iso_date_value(
        journey.get("route_source_review_due_on"),
        "reference journey.route_source_review_due_on",
    )
    if journey.get("route_source_status") != "current" or today > route_due:
        blockers.append("reference_journey_route_source")

    packet_due = _iso_date_value(
        packet.get("source_review_due_on"),
        "reference packet.source_review_due_on",
    )
    if packet.get("source_status") != "current" or today > packet_due:
        blockers.append("reference_packet_source")

    checked_on = _iso_date_value(
        program.get("checked_on"),
        "external gate.answer_key.program_availability.checked_on",
    )
    recheck_due_on = _iso_date_value(
        program.get("recheck_due_on"),
        "external gate.answer_key.program_availability.recheck_due_on",
    )
    if checked_on > today:
        raise ValueError(
            "external gate.answer_key.program_availability.checked_on: "
            "future dates are not allowed"
        )
    if recheck_due_on <= checked_on:
        raise ValueError(
            "external gate.answer_key.program_availability.recheck_due_on: "
            "must be after checked_on"
        )
    if (
        program.get("mode") != "future_state_simulation"
        or program.get("status") != "plans_not_listed"
        or today > recheck_due_on
    ):
        blockers.append("reference_program_availability")
    return tuple(sorted(blockers))


def _rule_currency_counts(
    rules: list[Any],
    ledger: dict[str, Any],
    *,
    today: date,
    changed_source_ids: tuple[str, ...],
) -> tuple[int, int]:
    stale = 0
    unverified = 0
    for rule in rules:
        if not rule.citation.is_verified:
            unverified += 1
        if effective_status(
            rule,
            ledger,
            today=today,
            changed_source_ids=changed_source_ids,
        ).stale:
            stale += 1
    return stale, unverified


def _validate_manual_rule_coverage(
    bindings: dict[str, ArtifactBinding], rules: list[Any]
) -> None:
    rows = _array(
        bindings["manual_evidence"].payload["spanish_semantic_reviews"],
        "manual ledger.spanish_semantic_reviews",
    )
    reviewed_rule_ids = sorted(
        _stable_id(
            _object(item, "Spanish semantic review row").get("source_rule_id"),
            "Spanish semantic review row.source_rule_id",
        )
        for item in rows
    )
    _exact(
        reviewed_rule_ids,
        sorted(rule.rule_id for rule in rules),
        "manual ledger Spanish rule coverage",
    )


def _derived_content_summary(
    binding: ArtifactBinding,
) -> dict[str, Any]:
    payload = binding.payload
    gate = _object(payload["gate"], "content review.gate")
    return {
        "disagreements_resolved_count": 0,
        "initial_agreement_count": gate["initial_agreement_count"],
        "known_blocking_content_defects": gate["known_blocking_content_defects"],
        "ledger_id": payload["record_type"],
        "ledger_path": binding.path,
        "ledger_version": payload["schema_version"],
        "requirements_reviewed": gate["rows_completed"],
        "reviewers_completed": gate["reviewers_completed"],
        "status": gate["status"],
    }


def _derived_participant_summary(binding: ArtifactBinding) -> dict[str, Any]:
    payload = binding.payload
    return {
        "ledger_id": payload["record_id"],
        "ledger_path": binding.path,
        "ledger_version": payload["record_version"],
        **_object(payload["aggregate"], "participant aggregate"),
    }


def _derived_manual_summaries(binding: ArtifactBinding) -> dict[str, dict[str, Any]]:
    payload = binding.payload
    checks = _array(payload["manual_checks"], "manual checks")
    usability = next(
        check for check in checks if check.get("check_id") == "ES-USABILITY-JOURNEY"
    )
    accessibility = [
        check for check in checks if check.get("check_id") != "ES-USABILITY-JOURNEY"
    ]
    spanish_rows = _array(payload["spanish_semantic_reviews"], "Spanish rows")
    identity = {
        "ledger_id": payload["record_id"],
        "ledger_path": binding.path,
        "ledger_version": payload["record_version"],
    }
    return {
        "manual_accessibility": {
            **identity,
            "checks_completed": 0,
            "checks_passing": None,
            "required_check_count": len(accessibility),
            "status": "not_run",
        },
        "spanish_semantic_review": {
            **identity,
            "records_approved": None,
            "records_required": len(spanish_rows),
            "records_reviewed": 0,
            "status": "not_run",
        },
        "spanish_usability": {
            **identity,
            "check_id": usability["check_id"],
            "checks_completed": 0,
            "checks_passing": None,
            "checks_required": 1,
            "status": "not_run",
        },
    }


def _derived_rehearsal_summary(binding: ArtifactBinding) -> dict[str, Any]:
    payload = binding.payload
    aggregate = _object(payload["aggregate"], "rehearsal aggregate")
    timing = _object(payload["timing"], "rehearsal timing")
    execution = _object(payload["execution"], "rehearsal execution")
    simulation = _object(payload["simulation_contract"], "simulation contract")
    return {
        "acceptable_burden": aggregate["acceptable_burden"],
        "acceptable_burden_decided_by_partner": aggregate[
            "acceptable_burden_decided_by_partner"
        ],
        "affected_requirements_confirmed": aggregate["affected_requirements_confirmed"],
        "defects_found": aggregate["defects_found"],
        "elapsed_minutes": timing["elapsed_minutes"],
        "human_owner_recorded": aggregate["human_owner_recorded"],
        "human_owner_role": execution["human_owner_role"],
        "ledger_id": payload["record_id"],
        "ledger_path": binding.path,
        "ledger_version": payload["record_version"],
        "maintainer_active_minutes": timing["maintainer_active_minutes"],
        "rehearsals_completed": aggregate["rehearsals_completed"],
        "republication_verified": aggregate["republication_verified"],
        "reviewer_active_minutes": timing["reviewer_active_minutes"],
        "stages_completed": aggregate["stages_completed"],
        "status": aggregate["status"],
        "target_source_id": simulation["target_source_id"],
        "unaffected_controls_confirmed": aggregate["unaffected_controls_confirmed"],
    }


def _validate_legacy_aggregate(bindings: dict[str, ArtifactBinding]) -> None:
    external = bindings["external_evidence_gate"].payload
    summaries = _object(external["external_evidence"], "external evidence")
    expected = {
        "content_authority_review": _derived_content_summary(
            bindings["content_review"]
        ),
        "participant_sessions": _derived_participant_summary(
            bindings["participant_sessions"]
        ),
        **_derived_manual_summaries(bindings["manual_evidence"]),
        "source_change_rehearsal": _derived_rehearsal_summary(
            bindings["source_change_rehearsal"]
        ),
    }
    for key, value in expected.items():
        _exact(summaries.get(key), value, f"external_evidence.{key}")


def _validate_export_boundary(
    value: Any,
    bindings: dict[str, ArtifactBinding],
    repository_root: Path,
) -> None:
    boundary = _object(value, "export_boundary")
    _exact_keys(boundary, _EXPORT_BOUNDARY_KEYS, "export_boundary")
    _exact(
        boundary["profile_path"],
        bindings["public_synthetic_export"].path,
        "export_boundary.profile_path",
    )
    profile_payload = bindings["public_synthetic_export"].payload
    package = _object(profile_payload["package"], "export profile.package")
    _exact(package.get("package_id"), _EXPORT_PROFILE_ID, "export profile.package_id")
    _exact(boundary["profile_id"], _EXPORT_PROFILE_ID, "export_boundary.profile_id")
    _exact(
        boundary["inclusion_status"],
        "excluded_from_profiles_v1_v2",
        "export_boundary.inclusion_status",
    )
    _exact(
        boundary["future_profile_review_status"],
        "not_run",
        "export_boundary.future_profile_review_status",
    )
    gate_path = _canonical_relative_path(
        boundary["gate_path"], "export_boundary.gate_path"
    )
    _exact(
        gate_path,
        DEFAULT_RECORD_PATH.as_posix(),
        "export_boundary.gate_path",
    )
    profile_paths = {
        _canonical_relative_path(
            _object(item, f"export profile.entries[{index}]").get("path"),
            f"export profile.entries[{index}].path",
        )
        for index, item in enumerate(
            _array(profile_payload["entries"], "export profile.entries")
        )
    }
    included = sorted(profile_paths.intersection(_EXPORT_EXCLUDED_PATHS))
    if included:
        raise ValueError(
            "export_boundary: profile v1 must exclude beta-gate files: "
            + ", ".join(included)
        )
    profile_v2_raw = _read_repository_file(
        repository_root,
        _EXPORT_PROFILE_V2_PATH,
        "export profile v2",
        maximum=MAX_ARTIFACT_BYTES,
    )
    _exact(
        _sha256(profile_v2_raw), _EXPORT_PROFILE_V2_SHA256, "export profile v2 bytes"
    )
    profile_v2 = _decode_json(
        profile_v2_raw,
        "export profile v2",
        maximum=MAX_ARTIFACT_BYTES,
    )
    package_v2 = _object(profile_v2.get("package"), "export profile v2.package")
    _exact(
        package_v2.get("package_id"),
        _EXPORT_PROFILE_V2_ID,
        "export profile v2.package_id",
    )
    included_v2 = sorted(
        {
            _canonical_relative_path(
                _object(item, f"export profile v2.entries[{index}]").get("path"),
                f"export profile v2.entries[{index}].path",
            )
            for index, item in enumerate(
                _array(profile_v2.get("entries"), "export profile v2.entries")
            )
        }.intersection(_EXPORT_EXCLUDED_PATHS)
    )
    if included_v2:
        raise ValueError(
            "export_boundary: profile v2 must exclude beta-gate files: "
            + ", ".join(included_v2)
        )
    _exact(boundary["claim"], EXPORT_BOUNDARY_CLAIM, "export_boundary.claim")


def _derived_gate_rows() -> list[dict[str, Any]]:
    return [
        {
            "artifact_ids": list(artifacts),
            "gate_id": gate_id,
            "reason_code": reason,
            "status": "not_run",
        }
        for gate_id, (artifacts, reason) in sorted(_GATE_CONTRACTS.items())
    ]


def _validate_derived_gates(value: Any) -> tuple[str, ...]:
    rows = _array(value, "derived_gates")
    for index, item in enumerate(rows):
        _exact_keys(
            _object(item, f"derived_gates[{index}]"), _GATE_KEYS, "derived gate"
        )
    expected = _derived_gate_rows()
    _exact(rows, expected, "derived_gates")
    return tuple(row["gate_id"] for row in expected)


def _binding_rows(value: Any) -> list[dict[str, Any]]:
    return [
        dict(_object(item, "artifact binding"))
        for item in _array(value, "artifact_bindings")
    ]


def _validate_aggregate(
    value: Any,
    *,
    binding_rows: list[dict[str, Any]],
    blocking_gate_ids: tuple[str, ...],
    changed_source_count: int,
    reference_currency_blocker_ids: tuple[str, ...],
    stale_rule_count: int,
    unverifiable_source_count: int,
    unverified_rule_count: int,
) -> str:
    aggregate = _object(value, "aggregate")
    _exact_keys(aggregate, _AGGREGATE_KEYS, "aggregate")
    fingerprint = artifact_set_fingerprint(binding_rows)
    expected = {
        "artifact_set_fingerprint": fingerprint,
        "blocking_gate_ids": list(blocking_gate_ids),
        "changed_source_count": changed_source_count,
        "not_run_gate_count": len(blocking_gate_ids),
        "prepared_gate_count": 0,
        "reference_currency_blocker_ids": list(reference_currency_blocker_ids),
        "stale_rule_count": stale_rule_count,
        "status": "not_run",
        "supports_deployment_approval_claim": False,
        "supports_human_review_claim": False,
        "supports_partner_acceptance_claim": False,
        "supports_statewide_beta_claim": False,
        "supports_tested_beta_claim": False,
        "unverifiable_source_count": unverifiable_source_count,
        "unverified_rule_count": unverified_rule_count,
    }
    _exact(aggregate, expected, "aggregate")
    return fingerprint


def load_beta_gate(
    path: Path = DEFAULT_RECORD_PATH,
    *,
    repository_root: Path | None = None,
    today: date | None = None,
) -> BetaGateSummary:
    """Validate the aggregate and recompute its conservative gate status.

    Success establishes only that the planning record and its current
    ``not_run`` evidence boundaries agree.  Schema v1 cannot express a tested
    beta or a favorable decision.
    """

    root = _repository_root(
        repository_root
        if repository_root is not None
        else Path(__file__).resolve().parents[2]
    )
    as_of = resolve_today(today)
    data_payloads, data_directories = _capture_repository_tree(root, "data")
    if _is_canonical_record(path, root):
        try:
            raw = data_payloads[DEFAULT_RECORD_PATH.as_posix()]
        except KeyError as error:
            raise ValueError("aggregate gate: canonical record is missing") from error
        payload = _decode_json(raw, "aggregate gate", maximum=MAX_RECORD_BYTES)
    else:
        payload, raw = _read_external_record(path)
    _exact_keys(payload, _TOP_LEVEL_KEYS, "aggregate gate")
    _exact(payload["schema_version"], SCHEMA_VERSION, "schema_version")
    _exact(payload["gate_id"], GATE_ID, "gate_id")
    _exact(payload["gate_version"], GATE_VERSION, "gate_version")
    _exact(payload["record_status"], RECORD_STATUS, "record_status")
    _exact(payload["beta_status"], BETA_STATUS, "beta_status")
    prepared_on = _prepared_on(payload["prepared_on"], today=as_of)
    _exact(payload["claim_boundary"], CLAIM_BOUNDARY, "claim_boundary")
    _validate_pilot_scope(payload["pilot_scope"])
    reference = _validate_reference(payload["prototype_reference"])
    binding_rows = _binding_rows(payload["artifact_bindings"])
    bindings = _load_bindings(payload["artifact_bindings"], data_payloads)

    _validate_external_gate(bindings["external_evidence_gate"].payload)
    _validate_content_review(bindings["content_review"].payload)
    _validate_participants(bindings["participant_sessions"].payload)
    _validate_manual(bindings["manual_evidence"].payload)
    _validate_rehearsal(bindings["source_change_rehearsal"].payload)
    _validate_reference_artifacts(
        bindings["reference_journey"].payload,
        bindings["reference_packet"].payload,
    )
    _validate_cross_bindings(bindings, reference)
    _validate_legacy_aggregate(bindings)
    _validate_not_run_pins(bindings)
    with _repository_snapshot(
        root,
        bindings,
        data_payloads,
        data_directories,
    ) as (snapshot, snapshot_payloads, snapshot_directories):
        _validate_rule_tree(snapshot_payloads)
        source_state = load_source_state_snapshot(
            snapshot / bindings["source_state"].path,
            snapshot / "data/sources.json",
            snapshot / "data/rules",
            snapshot / "data/golden/example.json",
            require_reviewed=True,
        )
        if date.fromisoformat(source_state.checked_at[:10]) > as_of:
            raise ValueError("source_state.checked_at: future dates are not allowed")
        rules = load_rules(snapshot / "data/rules", today=as_of)
        _validate_canonical_reference_outputs(
            snapshot,
            bindings,
            rules,
            source_state,
            today=as_of,
        )
        rule_ledger = load_rule_verifications(
            snapshot / bindings["rule_verification"].path,
            rules,
            require_complete=True,
            strict=True,
            today=as_of,
        )
        coverage = level_coverage(
            rules,
            rule_ledger,
            today=as_of,
            changed_source_ids=source_state.changed_source_ids,
        )
        if coverage.machine_linked != coverage.total:
            raise ValueError(
                "rule_verification: schema v1 requires every rule to remain "
                "machine_linked"
            )
        stale_rule_count, unverified_rule_count = _rule_currency_counts(
            rules,
            rule_ledger,
            today=as_of,
            changed_source_ids=source_state.changed_source_ids,
        )
        _validate_manual_rule_coverage(bindings, rules)
        load_evaluation_manifest(
            snapshot / bindings["heldout_evaluation"].path,
            snapshot,
        )
        load_beta_operations_readiness(
            snapshot / bindings["beta_operations"].path,
            repository_root=snapshot,
            today=as_of,
        )
        _validate_export_boundary(payload["export_boundary"], bindings, snapshot)
        _assert_snapshot_unchanged(
            snapshot,
            snapshot_payloads,
            snapshot_directories,
        )

    reference_currency_blocker_ids = _reference_currency_blockers(bindings, today=as_of)

    blocking_gate_ids = _validate_derived_gates(payload["derived_gates"])
    artifact_fingerprint = _validate_aggregate(
        payload["aggregate"],
        binding_rows=binding_rows,
        blocking_gate_ids=blocking_gate_ids,
        changed_source_count=len(source_state.changed_source_ids),
        reference_currency_blocker_ids=reference_currency_blocker_ids,
        stale_rule_count=stale_rule_count,
        unverifiable_source_count=len(source_state.unverifiable_source_ids),
        unverified_rule_count=unverified_rule_count,
    )
    return BetaGateSummary(
        gate_id=GATE_ID,
        gate_version=GATE_VERSION,
        prepared_on=prepared_on,
        record_status=RECORD_STATUS,
        beta_status=BETA_STATUS,
        artifact_count=len(bindings),
        artifact_set_fingerprint=artifact_fingerprint,
        not_run_gate_count=len(blocking_gate_ids),
        blocking_gate_ids=blocking_gate_ids,
        rule_count=coverage.total,
        machine_linked_rule_count=coverage.machine_linked,
        stale_rule_count=stale_rule_count,
        unverified_rule_count=unverified_rule_count,
        changed_source_count=len(source_state.changed_source_ids),
        unverifiable_source_count=len(source_state.unverifiable_source_ids),
        reference_currency_blocker_ids=reference_currency_blocker_ids,
        record_sha256=_sha256(raw),
    )
