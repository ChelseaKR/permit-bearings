"""Command-line packet-presence evaluator for a bounded readiness workflow."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from .readiness import load_and_evaluate_readiness
from .workflow_registry import FingerprintedArtifact, load_workflow_registry

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "data" / "workflows" / "registry.json"


def _selected_path(
    root: Path,
    artifact: FingerprintedArtifact,
    option: str,
    override: Path | None,
) -> Path:
    selected = artifact.resolve(root)
    if override is not None and override.resolve() != selected:
        raise ValueError(f"--{option}: path does not match the registered workflow")
    return selected


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare an explicit packet inventory with one source-bound "
            "requirement manifest. This is not a completeness or approval "
            "determination."
        )
    )
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument(
        "--workflow-id",
        default=None,
        help="registered workflow ID; defaults to the browser workflow",
    )
    parser.add_argument(
        "--workflow",
        type=Path,
        default=None,
        help="compatibility assertion; must equal the registered workflow path",
    )
    parser.add_argument(
        "--packet",
        type=Path,
        default=None,
        help="compatibility assertion; must equal the registered packet path",
    )
    parser.add_argument("--sources", type=Path, default=None)
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        help="evaluation date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--changed-source-id",
        action="append",
        default=[],
        help="mark a source changed and require review",
    )
    args = parser.parse_args(argv)
    try:
        root = args.repository_root.resolve()
        registry_path = args.registry or (
            DEFAULT_REGISTRY
            if root == ROOT.resolve()
            else root / "data" / "workflows" / "registry.json"
        )
        registry = load_workflow_registry(registry_path, root=root)
        entry = registry.select(args.workflow_id)
        workflow_path = _selected_path(
            root,
            entry.artifacts.readiness_workflow,
            "workflow",
            args.workflow,
        )
        packet_path = _selected_path(
            root,
            entry.artifacts.readiness_packet,
            "packet",
            args.packet,
        )
        sources_path = args.sources or root / "data" / "sources.json"
        workflow, packet, result = load_and_evaluate_readiness(
            workflow_path,
            packet_path,
            sources_path,
            today=args.as_of,
            changed_source_ids=set(args.changed_source_id),
        )
        if workflow.workflow_id != entry.workflow_id:
            raise ValueError("registered workflow ID does not match its artifact")
        if (
            packet.workflow_id != entry.workflow_id
            or packet.packet_id != entry.packet_id
        ):
            raise ValueError("registered packet IDs do not match its artifact")
        if (
            workflow.jurisdiction != entry.jurisdiction
            or packet.jurisdiction != entry.jurisdiction
        ):
            raise ValueError("registered jurisdiction does not match its artifacts")
    except (OSError, ValueError) as error:
        print(f"readiness: invalid input: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            result.to_manifest(workflow, packet),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
