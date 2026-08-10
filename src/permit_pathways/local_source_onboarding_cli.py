"""Validate a portable local-source onboarding intake.

This command is read-only.  A successful validation can report only
``not_run``, ``collection_in_progress``, or ``prepared_for_review``; it cannot
review, approve, encode, or publish a local layer.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from .local_source_onboarding import load_local_source_onboarding

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE = Path("data/onboarding/local-source-intake-template.json")


def _date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from error
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="permit_pathways.local_source_onboarding_cli",
        description=(
            "Validate an unreviewed local-source intake. Success does not "
            "establish operative law, local coverage, review, or approval."
        ),
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--input", type=Path, default=DEFAULT_TEMPLATE)
    validate.add_argument(
        "--as-of",
        type=_date,
        default=None,
        help="date for future-date checks; defaults to current UTC date",
    )
    return parser


def _under_root(root: Path, path: Path) -> Path:
    candidate = (path if path.is_absolute() else root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("input path must resolve inside --root") from error
    return candidate


def main(argv: Sequence[str] | None = None) -> int:
    """Validate the selected intake and emit a bounded JSON summary."""

    args = _parser().parse_args(argv)
    root = args.root.resolve()
    try:
        intake = load_local_source_onboarding(
            _under_root(root, args.input),
            today=args.as_of,
        )
    except (OSError, ValueError) as error:
        print(f"local-source onboarding: invalid input: {error}", file=sys.stderr)
        return 2

    historical_replay = args.as_of is not None
    payload: dict[str, object] = {
        "artifact_fingerprint": intake.artifact_fingerprint,
        "collected_source_requirement_count": (
            intake.collected_source_requirement_count
        ),
        "local_layer_status": intake.local_layer_status,
        "earliest_reverification_due_on": (intake.earliest_reverification_due_on),
        "onboarding_id": intake.onboarding_id,
        "operative_passage_count": intake.operative_passage_count,
        "ready_for_review": intake.ready_for_review and not historical_replay,
        "ready_for_review_as_of": intake.ready_for_review,
        "record_status": intake.status,
        "review_status": intake.review_status,
        "source_count": intake.source_count,
        "source_requirement_count": intake.source_requirement_count,
        "supports_approval_claim": False,
        "supports_local_layer_claim": False,
        "supports_review_claim": False,
        "validated_as_of": intake.validated_as_of,
        "validation_mode": ("historical_replay" if historical_replay else "current"),
    }
    sys.stdout.write(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
