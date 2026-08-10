"""Create a portable source-change re-verification worklist.

The command reads existing repository artifacts only. It does not fetch a
source, edit a rule, adopt a receipt, or publish a result. Exit 0 means the
validated worklist is clear, exit 1 means valid human work remains, and exit 2
means an input or output was invalid. A decision ledger cannot clear a source
condition on its own.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .harness.runner import load_golden
from .harness.watch import load_sources
from .journey import load_journey_config
from .program_availability import load_program_availability
from .readiness import (
    load_readiness_packet,
    load_readiness_remedies,
    load_readiness_workflow,
)
from .review_queue import (
    ReadinessReviewContext,
    build_review_worklist,
    decision_template,
    encoded_decision_ledger,
    encoded_review_worklist,
    load_review_decisions,
)
from .screening import load_rules
from .source_state import load_source_state_snapshot
from .workflow_registry import (
    FingerprintedArtifact,
    WorkflowRegistryEntry,
    load_workflow_registry,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_STATE = ROOT / "data" / "source-status" / "current.json"
DEFAULT_SOURCES = ROOT / "data" / "sources.json"
DEFAULT_RULES = ROOT / "data" / "rules"
DEFAULT_GOLDEN = ROOT / "data" / "golden" / "example.json"
DEFAULT_REGISTRY = ROOT / "data" / "workflows" / "registry.json"


def _write(path: Path, content: str, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote {label}: {path}", file=sys.stderr)


def _assert_registered_path(
    root: Path,
    artifact: FingerprintedArtifact,
    override: Path | None,
    option: str,
) -> Path:
    selected = artifact.resolve(root)
    if override is not None and override.resolve() != selected:
        raise ValueError(f"--{option}: path does not match the registered workflow")
    return selected


def _readiness_context(
    entry: WorkflowRegistryEntry,
    root: Path,
    sources_path: Path,
    *,
    workflow_override: Path | None = None,
    packet_override: Path | None = None,
    remedies_override: Path | None = None,
    journey_override: Path | None = None,
) -> ReadinessReviewContext:
    workflow = load_readiness_workflow(
        _assert_registered_path(
            root,
            entry.artifacts.readiness_workflow,
            workflow_override,
            "workflow",
        ),
        sources_path,
    )
    packet = load_readiness_packet(
        _assert_registered_path(
            root,
            entry.artifacts.readiness_packet,
            packet_override,
            "packet",
        ),
        workflow,
    )
    remedies = load_readiness_remedies(
        _assert_registered_path(
            root,
            entry.artifacts.readiness_remedies,
            remedies_override,
            "remedies",
        ),
        workflow,
    )
    journey = load_journey_config(
        _assert_registered_path(
            root,
            entry.artifacts.journey,
            journey_override,
            "journey",
        )
    )
    availability = load_program_availability(
        entry.artifacts.program_availability.resolve(root),
        policy=entry.availability_policy,
    )
    if workflow.workflow_id != entry.workflow_id:
        raise ValueError("registered workflow ID does not match its artifact")
    if packet.workflow_id != entry.workflow_id or packet.packet_id != entry.packet_id:
        raise ValueError("registered packet IDs do not match its artifact")
    if journey.journey_id != entry.journey_id:
        raise ValueError("registered journey ID does not match its artifact")
    if (
        journey.readiness_workflow_id != entry.workflow_id
        or journey.readiness_packet_id != entry.packet_id
    ):
        raise ValueError("registered journey references do not match its workflow")
    if (
        availability.workflow_id != entry.workflow_id
        or availability.program_id != entry.program_id
    ):
        raise ValueError("registered availability IDs do not match its artifact")
    if (
        workflow.jurisdiction != entry.jurisdiction
        or packet.jurisdiction != entry.jurisdiction
        or availability.jurisdiction != entry.jurisdiction
    ):
        raise ValueError("registered jurisdiction does not match its artifacts")
    return ReadinessReviewContext(
        workflow=workflow,
        packet=packet,
        remedies=remedies,
        journeys=(journey,),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="permit_pathways.review_queue_cli",
        description=(
            "Build a source-change worklist from explicit source IDs. "
            "This command cannot clear source-state holds or publish changes."
        ),
    )
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--workflow-registry", type=Path, default=None)
    parser.add_argument(
        "--workflow-id",
        default=None,
        help=(
            "include one registered workflow; by default every registered "
            "workflow is included"
        ),
    )
    parser.add_argument("--source-state", type=Path, default=None)
    parser.add_argument("--sources", type=Path, default=None)
    parser.add_argument("--rules", type=Path, default=None)
    parser.add_argument("--golden", type=Path, default=None)
    parser.add_argument(
        "--workflow",
        type=Path,
        default=None,
        help="compatibility assertion for one registered workflow path",
    )
    parser.add_argument(
        "--packet",
        type=Path,
        default=None,
        help="compatibility assertion for one registered packet path",
    )
    parser.add_argument(
        "--remedies",
        type=Path,
        default=None,
        help="compatibility assertion for one registered remedies path",
    )
    parser.add_argument(
        "--journey",
        type=Path,
        default=None,
        help="compatibility assertion for one registered journey path",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write the deterministic worklist JSON instead of stdout",
    )
    parser.add_argument(
        "--decisions-template-out",
        type=Path,
        default=None,
        help="write a complete unassigned decision-ledger template",
    )
    parser.add_argument(
        "--validate-decisions",
        type=Path,
        default=None,
        help="validate a separate decision ledger against the generated worklist",
    )
    args = parser.parse_args(argv)

    try:
        root = args.repository_root.resolve()
        registry_path = args.workflow_registry or (
            DEFAULT_REGISTRY
            if root == ROOT.resolve()
            else root / "data" / "workflows" / "registry.json"
        )
        registry = load_workflow_registry(registry_path, root=root)
        legacy_override = any(
            path is not None
            for path in (args.workflow, args.packet, args.remedies, args.journey)
        )
        entries: tuple[WorkflowRegistryEntry, ...]
        if args.workflow_id is not None or legacy_override:
            entries = (registry.select(args.workflow_id),)
        else:
            entries = registry.workflows
        source_state_path = args.source_state or (
            DEFAULT_SOURCE_STATE
            if root == ROOT.resolve()
            else root / "data" / "source-status" / "current.json"
        )
        sources_path = args.sources or (
            DEFAULT_SOURCES
            if root == ROOT.resolve()
            else root / "data" / "sources.json"
        )
        rules_path = args.rules or (
            DEFAULT_RULES if root == ROOT.resolve() else root / "data" / "rules"
        )
        golden_path = args.golden or (
            DEFAULT_GOLDEN
            if root == ROOT.resolve()
            else root / "data" / "golden" / "example.json"
        )
        snapshot = load_source_state_snapshot(
            source_state_path,
            sources_path,
            rules_path,
            golden_path,
            require_reviewed=False,
        )
        readiness_contexts = tuple(
            _readiness_context(
                entry,
                root,
                sources_path,
                workflow_override=args.workflow,
                packet_override=args.packet,
                remedies_override=args.remedies,
                journey_override=args.journey,
            )
            for entry in entries
        )
        sources = load_sources(sources_path)
        rules = load_rules(rules_path)
        golden_cases = load_golden(golden_path, rules)
        worklist = build_review_worklist(
            snapshot,
            sources,
            rules,
            golden_cases,
            readiness_contexts=readiness_contexts,
        )
        encoded = encoded_review_worklist(worklist)
        if args.out is None:
            print(encoded, end="")
        else:
            _write(args.out, encoded, "review worklist")

        if args.decisions_template_out is not None:
            _write(
                args.decisions_template_out,
                encoded_decision_ledger(decision_template(worklist)),
                "review decision template",
            )
        if args.validate_decisions is not None:
            ledger = load_review_decisions(args.validate_decisions, worklist)
            print(ledger.summary(), file=sys.stderr)
    except (OSError, ValueError) as error:
        print(f"review worklist: invalid input or output: {error}", file=sys.stderr)
        return 2

    print(worklist.summary(), file=sys.stderr)
    if worklist.status == "open":
        print(
            "Human review remains required. This worklist and any decision ledger "
            "cannot clear source-state holds, promote review, or republish output.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
