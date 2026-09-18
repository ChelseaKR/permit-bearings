"""CLI for the pilot-neutral aggregate beta gate: validate, and re-derive pins.

``validate`` is read-only.  ``recompute`` re-derives the mechanical digests the
record and the v2 export profile pin, so that two ordinary maintenance acts —
refreshing a public source snapshot and adopting a source-watch receipt — stop
requiring a hand-edit of a tamper-evidence anchor.  It is deliberately unable
to make the gate say anything more favorable: the immutable not-run ledgers
are refused, the export profile's membership is untouched, the aggregate is
whatever the validator recomputes, and the one anchor that lives in Python
source is reported for a person to re-pin rather than rewritten here.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .beta_gate import (
    DEFAULT_RECORD_PATH,
    PinChange,
    RecomputeProposal,
    load_beta_gate,
    recompute_beta_gate,
)

_NO_CHANGE = 0
_CHANGES_PENDING = 1
_INVALID = 2


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

    recompute = subparsers.add_parser(
        "recompute",
        help=(
            "re-derive the mechanical digests this record and the v2 export "
            "profile pin, and print the diff to review"
        ),
        description=(
            "Re-derive every pin that is mechanical, and refuse the two that "
            "are attestations. The immutable not-run planning ledgers are "
            "never re-pinned, and _EXPORT_PROFILE_V2_SHA256 is reported for a "
            "person to re-pin by hand. Exits 0 when nothing moved, 1 when "
            "there is a change to apply or a constant to re-pin, and 2 when "
            "the request is refused."
        ),
    )
    recompute.add_argument(
        "--record",
        type=Path,
        default=None,
        help=(
            "aggregate record to re-pin; defaults to DEFAULT_RECORD_PATH "
            "inside --repository-root"
        ),
    )
    recompute.add_argument("--repository-root", type=Path, default=repository_root)
    recompute.add_argument(
        "--write",
        action="store_true",
        help="apply the re-derived bytes instead of only reporting them",
    )
    return parser


def _resolved_record(args: argparse.Namespace) -> Path:
    record: Path | None = args.record
    root: Path = args.repository_root
    return root / DEFAULT_RECORD_PATH if record is None else record


def _validate(args: argparse.Namespace) -> int:
    try:
        summary = load_beta_gate(
            _resolved_record(args),
            repository_root=args.repository_root,
        )
    except ValueError as error:
        print(f"pilot beta aggregate gate: INVALID: {error}", file=sys.stderr)
        return _INVALID
    print(json.dumps(summary.to_dict(), ensure_ascii=True, indent=2, sort_keys=True))
    return _NO_CHANGE


def _report(label: str, changes: Sequence[PinChange]) -> None:
    if not changes:
        return
    print(f"{label}:", file=sys.stderr)
    for change in changes:
        print(f"  {change.field}", file=sys.stderr)
        print(f"    - {change.recorded!r}", file=sys.stderr)
        print(f"    + {change.recomputed!r}", file=sys.stderr)


def _report_constant(proposal: RecomputeProposal) -> None:
    change = proposal.export_profile_constant_change
    if change is None:
        return
    print(
        "\nMAINTAINER ATTESTATION REQUIRED — this tool will not make this edit."
        f"\n  {change.field}"
        f"\n    - {change.recorded!r}"
        f"\n    + {change.recomputed!r}"
        "\n  This constant is the tamper-evidence anchor over the public/"
        "synthetic\n  export profile. Read the profile diff above, edit the "
        "one line, then\n  run `recompute` again to re-derive the record's own "
        "pins.",
        file=sys.stderr,
    )


def _apply(proposal: RecomputeProposal, root: Path, record: Path) -> int:
    """Write the re-derived bytes, restoring the originals if anything fails."""

    profile_path = root / proposal.export_profile_path
    restore: list[tuple[Path, bytes]] = []
    if proposal.export_profile_changes:
        restore.append((profile_path, profile_path.read_bytes()))
    if proposal.record_bytes is not None:
        restore.append((record, record.read_bytes()))
    try:
        if proposal.export_profile_changes:
            profile_path.write_bytes(proposal.export_profile_bytes)
        if proposal.record_bytes is not None:
            record.write_bytes(proposal.record_bytes)
        if not proposal.blocked_on_export_profile_constant:
            load_beta_gate(record, repository_root=root)
    except (OSError, ValueError) as error:
        for path, original in restore:
            path.write_bytes(original)
        print(
            f"pilot beta aggregate gate: REFUSED: {error}\n"
            "  Nothing was left written; the working tree is unchanged.",
            file=sys.stderr,
        )
        return _INVALID
    for path, _ in restore:
        print(f"wrote {path}", file=sys.stderr)
    if proposal.blocked_on_export_profile_constant:
        return _CHANGES_PENDING
    print("re-pinned record validates", file=sys.stderr)
    return _NO_CHANGE


def _recompute(args: argparse.Namespace) -> int:
    record = _resolved_record(args)
    try:
        proposal = recompute_beta_gate(record, repository_root=args.repository_root)
    except ValueError as error:
        print(f"pilot beta aggregate gate: REFUSED: {error}", file=sys.stderr)
        return _INVALID

    print(json.dumps(proposal.to_dict(), ensure_ascii=True, indent=2, sort_keys=True))
    _report("export profile v2 digests", proposal.export_profile_changes)
    _report("record pins", proposal.record_changes)
    _report_constant(proposal)

    if args.write:
        return _apply(proposal, args.repository_root, record)
    if not proposal.changed and not proposal.blocked_on_export_profile_constant:
        print("every pin already matches the tree; nothing to do", file=sys.stderr)
        return _NO_CHANGE
    print("\nre-run with --write to apply", file=sys.stderr)
    return _CHANGES_PENDING


def main(argv: Sequence[str] | None = None) -> int:
    """Return 0 for nothing to do, 1 for a pending change, 2 for invalid input."""

    default_root = Path(__file__).resolve().parents[2]
    args = _parser(default_root).parse_args(argv)
    if args.command == "recompute":
        return _recompute(args)
    return _validate(args)


if __name__ == "__main__":
    raise SystemExit(main())
