"""Validate the proposed no-storage beta operating package.

The committed record is intentionally limited to ``prepared_not_approved``.
This module validates that fixed planning state, its no-application-storage
boundary, and the completeness of its pending control checklist.  It cannot
record an approval, bless a deployment, or produce a compliance finding.

A later execution or approval record requires a separately reviewed schema;
changing a null field in the current JSON cannot promote this package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

from .dates import resolve_today

SCHEMA_VERSION = 1
RECORD_ID = "no-storage-beta-operations-v1"
RECORD_VERSION = "1.0.0"
STATUS = "prepared_not_approved"
DECISION_STATUS = "proposed"
ADR_PATH = "docs/adr/0002-retain-no-storage-beta-boundary.md"
RUNBOOK_PATH = "docs/BETA-OPERATIONS-RUNBOOK.md"
MAX_RECORD_BYTES = 256 * 1024

CLAIM_BOUNDARY = (
    "PREPARED / NOT APPROVED. This record validates a proposed "
    "no-application-storage operating boundary and pending control checklist. "
    "It is not evidence of a beta deployment, partner acceptance, privacy or "
    "security approval, CPRA or Information Practices Act compliance, SAM or "
    "SIMM compliance, accessibility or language approval, legal advice, "
    "application completeness, eligibility, permit approval, or completed "
    "operational rehearsal."
)

BROWSER_MEMORY_PURPOSE = (
    "Render deterministic candidate guidance, source status, and temporary "
    "print-oriented outputs in the current page without persisting or "
    "transmitting applicant answers."
)
SYNTHETIC_PACKET_BOUNDARY = (
    "The packet page replays committed public synthetic records and accepts no "
    "applicant document or applicant-data submission."
)
HOSTING_METADATA_BOUNDARY = (
    "Static hosting, DNS, CDN, and linked third-party sites may process ordinary "
    "request metadata outside application code; deployment-specific review "
    "remains not_run."
)
USER_ARTIFACT_BOUNDARY = (
    "Browser Print or Save as PDF may create a user-controlled local artifact "
    "that the application does not create, upload, retain, or retrieve."
)

# ID -> (path, exact raw-byte SHA-256). Both the ledger and validator pin the
# documents so existence alone cannot validate materially changed guidance.
DOCUMENT_BINDINGS = {
    "beta-boundary-adr": (
        ADR_PATH,
        "226dd8b9af2a2ef68c2c941cc260ba3b662514cca34b38d687fdcebbbe13e585",
    ),
    "beta-operations-runbook": (
        RUNBOOK_PATH,
        "d09f9604adb10c2c075604de11f5ad0cbb9d8e37fda3620db3df8642d223b405",
    ),
}
EXPORT_CLAIM = (
    "This operating ledger, ADR, runbook, validator, and tests are outside "
    "pinned export profile v1. A reviewed future profile version is required "
    "before they are represented as part of an evidence handoff."
)

BROWSER_MEMORY_FIELDS = (
    "adu_project_form",
    "adjacent_sb9_split_same_actor",
    "demolishes_protected_housing",
    "ellis_withdrawal_last_15_years",
    "in_urbanized_area",
    "journey_applicability",
    "jurisdiction",
    "jurisdiction_name",
    "lot_split_alters_historic_district_resource",
    "lot_split_on_historic_landmark_site",
    "on_protected_site",
    "parcel_created_by_sb9_split",
    "primary_dwelling_status",
    "project_type",
    "proposed_lot_ratio_compliant",
    "proposed_lot_size_compliant",
    "sf_zone",
    "tenant_occupied_last_3_years",
    "two_unit_contributing_historic_location",
    "two_unit_individually_listed_historic_property",
    "unpermitted_existing",
)

POTENTIAL_EXTERNAL_RECORD_CLASSES = (
    "deployment and configuration records",
    "repository and release records",
    "security and incident records",
    "support records created outside the application",
)

APPROVAL_ROLES = {
    "accessibility-approval": "accessibility_owner",
    "beta-scope-approval": "product_scope_owner",
    "hosting-approval": "deployment_owner",
    "jurisdiction-partner-decision": "jurisdiction_authority",
    "language-access-approval": "language_access_owner",
    "privacy-approval": "privacy_owner",
    "records-approval": "records_owner",
    "security-approval": "security_owner",
    "support-approval": "support_owner",
}

# ID -> (domain, exact objective, approval ID, exact evidence paths)
CONTROL_CONTRACTS: dict[str, tuple[str, str, str, tuple[str, ...]]] = {
    "beta-access-001": (
        "access",
        "Define and review least-privilege repository, deployment, DNS, and "
        "rollback access before a beta release.",
        "security-approval",
        (RUNBOOK_PATH,),
    ),
    "beta-accessibility-001": (
        "accessibility",
        "Keep automated accessibility checks separate from pending human and "
        "assistive-technology approval.",
        "accessibility-approval",
        (RUNBOOK_PATH, "docs/BETA-ROADMAP.md"),
    ),
    "beta-boundary-001": (
        "architecture",
        "Retain public static delivery with no accounts, uploads, "
        "application-managed storage, telemetry, runtime external model call, "
        "or permitting-system writeback.",
        "beta-scope-approval",
        (ADR_PATH,),
    ),
    "beta-claims-001": (
        "claims",
        "Prevent the operating package from asserting legal advice, compliance, "
        "completeness, eligibility, approval, jurisdiction acceptance, or beta "
        "approval.",
        "beta-scope-approval",
        (
            "data/validation/beta-operations-readiness.json",
            "src/permit_pathways/beta_operations.py",
            "tests/test_beta_operations.py",
        ),
    ),
    "beta-data-001": (
        "data",
        "Keep service-collected applicant fields and purposes empty; process the "
        "enumerated project facts only in current page memory.",
        "privacy-approval",
        ("docs/DATA-FLOW.md", RUNBOOK_PATH),
    ),
    "beta-deployment-001": (
        "deployment",
        "Require an immutable commit, HTTPS URL, hosting boundary, release "
        "verification receipt, and rollback receipt before deployment approval.",
        "hosting-approval",
        (RUNBOOK_PATH,),
    ),
    "beta-export-001": (
        "portability",
        "Keep the existing evidence export limited to its pinned profile and "
        "require review before a future profile includes this operating package.",
        "records-approval",
        (
            "docs/EXPORT-RESTORE.md",
            "data/export/public-synthetic-evidence-v1.json",
        ),
    ),
    "beta-hosting-001": (
        "subprocessors",
        "Inventory the selected host, DNS, CDN, request metadata, subprocessors, "
        "retention, and transfer terms before approval.",
        "hosting-approval",
        (RUNBOOK_PATH,),
    ),
    "beta-incident-001": (
        "incident",
        "Triage integrity, source-currency, privacy, security, accessibility, and "
        "availability incidents with role-based escalation and preservation "
        "decisions.",
        "security-approval",
        (RUNBOOK_PATH,),
    ),
    "beta-language-001": (
        "language_access",
        "Keep Spanish source-derived guidance review-pending and outside any "
        "applicant-ready beta claim until exact-version semantic and usability "
        "review is approved.",
        "language-access-approval",
        ("docs/BETA-ROADMAP.md", RUNBOOK_PATH),
    ),
    "beta-privacy-001": (
        "privacy",
        "Require deployment-specific privacy review while preserving the "
        "no-application-storage and no-applicant-network-submission boundary.",
        "privacy-approval",
        ("docs/DATA-FLOW.md", RUNBOOK_PATH),
    ),
    "beta-records-001": (
        "records",
        "Route records requests and legal-hold questions to the records role and "
        "rehearse search and export across systems outside the application.",
        "records-approval",
        (RUNBOOK_PATH,),
    ),
    "beta-release-001": (
        "release",
        "Bind release verification to one commit and HTTPS deployment without "
        "treating automated checks as external approval.",
        "hosting-approval",
        (RUNBOOK_PATH,),
    ),
    "beta-retention-001": (
        "retention",
        "Record that the application has no applicant record to retain or delete "
        "while requiring separate schedules for hosting, repository, incident, "
        "and support records.",
        "records-approval",
        (RUNBOOK_PATH,),
    ),
    "beta-rollback-001": (
        "rollback",
        "Restore the last known-good static commit or place the beta on hold "
        "without altering evidence state or fabricating a successful verification "
        "receipt.",
        "hosting-approval",
        (RUNBOOK_PATH,),
    ),
    "beta-security-001": (
        "security",
        "Require deployment-specific threat and security review before release "
        "and again before any boundary expansion.",
        "security-approval",
        (RUNBOOK_PATH,),
    ),
    "beta-support-001": (
        "support",
        "Define role-based support intake, safe reproduction, evidence capture, "
        "response ownership, and escalation without collecting applicant case "
        "data in the application.",
        "support-approval",
        (RUNBOOK_PATH,),
    ),
}

_TOP_LEVEL_KEYS = {
    "schema_version",
    "record_id",
    "record_version",
    "prepared_on",
    "status",
    "decision_status",
    "architecture_decision_path",
    "runbook_path",
    "document_bindings",
    "boundary",
    "deployment",
    "records_boundary",
    "export_boundary",
    "approvals",
    "controls",
    "claim_boundary",
}
_BOUNDARY_KEYS = {
    "public_static_delivery",
    "accounts",
    "uploads",
    "application_managed_storage",
    "browser_persistence",
    "application_telemetry",
    "runtime_external_model_calls",
    "permitting_system_writeback",
    "applicant_data_network_submission",
    "service_collected_fields",
    "service_collection_purposes",
    "browser_memory_fields",
    "browser_memory_purpose",
    "synthetic_packet_boundary",
    "hosting_metadata_boundary",
    "user_controlled_artifact_boundary",
}
_DEPLOYMENT_KEYS = {
    "evidence_scope",
    "status",
    "commit_sha",
    "https_url",
    "hosting_provider",
    "dns_provider",
    "cdn_provider",
    "host_request_metadata_review_status",
    "host_request_metadata_fields",
    "subprocessor_review_status",
    "approved_subprocessors",
    "access_review_status",
    "release_verification_receipt_id",
    "rollback_verification_receipt_id",
}
_DOCUMENT_BINDING_KEYS = {"document_id", "path", "sha256"}
_RECORDS_KEYS = {
    "status",
    "application_applicant_record_store",
    "service_searchable_applicant_fields",
    "potential_external_record_classes",
    "cpra_routing_role",
    "search_export_rehearsal_status",
    "search_export_receipt_id",
    "legal_hold_review_status",
    "retention_schedule_status",
}
_EXPORT_KEYS = {
    "current_profile_id",
    "inclusion_status",
    "future_profile_review_status",
    "approved_future_profile_id",
    "claim",
}
_APPROVAL_KEYS = {
    "approval_id",
    "required_role",
    "status",
    "decision",
    "decided_by",
    "decided_on",
    "evidence_receipt_id",
}
_CONTROL_KEYS = {
    "control_id",
    "domain",
    "objective",
    "preparation_status",
    "verification_status",
    "approval_id",
    "evidence_paths",
    "execution_receipt_id",
}
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_STABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$")


class _DuplicateKey(ValueError):
    """Raised before a duplicate JSON key can overwrite an earlier value."""


@dataclass(frozen=True)
class PendingApproval:
    """One role-based approval that has not been executed."""

    approval_id: str
    required_role: str
    status: str


@dataclass(frozen=True)
class PreparedControl:
    """One prepared control whose operational verification is not run."""

    control_id: str
    domain: str
    approval_id: str


@dataclass(frozen=True)
class BetaOperationsReadiness:
    """Validated prepared/not-approved package summary."""

    record_id: str
    record_version: str
    prepared_on: str
    status: str
    decision_status: str
    approvals: tuple[PendingApproval, ...]
    controls: tuple[PreparedControl, ...]
    claim_boundary: str


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"unsupported JSON constant {value!r}")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ValueError(f"{path}: beta operations record could not be read") from error
    if len(raw) > MAX_RECORD_BYTES:
        raise ValueError(f"{path}: beta operations record exceeds byte limit")
    try:
        text = raw.decode("utf-8")
        payload = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        _DuplicateKey,
        RecursionError,
    ) as error:
        raise ValueError(
            f"{path}: beta operations record is not strict JSON"
        ) from error
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def _exact_keys(record: dict[str, Any], expected: set[str], field: str) -> None:
    unknown = sorted(set(record) - expected)
    if unknown:
        raise ValueError(f"{field}: unknown fields: {', '.join(unknown)}")
    missing = sorted(expected - set(record))
    if missing:
        raise ValueError(f"{field}: missing fields: {', '.join(missing)}")


def _exact(value: Any, expected: Any, field: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise ValueError(f"{field}: expected {expected!r}")


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
    return value


def _stable_id(value: Any, field: str) -> str:
    identifier = _text(value, field)
    if not _STABLE_ID.fullmatch(identifier):
        raise ValueError(f"{field}: expected a stable identifier")
    return identifier


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


def _validate_relative_path(value: Any, repository_root: Path, field: str) -> str:
    path = _text(value, field)
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or str(pure) != path:
        raise ValueError(f"{field}: expected a canonical repository-relative path")
    candidate = repository_root / pure
    try:
        candidate.resolve().relative_to(repository_root.resolve())
    except ValueError as error:
        raise ValueError(f"{field}: evidence path escapes repository root") from error
    if candidate.is_symlink():
        raise ValueError(f"{field}: evidence path must not be a symbolic link")
    if not candidate.is_file():
        raise ValueError(f"{field}: evidence path does not exist: {path}")
    return path


def _validate_document_bindings(value: Any, repository_root: Path) -> None:
    rows = _array(value, "document_bindings")
    observed_ids: list[str] = []
    for index, item in enumerate(rows):
        field = f"document_bindings[{index}]"
        record = _object(item, field)
        _exact_keys(record, _DOCUMENT_BINDING_KEYS, field)
        document_id = _stable_id(record["document_id"], f"{field}.document_id")
        observed_ids.append(document_id)
        if document_id not in DOCUMENT_BINDINGS:
            raise ValueError(f"{field}.document_id: unexpected document binding")
        expected_path, expected_sha256 = DOCUMENT_BINDINGS[document_id]
        _exact(record["path"], expected_path, f"{field}.path")
        _exact(record["sha256"], expected_sha256, f"{field}.sha256")
        path = _validate_relative_path(record["path"], repository_root, f"{field}.path")
        try:
            actual_sha256 = hashlib.sha256(
                (repository_root / path).read_bytes()
            ).hexdigest()
        except OSError as error:
            raise ValueError(f"{field}.path: document could not be read") from error
        if actual_sha256 != expected_sha256:
            raise ValueError(f"{field}.sha256: bound document bytes changed")
    if observed_ids != sorted(DOCUMENT_BINDINGS):
        raise ValueError(
            "document_bindings: expected the exact sorted document registry"
        )


def _validate_boundary(value: Any) -> None:
    record = _object(value, "boundary")
    _exact_keys(record, _BOUNDARY_KEYS, "boundary")
    _exact(record["public_static_delivery"], True, "boundary.public_static_delivery")
    for field in (
        "accounts",
        "uploads",
        "application_managed_storage",
        "browser_persistence",
        "application_telemetry",
        "runtime_external_model_calls",
        "permitting_system_writeback",
        "applicant_data_network_submission",
    ):
        _exact(record[field], False, f"boundary.{field}")
    _exact(record["service_collected_fields"], [], "boundary.service_collected_fields")
    _exact(
        record["service_collection_purposes"],
        [],
        "boundary.service_collection_purposes",
    )
    _exact(
        record["browser_memory_fields"],
        list(BROWSER_MEMORY_FIELDS),
        "boundary.browser_memory_fields",
    )
    _exact(
        record["browser_memory_purpose"],
        BROWSER_MEMORY_PURPOSE,
        "boundary.browser_memory_purpose",
    )
    _exact(
        record["synthetic_packet_boundary"],
        SYNTHETIC_PACKET_BOUNDARY,
        "boundary.synthetic_packet_boundary",
    )
    _exact(
        record["hosting_metadata_boundary"],
        HOSTING_METADATA_BOUNDARY,
        "boundary.hosting_metadata_boundary",
    )
    _exact(
        record["user_controlled_artifact_boundary"],
        USER_ARTIFACT_BOUNDARY,
        "boundary.user_controlled_artifact_boundary",
    )


def _validate_deployment(value: Any) -> None:
    record = _object(value, "deployment")
    _exact_keys(record, _DEPLOYMENT_KEYS, "deployment")
    _exact(
        record["evidence_scope"],
        "future_limited_beta_deployment_not_current_prototype",
        "deployment.evidence_scope",
    )
    for field in (
        "status",
        "host_request_metadata_review_status",
        "subprocessor_review_status",
        "access_review_status",
    ):
        _exact(record[field], "not_run", f"deployment.{field}")
    for field in _DEPLOYMENT_KEYS - {
        "evidence_scope",
        "status",
        "host_request_metadata_review_status",
        "subprocessor_review_status",
        "access_review_status",
    }:
        _exact(record[field], None, f"deployment.{field}")


def _validate_records_boundary(value: Any) -> None:
    record = _object(value, "records_boundary")
    _exact_keys(record, _RECORDS_KEYS, "records_boundary")
    for field in (
        "status",
        "search_export_rehearsal_status",
        "legal_hold_review_status",
        "retention_schedule_status",
    ):
        _exact(record[field], "not_run", f"records_boundary.{field}")
    _exact(
        record["application_applicant_record_store"],
        False,
        "records_boundary.application_applicant_record_store",
    )
    _exact(
        record["service_searchable_applicant_fields"],
        [],
        "records_boundary.service_searchable_applicant_fields",
    )
    _exact(
        record["potential_external_record_classes"],
        list(POTENTIAL_EXTERNAL_RECORD_CLASSES),
        "records_boundary.potential_external_record_classes",
    )
    _exact(
        record["cpra_routing_role"],
        "records_owner",
        "records_boundary.cpra_routing_role",
    )
    _exact(
        record["search_export_receipt_id"],
        None,
        "records_boundary.search_export_receipt_id",
    )


def _validate_export_boundary(value: Any) -> None:
    record = _object(value, "export_boundary")
    _exact_keys(record, _EXPORT_KEYS, "export_boundary")
    _exact(
        record["current_profile_id"],
        "public-synthetic-evidence-v1",
        "export_boundary.current_profile_id",
    )
    _exact(
        record["inclusion_status"],
        "excluded_pending_reviewed_future_profile",
        "export_boundary.inclusion_status",
    )
    _exact(
        record["future_profile_review_status"],
        "not_run",
        "export_boundary.future_profile_review_status",
    )
    _exact(
        record["approved_future_profile_id"],
        None,
        "export_boundary.approved_future_profile_id",
    )
    _exact(record["claim"], EXPORT_CLAIM, "export_boundary.claim")


def _validate_approvals(value: Any) -> tuple[PendingApproval, ...]:
    rows = _array(value, "approvals")
    expected_ids = sorted(APPROVAL_ROLES)
    observed_ids: list[str] = []
    approvals: list[PendingApproval] = []
    for index, item in enumerate(rows):
        field = f"approvals[{index}]"
        record = _object(item, field)
        _exact_keys(record, _APPROVAL_KEYS, field)
        approval_id = _stable_id(record["approval_id"], f"{field}.approval_id")
        observed_ids.append(approval_id)
        if approval_id not in APPROVAL_ROLES:
            raise ValueError(f"{field}.approval_id: unexpected approval")
        role = APPROVAL_ROLES[approval_id]
        _exact(record["required_role"], role, f"{field}.required_role")
        _exact(record["status"], "not_run", f"{field}.status")
        for pending_field in (
            "decision",
            "decided_by",
            "decided_on",
            "evidence_receipt_id",
        ):
            _exact(record[pending_field], None, f"{field}.{pending_field}")
        approvals.append(PendingApproval(approval_id, role, "not_run"))
    if observed_ids != expected_ids:
        raise ValueError(
            "approvals: expected the exact sorted pending approval registry"
        )
    return tuple(approvals)


def _validate_control(
    item: Any,
    *,
    index: int,
    repository_root: Path,
) -> PreparedControl:
    field = f"controls[{index}]"
    record = _object(item, field)
    _exact_keys(record, _CONTROL_KEYS, field)
    control_id = _stable_id(record["control_id"], f"{field}.control_id")
    if control_id not in CONTROL_CONTRACTS:
        raise ValueError(f"{field}.control_id: unexpected control")
    domain, objective, approval_id, evidence_paths = CONTROL_CONTRACTS[control_id]
    _exact(record["domain"], domain, f"{field}.domain")
    _exact(record["objective"], objective, f"{field}.objective")
    _exact(record["preparation_status"], "prepared", f"{field}.preparation_status")
    _exact(record["verification_status"], "not_run", f"{field}.verification_status")
    _exact(record["approval_id"], approval_id, f"{field}.approval_id")
    _exact(record["execution_receipt_id"], None, f"{field}.execution_receipt_id")
    paths = _array(record["evidence_paths"], f"{field}.evidence_paths")
    _exact(paths, list(evidence_paths), f"{field}.evidence_paths")
    for path_index, path in enumerate(paths):
        _validate_relative_path(
            path,
            repository_root,
            f"{field}.evidence_paths[{path_index}]",
        )
    return PreparedControl(control_id, domain, approval_id)


def _validate_controls(
    value: Any,
    *,
    repository_root: Path,
) -> tuple[PreparedControl, ...]:
    rows = _array(value, "controls")
    controls = tuple(
        _validate_control(item, index=index, repository_root=repository_root)
        for index, item in enumerate(rows)
    )
    if [control.control_id for control in controls] != sorted(CONTROL_CONTRACTS):
        raise ValueError("controls: expected the exact sorted control registry")
    return controls


def load_beta_operations_readiness(
    path: Path,
    *,
    repository_root: Path | None = None,
    today: date | None = None,
) -> BetaOperationsReadiness:
    """Load the strict prepared/not-approved beta operations record."""

    root = (
        repository_root.resolve()
        if repository_root is not None
        else Path(__file__).resolve().parents[2]
    )
    payload = _load_json(path)
    _exact_keys(payload, _TOP_LEVEL_KEYS, "beta operations record")
    _exact(payload["schema_version"], SCHEMA_VERSION, "schema_version")
    _exact(payload["record_id"], RECORD_ID, "record_id")
    _exact(payload["record_version"], RECORD_VERSION, "record_version")
    prepared_on = _prepared_on(payload["prepared_on"], today=resolve_today(today))
    _exact(payload["status"], STATUS, "status")
    _exact(payload["decision_status"], DECISION_STATUS, "decision_status")
    _exact(
        payload["architecture_decision_path"], ADR_PATH, "architecture_decision_path"
    )
    _exact(payload["runbook_path"], RUNBOOK_PATH, "runbook_path")
    _validate_relative_path(
        payload["architecture_decision_path"], root, "architecture_decision_path"
    )
    _validate_relative_path(payload["runbook_path"], root, "runbook_path")
    _validate_document_bindings(payload["document_bindings"], root)
    _validate_boundary(payload["boundary"])
    _validate_deployment(payload["deployment"])
    _validate_records_boundary(payload["records_boundary"])
    _validate_export_boundary(payload["export_boundary"])
    approvals = _validate_approvals(payload["approvals"])
    controls = _validate_controls(payload["controls"], repository_root=root)
    _exact(payload["claim_boundary"], CLAIM_BOUNDARY, "claim_boundary")
    return BetaOperationsReadiness(
        record_id=RECORD_ID,
        record_version=RECORD_VERSION,
        prepared_on=prepared_on,
        status=STATUS,
        decision_status=DECISION_STATUS,
        approvals=approvals,
        controls=controls,
        claim_boundary=CLAIM_BOUNDARY,
    )


def _parser(repository_root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the prepared/not-approved no-storage beta operating "
            "package. Success validates schema and pending state only."
        )
    )
    parser.add_argument(
        "--record",
        type=Path,
        default=repository_root / "data/validation/beta-operations-readiness.json",
    )
    parser.add_argument("--repository-root", type=Path, default=repository_root)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; exit 0 means valid planning data, never approval."""

    default_root = Path(__file__).resolve().parents[2]
    args = _parser(default_root).parse_args(argv)
    try:
        record = load_beta_operations_readiness(
            args.record,
            repository_root=args.repository_root,
        )
    except ValueError as error:
        print(f"beta operations package: INVALID: {error}", file=sys.stderr)
        return 2
    print("beta operations package: PREPARED / NOT APPROVED")
    print(
        f"  {len(record.controls)} controls prepared; "
        f"{len(record.approvals)} approvals not_run"
    )
    print("  schema validation is not deployment, approval, or compliance evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
