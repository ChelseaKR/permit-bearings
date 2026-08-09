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

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_STATE = ROOT / "data" / "source-status" / "current.json"
DEFAULT_SOURCES = ROOT / "data" / "sources.json"
DEFAULT_RULES = ROOT / "data" / "rules"
DEFAULT_GOLDEN = ROOT / "data" / "golden" / "example.json"
DEFAULT_READINESS_WORKFLOW = (
    ROOT / "data" / "readiness" / "workflows" / "woodland-preapproved-detached-adu.json"
)
DEFAULT_READINESS_PACKET = (
    ROOT / "data" / "readiness" / "samples" / "woodland-preapproved-adu.json"
)
DEFAULT_READINESS_REMEDIES = (
    ROOT / "data" / "readiness" / "remedies" / "woodland-preapproved-detached-adu.json"
)
DEFAULT_JOURNEY = ROOT / "data" / "journeys" / "woodland-preapproved-detached-adu.json"


def _write(path: Path, content: str, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote {label}: {path}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="permit_pathways.review_queue_cli",
        description=(
            "Build a source-change worklist from explicit source IDs. "
            "This command cannot clear source-state holds or publish changes."
        ),
    )
    parser.add_argument("--source-state", type=Path, default=DEFAULT_SOURCE_STATE)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument(
        "--workflow",
        type=Path,
        default=DEFAULT_READINESS_WORKFLOW,
        help="source-bound readiness workflow to include in the worklist",
    )
    parser.add_argument(
        "--packet",
        type=Path,
        default=DEFAULT_READINESS_PACKET,
        help="canonical packet bound to the readiness workflow",
    )
    parser.add_argument(
        "--remedies",
        type=Path,
        default=DEFAULT_READINESS_REMEDIES,
        help="versioned remedies bound to the readiness workflow",
    )
    parser.add_argument(
        "--journey",
        type=Path,
        default=DEFAULT_JOURNEY,
        help="versioned handoff journey bound to the packet workflow",
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
        snapshot = load_source_state_snapshot(
            args.source_state,
            args.sources,
            args.rules,
            args.golden,
            require_reviewed=False,
        )
        workflow = load_readiness_workflow(args.workflow, args.sources)
        packet = load_readiness_packet(args.packet, workflow)
        remedies = load_readiness_remedies(args.remedies, workflow)
        readiness_context = ReadinessReviewContext(
            workflow=workflow,
            packet=packet,
            remedies=remedies,
            journeys=(load_journey_config(args.journey),),
        )
        sources = load_sources(args.sources)
        rules = load_rules(args.rules)
        golden_cases = load_golden(args.golden, rules)
        worklist = build_review_worklist(
            snapshot,
            sources,
            rules,
            golden_cases,
            readiness_contexts=(readiness_context,),
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
