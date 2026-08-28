"""Cross-runtime parity verdicts for the deterministic matching core.

The fixture corpus in ``data/parity/fixtures.json`` carries inputs only.
This module computes the Python engine's verdicts; ``tests/test_parity.py``
assembles the browser's verdicts from the pure-logic zone of
``assets/demo.js``. The parity test fails unless the two verdict documents
are identical.

Every Python verdict comes from the function production screening uses:
``screening._same_scalar``, ``screening._criterion_matches``,
``screening.screen`` over real ``Rule`` objects, and
``screening.Citation.is_stale``. Nothing here reimplements engine semantics.
A parity check that compared two reimplementations could stay green through
a regression in the shipped engine, which is the failure mode this corpus
exists to rule out.

Each staleness case pins its own evaluation date and both runtimes are given
that date. A corpus whose verdicts move with the wall clock agrees only on
the day it was written.

Two known cross-runtime boundaries are deliberately outside the corpus,
because the fixture loader, like ``load_rules``, rejects them before either
runtime sees them. They are recorded here rather than silently omitted:

* A rule with an empty ``criteria`` list. Python's ``Rule.matches`` is
  vacuously true; the browser's ``matches`` requires at least one criterion.
  ``screening._criteria`` rejects the record at load time.
* A citation whose ``verified_on`` is present but is not an ISO date. The
  browser reports ``unverified``; ``Citation.is_stale`` raises.
  ``screening._citation`` rejects the record at load time.
* A criterion whose shape the loader would reject, such as ``eq`` against a
  blank string. The browser re-validates criterion shape inside ``matches``;
  Python validates it once in ``screening._validate_criterion`` at load time
  and ``Rule.matches`` trusts the result. ``_validate_screen_rule`` below
  holds the corpus to well-formed criteria so this boundary stays a stated
  scope limit rather than an accident.

Loader-level schema validation is likewise out of scope here; it is covered
by the rule-schema tests.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from .screening import Citation, Rule, _criterion_matches, _same_scalar, screen

TOP_LEVEL_KEYS = {
    "schema_version",
    "description",
    "scalar_cases",
    "criterion_cases",
    "screen_cases",
    "staleness_cases",
}
_SCALAR_CASE_KEYS = {"case_id", "left", "right"}
_CRITERION_CASE_KEYS = {"case_id", "op", "actual", "expected"}
_CRITERION_ABSENT_CASE_KEYS = {"case_id", "op", "actual_absent", "expected"}
_CRITERION_OPTIONAL_KEYS = {"expected_ill_shaped"}
_SCREEN_CASE_KEYS = {"case_id", "intake", "rules"}
_SCREEN_RULE_KEYS = {"rule_id", "jurisdiction_scope", "criteria"}
_CRITERION_KEYS = {"field", "op", "value"}
_STALENESS_CASE_KEYS = {
    "case_id",
    "verified_on",
    "today",
    "max_age_days",
    "source_dependencies",
    "changed_source_ids",
}
_OPS = ("eq", "lte", "gte", "in")
_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
# Mirrors the browser's validCriterion field-name test.
_FIELD_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_VERDICT_SECTIONS = ("scalar", "criterion", "screen", "stale")

# The browser pins MAX_AGE_DAYS as a module constant. A corpus case that
# chose its own age window would not be testing the same rule.
BROWSER_MAX_AGE_DAYS = 180

# Placeholder citation identity for corpus-constructed rules. Screening does
# not read either field; they exist because ``Citation`` requires them.
_CORPUS_SOURCE = "parity corpus fixture"
_CORPUS_URL = "https://example.invalid/parity-corpus"


def load_fixtures(path: Path) -> dict[str, Any]:
    """Strictly load and shape-check the parity corpus."""

    payload = _read_payload(path)
    seen: set[str] = set()
    _validate_scalar_cases(payload, path, seen)
    _validate_criterion_cases(payload, path, seen)
    _validate_screen_cases(payload, path, seen)
    _validate_staleness_cases(payload, path, seen)
    return payload


def _read_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: parity fixtures could not be loaded") from error
    if not isinstance(payload, dict) or set(payload) != TOP_LEVEL_KEYS:
        raise ValueError(f"{path}: unexpected parity fixture fields")
    if payload["schema_version"] != 1:
        raise ValueError(f"{path}: unsupported schema_version")
    if not isinstance(payload["description"], str) or not payload["description"]:
        raise ValueError(f"{path}: description must be non-blank text")
    return payload


def _case_list(payload: dict[str, Any], section: str, path: Path) -> list[Any]:
    cases = payload[section]
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path}.{section}: expected a non-empty case list")
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError(f"{path}.{section}: each case must be an object")
    return cases


def _check_case_id(case: dict[str, Any], seen: set[str], path: Path) -> None:
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not _IDENTIFIER.fullmatch(case_id):
        raise ValueError(f"{path}: invalid case_id {case_id!r}")
    if case_id in seen:
        raise ValueError(f"{path}: duplicate case_id {case_id!r}")
    seen.add(case_id)


def _validate_scalar_cases(
    payload: dict[str, Any],
    path: Path,
    seen: set[str],
) -> None:
    for case in _case_list(payload, "scalar_cases", path):
        _check_case_id(case, seen, path)
        if set(case) != _SCALAR_CASE_KEYS:
            raise ValueError(f"{path}.scalar_cases: unexpected scalar-case fields")


def _is_json_scalar(value: Any) -> bool:
    # str/int/float deliberately admits booleans: they are JSON scalars
    # and legitimate criterion values.
    return isinstance(value, (str, int, float))


def _validate_criterion_cases(
    payload: dict[str, Any],
    path: Path,
    seen: set[str],
) -> None:
    section = "criterion_cases"
    for case in _case_list(payload, section, path):
        _check_case_id(case, seen, path)
        keys = set(case) - _CRITERION_OPTIONAL_KEYS
        if "actual_absent" in keys:
            if keys != _CRITERION_ABSENT_CASE_KEYS:
                raise ValueError(
                    f"{path}.{section}: absent-actual case has extra fields"
                )
            if case["actual_absent"] is not True:
                raise ValueError(
                    f"{path}.{section}: actual_absent must be true when present"
                )
        elif keys != _CRITERION_CASE_KEYS:
            raise ValueError(f"{path}.{section}: unexpected criterion-case fields")
        if case["op"] not in _OPS:
            raise ValueError(f"{path}.{section}: unsupported operator")
        _validate_criterion_values(case, path, section)


def _validate_criterion_values(case: dict[str, Any], path: Path, section: str) -> None:
    """Expected values are scalars, scalar lists, or a deliberate ill shape.

    ``expected_ill_shaped: true`` marks a case whose expected value is a
    shape ``load_rules`` would reject. Both runtimes must fail closed on it
    rather than raise or coerce; a corpus that only carried well-formed
    input could not report that they stopped agreeing there.
    """

    if case.get("expected_ill_shaped") is True:
        return
    expected = case["expected"]
    if isinstance(expected, list):
        if not expected or any(not _is_json_scalar(item) for item in expected):
            raise ValueError(f"{path}.{section}: invalid in-list values")
    elif not _is_json_scalar(expected):
        raise ValueError(f"{path}.{section}: expected must be a scalar")
    actual = case.get("actual")
    if "actual" in case and actual is not None and not _is_json_scalar(actual):
        raise ValueError(f"{path}.{section}: actual must be a JSON scalar")


def _validate_screen_cases(
    payload: dict[str, Any],
    path: Path,
    seen: set[str],
) -> None:
    section = "screen_cases"
    for case in _case_list(payload, section, path):
        _check_case_id(case, seen, path)
        if set(case) != _SCREEN_CASE_KEYS:
            raise ValueError(f"{path}.{section}: unexpected screen-case fields")
        if not isinstance(case["intake"], dict):
            raise ValueError(f"{path}.{section}: expected an intake object")
        rules = case["rules"]
        if not isinstance(rules, list) or not rules:
            raise ValueError(f"{path}.{section}: expected a non-empty rules list")
        for rule in rules:
            _validate_screen_rule(rule, path, section)


def _validate_screen_rule(rule: Any, path: Path, section: str) -> None:
    if not isinstance(rule, dict) or set(rule) != _SCREEN_RULE_KEYS:
        raise ValueError(f"{path}.{section}: unexpected rule fields")
    if not isinstance(rule["rule_id"], str) or not rule["rule_id"]:
        raise ValueError(f"{path}.{section}: rule_id must be non-blank text")
    if not isinstance(rule["jurisdiction_scope"], str):
        raise ValueError(f"{path}.{section}: jurisdiction_scope must be text")
    criteria = rule["criteria"]
    if not isinstance(criteria, list) or not criteria:
        raise ValueError(f"{path}.{section}: criteria must be non-empty")
    for criterion in criteria:
        if not isinstance(criterion, dict) or set(criterion) != _CRITERION_KEYS:
            raise ValueError(f"{path}.{section}: unexpected criterion fields")
        if not isinstance(criterion["field"], str) or not _FIELD_NAME.fullmatch(
            criterion["field"]
        ):
            raise ValueError(f"{path}.{section}: invalid criterion field name")
        if criterion["op"] not in _OPS:
            raise ValueError(f"{path}.{section}: unsupported criterion operator")


def _validate_staleness_cases(
    payload: dict[str, Any],
    path: Path,
    seen: set[str],
) -> None:
    section = "staleness_cases"
    for case in _case_list(payload, section, path):
        _check_case_id(case, seen, path)
        if set(case) != _STALENESS_CASE_KEYS:
            raise ValueError(f"{path}.{section}: unexpected fields")
        if case["verified_on"] is not None and not _DATE.fullmatch(
            str(case["verified_on"])
        ):
            raise ValueError(f"{path}.{section}: verified_on must be ISO")
        if not _DATE.fullmatch(str(case["today"])):
            raise ValueError(f"{path}.{section}: today must be ISO")
        if case["max_age_days"] != BROWSER_MAX_AGE_DAYS:
            raise ValueError(
                f"{path}.{section}: max_age_days is pinned to the "
                "browser's MAX_AGE_DAYS constant"
            )
        for field in ("source_dependencies", "changed_source_ids"):
            if not isinstance(case[field], list):
                raise ValueError(f"{path}.{section}: {field} must be a list")


def _actual_value(case: dict[str, Any]) -> Any:
    return None if case.get("actual_absent") is True else case.get("actual")


def _corpus_rule(record: dict[str, Any]) -> Rule:
    """Build a real ``Rule`` so ``screen`` runs production matching."""

    return Rule(
        rule_id=record["rule_id"],
        pathway="parity corpus fixture",
        route_class="ministerial",
        jurisdiction_scope=record["jurisdiction_scope"],
        criteria=list(record["criteria"]),
        citation=Citation(source=_CORPUS_SOURCE, url=_CORPUS_URL),
        source_dependencies=[],
        display_group="route",
    )


def _corpus_rule_status(case: dict[str, Any]) -> str:
    """Three-state source status, matching the browser's ``ruleStatus``."""

    changed = case["changed_source_ids"]
    if any(dependency in changed for dependency in case["source_dependencies"]):
        return "stale"
    citation = Citation(
        source=_CORPUS_SOURCE,
        url=_CORPUS_URL,
        verified_on=case["verified_on"],
    )
    if not citation.is_verified:
        return "unverified"
    today = date.fromisoformat(str(case["today"]))
    return "stale" if citation.is_stale(int(case["max_age_days"]), today) else "current"


def python_verdicts(fixtures: dict[str, Any]) -> dict[str, Any]:
    """Compute the Python engine's verdict document for the corpus."""

    return {
        "scalar": {
            case["case_id"]: _same_scalar(case["left"], case["right"])
            for case in fixtures["scalar_cases"]
        },
        "criterion": {
            case["case_id"]: _criterion_matches(
                _actual_value(case), case["op"], case["expected"]
            )
            for case in fixtures["criterion_cases"]
        },
        "screen": {
            case["case_id"]: sorted(
                result.rule.rule_id
                for result in screen(
                    case["intake"],
                    [_corpus_rule(rule) for rule in case["rules"]],
                )
            )
            for case in fixtures["screen_cases"]
        },
        "stale": {
            case["case_id"]: _corpus_rule_status(case)
            for case in fixtures["staleness_cases"]
        },
    }


def assert_verdicts_agree(
    python_side: dict[str, Any],
    browser_side: dict[str, Any],
) -> list[str]:
    """Return human-readable disagreements between two verdict documents."""

    if set(python_side) != set(browser_side):
        return [
            f"verdict sections differ: {sorted(python_side)} vs {sorted(browser_side)}"
        ]
    findings: list[str] = []
    for section in _VERDICT_SECTIONS:
        left = python_side[section]
        right = browser_side[section]
        if set(left) != set(right):
            missing = sorted(set(left) - set(right))
            extra = sorted(set(right) - set(left))
            findings.append(
                f"{section}: case sets differ; python-only={missing} "
                f"browser-only={extra}"
            )
            continue
        for case_id in sorted(left):
            if left[case_id] != right[case_id]:
                findings.append(
                    f"{section}.{case_id}: python={left[case_id]!r} "
                    f"browser={right[case_id]!r}"
                )
    return findings
