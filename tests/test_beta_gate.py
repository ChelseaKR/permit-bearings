from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import pytest

import permit_pathways.beta_gate as beta_gate_module
from permit_pathways.beta_gate import (
    CLAIM_BOUNDARY,
    DEFAULT_RECORD_PATH,
    EXPORT_BOUNDARY_CLAIM,
    artifact_set_fingerprint,
    load_beta_gate,
)
from permit_pathways.beta_gate_cli import main

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / DEFAULT_RECORD_PATH
TODAY = date(2026, 8, 9)


def _payload() -> dict[str, Any]:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def _write_record(tmp_path: Path, payload: Any, *, raw: str | None = None) -> Path:
    path = tmp_path / "pilot-beta-gate.json"
    if raw is None:
        path.write_text(json.dumps(payload), encoding="utf-8")
    else:
        path.write_text(raw, encoding="utf-8")
    return path


def _binding(payload: dict[str, Any], artifact_id: str) -> dict[str, Any]:
    return next(
        row for row in payload["artifact_bindings"] if row["artifact_id"] == artifact_id
    )


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Registry inputs require an exclusive link count; a hard-linked fixture
    # would mutate the live repository file's metadata for the rest of the
    # test session and create order-dependent failures.
    shutil.copy2(source, destination)


def _repository(tmp_path: Path) -> Path:
    """Build a cheap complete-enough repository for artifact mutation tests."""

    repository = tmp_path / "repository"
    payload = _payload()
    paths = {row["path"] for row in payload["artifact_bindings"]}
    paths.update(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "data").rglob("*")
        if path.is_file()
    )
    profile = json.loads(
        (ROOT / "data/export/public-synthetic-evidence-v1.json").read_text(
            encoding="utf-8"
        )
    )
    paths.update(row["path"] for row in profile["entries"])

    operations = json.loads(
        (ROOT / "data/validation/beta-operations-readiness.json").read_text(
            encoding="utf-8"
        )
    )
    paths.update(
        {
            operations["architecture_decision_path"],
            operations["runbook_path"],
            *(row["path"] for row in operations["document_bindings"]),
            *(
                path
                for control in operations["controls"]
                for path in control["evidence_paths"]
            ),
        }
    )
    evaluation = json.loads(
        (ROOT / "data/conformance/evaluations/heldout-v1/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    paths.update(
        {
            evaluation["scanner"]["scanner_path"],
            evaluation["scanner"]["checks_path"],
            evaluation["scanner"]["evaluator_path"],
            "data/golden/example.json",
            "data/sources.json",
            "data/rules/index.json",
            "data/rules/statewide.json",
            "data/rules/davis.json",
            "data/rules/woodland.json",
            str(DEFAULT_RECORD_PATH),
        }
    )
    for relative in paths:
        _copy_file(ROOT / relative, repository / relative)
    return repository


def _replace_json(path: Path, payload: Any) -> None:
    path.unlink(missing_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _refresh_binding(
    repository: Path,
    gate: dict[str, Any],
    artifact_id: str,
) -> None:
    binding = _binding(gate, artifact_id)
    raw = (repository / binding["path"]).read_bytes()
    binding["sha256"] = f"sha256:{hashlib.sha256(raw).hexdigest()}"
    gate["aggregate"]["artifact_set_fingerprint"] = artifact_set_fingerprint(
        gate["artifact_bindings"]
    )


def _mutate_artifact(
    repository: Path,
    gate: dict[str, Any],
    artifact_id: str,
    mutate: Any,
) -> None:
    binding = _binding(gate, artifact_id)
    path = repository / binding["path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    _replace_json(path, payload)
    _refresh_binding(repository, gate, artifact_id)
    _replace_json(repository / DEFAULT_RECORD_PATH, gate)


def _refresh_export_profile_for_artifact(
    repository: Path,
    gate: dict[str, Any],
    artifact_id: str,
) -> None:
    binding = _binding(gate, artifact_id)
    profile_binding = _binding(gate, "public_synthetic_export")
    profile_path = repository / profile_binding["path"]
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    entry = next(row for row in profile["entries"] if row["path"] == binding["path"])
    entry["raw_sha256"] = (
        "sha256:"
        + hashlib.sha256((repository / binding["path"]).read_bytes()).hexdigest()
    )
    _replace_json(profile_path, profile)
    _refresh_binding(repository, gate, "public_synthetic_export")
    _replace_json(repository / DEFAULT_RECORD_PATH, gate)


def _source_state_variant(
    repository: Path,
    gate: dict[str, Any],
    *,
    status: str,
) -> None:
    binding = _binding(gate, "source_state")
    path = repository / binding["path"]
    state = json.loads(path.read_text(encoding="utf-8"))
    # A Davis-only dependency does not alter the Woodland reference outputs.
    observation = next(
        item
        for item in state["observations"]
        if item["source_id"] == "davis-adu-handout-2026"
    )
    source_id = observation["source_id"]
    if status == "changed":
        observation["status"] = "changed"
        observation["observed_sha256"] = "a" * 64
        observation["reason"] = None
        state["changed_source_ids"] = [source_id]
        state["unverifiable_source_ids"] = []
    else:
        observation["status"] = "unverifiable"
        observation["observed_sha256"] = None
        observation["reason"] = "controlled network failure"
        observation["unverifiable_kind"] = "transport"
        state["changed_source_ids"] = []
        state["unverifiable_source_ids"] = [source_id]

    rules = [
        record
        for file_path in sorted((repository / "data/rules").glob("*.json"))
        if file_path.name != "index.json"
        for record in json.loads(file_path.read_text(encoding="utf-8"))
    ]
    affected = (
        sorted(
            record["rule_id"]
            for record in rules
            if source_id in record["source_dependencies"]
        )
        if status == "changed"
        else []
    )
    all_rule_ids = sorted(record["rule_id"] for record in rules)
    state["affected_rule_ids"] = affected
    state["unaffected_rule_ids"] = sorted(set(all_rule_ids) - set(affected))
    golden = json.loads(
        (repository / "data/golden/example.json").read_text(encoding="utf-8")
    )
    affected_cases = sorted(
        record["case_id"]
        for record in golden
        if set(record["rule_dependency_ids"]).intersection(affected)
    )
    state["affected_golden_case_ids"] = affected_cases
    state["unaffected_golden_case_ids"] = sorted(
        record["case_id"]
        for record in golden
        if record["case_id"] not in affected_cases
    )
    _replace_json(path, state)
    _refresh_binding(repository, gate, "source_state")
    gate["aggregate"]["changed_source_count"] = len(state["changed_source_ids"])
    gate["aggregate"]["unverifiable_source_count"] = len(
        state["unverifiable_source_ids"]
    )
    gate["aggregate"]["stale_rule_count"] = len(affected)
    _replace_json(repository / DEFAULT_RECORD_PATH, gate)


def test_committed_gate_recomputes_prepared_not_run_state() -> None:
    summary = load_beta_gate(RECORD, repository_root=ROOT, today=TODAY)

    assert summary.record_status == "prepared"
    assert summary.beta_status == "not_run"
    assert summary.artifact_count == 12
    assert summary.not_run_gate_count == 14
    assert summary.rule_count == 19
    assert summary.machine_linked_rule_count == 19
    assert summary.stale_rule_count == 0
    assert summary.unverified_rule_count == 0
    assert summary.changed_source_count == 0
    assert summary.unverifiable_source_count == 0
    assert summary.reference_currency_blocker_ids == ()
    assert summary.blocking_gate_ids == tuple(sorted(summary.blocking_gate_ids))


def test_committed_record_has_no_pilot_or_person_evidence() -> None:
    payload = _payload()

    assert payload["pilot_scope"] == {
        "active_source_package_id": None,
        "deployment_url": None,
        "frozen_commit_sha": None,
        "jurisdiction_id": None,
        "permit_subtype_id": None,
        "review_owner_role": None,
        "source_owner_role": None,
        "sponsor_role": None,
        "status": "not_run",
        "workflow_id": None,
        "workflow_version": None,
    }
    assert payload["prototype_reference"]["counts_as_active_pilot"] is False
    assert payload["claim_boundary"] == CLAIM_BOUNDARY
    assert payload["export_boundary"]["claim"] == EXPORT_BOUNDARY_CLAIM
    assert payload["aggregate"]["supports_tested_beta_claim"] is False


def test_gate_is_outside_export_profile_v1() -> None:
    profile = json.loads(
        (ROOT / "data/export/public-synthetic-evidence-v1.json").read_text(
            encoding="utf-8"
        )
    )
    exported_paths = {row["path"] for row in profile["entries"]}
    assert {
        str(DEFAULT_RECORD_PATH),
        "src/permit_pathways/beta_gate.py",
        "src/permit_pathways/beta_gate_cli.py",
        "tests/test_beta_gate.py",
    }.isdisjoint(exported_paths)
    assert _payload()["export_boundary"]["inclusion_status"] == (
        "excluded_from_profiles_v1_v2"
    )


def test_cli_outputs_machine_readable_non_claim(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        main(["validate", "--record", str(RECORD), "--repository-root", str(ROOT)]) == 0
    )
    output = json.loads(capsys.readouterr().out)

    assert output["record_status"] == "prepared"
    assert output["beta_status"] == "not_run"
    assert output["not_run_gate_count"] == 14
    assert output["supports_tested_beta_claim"] is False
    assert output["supports_human_review_claim"] is False
    assert output["supports_partner_acceptance_claim"] is False
    assert output["supports_deployment_approval_claim"] is False
    assert output["supports_statewide_beta_claim"] is False
    assert output["stale_rule_count"] == 0
    assert output["unverified_rule_count"] == 0
    assert output["reference_currency_blocker_ids"] == []


@pytest.mark.parametrize(
    ("raw", "fragment"),
    [
        ("[]", "expected an object"),
        ('{"schema_version": 1, "schema_version": 1}', "strict UTF-8 JSON"),
        ('{"schema_version": NaN}', "strict UTF-8 JSON"),
        ("{", "strict UTF-8 JSON"),
    ],
)
def test_record_rejects_malformed_duplicate_and_nonfinite_json(
    tmp_path: Path,
    raw: str,
    fragment: str,
) -> None:
    with pytest.raises(ValueError, match=fragment):
        load_beta_gate(_write_record(tmp_path, None, raw=raw), repository_root=ROOT)


def test_oversized_record_is_rejected(tmp_path: Path) -> None:
    path = _write_record(tmp_path, None, raw=" " * (256 * 1024 + 1))
    with pytest.raises(ValueError, match="byte limit"):
        load_beta_gate(path, repository_root=ROOT)


@pytest.mark.parametrize(
    ("location", "field"),
    [
        ("root", "unexpected"),
        ("scope", "unexpected"),
        ("reference", "unexpected"),
        ("binding", "unexpected"),
        ("derived", "unexpected"),
        ("aggregate", "unexpected"),
        ("export", "unexpected"),
    ],
)
def test_unknown_fields_are_rejected(
    tmp_path: Path,
    location: str,
    field: str,
) -> None:
    payload = _payload()
    targets = {
        "root": payload,
        "scope": payload["pilot_scope"],
        "reference": payload["prototype_reference"],
        "binding": payload["artifact_bindings"][0],
        "derived": payload["derived_gates"][0],
        "aggregate": payload["aggregate"],
        "export": payload["export_boundary"],
    }
    targets[location][field] = None
    with pytest.raises(ValueError, match="unknown fields"):
        load_beta_gate(_write_record(tmp_path, payload), repository_root=ROOT)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", False),
        ("gate_id", "limited-beta-aggregate-v2"),
        ("gate_version", "2.0.0"),
        ("record_status", "approved"),
        ("beta_status", "tested_beta"),
        ("claim_boundary", "All gates passed."),
    ],
)
def test_root_identity_and_claim_cannot_be_promoted(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    payload = _payload()
    payload[field] = value
    with pytest.raises(ValueError):
        load_beta_gate(_write_record(tmp_path, payload), repository_root=ROOT)


@pytest.mark.parametrize(
    "field",
    sorted(
        {
            "active_source_package_id",
            "deployment_url",
            "frozen_commit_sha",
            "jurisdiction_id",
            "permit_subtype_id",
            "review_owner_role",
            "source_owner_role",
            "sponsor_role",
            "workflow_id",
            "workflow_version",
        }
    ),
)
def test_pilot_scope_cannot_be_filled_in_prepared_schema(
    tmp_path: Path,
    field: str,
) -> None:
    payload = _payload()
    payload["pilot_scope"][field] = "promotion-attempt"
    with pytest.raises(ValueError, match="pilot_scope"):
        load_beta_gate(_write_record(tmp_path, payload), repository_root=ROOT)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "proceed"),
        ("prepared_gate_count", 14),
        ("not_run_gate_count", 0),
        ("supports_tested_beta_claim", True),
        ("supports_statewide_beta_claim", True),
        ("supports_human_review_claim", True),
        ("supports_deployment_approval_claim", True),
        ("supports_partner_acceptance_claim", True),
    ],
)
def test_hand_edited_aggregate_promotion_is_rejected(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    payload = _payload()
    payload["aggregate"][field] = value
    with pytest.raises(ValueError, match="aggregate"):
        load_beta_gate(_write_record(tmp_path, payload), repository_root=ROOT)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "complete"),
        ("reason_code", "all_evidence_passed"),
        ("artifact_ids", []),
    ],
)
def test_hand_edited_derived_gate_is_rejected(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    payload = _payload()
    payload["derived_gates"][1][field] = value
    with pytest.raises(ValueError, match="derived_gates"):
        load_beta_gate(_write_record(tmp_path, payload), repository_root=ROOT)


def test_artifact_registry_must_be_exact_sorted_and_unique(tmp_path: Path) -> None:
    for mutate in (
        lambda rows: rows.reverse(),
        lambda rows: rows.pop(),
        lambda rows: rows.__setitem__(1, deepcopy(rows[0])),
    ):
        payload = _payload()
        mutate(payload["artifact_bindings"])
        payload["aggregate"]["artifact_set_fingerprint"] = artifact_set_fingerprint(
            payload["artifact_bindings"]
        )
        with pytest.raises(ValueError, match="artifact_bindings"):
            load_beta_gate(_write_record(tmp_path, payload), repository_root=ROOT)


@pytest.mark.parametrize(
    "path",
    ["../outside.json", "/outside.json", "data//sources.json"],
)
def test_artifact_paths_cannot_escape_or_be_noncanonical(
    tmp_path: Path,
    path: str,
) -> None:
    payload = _payload()
    payload["artifact_bindings"][0]["path"] = path
    with pytest.raises(ValueError, match="repository-relative path"):
        load_beta_gate(_write_record(tmp_path, payload), repository_root=ROOT)


def test_artifact_digest_drift_is_rejected(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    gate = _payload()
    binding = _binding(gate, "content_review")
    path = repository / binding["path"]
    raw = path.read_bytes() + b"\n"
    path.unlink()
    path.write_bytes(raw)

    with pytest.raises(ValueError, match="bound artifact bytes drifted"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_copying_another_artifact_digest_does_not_satisfy_binding(
    tmp_path: Path,
) -> None:
    payload = _payload()
    _binding(payload, "content_review")["sha256"] = _binding(
        payload, "participant_sessions"
    )["sha256"]
    payload["aggregate"]["artifact_set_fingerprint"] = artifact_set_fingerprint(
        payload["artifact_bindings"]
    )
    with pytest.raises(ValueError, match="bound artifact bytes drifted"):
        load_beta_gate(_write_record(tmp_path, payload), repository_root=ROOT)


def test_bound_artifact_duplicate_json_keys_are_rejected_even_with_new_digest(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()
    binding = _binding(gate, "content_review")
    path = repository / binding["path"]
    path.unlink()
    path.write_text('{"schema_version": 2, "schema_version": 2}', encoding="utf-8")
    _refresh_binding(repository, gate, "content_review")
    _replace_json(repository / DEFAULT_RECORD_PATH, gate)

    with pytest.raises(ValueError, match="strict UTF-8 JSON"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_bound_artifact_unknown_schema_field_is_rejected_even_with_new_digest(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["approval"] = "granted"

    _mutate_artifact(repository, gate, "content_review", mutate)
    with pytest.raises(ValueError, match="unknown fields"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_bound_artifact_symlink_is_rejected(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    gate = _payload()
    binding = _binding(gate, "content_review")
    path = repository / binding["path"]
    target = repository / _binding(gate, "participant_sessions")["path"]
    path.unlink()
    path.symlink_to(target)
    binding["sha256"] = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    gate["aggregate"]["artifact_set_fingerprint"] = artifact_set_fingerprint(
        gate["artifact_bindings"]
    )
    _replace_json(repository / DEFAULT_RECORD_PATH, gate)

    with pytest.raises(ValueError, match="symbolic links"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_bound_artifact_parent_symlink_alias_is_rejected(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    original = repository / "data/conformance/evaluations/heldout-v1"
    target = repository / "data/conformance/evaluations/heldout-v1-real"
    original.rename(target)
    original.symlink_to(target, target_is_directory=True)

    with pytest.raises(ValueError, match="symbolic links"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_symbolic_link_repository_root_is_rejected(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    alias = tmp_path / "repository-alias"
    alias.symlink_to(repository, target_is_directory=True)

    with pytest.raises(ValueError, match="repository roots"):
        load_beta_gate(alias / DEFAULT_RECORD_PATH, repository_root=alias)


def test_artifact_role_cannot_be_repointed_to_an_alternate_copy(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()
    binding = _binding(gate, "heldout_evaluation")
    original = repository / binding["path"]
    alternate = original.with_name("alternate-manifest.json")
    shutil.copy2(original, alternate)
    binding["path"] = "data/conformance/evaluations/heldout-v1/alternate-manifest.json"
    _refresh_binding(repository, gate, "heldout_evaluation")
    _replace_json(repository / DEFAULT_RECORD_PATH, gate)

    with pytest.raises(ValueError, match=r"artifact_bindings\[3\]\.path"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_nested_favorable_field_is_rejected_after_all_digest_updates(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["decision"]["approved"] = True

    _mutate_artifact(repository, gate, "external_evidence_gate", mutate)
    _refresh_export_profile_for_artifact(repository, gate, "external_evidence_gate")

    # The closed-world key check on `decision` now rejects the unknown
    # favorable field before the raw-byte pin backstop is ever reached.
    with pytest.raises(ValueError, match="unknown fields: approved"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


@pytest.mark.parametrize(
    ("artifact_id", "mutation"),
    [
        (
            "external_evidence_gate",
            lambda value: value.__setitem__(
                "claim_boundary", "The evidence gate completed successfully."
            ),
        ),
        (
            "source_change_rehearsal",
            lambda value: value["aggregate"].__setitem__("acceptable_burden", True),
        ),
    ],
)
def test_not_run_claims_and_favorable_outcomes_are_independently_pinned(
    tmp_path: Path,
    artifact_id: str,
    mutation: Any,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()
    _mutate_artifact(repository, gate, artifact_id, mutation)

    with pytest.raises(ValueError):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_shared_protocol_version_mismatch_rejected_after_all_digest_updates(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["artifact_lock"]["protocol_version"] = "9.9.9"

    _mutate_artifact(repository, gate, "participant_sessions", mutate)
    _refresh_export_profile_for_artifact(repository, gate, "participant_sessions")

    with pytest.raises(ValueError, match="protocol_version"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_specialized_loader_cannot_mutate_the_captured_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    live_manifest = repository / _binding(_payload(), "heldout_evaluation")["path"]
    original_loader = beta_gate_module.load_evaluation_manifest

    def mutate_snapshot(path: Path, snapshot_root: Path) -> Any:
        assert path != live_manifest
        assert path.is_relative_to(snapshot_root)
        path.chmod(0o600)
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["evaluation_id"] = "alternate-not-run-evaluation"
        _replace_json(path, payload)
        return original_loader(path, snapshot_root)

    monkeypatch.setattr(
        beta_gate_module,
        "load_evaluation_manifest",
        mutate_snapshot,
    )
    with pytest.raises(ValueError, match="validator mutated input"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_specialized_loader_cannot_add_a_snapshot_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    original_loader = beta_gate_module.load_evaluation_manifest

    def add_file(path: Path, snapshot_root: Path) -> Any:
        result = original_loader(path, snapshot_root)
        (snapshot_root / "data" / "rules" / "injected.json").write_text(
            "[]\n", encoding="utf-8"
        )
        return result

    monkeypatch.setattr(beta_gate_module, "load_evaluation_manifest", add_file)
    with pytest.raises(ValueError, match="added or removed a data file"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_exact_rule_manifest_rejects_an_added_live_rule_file(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    (repository / "data/rules/injected.json").write_text("[]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="exact directory membership"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


@pytest.mark.parametrize(
    ("artifact_id", "mutation"),
    [
        (
            "external_evidence_gate",
            lambda value: value["artifact_lock"].__setitem__("status", "complete"),
        ),
        (
            "content_review",
            lambda value: value["gate"].__setitem__("status", "complete"),
        ),
        (
            "participant_sessions",
            lambda value: value["aggregate"].__setitem__("status", "complete"),
        ),
        (
            "manual_evidence",
            lambda value: value["manual_checks"][0].__setitem__("result", "pass"),
        ),
        (
            "source_change_rehearsal",
            lambda value: value["aggregate"].__setitem__("status", "complete"),
        ),
        (
            "heldout_evaluation",
            lambda value: value.__setitem__("status", "complete"),
        ),
        (
            "beta_operations",
            lambda value: value.__setitem__("status", "approved"),
        ),
        (
            "reference_packet",
            lambda value: value.__setitem__("synthetic", False),
        ),
    ],
)
def test_specialized_status_cannot_be_promoted_with_a_rewritten_digest(
    tmp_path: Path,
    artifact_id: str,
    mutation: Any,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()
    _mutate_artifact(repository, gate, artifact_id, mutation)

    with pytest.raises(ValueError):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_final_proceed_decision_cannot_be_created_with_a_rewritten_digest(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["decision"]["status"] = "complete"
        payload["decision"]["recommendation"] = "proceed"

    _mutate_artifact(repository, gate, "external_evidence_gate", mutate)
    with pytest.raises(ValueError, match=r"external gate\.decision\.status"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_rule_review_promotion_cannot_be_inferred_from_edited_level(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["entries"][0]["level"] = "human_reviewed"

    _mutate_artifact(repository, gate, "rule_verification", mutate)
    with pytest.raises(ValueError):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


@pytest.mark.parametrize(
    ("artifact_id", "field", "value"),
    [
        ("participant_sessions", "journey_version", "9.9.9"),
        (
            "manual_evidence",
            "fact_envelope_fingerprint",
            "sha256:" + "a" * 64,
        ),
        (
            "source_change_rehearsal",
            "readiness_workflow_fingerprint",
            "sha256:" + "b" * 64,
        ),
    ],
)
def test_cross_ledger_identity_and_version_mismatch_is_rejected(
    tmp_path: Path,
    artifact_id: str,
    field: str,
    value: str,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["artifact_lock"][field] = value

    _mutate_artifact(repository, gate, artifact_id, mutate)
    with pytest.raises(ValueError):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_ledger_version_mismatch_with_legacy_gate_reference_is_rejected(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["record_version"] = "1.0.1"

    _mutate_artifact(repository, gate, "participant_sessions", mutate)
    with pytest.raises(ValueError, match="record_version"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_hand_edited_legacy_aggregate_is_recomputed_from_specialized_ledger(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["external_evidence"]["participant_sessions"]["sessions_completed"] = 6

    _mutate_artifact(repository, gate, "external_evidence_gate", mutate)
    with pytest.raises(ValueError, match=r"external_evidence\.participant_sessions"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_embedded_packet_drift_breaks_exact_journey_binding(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["readiness_evidence_manifest"]["overall_status"] = "complete"

    _mutate_artifact(repository, gate, "reference_journey", mutate)
    with pytest.raises(ValueError, match="readiness_evidence_manifest"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_coordinated_generated_output_edit_fails_canonical_recomputation(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()
    packet_binding = _binding(gate, "reference_packet")
    journey_binding = _binding(gate, "reference_journey")
    packet_path = repository / packet_binding["path"]
    journey_path = repository / journey_binding["path"]
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    journey = json.loads(journey_path.read_text(encoding="utf-8"))
    packet["findings"][0]["message"] = "Edited favorable interpretation."
    journey["readiness_evidence_manifest"] = deepcopy(packet)
    _replace_json(packet_path, packet)
    _replace_json(journey_path, journey)
    _refresh_binding(repository, gate, "reference_packet")
    _refresh_binding(repository, gate, "reference_journey")
    _replace_json(repository / DEFAULT_RECORD_PATH, gate)

    with pytest.raises(ValueError, match="canonical recomputation"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("inclusion_status", "included"),
        ("future_profile_review_status", "approved"),
        ("claim", "The gate is portable beta evidence."),
    ],
)
def test_export_profile_boundary_cannot_be_promoted(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    payload = _payload()
    payload["export_boundary"][field] = value
    with pytest.raises(ValueError, match="export_boundary"):
        load_beta_gate(_write_record(tmp_path, payload), repository_root=ROOT)


def test_export_gate_path_must_name_the_canonical_record(tmp_path: Path) -> None:
    payload = _payload()
    payload["export_boundary"]["gate_path"] = (
        "data/validation/not-the-pilot-beta-gate.json"
    )

    with pytest.raises(ValueError, match=r"export_boundary\.gate_path"):
        load_beta_gate(
            _write_record(tmp_path, payload),
            repository_root=ROOT,
            today=TODAY,
        )


def test_current_date_recomputes_rule_and_reference_currency(tmp_path: Path) -> None:
    far_future = date(2035, 1, 1)
    with pytest.raises(ValueError, match="aggregate"):
        load_beta_gate(RECORD, repository_root=ROOT, today=far_future)

    payload = _payload()
    payload["aggregate"]["stale_rule_count"] = 19
    payload["aggregate"]["reference_currency_blocker_ids"] = [
        "reference_journey_route_source",
        "reference_packet_source",
        "reference_program_availability",
    ]
    summary = load_beta_gate(
        _write_record(tmp_path, payload),
        repository_root=ROOT,
        today=far_future,
    )

    assert summary.stale_rule_count == 19
    assert summary.unverified_rule_count == 0
    assert summary.reference_currency_blocker_ids == (
        "reference_journey_route_source",
        "reference_packet_source",
        "reference_program_availability",
    )


@pytest.mark.parametrize("status", ["changed", "unverifiable"])
def test_valid_populated_source_state_arrays_are_semantically_validated(
    tmp_path: Path,
    status: str,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()
    _source_state_variant(repository, gate, status=status)

    summary = load_beta_gate(
        repository / DEFAULT_RECORD_PATH,
        repository_root=repository,
        today=TODAY,
    )

    assert summary.changed_source_count == (1 if status == "changed" else 0)
    assert summary.unverifiable_source_count == (1 if status == "unverifiable" else 0)


def test_future_prepared_date_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["prepared_on"] = "2026-08-10"
    with pytest.raises(ValueError, match="future"):
        load_beta_gate(
            _write_record(tmp_path, payload),
            repository_root=ROOT,
            today=TODAY,
        )


def test_cli_invalid_record_returns_two_without_success_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = _payload()
    payload["aggregate"]["supports_tested_beta_claim"] = True
    path = _write_record(tmp_path, payload)

    assert (
        main(["validate", "--record", str(path), "--repository-root", str(ROOT)]) == 2
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert "INVALID" in output.err
    assert "tested beta" not in output.out.lower()


def test_cli_repository_root_rebases_default_record(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _repository(tmp_path)
    path = repository / DEFAULT_RECORD_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["beta_status"] = "tested_beta"
    _replace_json(path, payload)

    assert main(["validate", "--repository-root", str(repository)]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "beta_status" in output.err


def test_explicit_record_rejects_a_symbolic_link_ancestor(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    record = _write_record(real, _payload())
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)

    with pytest.raises(ValueError, match="symbolic-link ancestors"):
        load_beta_gate(alias / record.name, repository_root=ROOT, today=TODAY)


def test_bound_artifact_hard_link_is_rejected(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    gate = _payload()
    binding = _binding(gate, "content_review")
    path = repository / binding["path"]
    target = repository / _binding(gate, "participant_sessions")["path"]
    path.unlink()
    path.hardlink_to(target)
    binding["sha256"] = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    gate["aggregate"]["artifact_set_fingerprint"] = artifact_set_fingerprint(
        gate["artifact_bindings"]
    )
    _replace_json(repository / DEFAULT_RECORD_PATH, gate)

    with pytest.raises(ValueError, match="linked files"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_missing_content_review_gate_key_is_rejected_cleanly(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        del payload["gate"]["initial_agreement_count"]

    _mutate_artifact(repository, gate, "content_review", mutate)

    with pytest.raises(ValueError, match=r"content review\.gate: missing fields"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_missing_rehearsal_simulation_target_source_id_is_rejected_cleanly(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        del payload["simulation_contract"]["target_source_id"]

    _mutate_artifact(repository, gate, "source_change_rehearsal", mutate)

    with pytest.raises(
        ValueError, match=r"rehearsal\.simulation_contract: missing fields"
    ):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_artifact_lock_source_snapshot_tamper_is_rejected(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["artifact_lock"]["source_snapshot"][0]["sha256"] = "not-a-sha256"

    _mutate_artifact(repository, gate, "external_evidence_gate", mutate)

    with pytest.raises(ValueError, match=r"source_snapshot.*sha256"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_artifact_lock_source_snapshot_unknown_field_is_rejected(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["artifact_lock"]["source_snapshot"][0]["verified"] = True

    _mutate_artifact(repository, gate, "external_evidence_gate", mutate)

    with pytest.raises(ValueError, match=r"source_snapshot.*unknown fields"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_decision_bounded_public_claim_cannot_be_blanked(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["decision"]["bounded_public_claim"] = ""

    _mutate_artifact(repository, gate, "external_evidence_gate", mutate)

    with pytest.raises(ValueError, match="bounded_public_claim"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_decision_permitted_recommendations_cannot_be_expanded(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["decision"]["permitted_recommendations"].append("approved_statewide")

    _mutate_artifact(repository, gate, "external_evidence_gate", mutate)

    with pytest.raises(ValueError, match="permitted_recommendations"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_recruitment_null_count_is_rejected(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["recruitment"]["reviewers"]["contacted"] = None

    _mutate_artifact(repository, gate, "external_evidence_gate", mutate)

    with pytest.raises(ValueError, match="recruitment"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_rehearsal_aggregate_defects_found_cannot_be_filled(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    gate = _payload()

    def mutate(payload: dict[str, Any]) -> None:
        payload["aggregate"]["defects_found"] = 3

    _mutate_artifact(repository, gate, "source_change_rehearsal", mutate)

    with pytest.raises(ValueError, match=r"rehearsal\.aggregate\.defects_found"):
        load_beta_gate(repository / DEFAULT_RECORD_PATH, repository_root=repository)


def test_aggregate_float_does_not_satisfy_expected_integer_count(
    tmp_path: Path,
) -> None:
    payload = _payload()
    payload["aggregate"]["changed_source_count"] = 0.0
    with pytest.raises(ValueError, match="aggregate"):
        load_beta_gate(_write_record(tmp_path, payload), repository_root=ROOT)


def test_exact_rejects_float_for_int_inside_nested_objects() -> None:
    assert beta_gate_module._strict_equal(0, 0) is True
    assert beta_gate_module._strict_equal(0.0, 0) is False
    assert beta_gate_module._strict_equal({"count": 0.0}, {"count": 0}) is False
    assert beta_gate_module._strict_equal({"count": 0}, {"count": 0}) is True
    assert beta_gate_module._strict_equal([0], [0.0]) is False
    with pytest.raises(ValueError, match=r"field: expected \{'count': 0\}"):
        beta_gate_module._exact({"count": 0.0}, {"count": 0}, "field")


def test_all_numbers_zero_rejects_none_and_string_leaves() -> None:
    with pytest.raises(ValueError, match="unexecuted zero count"):
        beta_gate_module._all_numbers_zero({"contacted": None}, "field")
    with pytest.raises(ValueError, match="unexecuted zero count"):
        beta_gate_module._all_numbers_zero({"contacted": "0"}, "field")
    beta_gate_module._all_numbers_zero({"contacted": 0, "nested": {"a": 0}}, "field")


def test_text_rejects_zero_width_space_only_content() -> None:
    with pytest.raises(ValueError, match="non-blank trimmed text"):
        beta_gate_module._text("\u200b", "field")
    assert beta_gate_module._text("visible text", "field") == "visible text"
