"""What the encoded rules attach to each answer, one fact at a time.

At a counter the question is rarely "am I eligible". It is "what if the lot
were in a single-family zone", "what if I converted the garage instead", "what
if I could answer the historic question". The matcher in
:mod:`permit_pathways.screening` is a pure function of the intake and the rule
set, so those questions are computable: re-run it once per allowed value of one
fact and report what the rule set does differently.

This is decision support without prediction. Nothing here says which answer is
true, which answer is better, or what the applicant should do. It enumerates
the consequences the encoded, cited rules already attach to each answer, and it
inherits every boundary the screening envelope carries:

* **A branch with a material unknown still withholds its routes.** Perturbing
  one fact does not answer the others. A branch whose intake still has an
  unanswered material fact reports ``needs_staff_review`` and an empty
  ``candidate_routes``, exactly as a real screening of that intake would.

* **A fact read by a rule on source hold gets no delta at all.** When a rule
  that reads the fact depends on a source the snapshot records as changed since
  it was last reviewed, the four delta lists are ``null`` -- not ``[]``. An
  empty delta list reads as "changing this answer changes nothing", which is a
  finding about the rule set; we do not have it while the rules under it are on
  hold. ``null`` says we did not compute it and names why.

  The hold set is deliberately fail-closed: every in-jurisdiction rule with a
  criterion on the fact counts, including one that cannot match this project
  type as encoded today. A hold says the *encoding* may no longer match its
  source, so narrowing the set to rules that match under the current encoding
  would assume exactly what the hold puts in doubt.

* **A fact whose alternatives all agree is reported, not dropped.**
  ``no_rule_reads_this_differently`` is a result. Omitting the fact would leave
  a reader to guess whether it was checked.

Single-fact perturbation only, by construction: there is no search here for a
best path, and no combination of two changes. ``project_type`` and
``jurisdiction`` are not perturbed either -- they are not facts the rule set
reads as criteria on one project, they decide *which* project is being
screened, and moving them would answer a different question than the one asked.

Order carries no ranking: facts come in the browser form's order and values in
the order the vocabulary declares them, so nothing about the output presents
one branch as preferable to another.

Dependency-free, deterministic, offline. No model, no clock, no filesystem.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .ai.facts import FIELDS_BY_NAME, material_fields
from .screening import Rule, screen
from .screening_contract import build_result, unresolved_facts

#: Bumped when this payload's shape changes in a way a consumer must notice.
#: Deliberately its own version: the screening envelope's ``schema_version``
#: describes a different document, and moving it for a change here would tell
#: every screening consumer their contract had changed when it had not.
WHAT_IF_SCHEMA_VERSION = 1

WHAT_IF_BOUNDARY_STATEMENT = (
    "This enumerates what the encoded rules attach to each allowed answer, one "
    "fact at a time. It does not say which answer is true, it does not rank "
    "answers, it is not advice, and answering differently here changes nothing "
    "about the project or about any application."
)

#: The only reason a delta is withheld today. Named rather than a bare boolean
#: so a second reason can be added without a consumer having to guess which one
#: it is looking at.
WITHHELD_SOURCE_HOLD = "source_on_review_hold"


def held_rule_ids(
    rules: Iterable[Rule], changed_source_ids: Sequence[str] | None
) -> frozenset[str]:
    """Rules whose sources the snapshot records as changed since review.

    ``None`` means the snapshot did not report the list. That is not the same
    finding as an empty list and is not treated as one: with no list, nothing
    is known to be on hold, and the caller's notices already say the snapshot
    was silent about it.
    """
    if not changed_source_ids:
        return frozenset()
    changed = set(changed_source_ids)
    return frozenset(
        rule.rule_id for rule in rules if changed.intersection(rule.source_dependencies)
    )


def applicable_rules(rules: Iterable[Rule], jurisdiction: Any) -> list[Rule]:
    """The rules a screening in this jurisdiction could reach.

    Same scope filter :func:`permit_pathways.screening.screen` applies, kept
    here because a what-if asks about rules that do *not* match yet.
    """
    return [
        rule for rule in rules if rule.jurisdiction_scope in ("statewide", jurisdiction)
    ]


def rules_reading(rules: Iterable[Rule], field: str) -> list[str]:
    """Ids of the rules with a criterion on ``field``, sorted for stability."""
    return sorted(
        rule.rule_id
        for rule in rules
        if any(criterion["field"] == field for criterion in rule.criteria)
    )


def _screened(intake: Mapping[str, Any], rules: Sequence[Rule]) -> dict[str, Any]:
    """One branch's matched rules, boundary, and routes.

    ``candidate_routes`` is withheld exactly the way ``build_result`` withholds
    it, because a route named while a material fact is unknown is a route the
    encoded rules do not support yet -- and a what-if branch is a screening.
    """
    matched = screen(dict(intake), list(rules))
    unresolved = unresolved_facts(intake)
    rule_ids = sorted(result.rule.rule_id for result in matched)
    routes = (
        [] if unresolved else sorted({result.rule.route_class for result in matched})
    )
    return {
        "matched_rule_ids": rule_ids,
        "candidate_routes": routes,
        "unresolved_facts": list(unresolved),
        "decision_boundary": (
            "needs_staff_review" if unresolved else "candidate_rules_only"
        ),
    }


def _delta(before: Sequence[str], after: Sequence[str]) -> tuple[list[str], list[str]]:
    """(added, removed), sorted. Both lists, never one list of signed entries."""
    return (
        sorted(set(after) - set(before)),
        sorted(set(before) - set(after)),
    )


def _alternative(
    *,
    intake: Mapping[str, Any],
    field: str,
    value: str,
    rules: Sequence[Rule],
    baseline: Mapping[str, Any],
    withheld: bool,
) -> dict[str, Any]:
    branch = _screened({**intake, field: value}, rules)
    rules_added, rules_removed = _delta(
        baseline["matched_rule_ids"], branch["matched_rule_ids"]
    )
    routes_added, routes_removed = _delta(
        baseline["candidate_routes"], branch["candidate_routes"]
    )
    return {
        "value": value,
        "is_current_answer": intake.get(field) == value,
        # Independent of the rule set: which facts are still unanswered is a
        # property of the intake alone, so a hold cannot make it unknowable.
        "decision_boundary": branch["decision_boundary"],
        "unresolved_facts": branch["unresolved_facts"],
        # null, never [], when withheld. See the module docstring.
        "candidate_routes": None if withheld else branch["candidate_routes"],
        "rules_added": None if withheld else rules_added,
        "rules_removed": None if withheld else rules_removed,
        "routes_added": None if withheld else routes_added,
        "routes_removed": None if withheld else routes_removed,
    }


def _fact_entry(
    *,
    intake: Mapping[str, Any],
    field: str,
    rules: Sequence[Rule],
    in_scope: Sequence[Rule],
    baseline: Mapping[str, Any],
    held: frozenset[str],
) -> dict[str, Any]:
    reading = rules_reading(in_scope, field)
    held_reading = sorted(rule_id for rule_id in reading if rule_id in held)
    withheld = bool(held_reading)
    alternatives = [
        _alternative(
            intake=intake,
            field=field,
            value=value,
            rules=rules,
            baseline=baseline,
            withheld=withheld,
        )
        for value in FIELDS_BY_NAME[field].values
    ]
    if withheld:
        unchanged: bool | None = None
    else:
        unchanged = all(
            not alternative["rules_added"] and not alternative["rules_removed"]
            for alternative in alternatives
        )
    return {
        "field": field,
        "current_value": intake.get(field, "unknown"),
        "known": intake.get(field, "unknown") != "unknown",
        "read_by_rule_ids": reading,
        # A result, not an omission: a fact every rule reads the same way is
        # listed saying so rather than dropped from the output.
        "no_rule_reads_this_differently": unchanged,
        "deltas_withheld": WITHHELD_SOURCE_HOLD if withheld else None,
        "rules_on_source_hold": held_reading,
        "alternatives": alternatives,
    }


def what_if(
    *,
    intake: Mapping[str, Any],
    rules: Sequence[Rule],
    as_of: str,
    source_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Per-fact, per-value rule deltas for one validated intake.

    ``intake`` must already have passed
    :func:`permit_pathways.screening_contract.validate_facts_document`; this
    function screens, it does not police.
    """
    baseline_envelope = build_result(
        intake=intake,
        rules=rules,
        results=screen(dict(intake), list(rules)),
        as_of=as_of,
        source_state=source_state,
    )
    baseline = _screened(intake, rules)
    in_scope = applicable_rules(rules, intake.get("jurisdiction"))
    held = held_rule_ids(
        in_scope, baseline_envelope["source_state"]["changed_source_ids"]
    )

    facts = [
        _fact_entry(
            intake=intake,
            field=field,
            rules=rules,
            in_scope=in_scope,
            baseline=baseline,
            held=held,
        )
        for field in material_fields(str(intake.get("project_type", "")))
    ]

    notices = list(baseline_envelope["notices"])
    withheld_fields = [fact["field"] for fact in facts if fact["deltas_withheld"]]
    if withheld_fields:
        notices.append(
            "No delta is reported for "
            + ", ".join(withheld_fields)
            + ": a rule that reads "
            + ("each of those facts" if len(withheld_fields) > 1 else "that fact")
            + " depends on a source recorded as changed since it was last "
            "reviewed. An empty delta would read as 'this answer changes "
            "nothing', which is a finding this run cannot make."
        )

    return {
        "what_if_schema_version": WHAT_IF_SCHEMA_VERSION,
        "as_of": as_of,
        "jurisdiction": intake.get("jurisdiction"),
        "project_type": intake.get("project_type"),
        "decision_boundary_statement": baseline_envelope["decision_boundary_statement"],
        "what_if_boundary_statement": WHAT_IF_BOUNDARY_STATEMENT,
        "baseline": baseline,
        "facts": facts,
        "rules_fingerprint": baseline_envelope["rules_fingerprint"],
        "source_state": baseline_envelope["source_state"],
        "notices": notices,
    }


__all__ = [
    "WHAT_IF_BOUNDARY_STATEMENT",
    "WHAT_IF_SCHEMA_VERSION",
    "WITHHELD_SOURCE_HOLD",
    "applicable_rules",
    "held_rule_ids",
    "rules_reading",
    "what_if",
]


if __name__ == "__main__":  # pragma: no cover - a thin alias for the CLI module
    # Same split `screening`/`screening_cli` uses: argparse and console
    # rendering do not belong in the module the browser port is checked
    # against.
    from .what_if_cli import main

    raise SystemExit(main())
