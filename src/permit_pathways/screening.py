"""Deterministic pathway screening.

Rules are data, not code: each rule is a JSON record carrying its own
citation and verification status. The engine never emits a result whose
rule lacks a citation — an uncited rule is a schema error, not a softer
answer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

ROUTE_CLASSES = ("ministerial", "discretionary", "mixed")
_OPS = {
    "eq": lambda a, b: a == b,
    "lte": lambda a, b: a is not None and a <= b,
    "gte": lambda a, b: a is not None and a >= b,
    "in": lambda a, b: a in b,
}


@dataclass(frozen=True)
class Citation:
    """The source a rule encodes. `verified_on` is None until the rule text
    has been checked against the cited source; the harness reports such
    rules as UNVERIFIED and the engine labels their results accordingly."""

    source: str          # e.g. "Gov. Code § 65852.2" or an HCD document title
    url: str
    excerpt_sha256: str | None = None
    verified_on: str | None = None  # ISO date of last human verification

    @property
    def is_verified(self) -> bool:
        return self.verified_on is not None

    def is_stale(self, max_age_days: int, today: date) -> bool:
        if not self.is_verified:
            return True
        verified = date.fromisoformat(self.verified_on)
        return (today - verified).days > max_age_days


@dataclass(frozen=True)
class Rule:
    rule_id: str
    pathway: str              # e.g. "ADU ministerial approval"
    route_class: str          # ministerial | discretionary | mixed
    jurisdiction_scope: str   # "statewide" or a jurisdiction slug
    criteria: list[dict[str, Any]]   # [{"field", "op", "value"}, ...]
    citation: Citation
    required_documents: list[str] = field(default_factory=list)
    notes: str = ""

    def matches(self, intake: dict[str, Any]) -> bool:
        for c in self.criteria:
            op = _OPS[c["op"]]
            if not op(intake.get(c["field"]), c["value"]):
                return False
        return True


@dataclass(frozen=True)
class PathwayResult:
    rule: Rule
    verified: bool

    def summary(self) -> str:
        badge = "verified" if self.verified else "UNVERIFIED — pending source check"
        return (
            f"{self.rule.pathway} ({self.rule.route_class}) — "
            f"{self.rule.citation.source} [{badge}]"
        )


def load_rules(path: Path) -> list[Rule]:
    rules = []
    for record in json.loads(path.read_text()):
        citation = Citation(**record.pop("citation"))
        rule = Rule(citation=citation, **record)
        if rule.route_class not in ROUTE_CLASSES:
            raise ValueError(f"{rule.rule_id}: unknown route_class {rule.route_class!r}")
        if not rule.citation.source or not rule.citation.url:
            raise ValueError(f"{rule.rule_id}: rule has no citation")
        rules.append(rule)
    return rules


def screen(intake: dict[str, Any], rules: list[Rule]) -> list[PathwayResult]:
    """Return candidate pathways for a structured intake. Results from
    unverified rules are still returned — flagged, never hidden — because
    hiding them would misrepresent coverage."""
    jurisdiction = intake.get("jurisdiction")
    applicable = [
        r for r in rules
        if r.jurisdiction_scope in ("statewide", jurisdiction)
    ]
    return [
        PathwayResult(rule=r, verified=r.citation.is_verified)
        for r in applicable
        if r.matches(intake)
    ]
