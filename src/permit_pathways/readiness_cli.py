"""Command-line packet-presence evaluator for a bounded readiness workflow."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .readiness import load_and_evaluate_readiness

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOW = (
    ROOT
    / "data"
    / "readiness"
    / "workflows"
    / "woodland-preapproved-detached-adu.json"
)
DEFAULT_PACKET = (
    ROOT
    / "data"
    / "readiness"
    / "samples"
    / "woodland-preapproved-adu.json"
)
DEFAULT_SOURCES = ROOT / "data" / "sources.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare an explicit packet inventory with one source-bound "
            "requirement manifest. This is not a completeness or approval "
            "determination."
        )
    )
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
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
    args = parser.parse_args()
    workflow, packet, result = load_and_evaluate_readiness(
        args.workflow,
        args.packet,
        args.sources,
        today=args.as_of,
        changed_source_ids=set(args.changed_source_id),
    )
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
