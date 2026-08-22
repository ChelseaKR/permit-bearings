#!/usr/bin/env python3
"""Build the browser demo's deterministic, offline-safe data bundle.

The JSON files remain canonical. ``data/demo-data.js`` is a generated
JavaScript assignment so ``index.html`` can be opened directly from disk
without browser-blocked ``file://`` fetches.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from permit_pathways.explanations import load_explanations  # noqa: E402
from permit_pathways.harness.watch import (  # noqa: E402
    load_sources,
    normalized_digest,
)
from permit_pathways.journey import (  # noqa: E402
    load_journey_config,
    resolve_journey,
)
from permit_pathways.jurisdictions import build_coverage_index  # noqa: E402
from permit_pathways.program_availability import (  # noqa: E402
    ProgramAvailability,
    load_program_availability,
)
from permit_pathways.readiness import (  # noqa: E402
    SOURCE_MAX_AGE_DAYS,
    ReadinessPacket,
    ReadinessResult,
    ReadinessWorkflow,
    load_and_evaluate_readiness,
    load_readiness_remedies,
)
from permit_pathways.rule_verification import (  # noqa: E402
    load_rule_verifications,
)
from permit_pathways.screening import load_rules  # noqa: E402
from permit_pathways.source_state import load_source_state_snapshot  # noqa: E402
from permit_pathways.workflow_registry import (  # noqa: E402
    WorkflowRegistry,
    WorkflowRegistryEntry,
    load_workflow_registry,
    registry_digest,
)

OUTPUT = ROOT / "data" / "demo-data.js"
RULE_MANIFEST_OUTPUT = ROOT / "data" / "rules" / "index.json"
WORKFLOW_REGISTRY = Path("data/workflows/registry.json")
COVERAGE_INDEX_OUTPUT = ROOT / "data/jurisdictions/generated/coverage-index.json"
SOURCE_STATE = Path("data/source-status/current.json")
INPUTS = {
    "golden": Path("data/golden/example.json"),
    "sources": Path("data/sources.json"),
    "checks": Path("data/conformance/checks.json"),
    "registry": Path("data/jurisdictions/registry.json"),
    "letters": Path("data/jurisdictions/hcd-letters.json"),
    "scans": Path("data/conformance/results/index.json"),
    "plain_language": Path("data/explanations/plain-language.json"),
    "rule_verification": Path("data/validation/rule-verification.json"),
}

CanonicalReadinessRecords = tuple[
    ReadinessWorkflow,
    ReadinessPacket,
    ReadinessResult,
    date,
]


def _workflow_registry(root: Path = ROOT) -> WorkflowRegistry:
    return load_workflow_registry(
        root / WORKFLOW_REGISTRY,
        root=root,
        validate_inventory=True,
    )


def _workflow_entry(
    root: Path,
    workflow_id: str | None = None,
) -> WorkflowRegistryEntry:
    return _workflow_registry(root).select(workflow_id)


def _validate_readiness_ids(
    entry: WorkflowRegistryEntry,
    workflow: ReadinessWorkflow,
    packet: ReadinessPacket,
) -> None:
    if workflow.workflow_id != entry.workflow_id:
        raise ValueError(f"{entry.workflow_id}: registered workflow ID does not match")
    if packet.workflow_id != entry.workflow_id:
        raise ValueError(
            f"{entry.workflow_id}: registered packet workflow ID does not match"
        )
    if packet.packet_id != entry.packet_id:
        raise ValueError(f"{entry.workflow_id}: registered packet ID does not match")
    if workflow.jurisdiction != entry.jurisdiction:
        raise ValueError(f"{entry.workflow_id}: registered jurisdiction does not match")
    if packet.jurisdiction != entry.jurisdiction:
        raise ValueError(
            f"{entry.workflow_id}: registered packet jurisdiction does not match"
        )


def _registered_program_availability(
    entry: WorkflowRegistryEntry,
    root: Path,
) -> ProgramAvailability:
    availability = load_program_availability(
        entry.artifacts.program_availability.resolve(root),
        policy=entry.availability_policy,
    )
    if availability.workflow_id != entry.workflow_id:
        raise ValueError(
            f"{entry.workflow_id}: availability workflow ID does not match"
        )
    if availability.program_id != entry.program_id:
        raise ValueError(f"{entry.workflow_id}: registered program ID does not match")
    if availability.jurisdiction != entry.jurisdiction:
        raise ValueError(
            f"{entry.workflow_id}: availability jurisdiction does not match"
        )
    return availability


def discover_rule_files(root: Path = ROOT) -> list[Path]:
    """Return every canonical rule file, excluding generated metadata."""

    return sorted(
        path
        for path in (root / "data" / "rules").glob("*.json")
        if path.name != "index.json"
    )


def rule_manifest(root: Path = ROOT) -> dict[str, object]:
    files = discover_rule_files(root)
    if not files:
        raise ValueError("data/rules: no canonical rule files found")
    return {
        "schema_version": 1,
        "files": [path.name for path in files],
    }


def encoded_rule_manifest(root: Path = ROOT) -> str:
    return (
        json.dumps(
            rule_manifest(root),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def aggregate_rule_records(
    root: Path = ROOT,
) -> tuple[list[object], dict[str, str]]:
    """Load every discovered rule file and return records plus digests."""

    aggregate: list[object] = []
    digests: dict[str, str] = {}
    for rule_path in discover_rule_files(root):
        raw = rule_path.read_bytes()
        records = json.loads(raw)
        if not isinstance(records, list):
            raise ValueError(f"{rule_path}: expected a list of rules")
        aggregate.extend(records)
        relative_path = rule_path.relative_to(root)
        digests[relative_path.as_posix()] = hashlib.sha256(raw).hexdigest()
    return aggregate, digests


def _canonical_readiness_records(
    root: Path,
    *,
    entry: WorkflowRegistryEntry | None = None,
) -> CanonicalReadinessRecords:
    selected = entry or _workflow_entry(root)
    workflow_path = selected.artifacts.readiness_workflow.resolve(root)
    sample_path = selected.artifacts.readiness_packet.resolve(root)
    sample_payload = json.loads(sample_path.read_text(encoding="utf-8"))
    try:
        canonical_evaluated_on = sample_payload["packet"]["evaluated_on"]
        evaluation_date = date.fromisoformat(canonical_evaluated_on)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            f"{selected.artifacts.readiness_packet.path}: invalid packet.evaluated_on"
        ) from error
    workflow, packet, result = load_and_evaluate_readiness(
        workflow_path,
        sample_path,
        root / "data" / "sources.json",
        today=evaluation_date,
    )
    _validate_readiness_ids(selected, workflow, packet)
    if not packet.synthetic:
        raise ValueError(
            f"{selected.artifacts.readiness_packet.path}: "
            "public demo packets must be synthetic"
        )
    return workflow, packet, result, evaluation_date


def build_readiness_payload(
    root: Path = ROOT,
    *,
    workflow_id: str | None = None,
    records: CanonicalReadinessRecords | None = None,
) -> tuple[dict[str, object], dict[str, str]]:
    """Build one registered deterministic synthetic readiness sample."""

    entry = _workflow_entry(root, workflow_id)
    remedies_path = entry.artifacts.readiness_remedies.resolve(root)
    workflow, packet, result, evaluation_date = records or (
        _canonical_readiness_records(root, entry=entry)
    )
    _validate_readiness_ids(entry, workflow, packet)
    remedies = load_readiness_remedies(
        remedies_path,
        workflow,
        today=evaluation_date,
    )
    manifest = result.to_manifest(workflow, packet)
    source_review_due_on = min(
        date.fromisoformat(binding.source_checked_on)
        + timedelta(days=SOURCE_MAX_AGE_DAYS)
        for binding in workflow.source_bindings
    ).isoformat()
    if source_review_due_on != result.source_review_due_on:
        raise AssertionError("readiness source-review deadline drifted")
    payload: dict[str, object] = {
        "workflow": asdict(workflow),
        "packet": asdict(packet),
        "result": asdict(result),
        "counts": result.counts(),
        "source_review_due_on": source_review_due_on,
        "remedies": asdict(remedies),
        "evidence_manifest": manifest,
        "ai_trace": {
            "role": (
                "AI proposed the checklist-to-requirement mapping, parcel-field "
                "bindings, and plain-language missing-item actions from the "
                "linked official sources."
            ),
            "runtime_model_call": False,
            "applicant_data_sent_to_model": False,
            "input_source_ids": [
                binding.source_id for binding in workflow.source_bindings
            ],
            "mapping_version": workflow.mapping_provenance.version,
            "mapping_review_status": (workflow.mapping_provenance.review_status),
            "mapping_provider": workflow.mapping_provenance.provider,
            "mapping_model": workflow.mapping_provenance.model,
            "mapping_run_record_status": (
                workflow.mapping_provenance.run_record_status
            ),
            "output_workflow_fingerprint": workflow.fingerprint(),
            "output_remedy_version": remedies.version,
            "output_remedy_content_fingerprint": remedies.content_fingerprint,
            "remedy_review_status": remedies.review.status,
            "remedy_reviewer": remedies.review.reviewer,
        },
    }
    digests = {
        artifact.path: hashlib.sha256(artifact.resolve(root).read_bytes()).hexdigest()
        for artifact in (
            entry.artifacts.readiness_workflow,
            entry.artifacts.readiness_packet,
            entry.artifacts.readiness_remedies,
        )
    }
    return payload, digests


def encoded_readiness_evidence(root: Path = ROOT) -> str:
    payload, _ = build_readiness_payload(root)
    return (
        json.dumps(
            payload["evidence_manifest"],
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def build_journey_payload(
    root: Path = ROOT,
    *,
    workflow_id: str | None = None,
    records: CanonicalReadinessRecords | None = None,
) -> tuple[dict[str, object], dict[str, str]]:
    """Build the versioned synthetic route-to-packet journey envelope."""

    entry = _workflow_entry(root, workflow_id)
    workflow, packet, result, _ = records or _canonical_readiness_records(
        root,
        entry=entry,
    )
    _validate_readiness_ids(entry, workflow, packet)
    journey_path = entry.artifacts.journey.resolve(root)
    config = load_journey_config(journey_path)
    if config.journey_id != entry.journey_id:
        raise ValueError(f"{entry.workflow_id}: registered journey ID does not match")
    if config.readiness_workflow_id != entry.workflow_id:
        raise ValueError(
            f"{entry.workflow_id}: journey readiness workflow ID does not match"
        )
    if config.readiness_packet_id != entry.packet_id:
        raise ValueError(f"{entry.workflow_id}: journey packet ID does not match")
    manifest = resolve_journey(
        config,
        root / INPUTS["golden"],
        load_rules(root / "data" / "rules"),
        workflow,
        packet,
        result,
    )
    return manifest, {
        entry.artifacts.journey.path: hashlib.sha256(
            journey_path.read_bytes()
        ).hexdigest()
    }


def encoded_journey(root: Path = ROOT) -> str:
    payload, _ = build_journey_payload(root)
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def build_coverage_index_payload(root: Path = ROOT) -> dict[str, object]:
    """Compile the compact statewide/local coverage inventory for the browser."""

    return build_coverage_index(
        root / INPUTS["registry"],
        root / "data" / "rules",
        root / INPUTS["letters"],
    )


def encoded_coverage_index(root: Path = ROOT) -> str:
    return (
        json.dumps(
            build_coverage_index_payload(root),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _validate_local_source_copies(root: Path) -> None:
    """Ensure preserved evidence bytes still match the source registry."""

    sources = load_sources(root / "data" / "sources.json")
    resolved_root = root.resolve()
    for source in sources.values():
        if source.watch and source.local_copy is None:
            raise ValueError(f"{source.source_id}: watched source requires local_copy")
        if source.local_copy is None:
            continue
        local_path = (root / source.local_copy).resolve()
        if resolved_root not in local_path.parents:
            raise ValueError(f"{source.source_id}.local_copy: path leaves repository")
        try:
            content = local_path.read_bytes()
        except OSError as error:
            raise ValueError(f"{source.source_id}.local_copy: unavailable") from error
        digest = normalized_digest(content, source.normalize)
        if digest != source.sha256:
            raise ValueError(
                f"{source.source_id}.local_copy: digest does not match registry"
            )


def _build_registered_payloads(
    root: Path,
    registry: WorkflowRegistry,
    records: CanonicalReadinessRecords | None,
) -> tuple[dict[str, object], dict[str, object], dict[str, str]]:
    default_entry = registry.select()
    default_readiness: dict[str, object] | None = None
    default_journey: dict[str, object] | None = None
    digests: dict[str, str] = {}
    for entry in registry.workflows:
        entry_records = (
            records
            if records is not None and entry.workflow_id == default_entry.workflow_id
            else _canonical_readiness_records(root, entry=entry)
        )
        readiness, readiness_digests = build_readiness_payload(
            root,
            workflow_id=entry.workflow_id,
            records=entry_records,
        )
        journey, journey_digests = build_journey_payload(
            root,
            workflow_id=entry.workflow_id,
            records=entry_records,
        )
        _registered_program_availability(entry, root)
        digests.update(readiness_digests)
        digests.update(journey_digests)
        digests[entry.artifacts.program_availability.path] = (
            entry.artifacts.program_availability.sha256
        )
        if entry.workflow_id == default_entry.workflow_id:
            default_readiness = readiness
            default_journey = journey
    if default_readiness is None or default_journey is None:
        raise AssertionError("browser-default workflow was not built")
    return default_readiness, default_journey, digests


def build_bundle(
    root: Path = ROOT,
    *,
    records: CanonicalReadinessRecords | None = None,
) -> str:
    """Return the generated bundle text from canonical JSON inputs."""

    rules = load_rules(root / "data" / "rules")
    sources = load_sources(root / "data" / "sources.json")
    known_sources = set(sources)
    for rule in rules:
        unknown = sorted(set(rule.source_dependencies) - known_sources)
        if unknown:
            raise ValueError(
                f"{rule.rule_id}: unknown source dependencies: " + ", ".join(unknown)
            )
        dependency_urls = {
            sources[source_id].url for source_id in rule.source_dependencies
        }
        if rule.citation.url not in dependency_urls:
            raise ValueError(
                f"{rule.rule_id}: citation URL is not an explicit dependency"
            )
        cited_source = next(
            sources[source_id]
            for source_id in rule.source_dependencies
            if sources[source_id].url == rule.citation.url
        )
        if rule.citation.verified_on is not None:
            if (
                cited_source.fetched_on is None
                or cited_source.sha256 is None
                or cited_source.local_copy is None
            ):
                raise ValueError(
                    f"{rule.rule_id}: dated citation has no preserved source evidence"
                )
            if cited_source.fetched_on > rule.citation.verified_on:
                raise ValueError(
                    f"{rule.rule_id}: citation verification predates "
                    "the preserved source evidence"
                )
    _validate_local_source_copies(root)
    load_explanations(
        root / "data" / "explanations" / "plain-language.json",
        rules,
    )
    from permit_pathways.reviewer_roster import load_reviewer_roster

    # Build-time promotion gate: a promoted ledger entry must name a
    # currently attested roster member. The roster file is required here so
    # deleting it cannot silently remove the gate. The committed template
    # has zero members and the committed ledger has zero promotions, so
    # this is a structural tripwire, not a present-tense review claim.
    load_rule_verifications(
        root / INPUTS["rule_verification"],
        rules,
        roster=load_reviewer_roster(root / "reviewer-roster.json"),
    )

    payload: dict[str, object] = {}
    digests: dict[str, str] = {}
    registry = _workflow_registry(root)
    default_entry = registry.select()
    aggregate_rules, rule_digests = aggregate_rule_records(root)
    digests.update(rule_digests)
    payload["rules"] = aggregate_rules
    payload["rule_manifest"] = rule_manifest(root)
    payload["coverage_index"] = build_coverage_index_payload(root)
    default_readiness, default_journey, workflow_digests = _build_registered_payloads(
        root, registry, records
    )
    digests.update(workflow_digests)
    payload["readiness"] = default_readiness
    payload["journeys"] = [default_journey]
    registry_path = root / WORKFLOW_REGISTRY
    registry_raw = registry_path.read_bytes()
    registry_text = registry_raw.decode("utf-8")
    payload["workflow_registry"] = json.loads(registry_text)
    payload["workflow_registry_raw"] = registry_text
    digests[WORKFLOW_REGISTRY.as_posix()] = registry_digest(registry_path)
    availability_path = default_entry.artifacts.program_availability.resolve(root)
    payload["program_availability"] = json.loads(
        availability_path.read_text(encoding="utf-8")
    )
    source_state = load_source_state_snapshot(
        root / SOURCE_STATE,
        root / INPUTS["sources"],
        root / "data" / "rules",
        root / INPUTS["golden"],
        require_reviewed=True,
    )
    payload["source_state"] = source_state.to_dict()
    digests[SOURCE_STATE.as_posix()] = hashlib.sha256(
        (root / SOURCE_STATE).read_bytes()
    ).hexdigest()

    for key, relative_path in INPUTS.items():
        raw = (root / relative_path).read_bytes()
        payload[key] = json.loads(raw)
        digests[relative_path.as_posix()] = hashlib.sha256(raw).hexdigest()

    payload["_meta"] = {
        "format_version": 6,
        "generated_from": digests,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return (
        "/* Generated by scripts/build_demo_bundle.py; do not edit by hand. */\n"
        f"globalThis.PERMIT_PATHWAYS_DEMO_DATA={encoded};\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the committed bundle differs from the canonical JSON",
    )
    args = parser.parse_args()
    registry = _workflow_registry(ROOT)
    default_entry = registry.select()
    default_records: CanonicalReadinessRecords | None = None
    generated_outputs: dict[Path, str] = {}
    for entry in registry.workflows:
        records = _canonical_readiness_records(ROOT, entry=entry)
        readiness, _ = build_readiness_payload(
            ROOT,
            workflow_id=entry.workflow_id,
            records=records,
        )
        journey, _ = build_journey_payload(
            ROOT,
            workflow_id=entry.workflow_id,
            records=records,
        )
        generated_outputs[entry.artifacts.readiness_evidence.resolve(ROOT)] = (
            json.dumps(
                readiness["evidence_manifest"],
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        generated_outputs[entry.artifacts.journey_evidence.resolve(ROOT)] = (
            json.dumps(
                journey,
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        if entry.workflow_id == default_entry.workflow_id:
            default_records = records
    if default_records is None:
        raise AssertionError("browser-default workflow was not built")
    expected_coverage_index = encoded_coverage_index()
    expected = build_bundle(ROOT, records=default_records)
    expected_manifest = encoded_rule_manifest()

    if args.check:
        bundle_current = (
            OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") == expected
        )
        manifest_current = (
            RULE_MANIFEST_OUTPUT.exists()
            and RULE_MANIFEST_OUTPUT.read_text(encoding="utf-8") == expected_manifest
        )
        registered_outputs_current = all(
            path.exists() and path.read_text(encoding="utf-8") == content
            for path, content in generated_outputs.items()
        )
        coverage_index_current = (
            COVERAGE_INDEX_OUTPUT.exists()
            and COVERAGE_INDEX_OUTPUT.read_text(encoding="utf-8")
            == expected_coverage_index
        )
        if (
            not bundle_current
            or not manifest_current
            or not registered_outputs_current
            or not coverage_index_current
        ):
            print(
                "generated demo data is out of date; "
                "run python3 scripts/build_demo_bundle.py"
            )
            return 1
        print(
            "demo bundle, rule manifest, registered workflow evidence, and "
            "coverage index are in sync"
        )
        return 0

    RULE_MANIFEST_OUTPUT.write_text(expected_manifest, encoding="utf-8")
    for path, content in generated_outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    COVERAGE_INDEX_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE_INDEX_OUTPUT.write_text(expected_coverage_index, encoding="utf-8")
    OUTPUT.write_text(expected, encoding="utf-8")
    print(f"wrote {RULE_MANIFEST_OUTPUT.relative_to(ROOT)}")
    for path in generated_outputs:
        print(f"wrote {path.relative_to(ROOT)}")
    print(f"wrote {COVERAGE_INDEX_OUTPUT.relative_to(ROOT)}")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
