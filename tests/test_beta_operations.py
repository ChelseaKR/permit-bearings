from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.beta_operations import (
    ADR_PATH,
    APPROVAL_ROLES,
    BROWSER_MEMORY_FIELDS,
    CLAIM_BOUNDARY,
    CONTROL_CONTRACTS,
    DOCUMENT_BINDINGS,
    MAX_RECORD_BYTES,
    RECORD_ID,
    RECORD_VERSION,
    RUNBOOK_PATH,
    load_beta_operations_readiness,
    main,
)

ROOT = Path(__file__).parent.parent
RECORD = ROOT / "data" / "validation" / "beta-operations-readiness.json"
TODAY = date(2026, 8, 9)


def _payload() -> dict[str, Any]:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def _write(tmp_path: Path, payload: Any, *, raw: bool = False) -> Path:
    path = tmp_path / "beta-operations.json"
    if raw:
        assert isinstance(payload, (bytes, str))
        if isinstance(payload, bytes):
            path.write_bytes(payload)
        else:
            path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _load(path: Path) -> Any:
    return load_beta_operations_readiness(
        path,
        repository_root=ROOT,
        today=TODAY,
    )


def test_committed_prepared_not_approved_package_loads() -> None:
    record = _load(RECORD)

    assert record.record_id == RECORD_ID
    assert record.record_version == RECORD_VERSION
    assert record.prepared_on == "2026-08-09"
    assert record.status == "prepared_not_approved"
    assert record.decision_status == "proposed"
    assert len(record.approvals) == len(APPROVAL_ROLES) == 9
    assert len(record.controls) == len(CONTROL_CONTRACTS) == 17
    assert all(approval.status == "not_run" for approval in record.approvals)
    assert record.claim_boundary == CLAIM_BOUNDARY


def test_committed_package_pins_current_browser_memory_fields() -> None:
    payload = _payload()

    assert payload["boundary"]["service_collected_fields"] == []
    assert payload["boundary"]["service_collection_purposes"] == []
    assert payload["boundary"]["browser_memory_fields"] == list(BROWSER_MEMORY_FIELDS)
    assert payload["boundary"]["applicant_data_network_submission"] is False


def test_committed_adr_and_runbook_have_exact_raw_byte_bindings() -> None:
    payload = _payload()

    assert [row["document_id"] for row in payload["document_bindings"]] == sorted(
        DOCUMENT_BINDINGS
    )
    for row in payload["document_bindings"]:
        expected_path, expected_sha256 = DOCUMENT_BINDINGS[row["document_id"]]
        assert row == {
            "document_id": row["document_id"],
            "path": expected_path,
            "sha256": expected_sha256,
        }


def test_cli_reports_prepared_not_approved_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--record", str(RECORD), "--repository-root", str(ROOT)]) == 0
    output = capsys.readouterr()

    assert "PREPARED / NOT APPROVED" in output.out
    assert "17 controls prepared; 9 approvals not_run" in output.out
    assert "not deployment, approval, or compliance evidence" in output.out
    assert output.err == ""


@pytest.mark.parametrize(
    "raw",
    [
        "{",
        "[]",
        '{"schema_version":1,"schema_version":1}',
        '{"value":NaN}',
        b"\xff",
    ],
)
def test_malformed_non_object_duplicate_nonfinite_and_non_utf8_json_are_rejected(
    tmp_path: Path,
    raw: str | bytes,
) -> None:
    with pytest.raises(ValueError):
        _load(_write(tmp_path, raw, raw=True))


def test_oversized_record_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "oversized.json"
    path.write_bytes(b" " * (MAX_RECORD_BYTES + 1))

    with pytest.raises(ValueError, match="exceeds byte limit"):
        _load(path)


def test_missing_file_and_missing_repository_evidence_are_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="could not be read"):
        _load(tmp_path / "missing.json")

    with pytest.raises(ValueError, match="evidence path does not exist"):
        load_beta_operations_readiness(
            RECORD,
            repository_root=tmp_path,
            today=TODAY,
        )


def test_materially_changed_bound_document_is_rejected(tmp_path: Path) -> None:
    for _, (relative_path, _) in DOCUMENT_BINDINGS.items():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        source = ROOT / relative_path
        target.write_bytes(source.read_bytes())
    changed_runbook = tmp_path / RUNBOOK_PATH
    changed_runbook.write_bytes(changed_runbook.read_bytes() + b"\nApproved.\n")

    with pytest.raises(ValueError, match="bound document bytes changed"):
        load_beta_operations_readiness(
            RECORD,
            repository_root=tmp_path,
            today=TODAY,
        )


def test_document_binding_digest_cannot_be_rewritten_to_match_drift(
    tmp_path: Path,
) -> None:
    payload = _payload()
    payload["document_bindings"][0]["sha256"] = "0" * 64

    with pytest.raises(ValueError, match=r"document_bindings\[0\]\.sha256"):
        _load(_write(tmp_path, payload))


def test_document_binding_registry_is_exact_sorted_and_strict(tmp_path: Path) -> None:
    reordered = _payload()
    reordered["document_bindings"].reverse()
    with pytest.raises(ValueError, match="exact sorted"):
        _load(_write(tmp_path, reordered))

    unexpected = _payload()
    unexpected["document_bindings"][0]["document_id"] = "unknown-document"
    with pytest.raises(ValueError, match="unexpected document binding"):
        _load(_write(tmp_path, unexpected))

    malformed = _payload()
    malformed["document_bindings"][0] = None
    with pytest.raises(ValueError, match="expected an object"):
        _load(_write(tmp_path, malformed))

    unknown_field = _payload()
    unknown_field["document_bindings"][0]["approved"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        _load(_write(tmp_path, unknown_field))


@pytest.mark.parametrize("location", ["top", "boundary", "deployment", "records"])
def test_unknown_fields_are_rejected(tmp_path: Path, location: str) -> None:
    payload = _payload()
    target = {
        "top": payload,
        "boundary": payload["boundary"],
        "deployment": payload["deployment"],
        "records": payload["records_boundary"],
    }[location]
    target["unexpected"] = True

    with pytest.raises(ValueError, match="unknown fields"):
        _load(_write(tmp_path, payload))


@pytest.mark.parametrize(
    ("location", "field"),
    [
        ("top", "claim_boundary"),
        ("boundary", "accounts"),
        ("deployment", "status"),
        ("records", "status"),
        ("export", "inclusion_status"),
    ],
)
def test_missing_fields_are_rejected(
    tmp_path: Path,
    location: str,
    field: str,
) -> None:
    payload = _payload()
    target = {
        "top": payload,
        "boundary": payload["boundary"],
        "deployment": payload["deployment"],
        "records": payload["records_boundary"],
        "export": payload["export_boundary"],
    }[location]
    del target[field]

    with pytest.raises(ValueError, match="missing fields"):
        _load(_write(tmp_path, payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("record_id", "approved-beta"),
        ("record_version", "2.0.0"),
        ("status", "approved"),
        ("decision_status", "accepted"),
        ("architecture_decision_path", "docs/adr/approved.md"),
        ("runbook_path", "docs/another-runbook.md"),
        ("claim_boundary", "Approved and compliant."),
    ],
)
def test_identity_status_paths_and_claim_cannot_be_promoted_or_weakened(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    payload = _payload()
    payload[field] = value

    with pytest.raises(ValueError, match=field):
        _load(_write(tmp_path, payload))


@pytest.mark.parametrize(
    ("prepared_on", "message"),
    [
        ("2026/08/09", "expected YYYY-MM-DD"),
        ("2026-02-30", "invalid date"),
        ("2026-08-10", "future dates"),
    ],
)
def test_prepared_date_is_real_and_not_future(
    tmp_path: Path,
    prepared_on: str,
    message: str,
) -> None:
    payload = _payload()
    payload["prepared_on"] = prepared_on

    with pytest.raises(ValueError, match=message):
        _load(_write(tmp_path, payload))


@pytest.mark.parametrize(
    "field",
    [
        "accounts",
        "uploads",
        "application_managed_storage",
        "browser_persistence",
        "application_telemetry",
        "runtime_external_model_calls",
        "permitting_system_writeback",
        "applicant_data_network_submission",
    ],
)
def test_boundary_expansion_is_rejected(tmp_path: Path, field: str) -> None:
    payload = _payload()
    payload["boundary"][field] = True

    with pytest.raises(ValueError, match=field):
        _load(_write(tmp_path, payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("public_static_delivery", False),
        ("service_collected_fields", ["email"]),
        ("service_collection_purposes", ["analytics"]),
        ("browser_memory_fields", [*BROWSER_MEMORY_FIELDS, "address"]),
        ("browser_memory_purpose", "Store applicant records."),
        ("synthetic_packet_boundary", "Accept applicant documents."),
        ("hosting_metadata_boundary", "No host can log anything."),
        ("user_controlled_artifact_boundary", "The app stores every PDF."),
    ],
)
def test_data_inventory_and_boundary_prose_are_exact(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    payload = _payload()
    payload["boundary"][field] = value

    with pytest.raises(ValueError, match=field):
        _load(_write(tmp_path, payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "evidence_scope",
            "current_prototype_deployment",
        ),
        ("status", "deployed"),
        ("commit_sha", "0" * 40),
        ("https_url", "https://beta.example.gov/"),
        ("hosting_provider", "provider"),
        ("dns_provider", "provider"),
        ("cdn_provider", "provider"),
        ("host_request_metadata_review_status", "approved"),
        ("host_request_metadata_fields", []),
        ("subprocessor_review_status", "approved"),
        ("approved_subprocessors", []),
        ("access_review_status", "approved"),
        ("release_verification_receipt_id", "release-1"),
        ("rollback_verification_receipt_id", "rollback-1"),
    ],
)
def test_deployment_fields_must_remain_not_run_or_null(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    payload = _payload()
    payload["deployment"][field] = value

    with pytest.raises(ValueError, match=field):
        _load(_write(tmp_path, payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "approved"),
        ("application_applicant_record_store", True),
        ("service_searchable_applicant_fields", ["address"]),
        ("potential_external_record_classes", []),
        ("cpra_routing_role", "automated_responder"),
        ("search_export_rehearsal_status", "passed"),
        ("search_export_receipt_id", "receipt-1"),
        ("legal_hold_review_status", "approved"),
        ("retention_schedule_status", "approved"),
    ],
)
def test_records_work_must_remain_explicitly_not_run(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    payload = _payload()
    payload["records_boundary"][field] = value

    with pytest.raises(ValueError, match=field):
        _load(_write(tmp_path, payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("current_profile_id", "public-synthetic-evidence-v2"),
        ("inclusion_status", "included"),
        ("future_profile_review_status", "approved"),
        ("approved_future_profile_id", "public-synthetic-evidence-v2"),
        ("claim", "The current export includes this package."),
    ],
)
def test_export_profile_v1_exclusion_cannot_be_bypassed(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    payload = _payload()
    payload["export_boundary"][field] = value

    with pytest.raises(ValueError, match=field):
        _load(_write(tmp_path, payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "approved"),
        ("decision", "approve"),
        ("decided_by", "person@example.gov"),
        ("decided_on", "2026-08-09"),
        ("evidence_receipt_id", "approval-receipt-1"),
    ],
)
def test_no_approval_can_be_recorded_in_this_schema(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    payload = _payload()
    payload["approvals"][0][field] = value

    with pytest.raises(ValueError, match=field):
        _load(_write(tmp_path, payload))


def test_approval_registry_is_exact_sorted_and_role_bound(tmp_path: Path) -> None:
    wrong_role = _payload()
    wrong_role["approvals"][0]["required_role"] = "partner"
    with pytest.raises(ValueError, match="required_role"):
        _load(_write(tmp_path, wrong_role))

    reordered = _payload()
    reordered["approvals"].reverse()
    with pytest.raises(ValueError, match="exact sorted"):
        _load(_write(tmp_path, reordered))

    unexpected = _payload()
    unexpected["approvals"][0]["approval_id"] = "unknown-approval"
    with pytest.raises(ValueError, match="unexpected approval"):
        _load(_write(tmp_path, unexpected))


def test_approval_shape_and_identifier_are_strict(tmp_path: Path) -> None:
    non_object = _payload()
    non_object["approvals"][0] = "not_run"
    with pytest.raises(ValueError, match="expected an object"):
        _load(_write(tmp_path, non_object))

    malformed = _payload()
    malformed["approvals"][0]["approval_id"] = "Bad Approval"
    with pytest.raises(ValueError, match="stable identifier"):
        _load(_write(tmp_path, malformed))

    unknown = _payload()
    unknown["approvals"][0]["extra"] = None
    with pytest.raises(ValueError, match="unknown fields"):
        _load(_write(tmp_path, unknown))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("domain", "compliance"),
        ("objective", "Certify CPRA compliance."),
        ("preparation_status", "approved"),
        ("verification_status", "passed"),
        ("approval_id", "jurisdiction-partner-decision"),
        ("evidence_paths", ["README.md"]),
        ("execution_receipt_id", "receipt-1"),
    ],
)
def test_control_contract_cannot_be_promoted_or_weakened(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    payload = _payload()
    payload["controls"][0][field] = value

    with pytest.raises(ValueError, match=field):
        _load(_write(tmp_path, payload))


def test_control_registry_is_exact_sorted_and_strict(tmp_path: Path) -> None:
    reordered = _payload()
    reordered["controls"].reverse()
    with pytest.raises(ValueError, match="exact sorted"):
        _load(_write(tmp_path, reordered))

    unexpected = _payload()
    unexpected["controls"][0]["control_id"] = "beta-unknown-999"
    with pytest.raises(ValueError, match="unexpected control"):
        _load(_write(tmp_path, unexpected))

    malformed = _payload()
    malformed["controls"][0]["control_id"] = "Bad Control"
    with pytest.raises(ValueError, match="stable identifier"):
        _load(_write(tmp_path, malformed))

    non_object = _payload()
    non_object["controls"][0] = None
    with pytest.raises(ValueError, match="expected an object"):
        _load(_write(tmp_path, non_object))


def test_control_shape_is_exact(tmp_path: Path) -> None:
    missing = _payload()
    del missing["controls"][0]["domain"]
    with pytest.raises(ValueError, match="missing fields"):
        _load(_write(tmp_path, missing))

    unknown = _payload()
    unknown["controls"][0]["extra"] = None
    with pytest.raises(ValueError, match="unknown fields"):
        _load(_write(tmp_path, unknown))


def test_cli_invalid_input_returns_two_without_success_claim(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = copy.deepcopy(_payload())
    payload["status"] = "approved"
    path = _write(tmp_path, payload)

    assert main(["--record", str(path), "--repository-root", str(ROOT)]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "INVALID" in output.err
    assert "PREPARED / NOT APPROVED" not in output.err


def test_default_paths_are_the_committed_paths() -> None:
    payload = _payload()

    assert payload["architecture_decision_path"] == ADR_PATH
    assert payload["runbook_path"] == RUNBOOK_PATH
