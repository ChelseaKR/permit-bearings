from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "currency.yml"


def _workflow_step(workflow: str, name: str) -> str:
    marker = f"      - name: {name}\n"
    start = workflow.index(marker)
    end = workflow.find("\n      - name: ", start + len(marker))
    return workflow[start:] if end == -1 else workflow[start:end]


def test_review_package_requires_a_nonempty_changed_source_list():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    watch_step = _workflow_step(workflow, "Re-fetch watched sources and diff hashes")
    package_step = _workflow_step(
        workflow,
        "Build the exact re-verification review package",
    )
    upload_step = _workflow_step(
        workflow,
        "Retain the exact re-verification review package",
    )

    assert 'payload.get("changed_source_ids")' in watch_step
    assert 'echo "has_changed_sources=$has_changed_sources"' in watch_step
    assert "if: steps.watch.outputs.has_changed_sources == 'true'" in package_step
    assert "if: steps.watch.outputs.has_changed_sources == 'true'" in upload_step
    assert "steps.watch.outputs.exit_code == '1'" not in package_step
    assert "steps.watch.outputs.exit_code == '1'" not in upload_step


def test_stale_only_or_golden_regression_still_opens_currency_alert():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    alert_step = _currency_alert_step(workflow)

    assert "always() && steps.watch.outputs.exit_code == '1'" in alert_step
    # The alert still fires for all three conditions; it now says which.
    assert "watched source(s) were fetched and their content hash moved" in alert_step
    assert "rule(s) aged out of the review window" in alert_step
    assert "golden case(s) regressed" in alert_step
    assert "has_changed_sources" not in alert_step


def test_package_failure_cannot_suppress_the_currency_alert():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    package_step = _workflow_step(
        workflow,
        "Build the exact re-verification review package",
    )
    upload_step = _workflow_step(
        workflow,
        "Retain the exact re-verification review package",
    )
    alert_step = _currency_alert_step(workflow)

    assert workflow.index(package_step) < workflow.index(alert_step)
    assert workflow.index(upload_step) < workflow.index(alert_step)
    assert "if: ${{ always() && steps.watch.outputs.exit_code == '1' }}" in alert_step


# --- The alert has to converge ------------------------------------------
#
# Issue #70: the weekly watch filed a brand-new issue every Monday with the
# date in the title and no deduplication of any kind, so drift that persists
# became an unbounded pile (#63 and #65 are two weeks of the same one). One
# step also conflated three signals with different owners and different
# urgency behind one heading: a changed source hash, an aged-out rule, and a
# golden regression.


def _currency_alert_step(workflow: str) -> str:
    return _workflow_step(workflow, "Open or update the currency review issue")


def _letters_alert_step(workflow: str) -> str:
    return _workflow_step(workflow, "Report drift on the one open letters issue")


def test_no_issue_title_carries_the_run_date():
    # A date in the title guarantees a distinct title every run, so even
    # GitHub-side title matching could not collapse them. The run date belongs
    # in the body.
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for line in workflow.splitlines():
        stripped = line.strip()
        if "--title" not in stripped:
            continue
        assert "date -u" not in stripped, f"run date in an issue title: {stripped}"
        assert "$(date" not in stripped, f"run date in an issue title: {stripped}"


def test_the_currency_alert_searches_before_it_creates():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    step = _currency_alert_step(workflow)
    assert "gh issue list" in step
    assert "in:title" in step
    assert "gh issue comment" in step
    # Creating is the fallback, not the default path.
    create_index = step.index("gh issue create")
    list_index = step.index("gh issue list")
    assert list_index < create_index


def test_both_alerts_carry_the_currency_label():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for step in (
        _currency_alert_step(workflow),
        _letters_alert_step(workflow),
    ):
        assert "--label currency" in step
        # The label has to exist before it can be applied, and creating it
        # must not fail a run that is already reporting a real problem.
        assert "gh label create currency" in step


def test_a_green_run_closes_the_alert_it_opened():
    # Without this the automation is an append-only log: nothing ever records
    # that the condition cleared.
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    step = _workflow_step(workflow, "Close currency alerts that have cleared")
    assert "steps.watch.outputs.exit_code == '0'" in step
    assert "steps.letters.outputs.exit_code == '0'" in step
    assert "gh issue close" in step
    assert "--label currency" in step
    # Closing has to say why, or the next reader cannot tell a resolved alert
    # from a dismissed one.
    assert "gh issue comment" in step


def test_the_currency_alert_names_which_condition_fired():
    # A changed source hash, an aged-out rule, and a golden regression have
    # different owners and different urgency. One heading for all three is how
    # a real regression arrives under a title people have learned to skip.
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    step = _currency_alert_step(workflow)
    assert "currency signals:" in step
    for signal in ("changed_sources", "stale_rules", "golden_regressions"):
        assert signal in step, f"{signal} not read from the harness signal line"


def test_a_repeat_report_says_how_long_the_condition_has_persisted():
    # Filing on the first Monday of drift is right; saying nothing new on the
    # fourth is how the pile stops being read.
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    step = _currency_alert_step(workflow)
    assert "createdAt" in step
    assert "days" in step


def test_unverifiable_runs_still_never_open_or_close_anything():
    # A source that could not be downloaded is evidence about the network.
    # It must not open an alert, and it must not close one either: nothing was
    # learned about the law in that run.
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    close_step = _workflow_step(workflow, "Close currency alerts that have cleared")
    assert "'2'" not in close_step
    alert_step = _currency_alert_step(workflow)
    assert "steps.watch.outputs.exit_code == '1'" in alert_step


# --- The alert step, actually executed -----------------------------------
#
# String assertions prove the workflow says the right words. They cannot
# prove the shell runs. These execute the step's own script against a fake
# `gh` and a fixture report, which is the only way to find out whether the
# convergence logic works.

FAKE_GH = """#!/usr/bin/env python3
import json, os, sys
log = open(os.environ["GH_CALL_LOG"], "a")
log.write(" ".join(sys.argv[1:]) + "\\n")
log.close()
if sys.argv[1:3] == ["issue", "list"]:
    sys.stdout.write(os.environ.get("GH_ISSUE_LIST_STDOUT", ""))
sys.exit(int(os.environ.get("GH_EXIT", "0")))
"""


def _run_script(step_name: str) -> str:
    """The step's shell body, dedented, ready to execute."""

    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    step = _workflow_step(workflow, step_name)
    body = step[step.index("run: |") + len("run: |") :]
    return textwrap.dedent(body).lstrip("\n")


def _execute(script: str, tmp_path, report: str, environment: dict[str, str]):
    binaries = tmp_path / "bin"
    binaries.mkdir(exist_ok=True)
    (binaries / "gh").write_text(FAKE_GH, encoding="utf-8")
    (binaries / "gh").chmod(0o755)
    (tmp_path / "report.txt").write_text(report, encoding="utf-8")
    log = tmp_path / "gh-calls.log"
    log.write_text("", encoding="utf-8")
    env = {
        **os.environ,
        "PATH": f"{binaries}{os.pathsep}{os.environ['PATH']}",
        "GH_CALL_LOG": str(log),
        "GH_TOKEN": "fake",
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_REPOSITORY": "ChelseaKR/permit-bearings",
        "GITHUB_RUN_ID": "12345",
        **environment,
    }
    completed = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    return completed, log.read_text(encoding="utf-8")


CLEAN_REPORT = (
    "automated source/regression checks: pass\n\n"
    "currency signals: changed_sources=0 stale_rules=0 "
    "golden_regressions=0 unverifiable_sources=0\n"
)
STALE_ONLY_REPORT = (
    "automated source/regression checks: REVIEW NEEDED\n\n"
    "currency signals: changed_sources=0 stale_rules=3 "
    "golden_regressions=0 unverifiable_sources=0\n"
)
CHANGED_AND_GOLDEN_REPORT = (
    "automated source/regression checks: REVIEW NEEDED\n\n"
    "currency signals: changed_sources=2 stale_rules=0 "
    "golden_regressions=1 unverifiable_sources=0\n"
)


@pytest.fixture()
def alert_script():
    return _run_script("Open or update the currency review issue")


requires_bash = pytest.mark.skipif(
    shutil.which("bash") is None, reason="bash unavailable"
)


@requires_bash
def test_alert_creates_one_undated_labelled_issue_when_none_is_open(
    alert_script, tmp_path
):
    completed, calls = _execute(
        alert_script,
        tmp_path,
        STALE_ONLY_REPORT,
        {"TITLE": "Source currency review needed", "GH_ISSUE_LIST_STDOUT": ""},
    )
    assert completed.returncode == 0, completed.stderr
    assert "issue create" in calls
    assert "issue comment" not in calls
    assert "--label currency" in calls
    assert "--title Source currency review needed" in calls


@requires_bash
def test_alert_comments_instead_of_filing_a_second_issue(alert_script, tmp_path):
    completed, calls = _execute(
        alert_script,
        tmp_path,
        STALE_ONLY_REPORT,
        {
            "TITLE": "Source currency review needed",
            "GH_ISSUE_LIST_STDOUT": "77 2026-08-01T00:00:00Z\n",
        },
    )
    assert completed.returncode == 0, completed.stderr
    # This is the whole of issue #70: an unresolved condition must not
    # produce a second issue next Monday.
    assert "issue create" not in calls
    assert "issue comment 77" in calls


@requires_bash
def test_alert_body_names_only_the_conditions_that_fired(alert_script, tmp_path):
    stale, stale_calls = _execute(
        alert_script,
        tmp_path,
        STALE_ONLY_REPORT,
        {"TITLE": "T", "GH_ISSUE_LIST_STDOUT": ""},
    )
    assert stale.returncode == 0, stale.stderr
    assert "3 rule(s) aged out" in stale_calls
    # An aged-out rule needs a human re-verification, not a data refresh, and
    # the body has to say which of the two it is.
    assert "watched source(s)" not in stale_calls
    assert "golden case(s) regressed" not in stale_calls

    changed, calls = _execute(
        alert_script,
        tmp_path,
        CHANGED_AND_GOLDEN_REPORT,
        {"TITLE": "T", "GH_ISSUE_LIST_STDOUT": ""},
    )
    assert changed.returncode == 0, changed.stderr
    assert "2 watched source(s)" in calls
    assert "1 golden case(s) regressed" in calls
    # A condition that did not fire is not mentioned.
    assert "rule(s) aged out" not in calls


@requires_bash
def test_alert_survives_a_report_with_no_signal_line(alert_script, tmp_path):
    # An older harness, or a run that died before printing, must still alert
    # rather than crash and leave the condition unreported.
    completed, calls = _execute(
        alert_script,
        tmp_path,
        "automated source/regression checks: REVIEW NEEDED\n",
        {"TITLE": "T", "GH_ISSUE_LIST_STDOUT": ""},
    )
    assert completed.returncode == 0, completed.stderr
    assert "issue create" in calls
    assert "without a signal breakdown" in calls


@requires_bash
def test_close_step_closes_and_comments_when_the_watch_is_green(tmp_path):
    script = _run_script("Close currency alerts that have cleared")
    completed, calls = _execute(
        script,
        tmp_path,
        CLEAN_REPORT,
        {
            "WATCH_EXIT": "0",
            "LETTERS_EXIT": "3",
            "GH_ISSUE_LIST_STDOUT": "77\n",
        },
    )
    assert completed.returncode == 0, completed.stderr
    assert "issue comment 77" in calls
    assert "issue close 77" in calls
    # Only the watch's alert clears; the letters condition is still drifted.
    assert "Source currency review needed" in calls
    assert "HCD HAU letters dataset drifted" not in calls
