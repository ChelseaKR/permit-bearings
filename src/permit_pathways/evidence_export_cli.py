"""Build, verify, or inertly restore a public/synthetic evidence package.

This command is intentionally limited to the portable package boundary.  It
does not publish material, adopt a source snapshot, make a review decision, or
handle applicant data.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .evidence_export import build_export, restore_export, verify_export

ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="permit_pathways.evidence_export_cli",
        description=(
            "Build, verify, or inertly restore a pinned public/synthetic "
            "evidence package. The command does not publish, adopt, or "
            "approve its contents."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser(
        "build",
        help="create one deterministic ZIP_STORED package outside the repository",
    )
    build.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root containing the pinned export profile",
    )
    build.add_argument(
        "--output",
        type=Path,
        required=True,
        help="new archive path outside --root; an existing path is refused",
    )
    build.add_argument(
        "--freeze-id",
        required=True,
        help="stable identifier for this frozen package",
    )
    build.add_argument(
        "--frozen-on",
        required=True,
        help="freeze date in YYYY-MM-DD format",
    )
    build.add_argument(
        "--repository-commit-sha",
        default=None,
        help=(
            "optional full Git SHA; it is accepted only when it exactly "
            "matches the repository's verified HEAD"
        ),
    )

    verify = commands.add_parser(
        "verify",
        help="verify archive structure, raw hashes, profile pins, and public state",
    )
    verify.add_argument("--archive", type=Path, required=True)

    restore = commands.add_parser(
        "restore",
        help="verify then restore into a new clean destination without adoption",
    )
    restore.add_argument("--archive", type=Path, required=True)
    restore.add_argument(
        "--destination",
        type=Path,
        required=True,
        help="new destination directory; an existing path is refused",
    )
    return parser


def _emit(payload: dict[str, object]) -> None:
    """Print a stable machine-readable evidence manifest."""

    sys.stdout.write(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the explicitly selected bounded evidence-package operation."""

    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            manifest = build_export(
                args.root,
                args.output,
                freeze_id=args.freeze_id,
                frozen_on=args.frozen_on,
                repository_commit_sha=args.repository_commit_sha,
            )
        elif args.command == "verify":
            manifest = verify_export(args.archive)
        else:
            manifest = restore_export(args.archive, args.destination)
    except (OSError, ValueError) as error:
        print(f"evidence export: invalid input or output: {error}", file=sys.stderr)
        return 2

    _emit(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
