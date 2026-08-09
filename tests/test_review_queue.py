from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from permit_pathways.harness.runner import load_golden
from permit_pathways.harness.watch import (
    UnverifiableSource,
    WatchResult,
    load_sources,
)
from permit_pathways.journey import load_journey_config
from permit_pathways.readiness import (
    load_readiness_packet,
    load_readiness_remedies,
    load_readiness_workflow,
)
from permit_pathways.review_queue import (
    ReadinessReviewContext,
    build_review_worklist,
    decision_template,
    encoded_review_worklist,
    load_review_decisions,
    load_review_worklist,
)
from permit_pathways.review_queue_cli import main as review_queue_main
from permit_pathways.screening import load_rules
from permit_pathways.source_state import (
    build_source_state_snapshot,
    encoded_source_state,
    load_source_state_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources.json"
RULES = ROOT / "data" / "rules"
GOLDEN = ROOT / "data" / "golden" / "example.json"
CURRENT = ROOT / "data" / "source-status" / "current.json"
WORKFLOW = (
    ROOT / "data" / "readiness" / "workflows" / "woodland-preapproved-detached-adu.json"
)
PACKET = ROOT / "data" / "readiness" / "samples" / "woodland-preapproved-adu.json"
REMEDIES = (
    ROOT / "data" / "readiness" / "remedies" / "woodland-preapproved-detached-adu.json"
)
JOURNEY = ROOT / "data" / "journeys" / "woodland-preapproved-detached-adu.json"
AS_OF = date(2026, 8, 9)
CHECKED_AT = "2026-08-09T12:00:00Z"
COMMIT_SHA = "8d841409dc5fd16fe56b52a8b57c826c07f176a6"
RUN_URL = "https://github.com/ChelseaKR/permit-pathways/actions/runs/30835371749"


def _watch(
    *, changed: str | None = None, unverifiable: str | None = None
) -> WatchResult:
    sources = load_sources(SOURCES, today=AS_OF)
    watched = {
        source_id: source for source_id, source in sources.items() if source.watch
    }
    unchanged = sorted(set(watched) - {changed, unverifiable})
    observed = {
        source_id: source.sha256
        for source_id, source in watched.items()
        if source_id in unchanged and source.sha256 is not None
    }
    result = WatchResult(unchanged=unchanged, observed_digests=observed)
    if changed is not None:
        result.changed.append(changed)
        result.observed_digests[changed] = "0" * 64
    if unverifiable is not None:
        result.unverifiable[unverifiable] = UnverifiableSource(
            source_id=unverifiable,
            reason="Synthetic offline fixture",
            last_verified_on=watched[unverifiable].fetched_on,
            attempts=3,
        )
    return result


def _snapshot(*, changed: str | None = None, unverifiable: str | None = None):
    return build_source_state_snapshot(
        _watch(changed=changed, unverifiable=unverifiable),
        SOURCES,
        RULES,
        GOLDEN,
        snapshot_id="review-queue-test",
        checked_at=CHECKED_AT,
        receipt_status="proposed",
        method="synthetic_test_fixture",
        run_url=RUN_URL,
        commit_sha=COMMIT_SHA,
    )


def _readiness_context() -> ReadinessReviewContext:
    workflow = load_readiness_workflow(WORKFLOW, SOURCES, today=AS_OF)
    packet = load_readiness_packet(PACKET, workflow, today=AS_OF)
    remedies = load_readiness_remedies(REMEDIES, workflow, today=AS_OF)
    return ReadinessReviewContext(
        workflow=workflow,
        packet=packet,
        remedies=remedies,
        journeys=(load_journey_config(JOURNEY),),
    )


def _rules_and_golden():
    rules = load_rules(RULES, today=AS_OF)
    return rules, load_golden(GOLDEN, rules)


def _worklist(
    *,
    changed: str | None = None,
    unverifiable: str | None = None,
    readiness_contexts: tuple[ReadinessReviewContext, ...] = (),
):
    rules, golden = _rules_and_golden()
    return build_review_worklist(
        _snapshot(changed=changed, unverifiable=unverifiable),
        load_sources(SOURCES, today=AS_OF),
        rules,
        golden,
        readiness_contexts=readiness_contexts,
    )


def _write_json(tmp_path: Path, name: str, payload: object) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def test_current_unchanged_receipt_creates_a_clear_worklist():
    snapshot = load_source_state_snapshot(
        CURRENT,
        SOURCES,
        RULES,
        GOLDEN,
        require_reviewed=True,
    )
    rules, golden = _rules_and_golden()
    worklist = build_review_worklist(
        snapshot,
        load_sources(SOURCES, today=AS_OF),
        rules,
        golden,
    )

    assert worklist.status == "clear"
    assert worklist.changed_sources == ()
    assert worklist.items == ()
    assert worklist.unverifiable_source_ids == ()
    assert decision_template(worklist).entries == ()


def test_changed_source_creates_exact_source_rule_and_golden_work_items():
    snapshot = _snapshot(changed="ca-gov-66317")
    rules, golden = _rules_and_golden()
    worklist = build_review_worklist(
        snapshot,
        load_sources(SOURCES, today=AS_OF),
        rules,
        golden,
    )
    items = {item.item_id: item for item in worklist.items}

    assert worklist.status == "open"
    assert worklist.changed_source_ids == ("ca-gov-66317",)
    assert [source.source_id for source in worklist.changed_sources] == ["ca-gov-66317"]
    assert worklist.changed_sources[0].observed_sha256 == "0" * 64
    assert "source-reverification:ca-gov-66317" in items
    assert {
        item.target_id
        for item in items.values()
        if item.item_type == "rule_reverification"
    } == {"adu-ministerial-review"}
    assert {
        item.target_id for item in items.values() if item.item_type == "golden_replay"
    } == set(snapshot.affected_golden_case_ids)
    assert all(item.source_ids == ("ca-gov-66317",) for item in items.values())
    assert [item.item_id for item in worklist.items] == sorted(items)
    assert all(item.fingerprint().startswith("sha256:") for item in worklist.items)


def test_changed_source_queues_expected_empty_negative_golden_cases():
    worklist = _worklist(changed="ca-gov-65852-21")

    assert {
        item.target_id for item in worklist.items if item.item_type == "golden_replay"
    } == {
        "sb9-duplex-clean",
        "sb9-duplex-tenant-occupied",
        "sb9-ellis-unknown",
        "sb9-two-unit-historic-location-unknown",
        "sb9-two-unit-individually-listed-historic-property",
    }


def test_changed_dependency_impact_is_rederived_before_work_is_created():
    snapshot = _snapshot(changed="ca-gov-66317")
    rules = load_rules(RULES, today=AS_OF)
    drifted = [
        replace(rule, source_dependencies=[])
        if rule.rule_id == "adu-ministerial-review"
        else rule
        for rule in rules
    ]

    with pytest.raises(ValueError, match="affected rule IDs drifted"):
        build_review_worklist(
            snapshot,
            load_sources(SOURCES, today=AS_OF),
            drifted,
            load_golden(GOLDEN, rules),
        )


def test_unverifiable_source_creates_no_work_or_staleness_proxy():
    worklist = _worklist(unverifiable="ca-gov-66317")

    assert worklist.status == "clear"
    assert worklist.changed_source_ids == ()
    assert worklist.unverifiable_source_ids == ("ca-gov-66317",)
    assert worklist.changed_sources == ()
    assert worklist.items == ()


def test_changed_checklist_creates_exact_requirement_remedy_and_output_work():
    context = _readiness_context()
    worklist = _worklist(
        changed="woodland-preapproved-adu-checklist",
        readiness_contexts=(context,),
    )
    items = tuple(worklist.items)
    expected_targets = {
        f"{context.workflow.workflow_id}.{requirement.requirement_id}"
        for requirement in context.workflow.requirements
    }

    assert len(items) == 53
    assert {
        item.target_id
        for item in items
        if item.item_type == "readiness_requirement_reverification"
    } == expected_targets
    assert {
        item.target_id
        for item in items
        if item.item_type == "readiness_remedy_reverification"
    } == expected_targets
    assert all(
        item.source_ids == ("woodland-preapproved-adu-checklist",)
        for item in items
        if item.item_type
        in {
            "readiness_requirement_reverification",
            "readiness_remedy_reverification",
        }
    )
    assert not [
        item
        for item in items
        if item.item_type == "readiness_fact_binding_reverification"
    ]
    assert {
        (item.item_type, item.target_id, item.source_ids)
        for item in items
        if item.item_type
        in {"readiness_packet_revalidation", "journey_handoff_revalidation"}
    } == {
        (
            "readiness_packet_revalidation",
            f"{context.workflow.workflow_id}.{context.packet.packet_id}",
            ("woodland-preapproved-adu-checklist",),
        ),
        (
            "journey_handoff_revalidation",
            "woodland-preapproved-detached-adu-synthetic",
            ("woodland-preapproved-adu-checklist",),
        ),
    }


def test_changed_parcel_source_creates_only_exact_fact_and_output_work():
    context = _readiness_context()
    worklist = _worklist(
        changed="yolo-public-parcels-layer",
        readiness_contexts=(context,),
    )
    items = tuple(worklist.items)

    assert len(items) == 5
    assert {
        (item.target_id, item.source_ids)
        for item in items
        if item.item_type == "readiness_fact_binding_reverification"
    } == {
        (
            "woodland-preapproved-detached-adu.parcel_city_matches_woodland",
            ("yolo-public-parcels-layer",),
        ),
        (
            "woodland-preapproved-detached-adu.parcel_land_use_is_residential",
            ("yolo-public-parcels-layer",),
        ),
    }
    assert not [
        item
        for item in items
        if item.item_type
        in {
            "readiness_requirement_reverification",
            "readiness_remedy_reverification",
        }
    ]
    assert {
        (item.item_type, item.source_ids)
        for item in items
        if item.item_type
        in {"readiness_packet_revalidation", "journey_handoff_revalidation"}
    } == {
        ("readiness_packet_revalidation", ("yolo-public-parcels-layer",)),
        ("journey_handoff_revalidation", ("yolo-public-parcels-layer",)),
    }


def test_journey_revalidation_uses_only_configured_candidate_route_dependencies():
    context = _readiness_context()
    route_worklist = _worklist(
        changed="ca-gov-66317",
        readiness_contexts=(context,),
    )
    unrelated_route_worklist = _worklist(
        changed="ca-gov-66321",
        readiness_contexts=(context,),
    )

    assert [
        item.source_ids
        for item in route_worklist.items
        if item.item_type == "journey_handoff_revalidation"
    ] == [("ca-gov-66317",)]
    assert not [
        item
        for item in route_worklist.items
        if item.item_type == "readiness_packet_revalidation"
    ]
    assert not [
        item
        for item in unrelated_route_worklist.items
        if item.item_type == "journey_handoff_revalidation"
    ]


def test_unverifiable_readiness_source_creates_no_packet_or_handoff_work():
    worklist = _worklist(
        unverifiable="woodland-preapproved-adu-checklist",
        readiness_contexts=(_readiness_context(),),
    )

    assert worklist.status == "clear"
    assert worklist.unverifiable_source_ids == ("woodland-preapproved-adu-checklist",)
    assert worklist.items == ()


def test_readiness_context_binding_and_worklist_loader_reject_drift(tmp_path):
    context = _readiness_context()
    snapshot = _snapshot(changed="yolo-public-parcels-layer")
    sources = load_sources(SOURCES, today=AS_OF)
    rules = load_rules(RULES, today=AS_OF)
    golden = load_golden(GOLDEN, rules)
    worklist = build_review_worklist(
        snapshot,
        sources,
        rules,
        golden,
        readiness_contexts=(context,),
    )
    path = _write_json(tmp_path, "readiness-worklist.json", worklist.to_dict())

    assert (
        load_review_worklist(
            path,
            snapshot,
            sources,
            rules,
            golden,
            readiness_contexts=(context,),
        )
        == worklist
    )
    assert (
        worklist.readiness_contexts[0].workflow_fingerprint
        == context.workflow.fingerprint()
    )
    drifted = replace(context, packet=replace(context.packet, label="Drifted"))
    with pytest.raises(ValueError, match="does not match source-state inputs"):
        load_review_worklist(
            path,
            snapshot,
            sources,
            rules,
            golden,
            readiness_contexts=(drifted,),
        )


def test_readiness_context_rejects_packet_remedy_and_journey_drift():
    context = _readiness_context()
    source_id = "yolo-public-parcels-layer"
    drifted_fact = replace(
        context.packet.facts[0],
        source_field="different_field",
    )
    drifted_packet = replace(
        context.packet,
        facts=(drifted_fact, *context.packet.facts[1:]),
    )
    with pytest.raises(ValueError, match="packet fact binding drifted"):
        _worklist(
            changed=source_id,
            readiness_contexts=(replace(context, packet=drifted_packet),),
        )

    with pytest.raises(ValueError, match="remedies workflow fingerprint drifted"):
        _worklist(
            changed=source_id,
            readiness_contexts=(
                replace(
                    context,
                    remedies=replace(
                        context.remedies,
                        workflow_fingerprint="sha256:" + "0" * 64,
                    ),
                ),
            ),
        )

    with pytest.raises(ValueError, match="is not a route record"):
        _worklist(
            changed=source_id,
            readiness_contexts=(
                replace(
                    context,
                    journeys=(
                        replace(
                            context.journeys[0],
                            candidate_route_rule_ids=("adu-height-standards",),
                        ),
                    ),
                ),
            ),
        )


def test_worklist_encoding_is_deterministic_and_loader_rejects_drift(tmp_path):
    snapshot = _snapshot(changed="ca-gov-66321")
    sources = load_sources(SOURCES, today=AS_OF)
    rules = load_rules(RULES, today=AS_OF)
    golden = load_golden(GOLDEN, rules)
    worklist = build_review_worklist(snapshot, sources, rules, golden)
    encoded = encoded_review_worklist(worklist)
    path = tmp_path / "worklist.json"
    path.write_text(encoded, encoding="utf-8")

    assert encoded == encoded_review_worklist(worklist)
    assert load_review_worklist(path, snapshot, sources, rules, golden) == worklist

    payload = json.loads(encoded)
    payload["items"][0]["reason"] = "wrong"
    with pytest.raises(ValueError, match="does not match source-state inputs"):
        load_review_worklist(
            _write_json(tmp_path, "drifted-worklist.json", payload),
            snapshot,
            sources,
            rules,
            golden,
        )


def test_decision_template_is_complete_and_supports_bound_assignment_and_resolution(
    tmp_path,
):
    worklist = _worklist(changed="ca-gov-66317")
    template = decision_template(worklist)
    payload = template.to_dict()
    assert [entry["item_id"] for entry in payload["entries"]] == sorted(
        item.item_id for item in worklist.items
    )
    assert {entry["status"] for entry in payload["entries"]} == {"unassigned"}

    payload["entries"][0].update(
        {
            "status": "assigned",
            "owner_code": "MAINTAINER_1",
            "assigned_on": "2026-08-09",
        }
    )
    payload["entries"][1].update(
        {
            "status": "resolved",
            "owner_code": "REVIEWER_1",
            "assigned_on": "2026-08-08",
            "disposition": "revise",
            "decided_on": "2026-08-09",
            "evidence_receipt_id": "review-receipt-1",
        }
    )
    path = _write_json(tmp_path, "decisions.json", payload)

    ledger = load_review_decisions(path, worklist, today=AS_OF)
    assert [entry.status for entry in ledger.entries[:2]] == ["assigned", "resolved"]
    assert worklist.status == "open"
    assert worklist.fingerprint() == template.worklist_fingerprint
    assert "cannot clear source-state holds" in ledger.summary()


@pytest.mark.parametrize(
    "mutate, error",
    [
        (
            lambda payload: payload["entries"].pop(),
            "cover every work item",
        ),
        (
            lambda payload: payload["entries"][0].update(
                {"item_fingerprint": "sha256:" + "0" * 64}
            ),
            "item fingerprint does not match",
        ),
        (
            lambda payload: payload["entries"][0].update(
                {
                    "status": "assigned",
                    "owner_code": "person name",
                    "assigned_on": "2026-08-09",
                }
            ),
            "opaque uppercase owner code",
        ),
        (
            lambda payload: payload["entries"][0].update(
                {
                    "status": "resolved",
                    "owner_code": "R1",
                    "assigned_on": "2026-08-09",
                    "disposition": "approved",
                    "decided_on": "2026-08-09",
                    "evidence_receipt_id": "receipt-1",
                }
            ),
            "unsupported value",
        ),
        (
            lambda payload: payload.update(
                {"worklist_fingerprint": "sha256:" + "0" * 64}
            ),
            "worklist fingerprint does not match",
        ),
    ],
)
def test_decision_loader_rejects_orphaned_or_unbound_state(
    tmp_path,
    mutate,
    error,
):
    worklist = _worklist(changed="ca-gov-66317")
    payload = copy.deepcopy(decision_template(worklist).to_dict())
    mutate(payload)

    with pytest.raises(ValueError, match=error):
        load_review_decisions(
            _write_json(tmp_path, "invalid-decisions.json", payload),
            worklist,
            today=AS_OF,
        )


def test_cli_writes_clear_worklist_and_template_then_validates_it(tmp_path, capsys):
    worklist_path = tmp_path / "worklist.json"
    decisions_path = tmp_path / "decisions.json"

    exit_code = review_queue_main(
        [
            "--out",
            str(worklist_path),
            "--decisions-template-out",
            str(decisions_path),
            "--validate-decisions",
            str(decisions_path),
        ]
    )

    assert exit_code == 0
    assert json.loads(worklist_path.read_text(encoding="utf-8"))["status"] == "clear"
    assert json.loads(decisions_path.read_text(encoding="utf-8"))["entries"] == []
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "wrote review worklist" in captured.err
    assert "0 source-change work item(s)" in captured.err


def test_cli_returns_review_needed_for_a_valid_proposed_changed_snapshot(
    tmp_path,
    capsys,
):
    source_state_path = tmp_path / "source-state.json"
    source_state_path.write_text(
        encoded_source_state(_snapshot(changed="ca-gov-66317")),
        encoding="utf-8",
    )

    exit_code = review_queue_main(["--source-state", str(source_state_path)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out)["status"] == "open"
    assert "source-change work item(s)" in captured.err
    assert "cannot clear source-state holds" in captured.err


def test_cli_distinguishes_invalid_inputs_from_an_open_worklist(tmp_path, capsys):
    invalid = tmp_path / "invalid-source-state.json"
    invalid.write_text("{}", encoding="utf-8")

    exit_code = review_queue_main(["--source-state", str(invalid)])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid input or output" in captured.err


def test_currency_workflow_retains_review_package_without_auto_publication():
    workflow = (ROOT / ".github" / "workflows" / "currency.yml").read_text(
        encoding="utf-8"
    )

    assert "python -m permit_pathways.review_queue_cli" in workflow
    assert "--source-state source-state-proposed.json" in workflow
    assert "--out source-review-worklist.json" in workflow
    assert "--decisions-template-out source-review-decisions-template.json" in workflow
    assert "name: source-review-package" in workflow
    assert "retention-days: 30" in workflow
    assert "data/source-status/current.json" not in workflow


def test_cli_uses_the_default_readiness_context_for_a_changed_checklist(
    tmp_path,
    capsys,
):
    source_state_path = tmp_path / "source-state.json"
    source_state_path.write_text(
        encoded_source_state(_snapshot(changed="woodland-preapproved-adu-checklist")),
        encoding="utf-8",
    )

    exit_code = review_queue_main(["--source-state", str(source_state_path)])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["items"]) == 53
    assert len(payload["readiness_contexts"]) == 1
    assert {item["item_type"] for item in payload["items"]} >= {
        "readiness_requirement_reverification",
        "readiness_remedy_reverification",
        "readiness_packet_revalidation",
        "journey_handoff_revalidation",
    }
