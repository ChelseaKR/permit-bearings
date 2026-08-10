"""Validate, predict, or score a bounded held-out scanner evaluation.

The committed plan is ``not_run``.  ``predict`` intentionally has no answer-key
argument; ``score`` requires a separately frozen prediction receipt.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .conformance_evaluation import (
    generate_blind_predictions,
    load_answer_key,
    load_case_set,
    load_evaluation_manifest,
    load_predictions,
    load_result,
    score_predictions,
    write_json_exclusive,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = Path("data/conformance/evaluations/heldout-v1/manifest.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="permit_pathways.conformance_evaluation_cli",
        description=(
            "Validate the unrun plan or create bounded raw scanner-evaluation "
            "receipts. This does not determine compliance or legal accuracy."
        ),
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate-plan")
    validate.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)

    predict = commands.add_parser(
        "predict",
        help="freeze binary scanner observations without loading an answer key",
    )
    predict.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    predict.add_argument("--cases", type=Path, required=True)
    predict.add_argument("--output", type=Path, required=True)
    predict.add_argument("--generated-at", required=True)
    predict.add_argument("--repository-commit-sha", required=True)

    score = commands.add_parser(
        "score",
        help="score a frozen prediction receipt against a reviewed answer key",
    )
    score.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    score.add_argument("--cases", type=Path, required=True)
    score.add_argument("--answer-key", type=Path, required=True)
    score.add_argument("--predictions", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    score.add_argument("--scored-at", required=True)
    score.add_argument("--repository-commit-sha", required=True)

    validate_result = commands.add_parser(
        "validate-result",
        help="reload and recompute a completed raw-count result receipt",
    )
    validate_result.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    validate_result.add_argument("--cases", type=Path, required=True)
    validate_result.add_argument("--answer-key", type=Path, required=True)
    validate_result.add_argument("--predictions", type=Path, required=True)
    validate_result.add_argument("--result", type=Path, required=True)
    return parser


def _under_root(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _emit(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    try:
        manifest_path = _under_root(root, args.manifest)
        manifest = load_evaluation_manifest(manifest_path, root)
        if args.command == "validate-plan":
            _emit(
                {
                    "active_check_count": len(manifest.check_ids),
                    "evaluation_id": manifest.evaluation_id,
                    "execution_status": "not_run",
                    "result_present": False,
                    "supports_accuracy_claim": False,
                }
            )
            return 0

        cases_path = _under_root(root, args.cases)
        cases = load_case_set(cases_path, manifest)
        if args.command == "predict":
            output = _under_root(root, args.output)
            predictions = generate_blind_predictions(
                manifest,
                cases,
                root,
                generated_at=args.generated_at,
                repository_commit_sha=args.repository_commit_sha,
            )
            receipt_sha = write_json_exclusive(output, predictions.payload)
            _emit(
                {
                    "evaluation_id": manifest.evaluation_id,
                    "machine_abstain": 0,
                    "output": str(output),
                    "predictions_sha256": receipt_sha,
                    "reference_labels_loaded": False,
                }
            )
            return 0

        answer_key = load_answer_key(
            _under_root(root, args.answer_key), manifest, cases
        )
        predictions = load_predictions(
            _under_root(root, args.predictions), manifest, cases, root
        )
        if args.command == "validate-result":
            receipt = load_result(
                _under_root(root, args.result),
                manifest,
                cases,
                answer_key,
                predictions,
            )
            _emit(
                {
                    "evaluation_id": manifest.evaluation_id,
                    "result_sha256": receipt.raw_sha256,
                    "status": receipt.payload["status"],
                    "supports_accuracy_claim": False,
                }
            )
            return 0
        result = score_predictions(
            manifest,
            cases,
            answer_key,
            predictions,
            scored_at=args.scored_at,
            repository_commit_sha=args.repository_commit_sha,
        )
        output = _under_root(root, args.output)
        receipt_sha = write_json_exclusive(output, result)
        _emit(
            {
                "evaluation_id": manifest.evaluation_id,
                "output": str(output),
                "result_sha256": receipt_sha,
                "status": result["status"],
                "supports_accuracy_claim": False,
            }
        )
        return 0
    except (OSError, ValueError) as error:
        print(
            f"conformance evaluation: invalid input or output: {error}", file=sys.stderr
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
