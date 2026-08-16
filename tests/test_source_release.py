from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

import permit_pathways.source_release as source_release_module
import permit_pathways.source_release_cli as source_release_cli_module
from permit_pathways.harness.runner import load_golden
from permit_pathways.harness.watch import UnverifiableSource, WatchResult, load_sources
from permit_pathways.journey import load_journey_config
from permit_pathways.readiness import (
    load_readiness_packet,
    load_readiness_remedies,
    load_readiness_workflow,
)
from permit_pathways.review_queue import (
    ReadinessReviewContext,
    ReviewDecision,
    ReviewDecisionLedger,
    build_review_worklist,
    decision_template,
    encoded_decision_ledger,
    encoded_review_worklist,
)
from permit_pathways.screening import load_rules
from permit_pathways.source_release import (
    MAX_RECEIPT_BYTES,
    approval_template,
    build_release_context,
    load_approval_receipt,
    load_publication_receipt,
    load_rollback_receipt,
    prepared_receipts,
)
from permit_pathways.source_release_cli import main as source_release_main
from permit_pathways.source_state import (
    build_source_state_snapshot,
    encoded_source_state,
    source_state_fingerprint,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources.json"
RULES = ROOT / "data" / "rules"
GOLDEN = ROOT / "data" / "golden" / "example.json"
WORKFLOW = (
    ROOT / "data" / "readiness" / "workflows" / "woodland-preapproved-detached-adu.json"
)
PACKET = ROOT / "data" / "readiness" / "samples" / "woodland-preapproved-adu.json"
REMEDIES = (
    ROOT / "data" / "readiness" / "remedies" / "woodland-preapproved-detached-adu.json"
)
JOURNEY = ROOT / "data" / "journeys" / "woodland-preapproved-detached-adu.json"
TEMPLATES = ROOT / "data" / "validation" / "source-change-release-v1"
EXPORT_PROFILES = (
    ROOT / "data" / "export" / "public-synthetic-evidence-v1.json",
    ROOT / "data" / "export" / "public-synthetic-evidence-v2.json",
)
AS_OF = date(2026, 8, 10)
NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
BASELINE_COMMIT = "a" * 40
PUBLISHED_COMMIT = "b" * 40
DEPLOYED_URL = "https://example.gov/permit-bearings/"


def _watch(changed: str | None = None) -> WatchResult:
    sources = load_sources(SOURCES, today=AS_OF)
    watched = {key: source for key, source in sources.items() if source.watch}
    unchanged = sorted(set(watched) - ({changed} if changed else set()))
    observed = {
        source_id: watched[source_id].sha256
        for source_id in unchanged
        if watched[source_id].sha256 is not None
    }
    result = WatchResult(unchanged=unchanged, observed_digests=observed)
    if changed is not None:
        result.changed.append(changed)
        result.observed_digests[changed] = "0" * 64
    return result


def _snapshot(
    snapshot_id: str,
    checked_at: str,
    commit_sha: str,
    *,
    changed: str | None = None,
    status: str = "proposed",
):
    return build_source_state_snapshot(
        _watch(changed),
        SOURCES,
        RULES,
        GOLDEN,
        snapshot_id=snapshot_id,
        checked_at=checked_at,
        receipt_status=status,  # type: ignore[arg-type]
        method="synthetic_test_fixture",
        run_url="https://example.gov/source-watch/run-1",
        commit_sha=commit_sha,
    )


def _unverifiable_snapshot(snapshot_id: str, checked_at: str, commit_sha: str):
    source_id = "ca-gov-66317"
    watch = _watch()
    watch.unchanged.remove(source_id)
    watch.observed_digests.pop(source_id)
    watch.unverifiable[source_id] = UnverifiableSource(
        source_id=source_id,
        reason="synthetic network failure",
        last_verified_on="2026-07-29",
        attempts=3,
    )
    return build_source_state_snapshot(
        watch,
        SOURCES,
        RULES,
        GOLDEN,
        snapshot_id=snapshot_id,
        checked_at=checked_at,
        receipt_status="reviewed",
        method="synthetic_test_fixture",
        run_url="https://example.gov/source-watch/run-1",
        commit_sha=commit_sha,
    )


def _readiness_context() -> ReadinessReviewContext:
    workflow = load_readiness_workflow(WORKFLOW, SOURCES, today=AS_OF)
    return ReadinessReviewContext(
        workflow=workflow,
        packet=load_readiness_packet(PACKET, workflow, today=AS_OF),
        remedies=load_readiness_remedies(REMEDIES, workflow, today=AS_OF),
        journeys=(load_journey_config(JOURNEY),),
    )


def _worklist(snapshot):
    rules = load_rules(RULES, today=AS_OF)
    return build_review_worklist(
        snapshot,
        load_sources(SOURCES, today=AS_OF),
        rules,
        load_golden(GOLDEN, rules),
        readiness_contexts=(_readiness_context(),),
    )


def _build_context(snapshot, worklist, decisions):
    return build_release_context(
        snapshot,
        worklist,
        decisions,
        sources_path=SOURCES,
        rules_path=RULES,
        golden_path=GOLDEN,
        readiness_contexts=(_readiness_context(),),
        as_of=AS_OF,
    )


def _resolved_ledger(worklist) -> ReviewDecisionLedger:
    template = decision_template(worklist)
    return ReviewDecisionLedger(
        worklist_id=template.worklist_id,
        worklist_fingerprint=template.worklist_fingerprint,
        entries=tuple(
            ReviewDecision(
                item_id=entry.item_id,
                item_fingerprint=entry.item_fingerprint,
                status="resolved",
                owner_code="REVIEWER_1",
                assigned_on="2026-08-10",
                disposition="retain",
                decided_on="2026-08-10",
                evidence_receipt_id=f"evidence-{index:03d}",
            )
            for index, entry in enumerate(template.entries, start=1)
        ),
    )


def _release_context(*, resolved: bool = True):
    snapshot = _snapshot(
        "source-release-change-1",
        "2026-08-10T09:00:00Z",
        BASELINE_COMMIT,
        changed="ca-gov-66317",
    )
    worklist = _worklist(snapshot)
    decisions = _resolved_ledger(worklist) if resolved else decision_template(worklist)
    return _build_context(snapshot, worklist, decisions)


def _write(tmp_path: Path, name: str, payload: object) -> Path:
    path = tmp_path / name
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def _completed_approval(tmp_path: Path, context, *, outcome="approved_for_publication"):
    approval, _, _ = prepared_receipts("controlled-release-1", context)
    payload = approval.to_dict()
    payload["status"] = "complete"
    payload["decision"].update(
        {
            "outcome": outcome,
            "reviewer_code": "APPROVER_1",
            "authority_receipt_id": "authority-scope-1",
            "decided_at": "2026-08-10T09:20:00Z",
            "evidence_receipt_ids": ["approval-evidence-1"],
            "source_resolutions": [
                {
                    "source_id": source.source_id,
                    "source_record_fingerprint": next(
                        item.target_fingerprint
                        for item in context.worklist.items
                        if item.item_type == "source_reverification"
                        and item.target_id == source.source_id
                    ),
                    "resolution": (
                        "restore_recorded"
                        if outcome == "approved_for_publication"
                        else "retain_hold"
                    ),
                    "target_sha256": (
                        source.recorded_sha256
                        if outcome == "approved_for_publication"
                        else None
                    ),
                }
                for source in context.worklist.changed_sources
            ],
        }
    )
    path = _write(tmp_path, "approval.json", payload)
    return load_approval_receipt(path, context, now=NOW), path


def _published_snapshot(*, retained: bool = False):
    return _snapshot(
        "published-source-state-1",
        "2026-08-10T09:25:00Z",
        PUBLISHED_COMMIT,
        changed="ca-gov-66317" if retained else None,
        status="reviewed",
    )


def _completed_publication(tmp_path: Path, context, approval, *, retained=False):
    _, prepared, _ = prepared_receipts("controlled-release-1", context)
    state = _published_snapshot(retained=retained)
    payload = prepared.to_dict()
    payload["status"] = "complete"
    payload["approval_receipt"] = {
        "receipt_id": approval.receipt_id,
        "receipt_fingerprint": approval.fingerprint(),
    }
    payload["publication"].update(
        {
            "actor_code": "MAINTAINER_1",
            "started_at": "2026-08-10T09:30:00Z",
            "completed_at": "2026-08-10T09:40:00Z",
            "baseline_commit_sha": BASELINE_COMMIT,
            "published_commit_sha": PUBLISHED_COMMIT,
            "published_url": DEPLOYED_URL,
            "published_source_snapshot_id": state.snapshot_id,
            "published_source_snapshot_fingerprint": source_state_fingerprint(state),
            "hold_state": (
                "retained_in_source_state" if retained else "clear_in_source_state"
            ),
            "verification_receipt_id": "deployment-verification-1",
        }
    )
    path = _write(tmp_path, "publication.json", payload)
    return (
        load_publication_receipt(path, approval, context, state, now=NOW),
        state,
        path,
    )


def _restored_snapshot():
    return _snapshot(
        "restored-source-state-1",
        "2026-08-10T09:50:00Z",
        BASELINE_COMMIT,
        status="reviewed",
    )


def _completed_rollback(
    tmp_path: Path,
    context,
    approval,
    publication,
    published_snapshot,
):
    _, _, prepared = prepared_receipts("controlled-release-1", context)
    state = _restored_snapshot()
    payload = prepared.to_dict()
    payload["status"] = "complete"
    payload["publication_receipt"] = {
        "receipt_id": publication.receipt_id,
        "receipt_fingerprint": publication.fingerprint(),
    }
    payload["rollback"].update(
        {
            "actor_code": "MAINTAINER_2",
            "triggered_at": "2026-08-10T09:45:00Z",
            "completed_at": "2026-08-10T09:55:00Z",
            "reason": "controlled_rehearsal",
            "restored_commit_sha": BASELINE_COMMIT,
            "restored_url": DEPLOYED_URL,
            "restored_source_snapshot_id": state.snapshot_id,
            "restored_source_snapshot_fingerprint": source_state_fingerprint(state),
            "hold_state": "clear_in_source_state",
            "verification_receipt_id": "rollback-verification-1",
        }
    )
    path = _write(tmp_path, "rollback.json", payload)
    return (
        load_rollback_receipt(
            path,
            publication,
            context,
            state,
            approval=approval,
            published_snapshot=published_snapshot,
            now=NOW,
        ),
        path,
    )


def test_committed_templates_are_strict_null_not_run_and_outside_export_v1_and_v2():
    approval_path = TEMPLATES / "approval-template.json"
    publication_path = TEMPLATES / "publication-template.json"
    rollback_path = TEMPLATES / "rollback-template.json"
    approval = load_approval_receipt(approval_path, now=NOW)
    publication = load_publication_receipt(publication_path, now=NOW)
    rollback = load_rollback_receipt(rollback_path, now=NOW)

    assert approval.status == publication.status == rollback.status == "not_run"
    assert approval.binding.is_empty()
    assert publication.binding.is_empty() and publication.approval.is_empty()
    assert rollback.binding.is_empty() and rollback.publication.is_empty()
    assert json.loads(approval_path.read_text(encoding="utf-8")) == approval.to_dict()
    assert (
        json.loads(publication_path.read_text(encoding="utf-8"))
        == publication.to_dict()
    )
    assert json.loads(rollback_path.read_text(encoding="utf-8")) == rollback.to_dict()
    assert {
        "approval": approval.fingerprint(),
        "publication": publication.fingerprint(),
        "rollback": rollback.fingerprint(),
    } == {
        "approval": "sha256:7c17aa6ddb7969b4023f8ea9ee4a48f6c4172ae46a2cd1735fff7951d006b365",
        "publication": "sha256:73b41f1c37d2572b2e048af3f4c6d6013025a49d4f18d9409701e0e5a26621bd",
        "rollback": "sha256:125dd8dcbf6e5cc9333ad48cdc2436981a52a13b571eaac5e5535542c07d2e7c",
    }

    for profile_path in EXPORT_PROFILES:
        exported = {
            entry["path"]
            for entry in json.loads(profile_path.read_text(encoding="utf-8"))["entries"]
        }
        assert not any(
            path.startswith("data/validation/source-change-release-v1/")
            for path in exported
        )


def test_receipt_parser_is_bounded_strict_and_does_not_leak_mutable_effects(
    tmp_path,
):
    template = approval_template()
    mutable_view = template.to_dict()
    mutable_view["effects"]["receipt_publishes"] = True
    assert template.to_dict()["effects"]["receipt_publishes"] is False

    with pytest.raises(ValueError, match="regular file"):
        load_approval_receipt(tmp_path, now=NOW)

    target = _write(tmp_path, "symlink-target.json", template.to_dict())
    symlink = tmp_path / "symlink.json"
    symlink.symlink_to(target)
    with pytest.raises(ValueError, match="could not be loaded"):
        load_approval_receipt(symlink, now=NOW)

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON field"):
        load_approval_receipt(duplicate, now=NOW)

    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"schema_version":NaN}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite JSON value"):
        load_approval_receipt(nonfinite, now=NOW)

    oversize = tmp_path / "oversize.json"
    oversize.write_bytes(b" " * (MAX_RECEIPT_BYTES + 1))
    with pytest.raises(ValueError, match=f"{MAX_RECEIPT_BYTES}-byte limit"):
        load_approval_receipt(oversize, now=NOW)

    non_utf8 = tmp_path / "non-utf8.json"
    non_utf8.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="not valid UTF-8"):
        load_approval_receipt(non_utf8, now=NOW)

    for index, invalid_version in enumerate((True, 1.0)):
        payload = template.to_dict()
        payload["schema_version"] = invalid_version
        with pytest.raises(ValueError, match="schema_version"):
            load_approval_receipt(
                _write(tmp_path, f"invalid-version-{index}.json", payload), now=NOW
            )

    numeric_effect = template.to_dict()
    numeric_effect["effects"]["receipt_publishes"] = 0
    with pytest.raises(ValueError, match="mutating or promoting"):
        load_approval_receipt(
            _write(tmp_path, "numeric-effect.json", numeric_effect), now=NOW
        )

    with pytest.raises(ValueError, match="timezone-aware UTC"):
        load_approval_receipt(
            _write(tmp_path, "naive-now.json", template.to_dict()),
            now=datetime(2026, 8, 10, 12, 0),
        )


@pytest.mark.parametrize(
    "url",
    [
        " https://example.gov/permit-bearings/",
        "https://example.gov/%zz",
        "https://example.gov:bad/permit-bearings/",
        "https://example.gov\\permit-bearings/",
    ],
)
def test_publication_rejects_malformed_deployment_urls(tmp_path, url):
    context = _release_context(resolved=False)
    approval, publication, _ = prepared_receipts("controlled-release-1", context)
    payload = publication.to_dict()
    payload["publication"]["published_url"] = url
    with pytest.raises(ValueError, match="expected an HTTPS URL"):
        load_publication_receipt(
            _write(tmp_path, "bad-url.json", payload),
            approval,
            context,
            now=NOW,
        )


def test_bound_prepared_receipts_preserve_open_hold_and_make_no_claim(tmp_path):
    context = _release_context(resolved=False)
    before_snapshot = context.snapshot.to_dict()
    before_worklist = context.worklist.to_dict()
    before_decisions = context.decisions.to_dict()
    approval, publication, rollback = prepared_receipts("controlled-release-1", context)

    assert approval.status == publication.status == rollback.status == "not_run"
    assert approval.binding == context.binding
    assert publication.approval.receipt_fingerprint == approval.fingerprint()
    assert rollback.publication.receipt_fingerprint == publication.fingerprint()
    assert context.worklist.status == "open"
    assert context.snapshot.to_dict() == before_snapshot
    assert context.worklist.to_dict() == before_worklist
    assert context.decisions.to_dict() == before_decisions

    approval_path = _write(tmp_path, "approval.json", approval.to_dict())
    publication_path = _write(tmp_path, "publication.json", publication.to_dict())
    rollback_path = _write(tmp_path, "rollback.json", rollback.to_dict())
    loaded_approval = load_approval_receipt(approval_path, context, now=NOW)
    loaded_publication = load_publication_receipt(
        publication_path, loaded_approval, context, now=NOW
    )
    assert (
        load_rollback_receipt(
            rollback_path,
            loaded_publication,
            context,
            approval=loaded_approval,
            now=NOW,
        ).status
        == "not_run"
    )

    stripped_publication = publication.to_dict()
    stripped_publication["approval_receipt"] = {
        "receipt_id": None,
        "receipt_fingerprint": None,
    }
    with pytest.raises(ValueError, match="complete receipt reference"):
        load_publication_receipt(
            _write(tmp_path, "publication-stripped.json", stripped_publication),
            loaded_approval,
            context,
            now=NOW,
        )

    stripped_rollback = rollback.to_dict()
    stripped_rollback["publication_receipt"] = {
        "receipt_id": None,
        "receipt_fingerprint": None,
    }
    with pytest.raises(ValueError, match="complete receipt reference"):
        load_rollback_receipt(
            _write(tmp_path, "rollback-stripped.json", stripped_rollback),
            loaded_publication,
            context,
            approval=loaded_approval,
            now=NOW,
        )

    drifted_context = replace(
        context,
        binding=replace(context.binding, worklist_id="wrong-worklist"),
    )
    with pytest.raises(ValueError, match="release context binding"):
        prepared_receipts("drifted-context", drifted_context)


def test_completed_chain_requires_three_separate_exact_receipts(tmp_path):
    context = _release_context()
    approval, _ = _completed_approval(tmp_path, context)
    publication, published_snapshot, _ = _completed_publication(
        tmp_path, context, approval
    )
    rollback, _ = _completed_rollback(
        tmp_path, context, approval, publication, published_snapshot
    )

    assert approval.outcome == "approved_for_publication"
    assert publication.hold_state == "clear_in_source_state"
    assert rollback.hold_state == "clear_in_source_state"
    assert context.worklist.status == "open"
    assert context.snapshot.changed_source_ids == ("ca-gov-66317",)


def test_status_only_and_decision_only_approval_promotions_are_rejected(tmp_path):
    unresolved = _release_context(resolved=False)
    approval, _, _ = prepared_receipts("controlled-release-1", unresolved)
    status_only = approval.to_dict()
    status_only["status"] = "complete"
    with pytest.raises(ValueError, match="lacks required decision evidence"):
        load_approval_receipt(
            _write(tmp_path, "status-only.json", status_only), unresolved, now=NOW
        )

    filled = copy.deepcopy(status_only)
    filled["decision"].update(
        {
            "outcome": "approved_for_publication",
            "reviewer_code": "APPROVER_1",
            "authority_receipt_id": "authority-scope-1",
            "decided_at": "2026-08-10T09:20:00Z",
            "evidence_receipt_ids": ["approval-evidence-1"],
            "source_resolutions": [
                {
                    "source_id": source.source_id,
                    "source_record_fingerprint": next(
                        item.target_fingerprint
                        for item in unresolved.worklist.items
                        if item.item_type == "source_reverification"
                        and item.target_id == source.source_id
                    ),
                    "resolution": "restore_recorded",
                    "target_sha256": source.recorded_sha256,
                }
                for source in unresolved.worklist.changed_sources
            ],
        }
    )
    with pytest.raises(ValueError, match="every exact worklist decision"):
        load_approval_receipt(
            _write(tmp_path, "unresolved.json", filled), unresolved, now=NOW
        )


def test_completed_receipts_and_ledgers_reject_placeholder_identity_evidence(
    tmp_path,
):
    context = _release_context()
    approval, _ = _completed_approval(tmp_path, context)
    with pytest.raises(ValueError, match="placeholder evidence identifiers"):
        prepared_receipts("pending-1", context)

    approval_cases = []
    reviewer = approval.to_dict()
    reviewer["decision"]["reviewer_code"] = "TBD"
    approval_cases.append((reviewer, "placeholder owner codes"))
    authority = approval.to_dict()
    authority["decision"]["authority_receipt_id"] = "pending"
    approval_cases.append((authority, "placeholder evidence identifiers"))
    evidence = approval.to_dict()
    evidence["decision"]["evidence_receipt_ids"] = ["unknown"]
    approval_cases.append((evidence, "placeholder evidence identifiers"))
    for index, (payload, message) in enumerate(approval_cases):
        with pytest.raises(ValueError, match=message):
            load_approval_receipt(
                _write(tmp_path, f"approval-placeholder-{index}.json", payload),
                context,
                now=NOW,
            )

    publication, state, _ = _completed_publication(tmp_path, context, approval)
    publication_cases = []
    actor = publication.to_dict()
    actor["publication"]["actor_code"] = "PENDING"
    publication_cases.append((actor, "placeholder owner codes"))
    verification = publication.to_dict()
    verification["publication"]["verification_receipt_id"] = "tbd"
    publication_cases.append((verification, "placeholder evidence identifiers"))
    for index, (payload, message) in enumerate(publication_cases):
        with pytest.raises(ValueError, match=message):
            load_publication_receipt(
                _write(tmp_path, f"publication-placeholder-{index}.json", payload),
                approval,
                context,
                state,
                now=NOW,
            )

    rollback, _ = _completed_rollback(tmp_path, context, approval, publication, state)
    restored = _restored_snapshot()
    rollback_cases = []
    rollback_actor = rollback.to_dict()
    rollback_actor["rollback"]["actor_code"] = "UNASSIGNED"
    rollback_cases.append((rollback_actor, "placeholder owner codes"))
    rollback_verification = rollback.to_dict()
    rollback_verification["rollback"]["verification_receipt_id"] = "none"
    rollback_cases.append((rollback_verification, "placeholder evidence identifiers"))
    for index, (payload, message) in enumerate(rollback_cases):
        with pytest.raises(ValueError, match=message):
            load_rollback_receipt(
                _write(tmp_path, f"rollback-placeholder-{index}.json", payload),
                publication,
                context,
                restored,
                approval=approval,
                published_snapshot=state,
                now=NOW,
            )

    invalid_entry = replace(context.decisions.entries[0], owner_code="UNKNOWN")
    invalid_context = replace(
        context,
        decisions=replace(
            context.decisions,
            entries=(invalid_entry, *context.decisions.entries[1:]),
        ),
    )
    with pytest.raises(ValueError, match="placeholder owner codes"):
        _build_context(
            invalid_context.snapshot,
            invalid_context.worklist,
            invalid_context.decisions,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reviewer_code", "PENDING_1"),
        ("reviewer_code", "NA"),
        ("authority_receipt_id", "tbd-1"),
        ("authority_receipt_id", "placeholder-receipt-1"),
    ],
)
def test_completed_approval_rejects_tokenized_placeholders(tmp_path, field, value):
    context = _release_context()
    approval, _ = _completed_approval(tmp_path, context)
    payload = approval.to_dict()
    payload["decision"][field] = value
    with pytest.raises(ValueError, match="placeholder"):
        load_approval_receipt(
            _write(tmp_path, f"approval-{field}-{value}.json", payload),
            context,
            now=NOW,
        )


def test_approval_rejects_binding_effect_and_chronology_tampering(tmp_path):
    context = _release_context()
    approval, path = _completed_approval(tmp_path, context)
    payload = approval.to_dict()
    mutations = []
    drift = copy.deepcopy(payload)
    drift["release_binding"]["worklist_fingerprint"] = "sha256:" + "0" * 64
    mutations.append((drift, "release binding"))
    effect = copy.deepcopy(payload)
    effect["effects"]["decision_ledger_publishes"] = True
    mutations.append((effect, "mutating or promoting"))
    chronology = copy.deepcopy(payload)
    chronology["decision"]["decided_at"] = "2026-08-10T08:59:59Z"
    mutations.append((chronology, "cannot predate"))
    resolution_digest = copy.deepcopy(payload)
    resolution_digest["decision"]["source_resolutions"][0]["target_sha256"] = "c" * 64
    mutations.append((resolution_digest, "target digest does not match"))
    resolution_binding = copy.deepcopy(payload)
    resolution_binding["decision"]["source_resolutions"][0][
        "source_record_fingerprint"
    ] = "sha256:" + "0" * 64
    mutations.append((resolution_binding, "source record fingerprint does not match"))

    assert load_approval_receipt(path, context, now=NOW) == approval
    for index, (mutated, error) in enumerate(mutations):
        with pytest.raises(ValueError, match=error):
            load_approval_receipt(
                _write(tmp_path, f"approval-bad-{index}.json", mutated),
                context,
                now=NOW,
            )


def test_publication_rejects_rejection_binding_hold_and_chronology_tampering(tmp_path):
    context = _release_context()
    approval, _ = _completed_approval(tmp_path, context)
    publication, state, path = _completed_publication(tmp_path, context, approval)
    payload = publication.to_dict()

    rejected, _ = _completed_approval(tmp_path, context, outcome="rejected")
    rejected_payload = copy.deepcopy(payload)
    rejected_payload["approval_receipt"] = {
        "receipt_id": rejected.receipt_id,
        "receipt_fingerprint": rejected.fingerprint(),
    }
    with pytest.raises(ValueError, match="approval-for-publication"):
        load_publication_receipt(
            _write(tmp_path, "publication-rejected.json", rejected_payload),
            rejected,
            context,
            state,
            now=NOW,
        )

    forged_approval = replace(
        approval,
        binding=replace(approval.binding, worklist_id="wrong-worklist"),
    )
    forged_payload = copy.deepcopy(payload)
    forged_payload["approval_receipt"]["receipt_fingerprint"] = (
        forged_approval.fingerprint()
    )
    with pytest.raises(ValueError, match="release binding does not match"):
        load_publication_receipt(
            _write(tmp_path, "publication-forged-approval.json", forged_payload),
            forged_approval,
            context,
            state,
            now=NOW,
        )

    incomplete_approval = replace(
        approval,
        reviewer_code=None,
        authority_receipt_id=None,
        evidence_receipt_ids=None,
    )
    incomplete_payload = copy.deepcopy(payload)
    incomplete_payload["approval_receipt"]["receipt_fingerprint"] = (
        incomplete_approval.fingerprint()
    )
    with pytest.raises(ValueError, match="lacks required decision evidence"):
        load_publication_receipt(
            _write(
                tmp_path, "publication-incomplete-approval.json", incomplete_payload
            ),
            incomplete_approval,
            context,
            state,
            now=NOW,
        )

    unverifiable_state = _unverifiable_snapshot(
        "published-source-state-unverifiable",
        "2026-08-10T09:25:00Z",
        PUBLISHED_COMMIT,
    )
    unverifiable_payload = copy.deepcopy(payload)
    unverifiable_payload["publication"].update(
        {
            "published_source_snapshot_id": unverifiable_state.snapshot_id,
            "published_source_snapshot_fingerprint": source_state_fingerprint(
                unverifiable_state
            ),
        }
    )
    with pytest.raises(ValueError, match="previously changed source as unverifiable"):
        load_publication_receipt(
            _write(
                tmp_path,
                "publication-unverifiable-source.json",
                unverifiable_payload,
            ),
            approval,
            context,
            unverifiable_state,
            now=NOW,
        )

    mismatched_observations = tuple(
        replace(item, recorded_sha256="1" * 64, observed_sha256="1" * 64)
        if item.source_id == "ca-gov-66317"
        else item
        for item in state.observations
    )
    mismatched_state = replace(state, observations=mismatched_observations)
    mismatched_payload = copy.deepcopy(payload)
    mismatched_payload["publication"]["published_source_snapshot_fingerprint"] = (
        source_state_fingerprint(mismatched_state)
    )
    with pytest.raises(ValueError, match="recorded evidence drifted"):
        load_publication_receipt(
            _write(tmp_path, "publication-unrelated-digest.json", mismatched_payload),
            approval,
            context,
            mismatched_state,
            now=NOW,
        )

    forged_summary = replace(
        state,
        changed_source_ids=("fake-source",),
        affected_rule_ids=("fake-rule",),
        unaffected_rule_ids=(),
    )
    forged_summary_payload = copy.deepcopy(payload)
    forged_summary_payload["publication"]["published_source_snapshot_fingerprint"] = (
        source_state_fingerprint(forged_summary)
    )
    with pytest.raises(ValueError, match="source-state summary contradicts"):
        load_publication_receipt(
            _write(tmp_path, "publication-forged-summary.json", forged_summary_payload),
            approval,
            context,
            forged_summary,
            now=NOW,
        )

    mutations = []
    binding = copy.deepcopy(payload)
    binding["approval_receipt"]["receipt_fingerprint"] = "sha256:" + "0" * 64
    mutations.append((binding, "fingerprint does not match"))
    hold = copy.deepcopy(payload)
    hold["publication"]["hold_state"] = "retained_in_source_state"
    mutations.append((hold, "hold state does not match"))
    chronology = copy.deepcopy(payload)
    chronology["publication"]["started_at"] = "2026-08-10T09:19:59Z"
    mutations.append((chronology, "chronology is invalid"))
    state_binding = copy.deepcopy(payload)
    state_binding["publication"]["published_source_snapshot_fingerprint"] = (
        "sha256:" + "0" * 64
    )
    mutations.append((state_binding, "source-state fingerprint"))

    assert (
        load_publication_receipt(path, approval, context, state, now=NOW) == publication
    )
    for index, (mutated, error) in enumerate(mutations):
        with pytest.raises(ValueError, match=error):
            load_publication_receipt(
                _write(tmp_path, f"publication-bad-{index}.json", mutated),
                approval,
                context,
                state,
                now=NOW,
            )


def test_publication_uses_explicit_source_resolution_not_generic_disposition(tmp_path):
    context = _release_context()
    approval, _ = _completed_approval(tmp_path, context)
    publication, state, _ = _completed_publication(tmp_path, context, approval)

    retain_payload = approval.to_dict()
    retain_payload["decision"]["source_resolutions"][0].update(
        {"resolution": "retain_hold", "target_sha256": None}
    )
    retain_approval = load_approval_receipt(
        _write(tmp_path, "approval-retain-hold.json", retain_payload),
        context,
        now=NOW,
    )
    publication_payload = publication.to_dict()
    publication_payload["approval_receipt"] = {
        "receipt_id": retain_approval.receipt_id,
        "receipt_fingerprint": retain_approval.fingerprint(),
    }
    with pytest.raises(ValueError, match="explicit resolution 'retain_hold'"):
        load_publication_receipt(
            _write(tmp_path, "publication-false-clear.json", publication_payload),
            retain_approval,
            context,
            state,
            now=NOW,
        )


def test_rollback_rejects_publication_binding_chronology_and_false_restore(tmp_path):
    context = _release_context()
    approval, _ = _completed_approval(tmp_path, context)
    publication, published_snapshot, _ = _completed_publication(
        tmp_path, context, approval
    )
    rollback, path = _completed_rollback(
        tmp_path, context, approval, publication, published_snapshot
    )
    restored = _restored_snapshot()
    payload = rollback.to_dict()

    forged_publication = replace(
        publication,
        binding=replace(publication.binding, worklist_id="wrong-worklist"),
    )
    forged_payload = copy.deepcopy(payload)
    forged_payload["publication_receipt"]["receipt_fingerprint"] = (
        forged_publication.fingerprint()
    )
    with pytest.raises(ValueError, match="release binding does not match"):
        load_rollback_receipt(
            _write(tmp_path, "rollback-forged-publication.json", forged_payload),
            forged_publication,
            context,
            restored,
            approval=approval,
            published_snapshot=published_snapshot,
            now=NOW,
        )

    incomplete_publication = replace(
        publication,
        actor_code=None,
        verification_receipt_id=None,
    )
    incomplete_payload = copy.deepcopy(payload)
    incomplete_payload["publication_receipt"]["receipt_fingerprint"] = (
        incomplete_publication.fingerprint()
    )
    with pytest.raises(ValueError, match="lacks required evidence"):
        load_rollback_receipt(
            _write(
                tmp_path, "rollback-incomplete-publication.json", incomplete_payload
            ),
            incomplete_publication,
            context,
            restored,
            approval=approval,
            published_snapshot=published_snapshot,
            now=NOW,
        )

    mutations = []
    reference = copy.deepcopy(payload)
    reference["publication_receipt"]["receipt_fingerprint"] = "sha256:" + "0" * 64
    mutations.append((reference, restored, "fingerprint does not match"))
    chronology = copy.deepcopy(payload)
    chronology["rollback"]["triggered_at"] = "2026-08-10T09:39:59Z"
    mutations.append((chronology, restored, "chronology is invalid"))
    commit = copy.deepcopy(payload)
    commit["rollback"]["restored_commit_sha"] = "c" * 40
    mutations.append((commit, restored, "restore the publication baseline"))
    retained_state = _snapshot(
        "restored-source-state-1",
        "2026-08-10T08:55:00Z",
        BASELINE_COMMIT,
        changed="ca-gov-66317",
        status="reviewed",
    )
    retained = copy.deepcopy(payload)
    retained["rollback"]["restored_source_snapshot_fingerprint"] = (
        source_state_fingerprint(retained_state)
    )
    retained["rollback"]["hold_state"] = "retained_in_source_state"
    mutations.append((retained, retained_state, "must not retain"))
    forged_summary = replace(
        restored,
        changed_source_ids=("fake-source",),
        affected_rule_ids=("fake-rule",),
        unaffected_rule_ids=(),
    )
    forged_summary_receipt = copy.deepcopy(payload)
    forged_summary_receipt["rollback"]["restored_source_snapshot_fingerprint"] = (
        source_state_fingerprint(forged_summary)
    )
    mutations.append(
        (forged_summary_receipt, forged_summary, "source-state summary contradicts")
    )
    future_state = replace(restored, checked_at="2099-01-01T00:00:00Z")
    future = copy.deepcopy(payload)
    future["rollback"]["restored_source_snapshot_fingerprint"] = (
        source_state_fingerprint(future_state)
    )
    mutations.append((future, future_state, "chronology is invalid"))

    assert (
        load_rollback_receipt(
            path,
            publication,
            context,
            restored,
            approval=approval,
            published_snapshot=published_snapshot,
            now=NOW,
        )
        == rollback
    )
    for index, (mutated, state, error) in enumerate(mutations):
        with pytest.raises(ValueError, match=error):
            load_rollback_receipt(
                _write(tmp_path, f"rollback-bad-{index}.json", mutated),
                publication,
                context,
                state,
                approval=approval,
                published_snapshot=published_snapshot,
                now=NOW,
            )


def test_cli_validates_templates_and_exclusively_prepares_bound_not_run_set(
    tmp_path,
    capsys,
):
    assert source_release_main(["validate-templates"]) == 0
    assert json.loads(capsys.readouterr().out)["execution_status"] == "not_run"

    altered_template = approval_template().to_dict()
    altered_template["receipt_id"] = "alternate-approval-template"
    altered_path = _write(tmp_path, "altered-template.json", altered_template)
    assert (
        source_release_main(["validate-templates", "--approval", str(altered_path)])
        == 2
    )
    assert "immutable fingerprints" in capsys.readouterr().err

    context = _release_context(resolved=False)
    source_state_path = tmp_path / "source-state.json"
    worklist_path = tmp_path / "worklist.json"
    decisions_path = tmp_path / "decisions.json"
    source_state_path.write_text(
        encoded_source_state(context.snapshot), encoding="utf-8"
    )
    worklist_path.write_text(
        encoded_review_worklist(context.worklist), encoding="utf-8"
    )
    decisions_path.write_text(
        encoded_decision_ledger(context.decisions), encoding="utf-8"
    )
    output = tmp_path / "release"
    args = [
        "prepare",
        "--source-state",
        str(source_state_path),
        "--worklist",
        str(worklist_path),
        "--decisions",
        str(decisions_path),
        "--release-id",
        "controlled-release-1",
        "--output-dir",
        str(output),
    ]
    assert source_release_main(args) == 1
    prepared = json.loads(capsys.readouterr().out)
    assert prepared["execution_status"] == "not_run"
    assert prepared["supports_approval_or_publication_claim"] is False
    assert json.loads((output / "approval.json").read_text())["status"] == "not_run"
    assert (output / ".complete").read_text(encoding="utf-8") == (
        "source-change-release-v1\n"
    )
    assert not list(tmp_path.glob(".release.*"))

    assert source_release_main(args) == 2
    assert "invalid input or output" in capsys.readouterr().err

    blocked = tmp_path / "existing-output"
    blocked.mkdir()
    sentinel = blocked / "keep.txt"
    sentinel.write_text("preserve", encoding="utf-8")
    blocked_args = [*args[:-1], str(blocked)]
    assert source_release_main(blocked_args) == 2
    assert sorted(path.name for path in blocked.iterdir()) == ["keep.txt"]
    assert sentinel.read_text(encoding="utf-8") == "preserve"


def test_release_context_rejects_input_drift_during_derivation(monkeypatch):
    context = _release_context(resolved=False)
    stable = context.input_fingerprints
    drifted = (stable[0], stable[1], "sha256:" + "0" * 64)
    results = iter((stable, drifted))
    monkeypatch.setattr(
        source_release_module,
        "_input_fingerprints",
        lambda *_args: next(results),
    )

    with pytest.raises(ValueError, match="input changed during validation"):
        build_release_context(
            context.snapshot,
            context.worklist,
            context.decisions,
            sources_path=SOURCES,
            rules_path=RULES,
            golden_path=GOLDEN,
            readiness_contexts=context.readiness_contexts,
            as_of=AS_OF,
        )


def test_prepared_package_removes_partial_directory_on_write_failure(
    tmp_path, monkeypatch
):
    context = _release_context(resolved=False)
    approval, publication, rollback = prepared_receipts("controlled-release-1", context)
    original_write = source_release_cli_module._write_durable_exclusive
    writes = 0

    def interrupted_write(path: Path, content: str) -> None:
        nonlocal writes
        writes += 1
        if writes == 2:
            raise OSError("simulated interrupted package write")
        original_write(path, content)

    monkeypatch.setattr(
        source_release_cli_module, "_write_durable_exclusive", interrupted_write
    )
    output = tmp_path / "interrupted-release"
    with pytest.raises(OSError, match="simulated interrupted"):
        source_release_cli_module._write_package_exclusive(
            output,
            (
                ("approval", approval),
                ("publication", publication),
                ("rollback", rollback),
            ),
        )
    assert not output.exists()


def test_cli_reports_decisive_completed_outcomes_and_hold_states(
    tmp_path,
    capsys,
    monkeypatch,
):
    monkeypatch.setattr(
        "permit_pathways.source_release._validation_now", lambda value: value or NOW
    )
    context = _release_context()
    source_state_path = _write(
        tmp_path, "chain-source-state.json", context.snapshot.to_dict()
    )
    worklist_path = _write(tmp_path, "chain-worklist.json", context.worklist.to_dict())
    decisions_path = _write(
        tmp_path, "chain-decisions.json", context.decisions.to_dict()
    )
    common = [
        "--source-state",
        str(source_state_path),
        "--worklist",
        str(worklist_path),
        "--decisions",
        str(decisions_path),
    ]

    approval, _ = _completed_approval(tmp_path, context)
    approval_path = _write(tmp_path, "chain-approval.json", approval.to_dict())
    assert (
        source_release_main(
            ["validate-approval", *common, "--approval", str(approval_path)]
        )
        == 0
    )
    approval_summary = json.loads(capsys.readouterr().out)
    assert approval_summary["outcome"] == "approved_for_publication"
    assert approval_summary["approved_for_publication"] is True

    rejected, _ = _completed_approval(tmp_path, context, outcome="rejected")
    rejected_path = _write(tmp_path, "chain-rejected.json", rejected.to_dict())
    assert (
        source_release_main(
            ["validate-approval", *common, "--approval", str(rejected_path)]
        )
        == 1
    )
    rejected_summary = json.loads(capsys.readouterr().out)
    assert rejected_summary["outcome"] == "rejected"
    assert rejected_summary["approved_for_publication"] is False

    publication, published_snapshot, publication_path = _completed_publication(
        tmp_path, context, approval
    )
    publication_path = _write(tmp_path, "chain-publication.json", publication.to_dict())
    published_path = _write(
        tmp_path, "chain-published-source-state.json", published_snapshot.to_dict()
    )
    publication_args = [
        "validate-publication",
        *common,
        "--approval",
        str(approval_path),
        "--publication",
        str(publication_path),
        "--published-source-state",
        str(published_path),
    ]
    assert source_release_main(publication_args) == 0
    publication_summary = json.loads(capsys.readouterr().out)
    assert publication_summary["hold_state"] == "clear_in_source_state"
    assert publication_summary["source_hold_clear"] is True

    retained, retained_snapshot, retained_path = _completed_publication(
        tmp_path, context, approval, retained=True
    )
    retained_state_path = _write(
        tmp_path, "chain-retained-source-state.json", retained_snapshot.to_dict()
    )
    retained_args = [
        "validate-publication",
        *common,
        "--approval",
        str(approval_path),
        "--publication",
        str(retained_path),
        "--published-source-state",
        str(retained_state_path),
    ]
    assert retained.hold_state == "retained_in_source_state"
    assert source_release_main(retained_args) == 1
    retained_summary = json.loads(capsys.readouterr().out)
    assert retained_summary["source_hold_clear"] is False

    rollback, rollback_path = _completed_rollback(
        tmp_path, context, approval, publication, published_snapshot
    )
    restored_path = _write(
        tmp_path, "chain-restored-source-state.json", _restored_snapshot().to_dict()
    )
    rollback_args = [
        "validate-rollback",
        *common,
        "--approval",
        str(approval_path),
        "--publication",
        str(publication_path),
        "--published-source-state",
        str(published_path),
        "--rollback",
        str(rollback_path),
        "--restored-source-state",
        str(restored_path),
    ]
    assert rollback.hold_state == "clear_in_source_state"
    assert source_release_main(rollback_args) == 0
    rollback_summary = json.loads(capsys.readouterr().out)
    assert rollback_summary["source_hold_clear"] is True


def test_release_context_rejects_a_clear_queue_and_cross_artifact_ledger():
    clear_snapshot = _snapshot(
        "source-release-clear-1",
        "2026-08-10T09:00:00Z",
        BASELINE_COMMIT,
    )
    clear_worklist = _worklist(clear_snapshot)
    with pytest.raises(ValueError, match="open changed-source worklist"):
        _build_context(
            clear_snapshot, clear_worklist, decision_template(clear_worklist)
        )

    context = _release_context(resolved=False)
    truncated = replace(context.worklist, items=context.worklist.items[:1])
    with pytest.raises(ValueError, match="canonical affected-output set"):
        _build_context(
            context.snapshot,
            truncated,
            _resolved_ledger(truncated),
        )

    wrong = replace(
        context.decisions,
        worklist_fingerprint="sha256:" + "0" * 64,
    )
    with pytest.raises(ValueError, match="worklist fingerprint"):
        _build_context(context.snapshot, context.worklist, wrong)

    invalid_entry = replace(
        context.decisions.entries[0],
        status="resolved",
        owner_code=None,
        assigned_on=None,
        disposition=None,
        decided_on=None,
        evidence_receipt_id=None,
    )
    invalid_decisions = replace(
        context.decisions,
        entries=(invalid_entry, *context.decisions.entries[1:]),
    )
    with pytest.raises(ValueError, match="resolved decision ledger entry"):
        _build_context(context.snapshot, context.worklist, invalid_decisions)
