"""Prepare or validate inert source-change release receipts.

The command never edits repository source state, clears a hold, invokes Git,
deploys, or rolls back.  Exit 0 means the selected receipt is complete and
valid (or the committed null templates are valid), exit 1 means a valid
``not_run`` or otherwise non-publishable result still needs human/external
action, and exit 2 means an input or output is invalid.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
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
    load_review_decisions,
    load_review_worklist,
)
from .screening import load_rules
from .source_release import (
    TEMPLATE_FINGERPRINTS_V1,
    ApprovalReceipt,
    PublicationReceipt,
    ReleaseContext,
    RollbackReceipt,
    build_release_context,
    encoded_receipt,
    load_approval_receipt,
    load_publication_receipt,
    load_rollback_receipt,
    prepared_receipts,
)
from .source_state import SourceStateSnapshot, load_source_state_snapshot

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATES = ROOT / "data" / "validation" / "source-change-release-v1"
DEFAULT_SOURCES = ROOT / "data" / "sources.json"
DEFAULT_RULES = ROOT / "data" / "rules"
DEFAULT_GOLDEN = ROOT / "data" / "golden" / "example.json"
DEFAULT_WORKFLOW = (
    ROOT / "data" / "readiness" / "workflows" / "woodland-preapproved-detached-adu.json"
)
DEFAULT_PACKET = (
    ROOT / "data" / "readiness" / "samples" / "woodland-preapproved-adu.json"
)
DEFAULT_REMEDIES = (
    ROOT / "data" / "readiness" / "remedies" / "woodland-preapproved-detached-adu.json"
)
DEFAULT_JOURNEY = ROOT / "data" / "journeys" / "woodland-preapproved-detached-adu.json"


def _add_release_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-state", type=Path, required=True)
    parser.add_argument("--worklist", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--remedies", type=Path, default=DEFAULT_REMEDIES)
    parser.add_argument("--journey", type=Path, default=DEFAULT_JOURNEY)


def _add_published_state_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--published-source-state", type=Path, default=None)
    parser.add_argument("--published-sources", type=Path, default=None)
    parser.add_argument("--published-rules", type=Path, default=None)
    parser.add_argument("--published-golden", type=Path, default=None)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="permit_pathways.source_release_cli",
        description=(
            "Prepare or validate non-mutating source-change approval, publication, "
            "and rollback receipts. A decision ledger cannot publish or clear a hold."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    templates = commands.add_parser("validate-templates")
    templates.add_argument(
        "--approval",
        type=Path,
        default=DEFAULT_TEMPLATES / "approval-template.json",
    )
    templates.add_argument(
        "--publication",
        type=Path,
        default=DEFAULT_TEMPLATES / "publication-template.json",
    )
    templates.add_argument(
        "--rollback",
        type=Path,
        default=DEFAULT_TEMPLATES / "rollback-template.json",
    )

    prepare = commands.add_parser("prepare")
    _add_release_inputs(prepare)
    prepare.add_argument("--release-id", required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)

    approval = commands.add_parser("validate-approval")
    _add_release_inputs(approval)
    approval.add_argument("--approval", type=Path, required=True)

    publication = commands.add_parser("validate-publication")
    _add_release_inputs(publication)
    _add_published_state_inputs(publication)
    publication.add_argument("--approval", type=Path, required=True)
    publication.add_argument("--publication", type=Path, required=True)

    rollback = commands.add_parser("validate-rollback")
    _add_release_inputs(rollback)
    _add_published_state_inputs(rollback)
    rollback.add_argument("--approval", type=Path, required=True)
    rollback.add_argument("--publication", type=Path, required=True)
    rollback.add_argument("--rollback", type=Path, required=True)
    rollback.add_argument("--restored-source-state", type=Path, default=None)
    rollback.add_argument("--restored-sources", type=Path, default=None)
    rollback.add_argument("--restored-rules", type=Path, default=None)
    rollback.add_argument("--restored-golden", type=Path, default=None)
    return parser


def _readiness_context(args: argparse.Namespace) -> ReadinessReviewContext:
    workflow = load_readiness_workflow(args.workflow, args.sources)
    packet = load_readiness_packet(args.packet, workflow)
    remedies = load_readiness_remedies(args.remedies, workflow)
    return ReadinessReviewContext(
        workflow=workflow,
        packet=packet,
        remedies=remedies,
        journeys=(load_journey_config(args.journey),),
    )


def _release_context(args: argparse.Namespace) -> ReleaseContext:
    snapshot = load_source_state_snapshot(
        args.source_state,
        args.sources,
        args.rules,
        args.golden,
        require_reviewed=False,
    )
    sources = load_sources(args.sources)
    rules = load_rules(args.rules)
    golden = load_golden(args.golden, rules)
    readiness = (_readiness_context(args),)
    worklist = load_review_worklist(
        args.worklist,
        snapshot,
        sources,
        rules,
        golden,
        readiness_contexts=readiness,
    )
    decisions = load_review_decisions(args.decisions, worklist)
    return build_release_context(
        snapshot,
        worklist,
        decisions,
        sources_path=args.sources,
        rules_path=args.rules,
        golden_path=args.golden,
        readiness_contexts=readiness,
    )


def _optional_state(
    path: Path | None,
    sources: Path,
    rules: Path,
    golden: Path,
) -> SourceStateSnapshot | None:
    if path is None:
        return None
    return load_source_state_snapshot(
        path,
        sources,
        rules,
        golden,
        require_reviewed=True,
    )


def _published_state(args: argparse.Namespace) -> SourceStateSnapshot | None:
    return _optional_state(
        args.published_source_state,
        args.published_sources or args.sources,
        args.published_rules or args.rules,
        args.published_golden or args.golden,
    )


def _restored_state(args: argparse.Namespace) -> SourceStateSnapshot | None:
    return _optional_state(
        args.restored_source_state,
        args.restored_sources or args.sources,
        args.restored_rules or args.rules,
        args.restored_golden or args.golden,
    )


def _write_durable_exclusive(path: Path, content: str) -> None:
    with path.open("x", encoding="utf-8") as destination:
        destination.write(content)
        destination.flush()
        os.fsync(destination.fileno())


def _write_package_exclusive(
    output_dir: Path,
    receipts: tuple[
        tuple[str, ApprovalReceipt | PublicationReceipt | RollbackReceipt], ...
    ],
) -> dict[str, Path]:
    parent = output_dir.parent.resolve(strict=True)
    destination = parent / output_dir.name
    try:
        destination.mkdir()
    except FileExistsError as error:
        raise ValueError(f"{destination}: output directory already exists") from error
    try:
        for name, receipt in receipts:
            _write_durable_exclusive(
                destination / f"{name}.json", encoded_receipt(receipt)
            )
        # The marker is deliberately durable and last. Consumers must treat a
        # directory without it as incomplete rather than as a prepared set.
        _write_durable_exclusive(
            destination / ".complete", "source-change-release-v1\n"
        )
        for directory_path in (destination, parent):
            directory = os.open(directory_path, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return {name: destination / f"{name}.json" for name, _ in receipts}


def _emit(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _receipt_summary(
    receipt: ApprovalReceipt | PublicationReceipt | RollbackReceipt,
) -> dict[str, object]:
    summary: dict[str, object] = {
        "receipt_fingerprint": receipt.fingerprint(),
        "receipt_id": receipt.receipt_id,
        "receipt_type": receipt.to_dict()["receipt_type"],
        "status": receipt.status,
        "external_evidence_authenticated": False,
        "validator_mutated_state": False,
    }
    if isinstance(receipt, ApprovalReceipt):
        summary.update(
            {
                "outcome": receipt.outcome,
                "approved_for_publication": (
                    receipt.status == "complete"
                    and receipt.outcome == "approved_for_publication"
                ),
            }
        )
    else:
        summary.update(
            {
                "hold_state": receipt.hold_state,
                "source_hold_clear": (
                    receipt.status == "complete"
                    and receipt.hold_state == "clear_in_source_state"
                ),
            }
        )
    return summary


def _validate_templates(args: argparse.Namespace) -> int:
    approval = load_approval_receipt(args.approval)
    publication = load_publication_receipt(args.publication)
    rollback = load_rollback_receipt(args.rollback)
    actual_fingerprints = {
        "approval": approval.fingerprint(),
        "publication": publication.fingerprint(),
        "rollback": rollback.fingerprint(),
    }
    if actual_fingerprints != dict(TEMPLATE_FINGERPRINTS_V1):
        raise ValueError(
            "schema-v1 templates do not match their immutable fingerprints"
        )
    _emit(
        {
            "approval": _receipt_summary(approval),
            "publication": _receipt_summary(publication),
            "rollback": _receipt_summary(rollback),
            "execution_status": "not_run",
            "supports_rehearsal_claim": False,
        }
    )
    return 0


def _prepare(args: argparse.Namespace) -> int:
    context = _release_context(args)
    approval, publication, rollback = prepared_receipts(args.release_id, context)
    paths = _write_package_exclusive(
        args.output_dir,
        (
            ("approval", approval),
            ("publication", publication),
            ("rollback", rollback),
        ),
    )
    _emit(
        {
            "execution_status": "not_run",
            "outputs": {name: str(path) for name, path in paths.items()},
            "release_binding": context.binding.to_dict(),
            "supports_approval_or_publication_claim": False,
        }
    )
    return 1


def _validate_approval(args: argparse.Namespace) -> int:
    receipt = load_approval_receipt(args.approval, _release_context(args))
    _emit(_receipt_summary(receipt))
    return (
        0
        if receipt.status == "complete"
        and receipt.outcome == "approved_for_publication"
        else 1
    )


def _load_publication_chain(
    args: argparse.Namespace,
) -> tuple[
    ReleaseContext,
    ApprovalReceipt,
    PublicationReceipt,
    SourceStateSnapshot | None,
]:
    context = _release_context(args)
    approval = load_approval_receipt(args.approval, context)
    published_snapshot = _published_state(args)
    publication = load_publication_receipt(
        args.publication,
        approval,
        context,
        published_snapshot,
        published_sources_path=args.published_sources or args.sources,
        published_rules_path=args.published_rules or args.rules,
        published_golden_path=args.published_golden or args.golden,
    )
    return context, approval, publication, published_snapshot


def _validate_publication(args: argparse.Namespace) -> int:
    _, _, receipt, _ = _load_publication_chain(args)
    _emit(_receipt_summary(receipt))
    return (
        0
        if receipt.status == "complete"
        and receipt.hold_state == "clear_in_source_state"
        else 1
    )


def _validate_rollback(args: argparse.Namespace) -> int:
    context, approval, publication, published_snapshot = _load_publication_chain(args)
    receipt = load_rollback_receipt(
        args.rollback,
        publication,
        context,
        _restored_state(args),
        approval=approval,
        published_snapshot=published_snapshot,
        published_sources_path=args.published_sources or args.sources,
        published_rules_path=args.published_rules or args.rules,
        published_golden_path=args.published_golden or args.golden,
        restored_sources_path=args.restored_sources or args.sources,
        restored_rules_path=args.restored_rules or args.rules,
        restored_golden_path=args.restored_golden or args.golden,
    )
    _emit(_receipt_summary(receipt))
    return (
        0
        if receipt.status == "complete"
        and receipt.hold_state == "clear_in_source_state"
        else 1
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate-templates":
            return _validate_templates(args)
        if args.command == "prepare":
            return _prepare(args)
        if args.command == "validate-approval":
            return _validate_approval(args)
        if args.command == "validate-publication":
            return _validate_publication(args)
        return _validate_rollback(args)
    except (OSError, ValueError) as error:
        print(f"source release: invalid input or output: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
