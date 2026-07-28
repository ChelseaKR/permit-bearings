"""Verification harness.

Reports which rules have dated source evidence inside the configured review
window, which have gone stale, which lack a dated source record, and whether
the structured golden scenarios still produce the expected pathways.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from ..screening import Rule, load_rules, screen

DEFAULT_MAX_AGE_DAYS = 180  # roughly one legislative cycle between re-checks


@dataclass
class GoldenCase:
    case_id: str
    question: str
    intake: dict
    expected_rule_ids: list[str]


@dataclass
class VerificationReport:
    checked_on: str
    verified: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)
    golden_passed: list[str] = field(default_factory=list)
    golden_failed: list[str] = field(default_factory=list)

    @property
    def trustworthy(self) -> bool:
        return not self.stale and not self.unverified and not self.golden_failed

    def summary(self) -> str:
        lines = [
            f"Verification report ({self.checked_on})",
            f"  rules inside source-review window: {len(self.verified)}",
            f"  rules stale:            {len(self.stale)}",
            f"  rules without dated source record: {len(self.unverified)}",
            f"  golden cases passing:   {len(self.golden_passed)}",
            f"  golden cases failing:   {len(self.golden_failed)}",
        ]
        for case_id in self.golden_failed:
            lines.append(f"    FAIL {case_id}")
        return "\n".join(lines)


def load_golden(path: Path) -> list[GoldenCase]:
    return [GoldenCase(**record) for record in json.loads(path.read_text())]


def verify_rules(
    rules_path: Path,
    golden_path: Path,
    today: date,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    changed_sources: list[str] | None = None,
) -> VerificationReport:
    """`changed_sources` marks sources known (or simulated) to have changed
    since rules were last verified — e.g. a code section renumbered by new
    legislation. Any rule citing a matching source is stale regardless of
    its verification date: verification against superseded text is no
    verification at all."""
    rules = load_rules(rules_path)
    golden = load_golden(golden_path)
    report = VerificationReport(checked_on=today.isoformat())
    changed = changed_sources or []

    for rule in rules:
        cite = rule.citation
        if any(marker in cite.source or marker in cite.url for marker in changed):
            report.stale.append(rule.rule_id)
        elif not cite.is_verified:
            report.unverified.append(rule.rule_id)
        elif cite.is_stale(max_age_days, today):
            report.stale.append(rule.rule_id)
        else:
            report.verified.append(rule.rule_id)

    for case in golden:
        got = sorted(r.rule.rule_id for r in screen(case.intake, rules))
        if got == sorted(case.expected_rule_ids):
            report.golden_passed.append(case.case_id)
        else:
            report.golden_failed.append(case.case_id)

    return report
