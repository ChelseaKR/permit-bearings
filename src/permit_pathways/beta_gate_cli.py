"""Read-only CLI for the pilot-neutral aggregate beta gate."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .beta_gate import DEFAULT_RECORD_PATH, load_beta_gate


def _parser(repository_root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and recompute the prepared pilot-neutral beta gate. "
            "Success is planning integrity only, never a tested-beta claim."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser(
        "validate",
        help="validate bound artifacts and print the recomputed status as JSON",
    )
    validate.add_argument(
        "--record",
        type=Path,
        default=None,
        help=(
            "aggregate record to validate; defaults to DEFAULT_RECORD_PATH "
            "inside --repository-root"
        ),
    )
    validate.add_argument("--repository-root", type=Path, default=repository_root)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Return 0 for a valid prepared/not-run record and 2 for invalid input."""

    default_root = Path(__file__).resolve().parents[2]
    args = _parser(default_root).parse_args(argv)
    record = (
        args.record
        if args.record is not None
        else args.repository_root / DEFAULT_RECORD_PATH
    )
    try:
        summary = load_beta_gate(
            record,
            repository_root=args.repository_root,
        )
    except ValueError as error:
        print(f"pilot beta aggregate gate: INVALID: {error}", file=sys.stderr)
        return 2
    print(json.dumps(summary.to_dict(), ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
