"""Verification harness.

Reports which rules have dated source evidence inside the configured review
window, which have gone stale, which lack a dated source record, and whether
the structured golden scenarios still produce the expected pathways.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from ..dates import SOURCE_REVIEW_WINDOW_DAYS, resolve_today
from ..screening import Rule, load_rules, screen

DEFAULT_MAX_AGE_DAYS = SOURCE_REVIEW_WINDOW_DAYS
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_GOLDEN_KEYS = {
    "case_id",
    "question",
    "intake",
    "expected_rule_ids",
    "rule_dependency_ids",
}


@dataclass
class GoldenCase:
    case_id: str
    question: str
    intake: dict[str, Any]
    expected_rule_ids: list[str]
    rule_dependency_ids: list[str]


@dataclass
class VerificationReport:
    checked_on: str
    verified: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)
    golden_passed: list[str] = field(default_factory=list)
    golden_failed: list[str] = field(default_factory=list)

    @property
    def automated_checks_pass(self) -> bool:
        """Whether bounded source-age and structured-regression checks pass.

        This deliberately does not claim legal accuracy, human review, or
        jurisdiction approval. Those are separate verification levels.
        """

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


def _golden_rule_ids(
    value: Any,
    field: str,
    *,
    known_rule_ids: set[str],
    sorted_unique: bool,
) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and _IDENTIFIER.fullmatch(item) for item in value
    ):
        raise ValueError(f"{field}: expected stable rule IDs")
    if len(value) != len(set(value)):
        raise ValueError(f"{field}: duplicate rule IDs are not allowed")
    if sorted_unique and (not value or value != sorted(value)):
        raise ValueError(f"{field}: expected a non-empty sorted unique list")
    unknown = sorted(set(value) - known_rule_ids)
    if unknown:
        raise ValueError(f"{field}: unknown rule IDs: {', '.join(unknown)}")
    return list(value)


def _golden_case(
    value: Any,
    field: str,
    *,
    known_rule_ids: set[str],
    seen_case_ids: set[str],
) -> GoldenCase:
    if not isinstance(value, dict) or set(value) != _GOLDEN_KEYS:
        raise ValueError(f"{field}: expected exactly the Golden case fields")
    case_id = value["case_id"]
    if not isinstance(case_id, str) or not _IDENTIFIER.fullmatch(case_id):
        raise ValueError(f"{field}.case_id: expected a stable identifier")
    if case_id in seen_case_ids:
        raise ValueError(f"{field}.case_id: duplicate Golden case ID")
    seen_case_ids.add(case_id)
    question = value["question"]
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"{field}.question: expected non-blank text")
    intake = value["intake"]
    if not isinstance(intake, dict):
        raise ValueError(f"{field}.intake: expected an object")
    expected = _golden_rule_ids(
        value["expected_rule_ids"],
        f"{field}.expected_rule_ids",
        known_rule_ids=known_rule_ids,
        sorted_unique=False,
    )
    dependencies = _golden_rule_ids(
        value["rule_dependency_ids"],
        f"{field}.rule_dependency_ids",
        known_rule_ids=known_rule_ids,
        sorted_unique=True,
    )
    missing_dependencies = sorted(set(expected) - set(dependencies))
    if missing_dependencies:
        raise ValueError(
            f"{field}.rule_dependency_ids: must include expected rule IDs: "
            + ", ".join(missing_dependencies)
        )
    return GoldenCase(
        case_id=case_id,
        question=question.strip(),
        intake=dict(intake),
        expected_rule_ids=expected,
        rule_dependency_ids=dependencies,
    )


def load_golden(path: Path, rules: Sequence[Rule]) -> list[GoldenCase]:
    """Load cases with explicit positive and negative rule dependencies."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: Golden cases could not be loaded") from error
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected a list of Golden cases")
    known_rule_ids = {rule.rule_id for rule in rules}
    if len(known_rule_ids) != len(rules):
        raise ValueError("canonical rules contain duplicate rule IDs")

    cases: list[GoldenCase] = []
    seen_case_ids: set[str] = set()
    for index, value in enumerate(payload):
        field = f"{path}[{index}]"
        cases.append(
            _golden_case(
                value,
                field,
                known_rule_ids=known_rule_ids,
                seen_case_ids=seen_case_ids,
            )
        )
    return cases


def verify_rules(
    rules_path: Path,
    golden_path: Path,
    today: date | None = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    changed_source_ids: list[str] | None = None,
    *,
    changed_sources: list[str] | None = None,
) -> VerificationReport:
    """Mark exact source dependencies stale after a source changes.

    ``changed_sources`` remains as a keyword-only compatibility alias; its
    values are stable source IDs, never citation substrings.
    """
    if changed_source_ids is not None and changed_sources is not None:
        raise ValueError("pass changed_source_ids or changed_sources, not both")
    as_of = resolve_today(today)
    rules = load_rules(rules_path, today=as_of)
    golden = load_golden(golden_path, rules)
    report = VerificationReport(checked_on=as_of.isoformat())
    changed = set(
        changed_source_ids
        if changed_source_ids is not None
        else (changed_sources or [])
    )

    for rule in rules:
        cite = rule.citation
        if changed.intersection(rule.source_dependencies):
            report.stale.append(rule.rule_id)
        elif not cite.is_verified:
            report.unverified.append(rule.rule_id)
        elif cite.is_stale(max_age_days, as_of):
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
