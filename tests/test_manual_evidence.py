import copy
import json
import re
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest

from permit_pathways.explanations import (
    load_explanations,
    localized_content_fingerprint,
)
from permit_pathways.screening import load_rules

ROOT = Path(__file__).parent.parent
EVIDENCE_PATH = ROOT / "data" / "validation" / "woodland-manual-evidence.json"
JOURNEY_PATH = (
    ROOT / "data" / "journeys" / "generated" / "woodland-preapproved-detached-adu.json"
)
EXPLANATIONS_PATH = ROOT / "data" / "explanations" / "plain-language.json"
RULES_PATH = ROOT / "data" / "rules"
DOCUMENT_PATH = ROOT / "docs" / "MANUAL-VALIDATION.md"

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VALID_JOURNEY_PATH = (
    "prepare.html?journey=woodland-preapproved-detached-adu-synthetic&version=1.0.0"
)

EXPECTED_CHECK_IDS = {
    "KB-INDEX",
    "KB-JOURNEY",
    "KB-REVIEW",
    "KB-EVIDENCE",
    "SR-JOURNEY-VOICEOVER-SAFARI",
    "SR-JOURNEY-NVDA",
    "SR-TOOLS",
    "REFLOW-JOURNEY",
    "REFLOW-OTHER-PAGES",
    "MOBILE-JOURNEY-IOS",
    "MOBILE-JOURNEY-ANDROID",
    "TEXT-SPACING-ALL",
    "FORCED-COLORS-JOURNEY",
    "FORCED-COLORS-OTHER-PAGES",
    "MOTION",
    "PRINT-JOURNEY-CHROME",
    "PRINT-JOURNEY-SAFARI",
    "PRINT-JOURNEY-FIREFOX",
    "PDF-AT-JOURNEY",
    "ES-USABILITY-JOURNEY",
    "ES-HANDOFF",
    "ES-PRONUNCIATION",
}

JOURNEY_CHECK_IDS = {
    "KB-JOURNEY",
    "SR-JOURNEY-VOICEOVER-SAFARI",
    "SR-JOURNEY-NVDA",
    "REFLOW-JOURNEY",
    "MOBILE-JOURNEY-IOS",
    "MOBILE-JOURNEY-ANDROID",
    "TEXT-SPACING-ALL",
    "FORCED-COLORS-JOURNEY",
    "PRINT-JOURNEY-CHROME",
    "PRINT-JOURNEY-SAFARI",
    "PRINT-JOURNEY-FIREFOX",
    "PDF-AT-JOURNEY",
    "ES-USABILITY-JOURNEY",
    "ES-HANDOFF",
    "ES-PRONUNCIATION",
}


def _payload() -> dict:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def _journey() -> dict:
    return json.loads(JOURNEY_PATH.read_text(encoding="utf-8"))


def _explanations():
    rules = load_rules(RULES_PATH, today=date(2026, 8, 2))
    return load_explanations(
        EXPLANATIONS_PATH,
        rules,
        today=date(2026, 8, 2),
    )


def _non_blank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _parse_iso_date(value: object) -> date:
    assert isinstance(value, str) and ISO_DATE.fullmatch(value)
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise AssertionError(f"invalid ISO date: {value}") from error


def _parse_iso_timestamp(value: object) -> datetime:
    assert isinstance(value, str) and value.strip()
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise AssertionError(f"invalid ISO timestamp: {value}") from error
    assert parsed.tzinfo is not None and parsed.utcoffset() is not None
    return parsed


def _assert_exact_keys(record: dict, expected: set[str], field: str) -> None:
    assert isinstance(record, dict), field
    assert set(record) == expected, field


def _assert_execution_lock(lock: dict, has_executed_result: bool) -> None:
    if not has_executed_result:
        assert lock["execution_status"] == "not_run"
        assert lock["tested_commit"] is None
        assert lock["deployed_url"] is None
        return
    assert lock["execution_status"] == "executed"
    assert COMMIT.fullmatch(lock["tested_commit"])
    deployed = urlsplit(lock["deployed_url"])
    assert deployed.scheme == "https"
    assert deployed.netloc


def _assert_manual_transition(check: dict) -> None:
    _assert_exact_keys(
        check,
        {
            "check_id",
            "category",
            "surface_paths",
            "required_methods",
            "required_tasks",
            "result",
            "execution",
            "reviewer",
            "evidence",
            "signoff",
        },
        check.get("check_id", "manual check"),
    )
    assert check["result"] in {"not_run", "pass", "fail", "blocked"}
    assert check["surface_paths"]
    assert all(_non_blank(value) for value in check["surface_paths"])
    assert check["required_methods"]
    assert all(_non_blank(value) for value in check["required_methods"])
    assert check["required_tasks"]
    assert all(_non_blank(value) for value in check["required_tasks"])

    if check["result"] == "not_run":
        assert check["execution"] is None
        assert check["reviewer"] is None
        assert check["evidence"] is None
        assert check["signoff"] is None
        return

    execution = check["execution"]
    _assert_exact_keys(
        execution,
        {
            "tester_public_identifier",
            "tester_role",
            "started_at",
            "completed_at",
            "os_device",
            "browser",
            "assistive_technology_or_setting",
            "task_paths",
            "observations",
            "privacy_confirmation",
        },
        f"{check['check_id']}.execution",
    )
    assert all(
        _non_blank(execution[field])
        for field in (
            "tester_public_identifier",
            "tester_role",
            "os_device",
            "browser",
            "assistive_technology_or_setting",
            "observations",
            "privacy_confirmation",
        )
    )
    started_at = _parse_iso_timestamp(execution["started_at"])
    completed_at = _parse_iso_timestamp(execution["completed_at"])
    assert started_at <= completed_at
    assert execution["task_paths"]
    assert all(_non_blank(path) for path in execution["task_paths"])

    reviewer = check["reviewer"]
    _assert_exact_keys(
        reviewer,
        {"public_identifier", "role", "reviewed_on", "publication_consent"},
        f"{check['check_id']}.reviewer",
    )
    assert _non_blank(reviewer["public_identifier"])
    assert _non_blank(reviewer["role"])
    _parse_iso_date(reviewer["reviewed_on"])
    assert reviewer["publication_consent"] is True

    assert isinstance(check["evidence"], list) and check["evidence"]
    assert all(_non_blank(reference) for reference in check["evidence"])

    signoff = check["signoff"]
    _assert_exact_keys(
        signoff,
        {"disposition", "signed_by", "signed_on", "retest_of"},
        f"{check['check_id']}.signoff",
    )
    assert _non_blank(signoff["signed_by"])
    _parse_iso_date(signoff["signed_on"])
    assert signoff["retest_of"] is None or _non_blank(signoff["retest_of"])
    expected_dispositions = {
        "pass": {"accepted_for_tested_artifact"},
        "fail": {"rejected"},
        "blocked": {"exception_pending"},
    }
    assert signoff["disposition"] in expected_dispositions[check["result"]]


def _assert_spanish_transition(row: dict, explanation) -> None:
    _assert_exact_keys(
        row,
        {
            "source_rule_id",
            "explanation_version",
            "citation_fingerprint",
            "rule_fingerprint",
            "english_content_fingerprint",
            "spanish_content_fingerprint",
            "result",
            "reviewer",
            "method",
            "reviewed_on",
            "evidence",
            "signoff",
        },
        row.get("source_rule_id", "Spanish review"),
    )
    assert row["result"] in {
        "not_run",
        "approved",
        "changes_required",
        "blocked_by_source",
    }
    assert row["explanation_version"] == explanation.version
    assert row["citation_fingerprint"] == explanation.citation_fingerprint
    assert row["rule_fingerprint"] == explanation.rule_fingerprint
    assert row["english_content_fingerprint"] == localized_content_fingerprint(
        explanation.version,
        "en",
        explanation.en,
    )
    assert explanation.es is not None
    assert row["spanish_content_fingerprint"] == localized_content_fingerprint(
        explanation.version,
        "es",
        explanation.es,
    )
    for field in (
        "citation_fingerprint",
        "rule_fingerprint",
        "english_content_fingerprint",
        "spanish_content_fingerprint",
    ):
        assert SHA256.fullmatch(row[field])

    if row["result"] == "not_run":
        assert row["reviewer"] is None
        assert row["method"] is None
        assert row["reviewed_on"] is None
        assert row["evidence"] is None
        assert row["signoff"] is None
        assert explanation.es.translation_status == "machine_draft"
        assert explanation.es.reviewer is None
        assert explanation.es.reviewed_on is None
        assert explanation.es.method is None
        assert explanation.es.reviewed_version is None
        assert explanation.es.content_fingerprint is None
        return

    reviewer = row["reviewer"]
    _assert_exact_keys(
        reviewer,
        {"public_identifier", "qualification", "publication_consent"},
        f"{row['source_rule_id']}.reviewer",
    )
    assert _non_blank(reviewer["public_identifier"])
    assert _non_blank(reviewer["qualification"])
    assert reviewer["publication_consent"] is True
    assert _non_blank(row["method"])
    _parse_iso_date(row["reviewed_on"])
    assert isinstance(row["evidence"], list) and row["evidence"]
    assert all(_non_blank(reference) for reference in row["evidence"])

    signoff = row["signoff"]
    _assert_exact_keys(
        signoff,
        {"disposition", "signed_by", "signed_on"},
        f"{row['source_rule_id']}.signoff",
    )
    assert _non_blank(signoff["signed_by"])
    _parse_iso_date(signoff["signed_on"])
    expected_dispositions = {
        "approved": "accepted_for_exact_record",
        "changes_required": "rejected_pending_revision",
        "blocked_by_source": "exception_pending_source_review",
    }
    assert signoff["disposition"] == expected_dispositions[row["result"]]

    if row["result"] == "approved":
        assert explanation.es.translation_status in {
            "human_reviewed",
            "jurisdiction_approved",
        }
        assert explanation.es.reviewer == reviewer["public_identifier"]
        assert explanation.es.reviewed_on == row["reviewed_on"]
        assert explanation.es.method == row["method"]
        assert explanation.es.reviewed_version == row["explanation_version"]
        assert explanation.es.content_fingerprint == row["spanish_content_fingerprint"]
    else:
        assert explanation.es.translation_status == "machine_draft"
        assert explanation.es.reviewer is None
        assert explanation.es.reviewed_on is None
        assert explanation.es.method is None
        assert explanation.es.reviewed_version is None
        assert explanation.es.content_fingerprint is None


def _assert_privacy_transition(privacy: dict, has_executed_result: bool) -> None:
    _assert_exact_keys(
        privacy,
        {
            "status",
            "allowed_material",
            "prohibited_material",
            "contact_storage",
            "recording",
            "execution_confirmation",
            "reviewer",
            "evidence",
            "signoff",
        },
        "privacy_protocol",
    )
    assert privacy["allowed_material"]
    assert privacy["prohibited_material"]
    assert privacy["contact_storage"] == "outside_repository"
    assert privacy["recording"] == "none"
    if not has_executed_result:
        assert privacy["status"] == "not_run"
        assert privacy["execution_confirmation"] is None
        assert privacy["reviewer"] is None
        assert privacy["evidence"] is None
        assert privacy["signoff"] is None
        return
    assert privacy["status"] == "confirmed"
    assert _non_blank(privacy["execution_confirmation"])
    _assert_exact_keys(
        privacy["reviewer"],
        {"public_identifier", "publication_consent", "reviewed_on"},
        "privacy_protocol.reviewer",
    )
    assert _non_blank(privacy["reviewer"]["public_identifier"])
    assert privacy["reviewer"]["publication_consent"] is True
    _parse_iso_date(privacy["reviewer"]["reviewed_on"])
    assert isinstance(privacy["evidence"], list) and privacy["evidence"]
    assert all(_non_blank(reference) for reference in privacy["evidence"])
    _assert_exact_keys(
        privacy["signoff"],
        {"signed_by", "signed_on"},
        "privacy_protocol.signoff",
    )
    assert _non_blank(privacy["signoff"]["signed_by"])
    _parse_iso_date(privacy["signoff"]["signed_on"])


def _assert_valid_payload(payload: dict, journey: dict, explanations: dict) -> None:
    _assert_exact_keys(
        payload,
        {
            "schema_version",
            "record_id",
            "record_version",
            "status",
            "prepared_on",
            "scope",
            "claim_boundary",
            "artifact_lock",
            "privacy_protocol",
            "manual_checks",
            "spanish_review_protocol",
            "spanish_semantic_reviews",
        },
        "manual evidence",
    )
    assert payload["schema_version"] == 1
    assert payload["record_id"] == "woodland-route-to-packet-manual-evidence"
    assert re.fullmatch(r"\d+\.\d+\.\d+", payload["record_version"])
    _parse_iso_date(payload["prepared_on"])
    assert _non_blank(payload["scope"])
    assert _non_blank(payload["claim_boundary"])

    lock = payload["artifact_lock"]
    _assert_exact_keys(
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
        "artifact_lock",
    )
    assert lock["sample_entry_path"] == "check.html?sample=adu"
    assert lock["valid_journey_path"] == VALID_JOURNEY_PATH
    parsed_path = urlsplit(lock["valid_journey_path"])
    assert parsed_path.path == "prepare.html"
    assert parse_qsl(parsed_path.query, keep_blank_values=True) == [
        ("journey", journey["journey_id"]),
        ("version", journey["version"]),
    ]
    expected_locks = {
        "journey_id": journey["journey_id"],
        "journey_version": journey["version"],
        "journey_fingerprint": journey["journey_fingerprint"],
        "screening_case_id": journey["screening_case_id"],
        "screening_case_fingerprint": journey["screening_case_fingerprint"],
        "fact_envelope_fingerprint": journey["fact_envelope_fingerprint"],
        "readiness_workflow_id": journey["readiness_workflow_id"],
        "readiness_workflow_fingerprint": journey["readiness_workflow_fingerprint"],
        "readiness_packet_id": journey["readiness_packet_id"],
        "readiness_packet_fingerprint": journey["readiness_packet_fingerprint"],
        "route_source_status_as_of": journey["route_source_status_as_of"],
        "route_source_review_due_on": journey["route_source_review_due_on"],
    }
    for field, expected in expected_locks.items():
        assert lock[field] == expected, field
    for field in (
        "journey_fingerprint",
        "screening_case_fingerprint",
        "fact_envelope_fingerprint",
        "readiness_workflow_fingerprint",
        "readiness_packet_fingerprint",
    ):
        assert SHA256.fullmatch(lock[field])

    checks = payload["manual_checks"]
    assert len({check["check_id"] for check in checks}) == len(checks)
    assert {check["check_id"] for check in checks} == EXPECTED_CHECK_IDS
    for check in checks:
        _assert_manual_transition(check)

    rows = payload["spanish_semantic_reviews"]
    assert len({row["source_rule_id"] for row in rows}) == len(rows)
    assert {row["source_rule_id"] for row in rows} == set(explanations)
    for row in rows:
        _assert_spanish_transition(row, explanations[row["source_rule_id"]])

    protocol = payload["spanish_review_protocol"]
    _assert_exact_keys(
        protocol,
        {
            "allowed_results",
            "required_dimensions",
            "same_version_and_fingerprints_required",
            "english_content_review_is_independent",
        },
        "spanish_review_protocol",
    )
    assert protocol["allowed_results"] == [
        "not_run",
        "approved",
        "changes_required",
        "blocked_by_source",
    ]
    assert len(protocol["required_dimensions"]) == 6
    assert protocol["same_version_and_fingerprints_required"] is True
    assert protocol["english_content_review_is_independent"] is True

    result_states = [check["result"] != "not_run" for check in checks] + [
        row["result"] != "not_run" for row in rows
    ]
    has_executed_result = any(result_states)
    all_results_recorded = all(result_states)
    expected_status = (
        "complete"
        if all_results_recorded
        else "in_progress"
        if has_executed_result
        else "prepared_not_executed"
    )
    assert payload["status"] == expected_status
    _assert_execution_lock(lock, has_executed_result)
    _assert_privacy_transition(payload["privacy_protocol"], has_executed_result)


def _lock_executed(payload: dict) -> None:
    payload["artifact_lock"].update(
        {
            "execution_status": "executed",
            "tested_commit": "a" * 40,
            "deployed_url": "https://chelseakr.github.io/permit-pathways/",
        }
    )


def _confirm_privacy(payload: dict) -> None:
    payload["privacy_protocol"].update(
        {
            "status": "confirmed",
            "execution_confirmation": (
                "Synthetic fixture and redacted evidence with consented public "
                "identifiers only."
            ),
            "reviewer": {
                "public_identifier": "Privacy reviewer P01",
                "publication_consent": True,
                "reviewed_on": "2026-08-02",
            },
            "evidence": ["evidence/privacy-review.txt"],
            "signoff": {
                "signed_by": "Privacy reviewer P01",
                "signed_on": "2026-08-02",
            },
        }
    )


def _record_manual_result(check: dict, result: str = "pass") -> None:
    dispositions = {
        "pass": "accepted_for_tested_artifact",
        "fail": "rejected",
        "blocked": "exception_pending",
    }
    check.update(
        {
            "result": result,
            "execution": {
                "tester_public_identifier": "Tester T01",
                "tester_role": "Manual accessibility tester",
                "started_at": "2026-08-02T10:00:00-07:00",
                "completed_at": "2026-08-02T10:30:00-07:00",
                "os_device": "Recorded operating system and device",
                "browser": "Recorded browser and version",
                "assistive_technology_or_setting": "Method required by the row",
                "task_paths": list(check["surface_paths"]),
                "observations": "Version-bound observations recorded.",
                "privacy_confirmation": (
                    "Synthetic fixture and consented public identifiers only."
                ),
            },
            "reviewer": {
                "public_identifier": "Acceptance reviewer A01",
                "role": "Independent acceptance reviewer",
                "reviewed_on": "2026-08-02",
                "publication_consent": True,
            },
            "evidence": [f"evidence/{check['check_id'].lower()}.txt"],
            "signoff": {
                "disposition": dispositions[result],
                "signed_by": "Acceptance reviewer A01",
                "signed_on": "2026-08-02",
                "retest_of": None,
            },
        }
    )


def _record_spanish_result(row: dict, result: str = "changes_required") -> None:
    dispositions = {
        "approved": "accepted_for_exact_record",
        "changes_required": "rejected_pending_revision",
        "blocked_by_source": "exception_pending_source_review",
    }
    row.update(
        {
            "result": result,
            "reviewer": {
                "public_identifier": "Semantic reviewer S01",
                "qualification": ("Spanish-language and permitting-domain reviewer"),
                "publication_consent": True,
            },
            "method": "Rule-by-rule bilingual comparison with cited source evidence",
            "reviewed_on": "2026-08-02",
            "evidence": [f"evidence/spanish-{row['source_rule_id']}.txt"],
            "signoff": {
                "disposition": dispositions[result],
                "signed_by": "Language acceptance reviewer L01",
                "signed_on": "2026-08-02",
            },
        }
    )


def _promote_spanish_explanation(explanations: dict, row: dict) -> dict:
    updated = dict(explanations)
    explanation = updated[row["source_rule_id"]]
    promoted = replace(
        explanation.es,
        translation_status="human_reviewed",
        reviewer=row["reviewer"]["public_identifier"],
        reviewed_on=row["reviewed_on"],
        method=row["method"],
        reviewed_version=row["explanation_version"],
        content_fingerprint=row["spanish_content_fingerprint"],
    )
    updated[row["source_rule_id"]] = replace(explanation, es=promoted)
    return updated


def test_committed_manual_evidence_is_strictly_unexecuted_and_cross_bound():
    payload = _payload()
    _assert_valid_payload(payload, _journey(), _explanations())

    assert all(check["result"] == "not_run" for check in payload["manual_checks"])
    assert all(
        row["result"] == "not_run" for row in payload["spanish_semantic_reviews"]
    )


def test_matrix_covers_required_modalities_and_exact_journey_state():
    payload = _payload()
    checks = {check["check_id"]: check for check in payload["manual_checks"]}

    for check_id in JOURNEY_CHECK_IDS:
        assert VALID_JOURNEY_PATH in checks[check_id]["surface_paths"], check_id

    assert "VoiceOver" in " ".join(
        checks["SR-JOURNEY-VOICEOVER-SAFARI"]["required_methods"]
    )
    assert "Safari" in " ".join(
        checks["SR-JOURNEY-VOICEOVER-SAFARI"]["required_methods"]
    )
    assert "NVDA" in " ".join(checks["SR-JOURNEY-NVDA"]["required_methods"])
    assert "200 percent" in " ".join(checks["REFLOW-JOURNEY"]["required_methods"])
    assert "400 percent" in " ".join(checks["REFLOW-JOURNEY"]["required_methods"])
    assert "Physical iPhone" in " ".join(
        checks["MOBILE-JOURNEY-IOS"]["required_methods"]
    )
    assert "Physical Android" in " ".join(
        checks["MOBILE-JOURNEY-ANDROID"]["required_methods"]
    )
    assert "forced-colors" in " ".join(
        checks["FORCED-COLORS-JOURNEY"]["required_methods"]
    )
    assert {checks[check_id]["category"] for check_id in JOURNEY_CHECK_IDS} >= {
        "keyboard_focus",
        "screen_reader",
        "zoom_reflow",
        "physical_mobile",
        "forced_colors",
        "print_visual",
        "saved_pdf_accessibility",
        "spanish_language_usability",
        "mixed_language_boundary",
        "mixed_language_screen_reader",
    }


def test_documented_tables_match_every_machine_readable_not_run_row():
    payload = _payload()
    document = DOCUMENT_PATH.read_text(encoding="utf-8")

    documented_checks = set(
        re.findall(r"^\| ([A-Z][A-Z0-9-]+) \|.*\| `not_run` \|$", document, re.M)
    )
    assert documented_checks == EXPECTED_CHECK_IDS
    for row in payload["spanish_semantic_reviews"]:
        expected = (
            f"| `{row['source_rule_id']}` | `{row['explanation_version']}` "
            "| `not_run` |"
        )
        assert expected in document
    assert VALID_JOURNEY_PATH in document
    assert "does **not** report a completed accessibility audit" in document
    normalized_document = " ".join(document.split())
    assert (
        "visual PDF inspection standing in for assistive-technology review"
        in normalized_document
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("execution", {"tester": "Hidden result"}),
        ("reviewer", {"name": "Hidden reviewer"}),
        ("evidence", ["hidden-evidence.txt"]),
        ("signoff", {"disposition": "accepted_for_tested_artifact"}),
    ],
)
def test_not_run_manual_rows_reject_hidden_execution_evidence_or_signoff(field, value):
    payload = _payload()
    payload["manual_checks"][0][field] = value

    with pytest.raises(AssertionError):
        _assert_valid_payload(payload, _journey(), _explanations())


def test_manual_pass_cannot_outrun_artifact_execution_and_signoff():
    payload = _payload()
    payload["status"] = "in_progress"
    _lock_executed(payload)
    _confirm_privacy(payload)
    _record_manual_result(payload["manual_checks"][0])
    payload["artifact_lock"]["execution_status"] = "locked_for_execution"

    with pytest.raises(AssertionError):
        _assert_valid_payload(payload, _journey(), _explanations())


def test_one_signed_manual_result_is_a_valid_in_progress_transition():
    payload = _payload()
    payload["status"] = "in_progress"
    _lock_executed(payload)
    _confirm_privacy(payload)
    _record_manual_result(payload["manual_checks"][0])

    _assert_valid_payload(payload, _journey(), _explanations())


@pytest.mark.parametrize(
    ("started_at", "completed_at"),
    [
        ("not-a-timestamp", "2026-08-02T10:30:00-07:00"),
        ("2026-08-02T10:00:00", "2026-08-02T10:30:00"),
        ("2026-08-02T11:00:00-07:00", "2026-08-02T10:30:00-07:00"),
    ],
)
def test_manual_execution_requires_parseable_ordered_timezone_timestamps(
    started_at, completed_at
):
    payload = _payload()
    payload["status"] = "in_progress"
    _lock_executed(payload)
    _confirm_privacy(payload)
    check = payload["manual_checks"][0]
    _record_manual_result(check)
    check["execution"]["started_at"] = started_at
    check["execution"]["completed_at"] = completed_at

    with pytest.raises(AssertionError):
        _assert_valid_payload(payload, _journey(), _explanations())


def test_complete_status_requires_every_manual_and_spanish_result():
    payload = _payload()
    payload["status"] = "complete"
    _lock_executed(payload)
    _confirm_privacy(payload)
    _record_manual_result(payload["manual_checks"][0])

    with pytest.raises(AssertionError):
        _assert_valid_payload(payload, _journey(), _explanations())


def test_complete_status_accepts_all_signed_results_even_when_unfavorable():
    payload = _payload()
    payload["status"] = "complete"
    _lock_executed(payload)
    _confirm_privacy(payload)
    for index, check in enumerate(payload["manual_checks"]):
        _record_manual_result(check, "fail" if index == 0 else "pass")
    for index, row in enumerate(payload["spanish_semantic_reviews"]):
        _record_spanish_result(
            row,
            "blocked_by_source" if index == 0 else "changes_required",
        )

    _assert_valid_payload(payload, _journey(), _explanations())


@pytest.mark.parametrize(
    "field",
    [
        "journey_fingerprint",
        "screening_case_fingerprint",
        "fact_envelope_fingerprint",
        "readiness_workflow_fingerprint",
        "readiness_packet_fingerprint",
    ],
)
def test_artifact_fingerprint_drift_invalidates_the_prepared_matrix(field):
    payload = _payload()
    payload["artifact_lock"][field] = "sha256:" + "0" * 64

    with pytest.raises(AssertionError):
        _assert_valid_payload(payload, _journey(), _explanations())


def test_spanish_copy_drift_invalidates_the_semantic_review_lock():
    payload = _payload()
    payload["spanish_semantic_reviews"][0]["spanish_content_fingerprint"] = (
        "sha256:" + "0" * 64
    )

    with pytest.raises(AssertionError):
        _assert_valid_payload(payload, _journey(), _explanations())


def test_spanish_approval_cannot_outrun_underlying_translation_metadata():
    payload = copy.deepcopy(_payload())
    payload["status"] = "in_progress"
    _lock_executed(payload)
    _confirm_privacy(payload)
    row = payload["spanish_semantic_reviews"][0]
    _record_spanish_result(row, "approved")

    with pytest.raises(AssertionError):
        _assert_valid_payload(payload, _journey(), _explanations())


def test_spanish_approval_is_valid_only_with_matching_promoted_metadata():
    payload = _payload()
    payload["status"] = "in_progress"
    _lock_executed(payload)
    _confirm_privacy(payload)
    row = payload["spanish_semantic_reviews"][0]
    _record_spanish_result(row, "approved")
    explanations = _promote_spanish_explanation(_explanations(), row)

    _assert_valid_payload(payload, _journey(), explanations)


@pytest.mark.parametrize("result", ["changes_required", "blocked_by_source"])
def test_nonapproved_spanish_result_rejects_promoted_translation_metadata(result):
    payload = _payload()
    payload["status"] = "in_progress"
    _lock_executed(payload)
    _confirm_privacy(payload)
    row = payload["spanish_semantic_reviews"][0]
    _record_spanish_result(row, result)
    explanations = _promote_spanish_explanation(_explanations(), row)

    with pytest.raises(AssertionError):
        _assert_valid_payload(payload, _journey(), explanations)
