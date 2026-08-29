"""Maintain the English readability regression baseline.

``check`` exits 0 when no explanation's reading ease fell below its
baseline score. ``regenerate`` rewrites the baseline from current copy —
a deliberate, committed decision, never a side effect.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .readability import (
    build_baseline,
    explanation_scores,
    load_baseline,
    load_explanations_payload,
    regressions,
)

EXPLANATIONS_PATH = Path("data/explanations/plain-language.json")
BASELINE_PATH = Path("data/explanations/readability-baseline.json")


def _paths(root: Path) -> tuple[Path, Path]:
    return root / EXPLANATIONS_PATH, root / BASELINE_PATH


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="permit-pathways-readability")
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    commands.add_parser("regenerate")
    args = parser.parse_args(argv)

    explanations_path, baseline_path = _paths(args.repository_root)
    current = explanation_scores(load_explanations_payload(explanations_path))

    if args.command == "regenerate":
        payload = build_baseline(current)
        baseline_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {baseline_path}: {len(payload['scores'])} entries scored")
        return 0

    findings = regressions(load_baseline(baseline_path), current)
    if findings:
        for finding in findings:
            print(f"readability regression: {finding}", file=sys.stderr)
        return 1
    print(f"readability gate: pass ({len(current)} entries at or above baseline)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
