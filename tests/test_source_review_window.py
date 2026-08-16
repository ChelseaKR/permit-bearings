"""One review window, three runtimes.

The 180-day source review window used to be written out separately in the
harness, the readiness validator, the deployed browser bundle, and the
reference server, with nothing tying them together. These tests fail if any
of them drifts, and if the reference server's staleness precedence stops
matching the harness the browser copies.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from types import ModuleType

import pytest

from permit_pathways.dates import SOURCE_REVIEW_WINDOW_DAYS
from permit_pathways.harness.runner import DEFAULT_MAX_AGE_DAYS
from permit_pathways.readiness import SOURCE_MAX_AGE_DAYS
from permit_pathways.screening import Rule, load_rules

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEMO_APP_PATH = REPOSITORY_ROOT / "demo" / "app.py"
DEMO_JS_PATH = REPOSITORY_ROOT / "assets" / "demo.js"
RULES_PATH = REPOSITORY_ROOT / "data" / "rules"


def _load_demo_app() -> ModuleType:
    """Import the reference server without starting it."""

    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))
    try:
        spec = importlib.util.spec_from_file_location("_demo_app", DEMO_APP_PATH)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(REPOSITORY_ROOT / "src"))
    return module


@pytest.fixture(scope="module")
def demo_app() -> ModuleType:
    return _load_demo_app()


def test_python_constants_share_one_definition() -> None:
    assert DEFAULT_MAX_AGE_DAYS is SOURCE_REVIEW_WINDOW_DAYS
    assert SOURCE_MAX_AGE_DAYS is SOURCE_REVIEW_WINDOW_DAYS


def test_browser_bundle_mirrors_the_python_window() -> None:
    """``assets/demo.js`` ships to users; it cannot import Python."""

    source = DEMO_JS_PATH.read_text(encoding="utf-8")
    matches = re.findall(r"^const MAX_AGE_DAYS = (\d+);$", source, re.MULTILINE)
    assert matches == [str(SOURCE_REVIEW_WINDOW_DAYS)], (
        "assets/demo.js MAX_AGE_DAYS must equal "
        f"permit_pathways.dates.SOURCE_REVIEW_WINDOW_DAYS ({SOURCE_REVIEW_WINDOW_DAYS})"
    )


def test_reference_server_holds_no_second_window_literal() -> None:
    """The server renders the window; it must not restate the number."""

    source = DEMO_APP_PATH.read_text(encoding="utf-8")
    assert str(SOURCE_REVIEW_WINDOW_DAYS) not in source, (
        "demo/app.py must take the review window from "
        "permit_pathways.dates.SOURCE_REVIEW_WINDOW_DAYS, not restate it"
    )


def _first_rule_with_dependencies() -> Rule:
    rules = load_rules(RULES_PATH)
    for rule in rules:
        if rule.source_dependencies and rule.citation.is_verified:
            return rule
    raise AssertionError("no verified rule with source dependencies in data/rules")


def _result_for(rule: Rule):
    class _Result:
        def __init__(self, matched: Rule) -> None:
            self.rule = matched
            self.verified = matched.citation.is_verified

    return _Result(rule)


def test_changed_source_beats_a_fresh_citation(demo_app: ModuleType) -> None:
    """The bug this file was written for.

    A rule whose citation was verified yesterday is still stale once one of
    its sources changes. ``harness.runner`` and ``assets/demo.js`` both said
    so; ``demo/app.py`` used to answer ``verified``.
    """

    rule = _first_rule_with_dependencies()
    result = _result_for(rule)
    strings = demo_app.STRINGS["en"]
    today = date.fromisoformat(rule.citation.verified_on) + timedelta(days=1)

    unchanged, _ = demo_app._result_badge(result, strings, today=today)
    assert unchanged == "verified"

    changed, _ = demo_app._result_badge(
        result,
        strings,
        today=today,
        changed_source_ids=[rule.source_dependencies[0]],
    )
    assert changed == "stale"


def test_reference_server_matches_the_harness_for_every_rule(
    demo_app: ModuleType,
) -> None:
    """Walk every rule under both precedences and require agreement."""

    from permit_pathways.harness.runner import verify_rules

    rules = load_rules(RULES_PATH)
    golden_path = REPOSITORY_ROOT / "data" / "golden" / "example.json"
    strings = demo_app.STRINGS["en"]
    today = date(2026, 8, 15)

    for changed in ([], [rule.source_dependencies[0] for rule in rules[:1]]):
        report = verify_rules(
            RULES_PATH, golden_path, today=today, changed_source_ids=changed
        )
        expected = {rule_id: "stale" for rule_id in report.stale}
        expected.update({rule_id: "unverified" for rule_id in report.unverified})
        expected.update({rule_id: "verified" for rule_id in report.verified})

        for rule in rules:
            status, _ = demo_app._result_badge(
                _result_for(rule), strings, today=today, changed_source_ids=changed
            )
            assert status == expected[rule.rule_id], (
                f"{rule.rule_id}: demo/app.py said {status}, "
                f"harness said {expected[rule.rule_id]} (changed={changed})"
            )


def test_committed_changed_sources_reach_the_screen_path(
    demo_app: ModuleType,
) -> None:
    """The server must read the same record the browser bundle ships."""

    assert demo_app.SOURCE_STATE_PATH == (
        REPOSITORY_ROOT / "data" / "source-status" / "current.json"
    )
    committed = demo_app.committed_changed_source_ids()
    assert isinstance(committed, tuple)
    assert all(isinstance(value, str) for value in committed)

    record = json.loads(demo_app.SOURCE_STATE_PATH.read_text(encoding="utf-8"))
    assert committed == tuple(record["changed_source_ids"])


def test_missing_source_state_does_not_break_the_server(
    demo_app: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreadable record must not crash a screening result."""

    monkeypatch.setattr(demo_app, "SOURCE_STATE_PATH", tmp_path / "absent.json")
    assert demo_app.committed_changed_source_ids() == ()
