import json
from pathlib import Path

import pytest

from permit_pathways.harness.watch import (
    UnverifiableSource,
    WatchResult,
    load_sources,
)
from permit_pathways.source_state import (
    build_source_state_snapshot,
    encoded_source_state,
    load_source_state_snapshot,
)

ROOT = Path(__file__).parent.parent
SOURCES = ROOT / "data" / "sources.json"
RULES = ROOT / "data" / "rules"
GOLDEN = ROOT / "data" / "golden" / "example.json"
CURRENT = ROOT / "data" / "source-status" / "current.json"
CHECKED_AT = "2026-08-03T17:08:28Z"
COMMIT_SHA = "8d841409dc5fd16fe56b52a8b57c826c07f176a6"
RUN_URL = "https://github.com/ChelseaKR/permit-pathways/actions/runs/30835371749"


def _unchanged_watch() -> WatchResult:
    sources = load_sources(SOURCES)
    watched = {
        source_id: source for source_id, source in sources.items() if source.watch
    }
    return WatchResult(
        unchanged=sorted(watched),
        observed_digests={
            source_id: source.sha256
            for source_id, source in watched.items()
            if source.sha256 is not None
        },
    )


def _build(watch: WatchResult, *, receipt_status="reviewed"):
    return build_source_state_snapshot(
        watch,
        SOURCES,
        RULES,
        GOLDEN,
        snapshot_id="source-watch-test",
        checked_at=CHECKED_AT,
        receipt_status=receipt_status,
        method="github_actions_scheduled_watch",
        run_url=RUN_URL,
        commit_sha=COMMIT_SHA,
    )


def _write_payload(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "source-state.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_committed_snapshot_binds_the_exact_successful_watch_run():
    snapshot = load_source_state_snapshot(
        CURRENT,
        SOURCES,
        RULES,
        GOLDEN,
        require_reviewed=True,
    )

    assert snapshot.checked_at == CHECKED_AT
    assert snapshot.receipt.run_url == RUN_URL
    assert snapshot.receipt.commit_sha == COMMIT_SHA
    assert len(snapshot.observations) == 19
    assert snapshot.changed_source_ids == ()
    assert snapshot.unverifiable_source_ids == ()
    assert snapshot.affected_rule_ids == ()
    assert snapshot.affected_golden_case_ids == ()
    assert len(snapshot.unaffected_rule_ids) == 19
    assert len(snapshot.unaffected_golden_case_ids) == 29


def test_changed_source_derives_only_exact_rule_and_case_dependencies():
    watch = _unchanged_watch()
    watch.unchanged.remove("ca-gov-66321")
    watch.changed.append("ca-gov-66321")
    watch.observed_digests["ca-gov-66321"] = "0" * 64

    snapshot = _build(watch)

    assert snapshot.changed_source_ids == ("ca-gov-66321",)
    assert set(snapshot.affected_rule_ids) == {
        "adu-height-standards",
        "adu-multifamily-66323",
        "adu-multifamily-proposed-66323",
        "adu-protected-minimum",
        "adu-size-allowances",
    }
    assert "adu-detached-basic" in snapshot.affected_golden_case_ids
    assert "sb9-duplex-clean" in snapshot.unaffected_golden_case_ids
    assert "sb9-two-unit-ministerial" in snapshot.unaffected_rule_ids


def test_unverifiable_source_remains_warning_and_stales_no_dependents():
    watch = _unchanged_watch()
    watch.unchanged.remove("ca-gov-66321")
    watch.observed_digests.pop("ca-gov-66321")
    watch.unverifiable["ca-gov-66321"] = UnverifiableSource(
        source_id="ca-gov-66321",
        reason="HTTP 403 Forbidden",
        last_verified_on="2026-07-27",
        attempts=3,
    )

    snapshot = _build(watch)

    assert snapshot.changed_source_ids == ()
    assert snapshot.unverifiable_source_ids == ("ca-gov-66321",)
    assert snapshot.affected_rule_ids == ()
    observation = next(
        item for item in snapshot.observations if item.source_id == "ca-gov-66321"
    )
    assert observation.observed_sha256 is None
    assert observation.reason == "HTTP 403 Forbidden"


def test_loader_rejects_summary_or_dependency_impact_drift(tmp_path):
    payload = json.loads(CURRENT.read_text(encoding="utf-8"))
    payload["changed_source_ids"] = ["ca-gov-66321"]
    with pytest.raises(ValueError, match="contradicts observations"):
        load_source_state_snapshot(
            _write_payload(tmp_path, payload),
            SOURCES,
            RULES,
            GOLDEN,
        )

    payload = json.loads(CURRENT.read_text(encoding="utf-8"))
    payload["unaffected_rule_ids"].pop()
    with pytest.raises(ValueError, match="dependency impact drifted"):
        load_source_state_snapshot(
            _write_payload(tmp_path, payload),
            SOURCES,
            RULES,
            GOLDEN,
        )


def test_loader_rejects_observation_or_registry_drift(tmp_path):
    payload = json.loads(CURRENT.read_text(encoding="utf-8"))
    payload["observations"][0]["observed_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="status contradicts observed digest"):
        load_source_state_snapshot(
            _write_payload(tmp_path, payload),
            SOURCES,
            RULES,
            GOLDEN,
        )

    payload = json.loads(CURRENT.read_text(encoding="utf-8"))
    payload["source_registry_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="does not bind current registry"):
        load_source_state_snapshot(
            _write_payload(tmp_path, payload),
            SOURCES,
            RULES,
            GOLDEN,
        )


def test_public_loader_requires_reviewed_receipt(tmp_path):
    proposed = _build(_unchanged_watch(), receipt_status="proposed")
    path = tmp_path / "proposed.json"
    path.write_text(encoded_source_state(proposed), encoding="utf-8")

    assert load_source_state_snapshot(path, SOURCES, RULES, GOLDEN).receipt.status == (
        "proposed"
    )
    with pytest.raises(ValueError, match="public bundle requires reviewed"):
        load_source_state_snapshot(
            path,
            SOURCES,
            RULES,
            GOLDEN,
            require_reviewed=True,
        )


def test_builder_rejects_incomplete_or_overlapping_classification():
    incomplete = _unchanged_watch()
    incomplete.unchanged.pop()
    with pytest.raises(ValueError, match="classify every watched source"):
        _build(incomplete)

    overlapping = _unchanged_watch()
    source_id = overlapping.unchanged[0]
    overlapping.changed.append(source_id)
    overlapping.observed_digests[source_id] = "0" * 64
    with pytest.raises(ValueError, match="classifications overlap"):
        _build(overlapping)


def test_source_state_payload_is_deterministic():
    first = encoded_source_state(_build(_unchanged_watch()))
    reordered = _unchanged_watch()
    reordered.unchanged.reverse()
    second = encoded_source_state(_build(reordered))

    assert first == second
    assert first.endswith("\n")


def test_currency_workflow_retains_only_a_proposed_snapshot_for_review():
    workflow = (ROOT / ".github" / "workflows" / "currency.yml").read_text(
        encoding="utf-8"
    )

    assert "--snapshot-out source-state-proposed.json" in workflow
    assert '--snapshot-id "source-watch-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"' in (
        workflow
    )
    assert "--receipt-method github_actions_source_currency_watch" in workflow
    assert '--commit-sha "$GITHUB_SHA"' in workflow
    assert "name: source-state-proposed" in workflow
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in (
        workflow
    )
    assert "--receipt-status reviewed" not in workflow
    assert "data/source-status/current.json" not in workflow
