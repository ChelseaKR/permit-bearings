"""Explore one fact at a time from a command line, offline.

    python -m permit_pathways.what_if --facts facts.json --jurisdiction woodland

Same inputs, same rule set and same snapshot as
``python -m permit_pathways.screening``; a different question. The screening
command answers "what do the encoded rules say about this project". This one
answers "which rules and routes would change if one answer were different",
for every allowed value of every material fact, including the ones the
applicant left unknown.

It runs no model, opens no network connection, and writes nothing.

Exit codes are the same contract the screening command publishes, for the
same reason:

``0``
    Deltas were produced and every material fact in the submitted intake was
    answered.
``1``
    **Staff review needed.** The submitted intake still has an unanswered
    material fact, so its baseline reports no candidate route. The branches are
    still printed -- that is the point of the command -- but the run is not a
    completed screening and does not exit as one.
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
from .screening import load_rules
from .screening_cli import (
    DEFAULT_RULES,
    DEFAULT_SOURCE_STATE,
    EXIT_INVALID_INPUT,
    EXIT_NEEDS_STAFF_REVIEW,
    EXIT_OK,
    _facts_document,
    _source_state,
)
from .screening_contract import FactsDocumentError
from .what_if import what_if


def _alternative_lines(alternative: dict[str, Any]) -> list[str]:
    marker = "  (current answer)" if alternative["is_current_answer"] else ""
    lines = [f"  {alternative['value']}{marker}"]
    if alternative["rules_added"] is None:
        lines.append("      delta withheld — a rule reading this fact is on hold")
    else:
        for label, key in (
            ("rules that would apply", "rules_added"),
            ("rules that would stop applying", "rules_removed"),
            ("route classes that would appear", "routes_added"),
            ("route classes that would drop", "routes_removed"),
        ):
            if alternative[key]:
                lines.append(f"      {label}: {', '.join(alternative[key])}")
        if not any(
            alternative[key]
            for key in (
                "rules_added",
                "rules_removed",
                "routes_added",
                "routes_removed",
            )
        ):
            lines.append("      no rule or route changes")
    if alternative["decision_boundary"] == "needs_staff_review":
        lines.append(
            "      needs staff review — still unanswered: "
            + ", ".join(alternative["unresolved_facts"])
        )
        lines.append("      no candidate route is reported for this answer")
    return lines


def _fact_lines(fact: dict[str, Any]) -> list[str]:
    current = fact["current_value"] if fact["known"] else "unanswered"
    lines = [f"{fact['field']} (now: {current})"]
    if fact["deltas_withheld"]:
        lines.append(
            "  Deltas withheld ("
            + fact["deltas_withheld"]
            + "): "
            + ", ".join(fact["rules_on_source_hold"])
        )
    elif fact["no_rule_reads_this_differently"]:
        lines.append("  No rule reads this differently for this project.")
    for alternative in fact["alternatives"]:
        lines.extend(_alternative_lines(alternative))
    return lines


def _console(payload: dict[str, Any]) -> str:
    baseline = payload["baseline"]
    lines = [
        f"What-if for {payload['project_type']} in {payload['jurisdiction']} "
        f"(as of {payload['as_of']})",
        payload["decision_boundary_statement"],
        payload["what_if_boundary_statement"],
        "",
        "Now: "
        + (", ".join(baseline["candidate_routes"]) or "no candidate route reported")
        + f" — {len(baseline['matched_rule_ids'])} matched rules",
    ]
    if baseline["unresolved_facts"]:
        lines.append(
            "  Staff review needed; unanswered: "
            + ", ".join(baseline["unresolved_facts"])
        )
    lines.append("")
    for fact in payload["facts"]:
        lines.extend(_fact_lines(fact))
        lines.append("")
    lines.append(f"Rule set: {payload['rules_fingerprint']}")
    lines.extend(f"NOTICE: {notice}" for notice in payload["notices"])
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="permit_pathways.what_if",
        description=(
            "Enumerate what the encoded, cited rules attach to each allowed "
            "answer, one fact at a time. Deterministic and offline. This is "
            "not advice, not a ranking, and not an eligibility determination."
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
        help="source-watch snapshot; pass an empty value to run without one",
    )
    parser.add_argument("--format", choices=("json", "console"), default="console")
    parser.add_argument(
        "--as-of",
        default=None,
        help="ISO date used for source-status evaluation; defaults to today",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)

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

    payload = what_if(
        intake=intake,
        rules=rules,
        as_of=as_of.isoformat(),
        source_state=snapshot,
    )

    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_console(payload))

    if payload["baseline"]["decision_boundary"] == "needs_staff_review":
        return EXIT_NEEDS_STAFF_REVIEW
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - exercised through `main`
    raise SystemExit(main())
