"""The browser-quality job's gates each report on every run.

`Run axe WCAG checks` and `Run Lighthouse budgets` are independent: each needs
the locked dependencies and Chromium, never the other's verdict. Under the
default step condition (`success()`), a red axe step skipped the budgets on
five consecutive runs (2026-09-09 to 09-10), and the job reported only the axe
failure. A gate that did not run looked the same as one that passed. This pins
each gate to its setup instead of to every step before it.

It parses the workflow rather than matching its text, so a condition that only
appears in a comment cannot satisfy it.
"""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "accessibility-performance.yml"
)
SETUP_IDS = ("install", "chromium")


def _steps() -> list[dict]:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return document["jobs"]["browser-quality"]["steps"]


def _gates(steps: list[dict]) -> list[dict]:
    return [
        s for s in steps if str(s.get("run", "")).strip().startswith("npm run test:")
    ]


def test_the_gates_under_test_are_the_ones_in_the_job() -> None:
    names = [gate.get("name") for gate in _gates(_steps())]
    assert "Run axe WCAG checks" in names, names
    assert "Run Lighthouse budgets" in names, names


def test_the_setup_steps_the_gates_depend_on_carry_ids() -> None:
    ids = {step.get("id") for step in _steps()}
    for setup_id in SETUP_IDS:
        assert setup_id in ids, (
            f"no step has id {setup_id!r}, so a gate's condition names nothing"
        )


def test_every_gate_runs_whenever_its_setup_succeeded() -> None:
    gates = _gates(_steps())
    gate_ids = {gate["id"] for gate in gates if "id" in gate}
    for gate in gates:
        name = gate.get("name")
        condition = str(gate.get("if", ""))
        assert "!cancelled()" in condition, (
            f"{name!r} runs only if every earlier step passed, so a red gate in front of it hides it"
        )
        for setup_id in SETUP_IDS:
            assert f"steps.{setup_id}.outcome == 'success'" in condition, (
                f"{name!r} does not require {setup_id!r} to have succeeded"
            )
        for other in gate_ids - {gate.get("id")}:
            assert f"steps.{other}." not in condition, (
                f"{name!r} depends on another gate's verdict"
            )
