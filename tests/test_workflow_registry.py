import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest
from scripts.build_demo_bundle import build_bundle

from permit_pathways.harness.watch import WatchResult, load_sources
from permit_pathways.program_availability import (
    GENERIC_PROTOTYPE_AVAILABILITY_POLICY,
    GENERIC_PROTOTYPE_BOUNDARY,
    GENERIC_PROTOTYPE_EXCERPT,
    WOODLAND_AVAILABILITY_POLICY,
    excerpt_fingerprint,
)
from permit_pathways.readiness import load_readiness_workflow
from permit_pathways.readiness_cli import main as readiness_cli_main
from permit_pathways.review_queue_cli import main as review_queue_cli_main
from permit_pathways.source_release_cli import main as source_release_cli_main
from permit_pathways.source_state import (
    build_source_state_snapshot,
    encoded_source_state,
)
from permit_pathways.workflow_context import load_registered_review_context
from permit_pathways.workflow_registry import (
    MAX_REGISTRY_BYTES,
    load_workflow_registry,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "workflows" / "registry.json"
ARTIFACT_DIRECTORIES = (
    "data/availability",
    "data/journeys",
    "data/readiness",
    "data/workflows",
)


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _copy_registry_root(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    for relative in ARTIFACT_DIRECTORIES:
        shutil.copytree(ROOT / relative, root / relative)
    return root


def _copy_full_root(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    shutil.copytree(ROOT / "data", root / "data")
    shutil.copytree(ROOT / "corpus", root / "corpus")
    # The bundle build requires the reviewer-roster promotion gate.
    shutil.copy2(ROOT / "reviewer-roster.json", root / "reviewer-roster.json")
    return root


def _registry(root: Path):
    return load_workflow_registry(
        root / "data" / "workflows" / "registry.json",
        root=root,
    )


def _update_artifact_fingerprint(root: Path, registry, artifact_name: str) -> None:
    artifact = registry["workflows"][0]["artifacts"][artifact_name]
    artifact["sha256"] = hashlib.sha256(
        (root / artifact["path"]).read_bytes()
    ).hexdigest()


def _bundle_payload() -> dict:
    assignment = build_bundle().split("=", 1)[1]
    return json.loads(assignment.removesuffix(";\n"))


def _add_second_registered_workflow(
    root: Path,
    *,
    browser_default: bool = False,
) -> str:
    """Add a distinct synthetic registry entry without publishing it."""

    second_workflow_id = "second-prototype-workflow"
    second_packet_id = "second-prototype-packet"
    second_journey_id = "second-prototype-journey"
    second_program_id = "second-prototype-program"
    registry_path = root / "data/workflows/registry.json"
    registry = _json(registry_path)
    template = copy.deepcopy(registry["workflows"][0])
    artifact_names = {
        "readiness_workflow": (
            "data/readiness/workflows/second-prototype-workflow.json"
        ),
        "readiness_packet": "data/readiness/samples/second-prototype-packet.json",
        "readiness_remedies": (
            "data/readiness/remedies/second-prototype-workflow.json"
        ),
        "readiness_evidence": (
            "data/readiness/generated/second-prototype-evidence.json"
        ),
        "journey": "data/journeys/second-prototype-journey.json",
        "journey_evidence": ("data/journeys/generated/second-prototype-journey.json"),
        "program_availability": ("data/availability/second-prototype-program.json"),
    }
    for name, destination in artifact_names.items():
        source = root / template["artifacts"][name]["path"]
        target = root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        if name not in {"readiness_evidence", "journey_evidence"}:
            shutil.copy2(source, target)
        template["artifacts"][name]["path"] = destination

    workflow_path = root / artifact_names["readiness_workflow"]
    workflow_payload = _json(workflow_path)
    workflow_payload["workflow"]["workflow_id"] = second_workflow_id
    workflow_payload["workflow"]["title"] = "Second synthetic workflow"
    _write_json(workflow_path, workflow_payload)
    workflow = load_readiness_workflow(
        workflow_path,
        root / "data/sources.json",
    )

    packet_path = root / artifact_names["readiness_packet"]
    packet_payload = _json(packet_path)
    packet_payload["packet"].update(
        {
            "packet_id": second_packet_id,
            "workflow_id": second_workflow_id,
            "label": "Second made-up packet",
        }
    )
    _write_json(packet_path, packet_payload)

    remedies_path = root / artifact_names["readiness_remedies"]
    remedies_payload = _json(remedies_path)
    remedies_payload["workflow_id"] = second_workflow_id
    remedies_payload["workflow_fingerprint"] = workflow.fingerprint()
    _write_json(remedies_path, remedies_payload)

    journey_path = root / artifact_names["journey"]
    journey_payload = _json(journey_path)
    journey_payload["journey"].update(
        {
            "journey_id": second_journey_id,
            "label": "Second made-up journey",
            "readiness_workflow_id": second_workflow_id,
            "readiness_packet_id": second_packet_id,
        }
    )
    _write_json(journey_path, journey_payload)

    availability_path = root / artifact_names["program_availability"]
    availability_payload = _json(availability_path)
    availability = availability_payload["availability"]
    availability.update(
        {
            "program_id": second_program_id,
            "workflow_id": second_workflow_id,
            "boundary": GENERIC_PROTOTYPE_BOUNDARY,
        }
    )
    source = availability["source"]
    source.update(
        {
            "source_id": "second-prototype-program-page",
            "url": "https://example.gov/second-prototype-program",
            "label": "Second prototype program page",
            "excerpt": GENERIC_PROTOTYPE_EXCERPT,
        }
    )
    source["excerpt_sha256"] = excerpt_fingerprint(source["excerpt"])
    _write_json(availability_path, availability_payload)

    template.update(
        {
            "workflow_id": second_workflow_id,
            "packet_id": second_packet_id,
            "journey_id": second_journey_id,
            "program_id": second_program_id,
            "availability_policy": GENERIC_PROTOTYPE_AVAILABILITY_POLICY,
        }
    )
    for name in (
        "readiness_workflow",
        "readiness_packet",
        "readiness_remedies",
        "journey",
        "program_availability",
    ):
        target = root / template["artifacts"][name]["path"]
        template["artifacts"][name]["sha256"] = hashlib.sha256(
            target.read_bytes()
        ).hexdigest()
    registry["workflows"].append(template)
    if browser_default:
        registry["browser_default_workflow_id"] = second_workflow_id
    _write_json(registry_path, registry)
    return second_workflow_id


def _changed_snapshot(root: Path, source_id: str):
    sources_path = root / "data/sources.json"
    sources = load_sources(sources_path)
    watched = {key: source for key, source in sources.items() if source.watch}
    unchanged = sorted(set(watched) - {source_id})
    result = WatchResult(
        unchanged=unchanged,
        changed=[source_id],
        observed_digests={
            key: watched[key].sha256 for key in unchanged if watched[key].sha256
        },
    )
    result.observed_digests[source_id] = "0" * 64
    return build_source_state_snapshot(
        result,
        sources_path,
        root / "data/rules",
        root / "data/golden/example.json",
        snapshot_id="two-workflow-release-test",
        checked_at="2026-08-10T04:00:00Z",
        receipt_status="proposed",
        method="synthetic_test_fixture",
        run_url="https://example.gov/source-watch/two-workflow-release-test",
        commit_sha="a" * 40,
    )


def test_canonical_registry_selects_exactly_the_one_browser_workflow():
    registry = load_workflow_registry(REGISTRY_PATH, root=ROOT)

    assert len(registry.workflows) == 1
    entry = registry.select()
    assert entry.workflow_id == "woodland-preapproved-detached-adu"
    assert entry.packet_id == "woodland-preapproved-adu-hypothetical-001"
    assert entry.journey_id == "woodland-preapproved-detached-adu-synthetic"
    assert entry.status == "prototype"
    assert entry.availability_policy == WOODLAND_AVAILABILITY_POLICY
    assert entry.artifacts.readiness_evidence.path == (
        "data/readiness/generated/woodland-preapproved-adu-evidence.json"
    )
    with pytest.raises(ValueError, match="unknown workflow ID"):
        registry.select("")


def test_bundle_uses_format_six_with_a_raw_registry_receipt_and_aliases():
    payload = _bundle_payload()
    entry = payload["workflow_registry"]["workflows"][0]

    assert payload["_meta"]["format_version"] == 6
    assert json.loads(payload["workflow_registry_raw"]) == payload["workflow_registry"]
    assert len(payload["workflow_registry"]["workflows"]) == 1
    assert len(payload["journeys"]) == 1
    assert payload["readiness"]["workflow"]["workflow_id"] == entry["workflow_id"]
    assert payload["journeys"][0]["journey_id"] == entry["journey_id"]
    assert (
        payload["program_availability"]["availability"]["program_id"]
        == (entry["program_id"])
    )
    for name in (
        "readiness_workflow",
        "readiness_packet",
        "readiness_remedies",
        "journey",
        "program_availability",
    ):
        artifact = entry["artifacts"][name]
        assert (
            payload["_meta"]["generated_from"][artifact["path"]] == (artifact["sha256"])
        )
    assert "data/workflows/registry.json" in payload["_meta"]["generated_from"]


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (
            lambda payload: payload.update({"browser_default_workflow_id": "missing"}),
            "unknown workflow ID",
        ),
        (
            lambda payload: payload["workflows"].append(
                copy.deepcopy(payload["workflows"][0])
            ),
            "duplicate workflow ID",
        ),
        (
            lambda payload: payload["workflows"][0]["artifacts"][
                "readiness_workflow"
            ].update({"sha256": "0" * 64}),
            "registered fingerprint does not match",
        ),
        (
            lambda payload: payload["workflows"][0]["artifacts"][
                "readiness_workflow"
            ].update({"path": "../outside.json"}),
            "repository-relative JSON path",
        ),
        (
            lambda payload: payload["workflows"][0]["artifacts"][
                "readiness_workflow"
            ].update({"path": "/absolute/outside.json"}),
            "repository-relative JSON path",
        ),
        (
            lambda payload: payload["workflows"][0]["artifacts"][
                "readiness_evidence"
            ].update({"path": "data/journeys/generated/wrong.json"}),
            "data/readiness/generated",
        ),
        (
            lambda payload: payload.update({"unexpected": True}),
            "unknown fields",
        ),
    ],
)
def test_registry_rejects_duplicate_default_fingerprint_and_path_attacks(
    tmp_path: Path,
    mutate,
    error: str,
):
    root = _copy_registry_root(tmp_path)
    path = root / "data" / "workflows" / "registry.json"
    payload = _json(path)
    mutate(payload)
    _write_json(path, payload)

    with pytest.raises(ValueError, match=error):
        _registry(root)


def test_registry_rejects_an_unregistered_canonical_artifact(tmp_path: Path):
    root = _copy_registry_root(tmp_path)
    orphan = root / "data" / "readiness" / "workflows" / "orphan.json"
    orphan.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"orphan files:.*orphan\.json"):
        _registry(root)


def test_registry_rejects_an_unsafe_orphan_json_filename(tmp_path: Path):
    root = _copy_registry_root(tmp_path)
    orphan = root / "data" / "readiness" / "workflows" / "CON.json"
    orphan.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unsafe canonical artifact filename"):
        _registry(root)


def test_registry_rejects_wrong_declared_workflow_id(tmp_path: Path):
    root = _copy_registry_root(tmp_path)
    path = root / "data" / "workflows" / "registry.json"
    payload = _json(path)
    payload["browser_default_workflow_id"] = "different-workflow"
    payload["workflows"][0]["workflow_id"] = "different-workflow"
    _write_json(path, payload)

    with pytest.raises(ValueError, match=r"workflow\.workflow_id"):
        _registry(root)


def test_woodland_workflow_requires_its_exact_availability_policy(
    tmp_path: Path,
) -> None:
    root = _copy_registry_root(tmp_path)
    path = root / "data/workflows/registry.json"
    payload = _json(path)
    payload["workflows"][0]["availability_policy"] = (
        GENERIC_PROTOTYPE_AVAILABILITY_POLICY
    )
    _write_json(path, payload)

    with pytest.raises(ValueError, match="requires its exact source policy"):
        _registry(root)


def test_registry_rejects_orphan_journey_reference_even_when_repinned(
    tmp_path: Path,
):
    root = _copy_registry_root(tmp_path)
    registry_path = root / "data" / "workflows" / "registry.json"
    registry = _json(registry_path)
    journey_ref = registry["workflows"][0]["artifacts"]["journey"]
    journey_path = root / journey_ref["path"]
    journey = _json(journey_path)
    journey["journey"]["readiness_workflow_id"] = "orphan-workflow"
    _write_json(journey_path, journey)
    _update_artifact_fingerprint(root, registry, "journey")
    _write_json(registry_path, registry)

    with pytest.raises(ValueError, match=r"journey\.readiness_workflow_id"):
        _registry(root)


def test_registry_rejects_duplicate_artifact_paths_across_distinct_entries(
    tmp_path: Path,
):
    root = _copy_registry_root(tmp_path)
    registry_path = root / "data" / "workflows" / "registry.json"
    registry = _json(registry_path)
    duplicate = copy.deepcopy(registry["workflows"][0])
    duplicate.update(
        {
            "workflow_id": "second-workflow",
            "packet_id": "second-packet",
            "journey_id": "second-journey",
            "program_id": "second-program",
        }
    )
    registry["workflows"].append(duplicate)
    _write_json(registry_path, registry)

    with pytest.raises(ValueError, match="duplicate input path"):
        _registry(root)


def test_readiness_cli_rejects_unknown_registry_selection(capsys):
    assert readiness_cli_main(["--workflow-id", "not-registered"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown workflow ID" in captured.err


def test_readiness_cli_legacy_path_options_cannot_bypass_registry(
    tmp_path: Path,
    capsys,
):
    outside = tmp_path / "unregistered.json"
    outside.write_text("{}\n", encoding="utf-8")

    assert readiness_cli_main(["--workflow", str(outside)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "does not match the registered workflow" in captured.err


def test_review_queue_cli_rejects_unknown_registry_selection(capsys):
    assert review_queue_cli_main(["--workflow-id", "not-registered"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown workflow ID" in captured.err


def test_two_distinct_registered_workflows_build_and_reach_the_review_cli(
    tmp_path: Path,
    capsys,
) -> None:
    root = _copy_full_root(tmp_path)
    second_workflow_id = _add_second_registered_workflow(root)

    registry = _registry(root)
    assert len(registry.workflows) == 2
    assert registry.select().workflow_id == "woodland-preapproved-detached-adu"
    assert registry.select(second_workflow_id).availability_policy == (
        GENERIC_PROTOTYPE_AVAILABILITY_POLICY
    )
    bundle = json.loads(build_bundle(root).split("=", 1)[1].removesuffix(";\n"))
    assert len(bundle["workflow_registry"]["workflows"]) == 2
    assert bundle["readiness"]["workflow"]["workflow_id"] == (
        "woodland-preapproved-detached-adu"
    )

    result = review_queue_cli_main(
        [
            "--repository-root",
            str(root),
            "--workflow-id",
            second_workflow_id,
        ]
    )
    assert result in {0, 1}
    captured = capsys.readouterr()
    assert second_workflow_id not in captured.err


def test_two_registered_workflows_load_as_distinct_release_contexts(
    tmp_path: Path,
) -> None:
    root = _copy_full_root(tmp_path)
    second_workflow_id = _add_second_registered_workflow(root)
    registry = _registry(root)

    contexts = tuple(
        load_registered_review_context(
            entry,
            root,
            root / "data/sources.json",
        )
        for entry in registry.workflows
    )

    assert [context.workflow.workflow_id for context in contexts] == [
        "woodland-preapproved-detached-adu",
        second_workflow_id,
    ]
    assert len({context.packet.packet_id for context in contexts}) == 2
    assert len({context.journeys[0].journey_id for context in contexts}) == 2


def test_source_release_cli_binds_every_registered_workflow_by_default(
    tmp_path: Path,
    capsys,
) -> None:
    root = _copy_full_root(tmp_path)
    second_workflow_id = _add_second_registered_workflow(root)
    snapshot = _changed_snapshot(root, "woodland-preapproved-adu-checklist")
    snapshot_path = tmp_path / "source-state.json"
    snapshot_path.write_text(encoded_source_state(snapshot), encoding="utf-8")
    worklist_path = tmp_path / "worklist.json"
    decisions_path = tmp_path / "decisions.json"

    assert (
        review_queue_cli_main(
            [
                "--repository-root",
                str(root),
                "--source-state",
                str(snapshot_path),
                "--out",
                str(worklist_path),
                "--decisions-template-out",
                str(decisions_path),
            ]
        )
        == 1
    )
    capsys.readouterr()
    worklist = _json(worklist_path)
    assert [item["workflow_id"] for item in worklist["readiness_contexts"]] == [
        second_workflow_id,
        "woodland-preapproved-detached-adu",
    ]
    item_counts = {
        item_type: sum(item["item_type"] == item_type for item in worklist["items"])
        for item_type in (
            "readiness_requirement_reverification",
            "readiness_remedy_reverification",
            "readiness_packet_revalidation",
            "journey_handoff_revalidation",
        )
    }
    assert item_counts == {
        "readiness_requirement_reverification": 50,
        "readiness_remedy_reverification": 50,
        "readiness_packet_revalidation": 2,
        "journey_handoff_revalidation": 2,
    }

    output = tmp_path / "prepared-release"
    assert (
        source_release_cli_main(
            [
                "prepare",
                "--repository-root",
                str(root),
                "--source-state",
                str(snapshot_path),
                "--worklist",
                str(worklist_path),
                "--decisions",
                str(decisions_path),
                "--release-id",
                "two-workflow-release",
                "--output-dir",
                str(output),
            ]
        )
        == 1
    )
    prepared = json.loads(capsys.readouterr().out)
    approval = _json(output / "approval.json")
    assert prepared["release_binding"] == approval["release_binding"]
    assert approval["release_binding"]["worklist_id"] == worklist["worklist_id"]


def test_bundle_aliases_follow_a_generic_registry_default(tmp_path: Path) -> None:
    root = _copy_full_root(tmp_path)
    second_workflow_id = _add_second_registered_workflow(
        root,
        browser_default=True,
    )

    registry = _registry(root)
    assert registry.select().workflow_id == second_workflow_id
    bundle = json.loads(build_bundle(root).split("=", 1)[1].removesuffix(";\n"))
    assert bundle["readiness"]["workflow"]["workflow_id"] == second_workflow_id
    assert bundle["journeys"][0]["readiness_workflow_id"] == second_workflow_id
    assert bundle["program_availability"]["availability"]["workflow_id"] == (
        second_workflow_id
    )


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "question?.json",
        "fragment#.json",
        "percent%2e.json",
        "colon:name.json",
        "Uppercase.json",
        "caf\u00e9.json",
        "con.json",
        "name..json",
    ],
)
def test_registry_rejects_cross_platform_unsafe_artifact_names(
    tmp_path: Path,
    unsafe_name: str,
) -> None:
    root = _copy_registry_root(tmp_path)
    path = root / "data/workflows/registry.json"
    payload = _json(path)
    payload["workflows"][0]["artifacts"]["readiness_workflow"]["path"] = (
        f"data/readiness/workflows/{unsafe_name}"
    )
    _write_json(path, payload)

    with pytest.raises(ValueError, match="repository-relative JSON path"):
        _registry(root)


def test_registry_rejects_a_symlinked_generated_output_without_touching_input(
    tmp_path: Path,
) -> None:
    root = _copy_registry_root(tmp_path)
    registry = _json(root / "data/workflows/registry.json")
    entry = registry["workflows"][0]["artifacts"]
    input_path = root / entry["readiness_workflow"]["path"]
    generated_path = root / entry["readiness_evidence"]["path"]
    before = input_path.read_bytes()
    generated_path.unlink()
    generated_path.symlink_to(input_path)

    with pytest.raises(ValueError, match="symbolic links are not allowed"):
        _registry(root)
    assert input_path.read_bytes() == before


def test_registry_rejects_a_symlinked_input_and_registry_file(
    tmp_path: Path,
) -> None:
    root = _copy_registry_root(tmp_path)
    registry_path = root / "data/workflows/registry.json"
    registry = _json(registry_path)
    input_path = (
        root / registry["workflows"][0]["artifacts"]["program_availability"]["path"]
    )
    outside_input = tmp_path / "outside-input.json"
    outside_input.write_bytes(input_path.read_bytes())
    input_path.unlink()
    input_path.symlink_to(outside_input)
    with pytest.raises(ValueError, match="symbolic links are not allowed"):
        _registry(root)

    root = _copy_registry_root(tmp_path / "second")
    registry_path = root / "data/workflows/registry.json"
    outside_registry = tmp_path / "outside-registry.json"
    outside_registry.write_bytes(registry_path.read_bytes())
    registry_path.unlink()
    registry_path.symlink_to(outside_registry)
    with pytest.raises(ValueError, match="could not be loaded"):
        _registry(root)


@pytest.mark.parametrize(
    "raw",
    [
        '{"schema_version":1,"schema_version":1,"workflows":[]}',
        '{"schema_version":NaN,"workflows":[]}',
        '{"schema_version":Infinity,"workflows":[]}',
    ],
)
def test_registry_rejects_duplicate_keys_and_nonfinite_json(
    tmp_path: Path,
    raw: str,
) -> None:
    root = _copy_registry_root(tmp_path)
    (root / "data/workflows/registry.json").write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError, match="could not be loaded"):
        _registry(root)


def test_registry_rejects_an_oversized_record(tmp_path: Path) -> None:
    root = _copy_registry_root(tmp_path)
    (root / "data/workflows/registry.json").write_bytes(b" " * (MAX_REGISTRY_BYTES + 1))
    with pytest.raises(ValueError, match="could not be loaded"):
        _registry(root)


def test_registry_rejects_boolean_schema_version(tmp_path: Path) -> None:
    root = _copy_registry_root(tmp_path)
    registry_path = root / "data/workflows/registry.json"
    payload = _json(registry_path)
    payload["schema_version"] = True
    _write_json(registry_path, payload)

    with pytest.raises(ValueError, match="schema_version"):
        _registry(root)


def test_registry_rejects_recursively_nested_json(tmp_path: Path) -> None:
    root = _copy_registry_root(tmp_path)
    registry_path = root / "data/workflows/registry.json"
    registry_path.write_text(
        "[" * 10_000 + "0" + "]" * 10_000,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="could not be loaded"):
        _registry(root)


def test_registry_rejects_ambiguous_json_inside_a_repinned_artifact(
    tmp_path: Path,
) -> None:
    root = _copy_registry_root(tmp_path)
    registry_path = root / "data/workflows/registry.json"
    registry = _json(registry_path)
    artifact = registry["workflows"][0]["artifacts"]["program_availability"]
    artifact_path = root / artifact["path"]
    raw = artifact_path.read_text(encoding="utf-8")
    ambiguous = raw.replace(
        '"schema_version": 1,',
        '"schema_version": 1,\n  "schema_version": 1,',
        1,
    )
    artifact_path.write_text(ambiguous, encoding="utf-8")
    artifact["sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    _write_json(registry_path, registry)

    with pytest.raises(ValueError, match="registered JSON could not be loaded"):
        _registry(root)
