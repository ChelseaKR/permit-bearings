"""Run the deterministic matcher from a command line, offline.

    python -m permit_pathways.screening --facts facts.json --jurisdiction davis

Reachable before this, the matcher had three consumers -- the browser bundle,
the Python reference demo, and the optional AI service's internal re-run -- and
no command anyone outside the project could run. A permitting platform or a
jurisdiction's IT staff who want the "open evidence/verification layer" the
product context describes had no entry point and no contract.

This runs no model, opens no network connection, writes nothing, and imports
nothing from the optional AI extra beyond the dependency-free fact vocabulary
in :mod:`permit_pathways.ai.facts` (the same precedent
:mod:`permit_pathways.excerpt_survival` already sets with ``ai.corpus``).

Exit codes are the contract, and the middle one is the point:

``0``
    A result was produced and every material fact was answered.
``1``
    **Staff review needed.** A material fact is unknown, so no candidate route
    is reported. This is not an error, and it is deliberately not ``0``: a
    caller that treats a run with unanswered questions as a successful screening
    is publishing an absence as an answer, which is exactly what the withheld
    routes exist to prevent.
``2``
    The facts document is invalid, or the rule set or snapshot could not be
    read. Nothing is screened.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

from .dates import resolve_today
from .screening import load_rules, screen
from .screening_contract import (
    FactsDocumentError,
    build_result,
    validate_facts_document,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULES = ROOT / "data" / "rules"
DEFAULT_SOURCE_STATE = ROOT / "data" / "source-status" / "current.json"

EXIT_OK = 0
EXIT_NEEDS_STAFF_REVIEW = 1
EXIT_INVALID_INPUT = 2


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise FactsDocumentError([f"{label}: cannot read {path}: {error}"]) from error
    except json.JSONDecodeError as error:
        raise FactsDocumentError([f"{label}: {path} is not valid JSON: {error}"]) from (
            error
        )


def _facts_document(facts_path: Path, jurisdiction: str | None) -> dict[str, Any]:
    document = _load_json(facts_path, "--facts")
    if jurisdiction is not None:
        if not isinstance(document, dict):
            raise FactsDocumentError(["facts document must be a JSON object"])
        existing = document.get("jurisdiction")
        if existing is not None and existing != jurisdiction:
            # Refused rather than resolved. Either the file or the flag is wrong,
            # and screening under a jurisdiction the file does not name would
            # attribute the result to a place the applicant never described.
            raise FactsDocumentError(
                [
                    f"jurisdiction: --jurisdiction {jurisdiction!r} contradicts "
                    f"the facts document's {existing!r}"
                ]
            )
        document = {**document, "jurisdiction": jurisdiction}
    return validate_facts_document(document)


def _source_state(path: Path | None) -> dict[str, Any] | None:
    """The snapshot, or ``None`` when there is none to read.

    ``None`` reaches the envelope as nulls plus a notice. It is never turned
    into an empty snapshot: "we did not check" and "we checked and nothing had
    changed" are different findings and must not render the same.
    """
    if path is None:
        return None
    snapshot = _load_json(path, "--source-state")
    if not isinstance(snapshot, dict):
        raise FactsDocumentError([f"--source-state: {path} is not a JSON object"])
    return snapshot


def _console(result: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(
        f"{result['project_type']} in {result['jurisdiction']} "
        f"(as of {result['as_of']})"
    )
    lines.append(result["decision_boundary_statement"])
    lines.append("")

    if result["unresolved_facts"]:
        lines.append("STAFF REVIEW NEEDED — unanswered material facts:")
        for name in result["unresolved_facts"]:
            lines.append(f"  - {name}")
        lines.append("  No candidate route is reported while these are unanswered.")
    else:
        routes = ", ".join(result["candidate_routes"]) or "none"
        lines.append(f"Candidate route classes: {routes}")
    lines.append("")

    lines.append(f"Matched rules ({len(result['matched_rules'])}):")
    for rule in result["matched_rules"]:
        badge = (
            "dated source record"
            if rule["has_dated_source_record"]
            else "NO DATED SOURCE RECORD"
        )
        lines.append(f"  {rule['rule_id']} — {rule['pathway']} [{badge}]")
        lines.append(f"      {rule['citation']['source']} — {rule['citation']['url']}")
    lines.append("")

    source = result["source_state"]
    if source["available"]:
        lines.append(
            f"Source state: {source['snapshot_id']} "
            f"({source['receipt_status']}) checked {source['checked_at']}"
        )
    else:
        lines.append("Source state: not supplied")
    lines.append(f"Rule set: {result['rules_fingerprint']}")

    for notice in result["notices"]:
        lines.append(f"NOTICE: {notice}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="permit_pathways.screening",
        description=(
            "Screen one structured intake against the encoded, cited rule set. "
            "Deterministic and offline. This is not an eligibility "
            "determination, a completeness determination, or a jurisdiction "
            "approval."
        ),
    )
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument(
        "--jurisdiction",
        default=None,
        help="jurisdiction slug; must agree with the facts document if it names one",
    )
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument(
        "--source-state",
        type=Path,
        default=DEFAULT_SOURCE_STATE,
        help="source-watch snapshot; pass an empty value to screen without one",
    )
    parser.add_argument("--format", choices=("json", "console"), default="console")
    parser.add_argument(
        "--as-of",
        default=None,
        help="ISO date used for source-status evaluation; defaults to today",
    )
    args = parser.parse_args(argv)

    try:
        as_of = resolve_today(date.fromisoformat(args.as_of) if args.as_of else None)
    except ValueError as error:
        print(f"--as-of: {error}", file=sys.stderr)
        return EXIT_INVALID_INPUT

    try:
        intake = _facts_document(args.facts, args.jurisdiction)
        snapshot_path = (
            args.source_state if args.source_state and str(args.source_state) else None
        )
        if snapshot_path is not None and not snapshot_path.exists():
            # Absent is reported as absent. Falling back to "no snapshot" would
            # be right; silently substituting a stale committed one would not.
            snapshot_path = None
        snapshot = _source_state(snapshot_path)
        rules = load_rules(args.rules, today=as_of)
    except FactsDocumentError as error:
        for reason in error.reasons:
            print(reason, file=sys.stderr)
        return EXIT_INVALID_INPUT
    except (OSError, ValueError) as error:
        print(f"--rules: {error}", file=sys.stderr)
        return EXIT_INVALID_INPUT

    results = screen(intake, rules)
    result = build_result(
        intake=intake,
        rules=rules,
        results=results,
        as_of=as_of.isoformat(),
        source_state=snapshot,
    )

    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(_console(result))

    if result["decision_boundary"] == "needs_staff_review":
        return EXIT_NEEDS_STAFF_REVIEW
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - exercised through `main`
    raise SystemExit(main())
