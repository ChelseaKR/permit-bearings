"""Cross-runtime parity: Python matching core vs the browser's pure logic.

Both runtimes independently compute verdicts over
``data/parity/fixtures.json``. The test fails unless the verdict documents
are identical. Extend the corpus deliberately: every case runs in both
engines on every test invocation.

The Python side runs through ``screening.screen``, ``Rule.matches`` and
``Citation.is_stale`` — the functions production uses — so a regression in
the shipped engine shows up here. The browser side is assembled from
non-overlapping slices of ``assets/demo.js``; overlapping slices redeclare
identifiers and Node refuses to parse the program, which is a test failure
rather than a silent skip.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from itertools import pairwise
from pathlib import Path

import pytest

from permit_pathways.parity import (
    BROWSER_MAX_AGE_DAYS,
    TOP_LEVEL_KEYS,
    assert_verdicts_agree,
    load_fixtures,
    python_verdicts,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_PATH = ROOT / "data" / "parity" / "fixtures.json"
DEMO_PATH = ROOT / "assets" / "demo.js"

# Slice boundaries into assets/demo.js. They must not overlap: two slices
# carrying the same function declaration produce a SyntaxError.
_SLICES = (
    ("function nonBlank", "function validStableId"),
    ("function isJsonNumber", "function uiText"),
)

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js unavailable"
)

_DRIVER = r"""
const fixtures = JSON.parse(
  readFileSync("data/parity/fixtures.json", "utf8"),
);
if (fixtures.schema_version !== 1)
  throw new Error("unsupported parity corpus schema_version");

const verdicts = {scalar: {}, criterion: {}, screen: {}, stale: {}};
for (const c of fixtures.scalar_cases)
  verdicts.scalar[c.case_id] = sameScalar(c.left, c.right);
for (const c of fixtures.criterion_cases) {
  const actual = c.actual_absent === true ? undefined : c.actual;
  verdicts.criterion[c.case_id] = OPS[c.op](actual, c.expected);
}
for (const c of fixtures.screen_cases) {
  RULES = c.rules;
  verdicts.screen[c.case_id] =
    screen(c.intake).map(rule => rule.rule_id).sort();
}
for (const c of fixtures.staleness_cases) {
  const rule = {
    rule_id: c.case_id,
    citation: {verified_on: c.verified_on},
    source_dependencies: c.source_dependencies,
  };
  if (c.max_age_days !== MAX_AGE_DAYS)
    throw new Error(`case ${c.case_id} does not use the browser MAX_AGE_DAYS`);
  // Pin the evaluation date. Without it the browser reads the wall clock and
  // the corpus would agree only on the day it was written.
  const todayUtc = Date.parse(`${c.today}T00:00:00Z`);
  // Python names the fresh state "current"; align vocabularies here.
  const raw = ruleStatus(rule, c.changed_source_ids, todayUtc);
  verdicts.stale[c.case_id] = raw === "verified" ? "current" : raw;
}
console.log(JSON.stringify(verdicts));
"""

# Replaces the global Date with one whose zero-argument constructor and now()
# report a far-future instant, leaving UTC() and parse() intact. Any verdict
# that still reads the wall clock moves; a pinned one does not.
_SHIFTED_CLOCK = r"""
const RealDate = Date;
const FROZEN = RealDate.parse("2099-06-01T00:00:00Z");
class ShiftedDate extends RealDate {
  constructor(...args) {
    if (args.length === 0) super(FROZEN);
    else super(...args);
  }
  static now() { return FROZEN; }
}
ShiftedDate.UTC = RealDate.UTC;
ShiftedDate.parse = RealDate.parse;
globalThis.Date = ShiftedDate;
"""


def _source_between(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


def _browser_program(*, shift_clock: bool = False) -> str:
    application = DEMO_PATH.read_text(encoding="utf-8")
    parts = [
        "import {readFileSync} from 'node:fs';",
        "let RULES = [];",
        *(_source_between(application, start, end) for start, end in _SLICES),
    ]
    if shift_clock:
        parts.append(_SHIFTED_CLOCK)
    parts.append(_DRIVER)
    return "\n".join(parts)


def _run_browser(*, shift_clock: bool = False) -> dict[str, object]:
    completed = subprocess.run(
        ["node", "--input-type=module"],
        cwd=ROOT,
        input=_browser_program(shift_clock=shift_clock),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    result: dict[str, object] = json.loads(completed.stdout)
    return result


@requires_node
def test_python_and_browser_engines_agree_on_every_parity_case() -> None:
    fixtures = load_fixtures(FIXTURES_PATH)
    expected = python_verdicts(fixtures)

    findings = assert_verdicts_agree(expected, _run_browser())
    assert findings == []
    total_cases = sum(len(section) for section in expected.values())
    assert total_cases >= 50, f"parity corpus shrank unexpectedly: {total_cases}"


@requires_node
def test_browser_verdicts_do_not_move_with_the_wall_clock() -> None:
    """A corpus whose verdicts drift by date is green only on one day.

    Every staleness case pins ``today``. Running the browser under a clock
    shifted decades forward must not change a single verdict. If the pinned
    date stops being threaded through ``ruleStatus``, this fails.
    """

    assert _run_browser() == _run_browser(shift_clock=True)


@requires_node
def test_browser_slices_do_not_overlap() -> None:
    """Overlapping slices redeclare identifiers and Node refuses to parse."""

    application = DEMO_PATH.read_text(encoding="utf-8")
    spans = [
        (application.index(start), application.index(end, application.index(start)))
        for start, end in _SLICES
    ]
    ordered = sorted(spans)
    for (_, first_end), (second_start, _) in pairwise(ordered):
        assert first_end <= second_start, f"demo.js slices overlap: {ordered}"


def test_python_side_uses_the_shipped_engine_not_a_reimplementation() -> None:
    """The corpus is worthless if it grades a copy of the engine.

    Patching the shipped matcher must change the Python verdicts. If
    ``python_verdicts`` ever grows its own operator table again, this fails.
    """

    from permit_pathways import parity, screening

    fixtures = load_fixtures(FIXTURES_PATH)
    before = python_verdicts(fixtures)

    original = screening._criterion_matches
    try:
        screening._criterion_matches = lambda *_: False  # type: ignore[assignment]
        parity._criterion_matches = screening._criterion_matches  # type: ignore[assignment]
        after = python_verdicts(fixtures)
    finally:
        screening._criterion_matches = original  # type: ignore[assignment]
        parity._criterion_matches = original  # type: ignore[assignment]

    assert before["criterion"] != after["criterion"]
    assert any(
        before["screen"][case] != after["screen"][case] for case in after["screen"]
    )
    assert python_verdicts(fixtures) == before


def test_load_fixtures_accepts_the_committed_corpus() -> None:
    fixtures = load_fixtures(FIXTURES_PATH)
    assert set(fixtures) == TOP_LEVEL_KEYS


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda good: {**good, "unexpected": True}, "unexpected parity fixture fields"),
        (
            lambda good: {k: v for k, v in good.items() if k != "description"},
            "unexpected parity fixture fields",
        ),
        (lambda good: {**good, "schema_version": 2}, "unsupported schema_version"),
        (lambda good: {**good, "description": ""}, "description must be non-blank"),
        (lambda good: {**good, "scalar_cases": []}, "expected a non-empty case list"),
        (lambda good: {**good, "scalar_cases": ["nope"]}, "must be an object"),
        (
            lambda good: {
                **good,
                "scalar_cases": [{**good["scalar_cases"][0], "extra": 1}],
            },
            "unexpected scalar-case fields",
        ),
        (
            lambda good: {
                **good,
                "scalar_cases": [{**good["scalar_cases"][0], "case_id": "Bad Id"}],
            },
            "invalid case_id",
        ),
        (
            lambda good: {
                **good,
                "scalar_cases": [*good["scalar_cases"], good["scalar_cases"][0]],
            },
            "duplicate case_id",
        ),
        (
            lambda good: {
                **good,
                "criterion_cases": [{**good["criterion_cases"][0], "op": "regex"}],
            },
            "unsupported operator",
        ),
        (
            lambda good: {
                **good,
                "criterion_cases": [
                    {**good["criterion_cases"][2], "expected": {"a": 1}},
                ],
            },
            "expected must be a scalar",
        ),
        (
            lambda good: {
                **good,
                "criterion_cases": [
                    {**good["criterion_cases"][0], "actual_absent": "yes"},
                ],
            },
            "actual_absent must be true",
        ),
        (
            lambda good: {
                **good,
                "screen_cases": [{**good["screen_cases"][0], "intake": "woodland"}],
            },
            "expected an intake object",
        ),
        (
            lambda good: {
                **good,
                "screen_cases": [{**good["screen_cases"][0], "rules": []}],
            },
            "expected a non-empty rules list",
        ),
        (
            lambda good: {
                **good,
                "screen_cases": [
                    {
                        **good["screen_cases"][0],
                        "rules": [
                            {
                                **good["screen_cases"][0]["rules"][0],
                                "criteria": [
                                    {
                                        "field": "Project_Type",
                                        "op": "eq",
                                        "value": "adu",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
            "invalid criterion field name",
        ),
        (
            lambda good: {
                **good,
                "screen_cases": [
                    {
                        **good["screen_cases"][0],
                        "rules": [
                            {
                                **good["screen_cases"][0]["rules"][0],
                                "criteria": [
                                    {
                                        "field": "project_type",
                                        "op": "regex",
                                        "value": "a",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
            "unsupported criterion operator",
        ),
        (
            lambda good: {
                **good,
                "staleness_cases": [
                    {**good["staleness_cases"][0], "max_age_days": 90},
                ],
            },
            "pinned",
        ),
        (
            lambda good: {
                **good,
                "staleness_cases": [
                    {**good["staleness_cases"][0], "today": "2026-08-22T00:00"},
                ],
            },
            "today must be ISO",
        ),
        (
            lambda good: {
                **good,
                "staleness_cases": [
                    {**good["staleness_cases"][0], "verified_on": "22-08-2026"},
                ],
            },
            "verified_on must be ISO",
        ),
        (
            lambda good: {
                **good,
                "staleness_cases": [
                    {**good["staleness_cases"][0], "changed_source_ids": "one"},
                ],
            },
            "changed_source_ids must be a list",
        ),
    ],
)
def test_load_fixtures_rejects_schema_and_case_drift(
    tmp_path: Path,
    mutate,
    match: str,
) -> None:
    """Each mutation is written verbatim. Nothing sanitizes it back."""

    good = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    path = tmp_path / "fixtures.json"
    path.write_text(json.dumps(mutate(good)), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        load_fixtures(path)


def test_load_fixtures_reports_unreadable_and_malformed_files(tmp_path: Path) -> None:
    missing = tmp_path / "absent.json"
    with pytest.raises(ValueError, match="could not be loaded"):
        load_fixtures(missing)
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{ not json", encoding="utf-8")
    with pytest.raises(ValueError, match="could not be loaded"):
        load_fixtures(malformed)


def test_assert_verdicts_agree_pinpoints_disagreements() -> None:
    left = {"scalar": {"a": True}, "criterion": {"b": False}, "screen": {}, "stale": {}}
    same = {"scalar": {"a": True}, "criterion": {"b": False}, "screen": {}, "stale": {}}
    flipped = {
        "scalar": {"a": False},
        "criterion": {"b": False},
        "screen": {},
        "stale": {},
    }
    extra = {
        "scalar": {"a": True, "z": True},
        "criterion": {},
        "screen": {},
        "stale": {},
    }
    section_drift = {"nope": {}}

    assert assert_verdicts_agree(left, same) == []
    assert assert_verdicts_agree(left, flipped) == [
        "scalar.a: python=True browser=False"
    ]
    finding = assert_verdicts_agree(left, extra)[0]
    assert "case sets differ" in finding and "'z'" in finding
    assert assert_verdicts_agree(left, section_drift) == [
        "verdict sections differ: ['criterion', 'scalar', 'screen', 'stale'] vs ['nope']"
    ]


def test_corpus_covers_every_operator_and_staleness_state() -> None:
    """Keep the corpus honest: no silent erosion of covered semantics."""

    fixtures = load_fixtures(FIXTURES_PATH)
    ops = {case["op"] for case in fixtures["criterion_cases"]}
    assert ops == {"eq", "lte", "gte", "in"}

    outcomes = {case["case_id"] for case in fixtures["staleness_cases"]}
    assert {
        "age_180_is_current",
        "age_181_is_stale",
        "future_verified_on_is_stale",
        "missing_verification_is_unverified",
        "changed_dependency_is_stale_even_when_fresh",
        "unrelated_changed_source_leaves_rule_current",
    } <= outcomes

    assert [
        case
        for case in fixtures["criterion_cases"]
        if case.get("actual_absent") is True
    ], "the missing-intake-value edge must stay represented"

    ill_shaped = [
        case
        for case in fixtures["criterion_cases"]
        if case.get("expected_ill_shaped") is True
    ]
    assert {case["op"] for case in ill_shaped} >= {"lte", "gte", "in"}, (
        "each comparison operator needs a case proving it fails closed on a "
        "criterion value the loader would reject"
    )

    assert all(
        case["max_age_days"] == BROWSER_MAX_AGE_DAYS
        for case in fixtures["staleness_cases"]
    )


def test_every_verdict_state_actually_occurs_in_the_corpus() -> None:
    """A corpus of all-false verdicts would pass parity and prove nothing."""

    verdicts = python_verdicts(load_fixtures(FIXTURES_PATH))
    assert set(verdicts["scalar"].values()) == {True, False}
    assert set(verdicts["criterion"].values()) == {True, False}
    assert set(verdicts["stale"].values()) == {"current", "stale", "unverified"}
    matched = [ids for ids in verdicts["screen"].values() if ids]
    assert matched and any(len(ids) > 1 for ids in matched)
    assert any(not ids for ids in verdicts["screen"].values())
