"""The weekly watch's reading of `data/availability/`, and the lead time it derives.

Issue #164. `main` went red on 2026-09-09 with no commit behind it, because
`data/availability/woodland-preapproved-adu-program.json` passed its
`recheck_due_on` at 00:00 UTC. That behaviour is correct -- the product fails
closed. The defect is that the instrument built to give notice reported clean 33
hours earlier: none of the harness's five signals read `data/availability/` at
all, so a directory it never opened was reported as nothing to report.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from permit_pathways.harness.availability import (
    WATCH_WORKFLOW_PATH,
    availability_note,
    load_availability_records,
    signal_values,
    watch_availability,
    watch_interval_days,
)

ROOT = Path(__file__).resolve().parents[1]
AVAILABILITY_DIR = ROOT / "data" / "availability"
WORKFLOW = ROOT / WATCH_WORKFLOW_PATH


def _record(tmp_path: Path, name: str, checked_on: str, recheck_due_on: str) -> Path:
    path = tmp_path / f"{name}.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "availability": {
                    "program_id": name,
                    "source": {
                        "checked_on": checked_on,
                        "recheck_due_on": recheck_due_on,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# The lead time is derived, not chosen
# ---------------------------------------------------------------------------


def test_the_lead_time_comes_from_the_workflows_own_cron() -> None:
    """A hand-picked `7` would keep saying 7 after the cron moved.

    The committed schedule is `0 15 * * 1`, so the longest gap between two
    consecutive fires is a week. That number is measured off the expression
    rather than written down beside it.
    """

    assert watch_interval_days(WORKFLOW, today=date(2026, 1, 1)) == 7
    assert "cron:" in WORKFLOW.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("0 15 * * 1", 7),
        ("0 15 * * 1,4", 4),  # Mon and Thu: the longest gap is Thu -> Mon
        ("0 15 * * *", 1),
        ("0 15 1 * *", 31),  # monthly: the longest month decides, not the mean
        ("0 15 1,15 * *", 17),  # 15th -> 1st across a 31-day month
    ],
)
def test_the_longest_gap_is_what_a_lead_time_has_to_cover(
    tmp_path: Path, expression: str, expected: int
) -> None:
    """Nominal cadence is optimistic; the gap a deadline can hide in is the max.

    A lead time set to the *mean* interval of a Mon/Thu schedule would miss
    every deadline that falls in the longer half of the week.
    """

    workflow = tmp_path / "currency.yml"
    workflow.write_text(
        f'on:\n  schedule:\n    - cron: "{expression}"\n', encoding="utf-8"
    )

    assert watch_interval_days(workflow, today=date(2026, 1, 1)) == expected


def test_a_workflow_with_no_schedule_yields_no_lead_time_rather_than_a_default(
    tmp_path: Path,
) -> None:
    """`None` is not `0` and not seven.

    A run that does not know when it will next happen cannot answer "does this
    lapse before then". Answering it anyway with a default is the whole defect
    one layer down.
    """

    manual = tmp_path / "manual.yml"
    manual.write_text("on:\n  workflow_dispatch:\n", encoding="utf-8")

    assert watch_interval_days(manual, today=date(2026, 1, 1)) is None
    assert watch_interval_days(tmp_path / "absent.yml", today=date(2026, 1, 1)) is None


def test_a_bare_on_key_does_not_defeat_the_schedule_reader() -> None:
    """PyYAML reads a bare `on` as the boolean True, so a YAML read of the
    trigger block returns nothing over a file that plainly declares one. The
    reader here is line-based for exactly that reason, and this pins it against
    the committed workflow rather than a fixture.
    """

    import yaml

    loaded = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert loaded.get("on") is None, "the YAML trap this reader avoids has gone away"
    assert watch_interval_days(WORKFLOW, today=date(2026, 1, 1)) == 7


# ---------------------------------------------------------------------------
# What is due, and what could not be read
# ---------------------------------------------------------------------------


def test_a_reading_inside_the_next_interval_is_named_and_one_outside_it_is_not(
    tmp_path: Path,
) -> None:
    """Both directions. A notice that fires on every record is not a notice."""

    today = date(2026, 9, 9)
    _record(tmp_path, "due-in-three", "2026-08-20", "2026-09-12")
    _record(tmp_path, "due-in-thirty", "2026-08-20", "2026-10-09")
    workflow = tmp_path / "currency.yml"
    workflow.write_text(
        'on:\n  schedule:\n    - cron: "0 15 * * 1"\n', encoding="utf-8"
    )

    watch = watch_availability(tmp_path, today=today, workflow_path=workflow)

    assert [record.program_id for record in watch.due] == ["due-in-three"]
    assert len(watch.records) == 2
    assert watch.lead_days == 7
    assert watch.checked is True


def test_a_reading_that_already_lapsed_is_still_reported(tmp_path: Path) -> None:
    """The loudest case, and the one the notice would be useless without.

    A window that only looks forward stops mentioning a deadline the moment it
    matters most.
    """

    today = date(2026, 9, 9)
    _record(tmp_path, "lapsed", "2026-08-09", "2026-09-08")
    workflow = tmp_path / "currency.yml"
    workflow.write_text(
        'on:\n  schedule:\n    - cron: "0 15 * * 1"\n', encoding="utf-8"
    )

    watch = watch_availability(tmp_path, today=today, workflow_path=workflow)
    note = availability_note(watch, today=today, root=tmp_path)

    assert [record.program_id for record in watch.due] == ["lapsed"]
    assert "LAPSED 1 day(s) ago" in note
    assert "recheck_due_on 2026-09-08" in note
    assert "an automated fetch must not write checked_on" in note


def test_an_unreadable_record_is_named_and_makes_the_signal_not_checked(
    tmp_path: Path,
) -> None:
    """A record silently dropped is a record reported as not due.

    This is the failure this whole module exists to refuse, one level in: the
    count must not go on being a number once the population behind it is
    incomplete.
    """

    today = date(2026, 9, 9)
    _record(tmp_path, "fine", "2026-08-20", "2026-10-09")
    (tmp_path / "broken.json").write_text("{ not json", encoding="utf-8")
    workflow = tmp_path / "currency.yml"
    workflow.write_text(
        'on:\n  schedule:\n    - cron: "0 15 * * 1"\n', encoding="utf-8"
    )

    watch = watch_availability(tmp_path, today=today, workflow_path=workflow)

    assert [path.name for path in watch.unreadable] == ["broken.json"]
    assert watch.checked is False
    assert signal_values(watch, not_checked="not_checked") == (
        "not_checked",
        "not_checked",
    )
    assert "UNREADABLE: broken.json" in availability_note(
        watch, today=today, root=tmp_path
    )


def test_no_lead_time_makes_the_signal_not_checked_rather_than_zero(
    tmp_path: Path,
) -> None:
    """`0 due` and `we could not work out when the next run is` are not the same
    sentence, and only one of them is an answer.
    """

    today = date(2026, 9, 9)
    _record(tmp_path, "lapsed", "2026-08-09", "2026-09-08")
    manual = tmp_path / "manual.yml"
    manual.write_text("on:\n  workflow_dispatch:\n", encoding="utf-8")

    watch = watch_availability(tmp_path, today=today, workflow_path=manual)

    assert watch.checked is False
    assert signal_values(watch, not_checked="not_checked") == (
        "not_checked",
        "not_checked",
    )
    assert "NOT CHECKED" in availability_note(watch, today=today, root=tmp_path)


def test_both_numbers_are_printed_so_a_clean_run_carries_its_denominator(
    tmp_path: Path,
) -> None:
    """`0 due` over an empty directory and `0 due` over five healthy records are
    the same word without the denominator beside it.
    """

    today = date(2026, 9, 9)
    workflow = tmp_path / "currency.yml"
    workflow.write_text(
        'on:\n  schedule:\n    - cron: "0 15 * * 1"\n', encoding="utf-8"
    )

    empty = watch_availability(tmp_path, today=today, workflow_path=workflow)
    assert signal_values(empty, not_checked="not_checked") == ("0", "0")

    _record(tmp_path, "healthy", "2026-08-20", "2026-12-01")
    populated = watch_availability(tmp_path, today=today, workflow_path=workflow)
    assert signal_values(populated, not_checked="not_checked") == ("0", "1")


# ---------------------------------------------------------------------------
# The committed record, and the harness that prints the signal
# ---------------------------------------------------------------------------


def test_the_committed_availability_directory_is_readable_by_this_reader() -> None:
    """A reader that cannot parse the shipped records reports nothing due forever.

    The floor is the point: `0` records read is what a reader that stopped
    matching returns, and it is indistinguishable from a directory with nothing
    in it.
    """

    records, unreadable = load_availability_records(AVAILABILITY_DIR)

    assert unreadable == []
    assert len(records) >= 1
    assert {record.program_id for record in records} == {
        "woodland-preapproved-adu-plan-program"
    }


def test_the_harness_prints_both_availability_numbers_on_every_run() -> None:
    """Unconditional, like the four signals beside it.

    A signal that appears only when something is wrong cannot be used to detect
    recovery, and cannot be told apart from a harness that stopped printing it.
    """

    completed = subprocess.run(
        [sys.executable, "-m", "permit_pathways.harness"],
        cwd=ROOT,
        env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    signal_line = [
        line
        for line in completed.stdout.splitlines()
        if line.startswith("currency signals:")
    ]

    assert len(signal_line) == 1, completed.stdout[-2000:]
    assert "program_availability_due=" in signal_line[0]
    assert "program_availability_records=" in signal_line[0]


def test_the_watch_reports_the_committed_record_without_changing_the_exit_code() -> (
    None
):
    """Report-only, and that is a decision the issue leaves open (#164, decision 2).

    The expiry itself is already merge-blocking through the beta gate. A lead-time
    warning that reddens the build for a week before anything is wrong is a gate
    that cries wolf, so this one does not touch the exit code. If that call is
    reversed, this test is where the reversal has to be recorded.
    """

    # Read the day after the committed record lapses, derived from the record
    # rather than written out. A literal here passes only while the committed
    # reading happens to be near its deadline: `date(2026, 9, 9)` held while
    # `recheck_due_on` was `2026-09-08` and went red the moment the attestation
    # was renewed, for a reason about the fixture rather than about the watch.
    committed = load_availability_records(AVAILABILITY_DIR)[0][0]
    today = committed.recheck_due_on + timedelta(days=1)
    watch = watch_availability(AVAILABILITY_DIR, today=today, workflow_path=WORKFLOW)

    assert watch.lead_days == 7
    assert watch.checked is True
    # The committed record is past due on that day, so this is a live assertion
    # rather than a fixture: the notice fires against the tree as it stands.
    assert len(watch.due) == 1
    note = availability_note(watch, today=today, root=ROOT)
    assert "data/availability/woodland-preapproved-adu-program.json" in note


def test_a_record_comfortably_current_produces_no_notice_at_all() -> None:
    """The accepted case the refusal above needs.

    Read the committed record far enough before its due date and the watch must
    be silent, or "reports readings that lapse soon" is satisfied by a watch that
    reports every reading there is.
    """

    committed = load_availability_records(AVAILABILITY_DIR)[0][0]
    early = committed.recheck_due_on - timedelta(days=60)
    watch = watch_availability(AVAILABILITY_DIR, today=early, workflow_path=WORKFLOW)

    assert watch.due == ()
    assert availability_note(watch, today=early, root=ROOT) == ""
    assert signal_values(watch, not_checked="not_checked") == ("0", "1")


def test_the_tolerant_reader_and_the_strict_loader_read_the_same_two_dates() -> None:
    """The duplicate is deliberate; the drift is not.

    `program_availability.load_program_availability` is the product's strict
    loader -- named policy, no future `checked_on`, a bounded window, and it
    raises. Those are the right rules for the thing that decides whether a packet
    may be built and the wrong ones for a watch, which has to be able to name the
    due date of a record that is invalid for some other reason. Two readers is
    therefore the design. Two readers reading *different dates* is the defect,
    and nothing else in the repository would catch it.
    """

    from permit_pathways.program_availability import load_program_availability

    records, unreadable = load_availability_records(AVAILABILITY_DIR)
    assert unreadable == []
    assert records, "no committed record to compare; this check would be vacuous"

    for record in records:
        strict = load_program_availability(record.path, today=record.checked_on)
        assert record.checked_on.isoformat() == strict.source.checked_on, record.path
        assert record.recheck_due_on.isoformat() == strict.source.recheck_due_on, (
            record.path
        )
        assert record.program_id == strict.program_id, record.path


# ---------------------------------------------------------------------------
# The workflow step that surfaces the signal
# ---------------------------------------------------------------------------


def _workflow_step(workflow: str, name: str) -> str:
    marker = f"      - name: {name}\n"
    start = workflow.index(marker)
    end = workflow.find("\n      - name: ", start + len(marker))
    return workflow[start:] if end == -1 else workflow[start:end]


def test_the_workflow_step_treats_not_checked_as_news_rather_than_as_none_due() -> None:
    """`not_checked` is the value that most looks like "nothing is due".

    The sibling step that parses this line already refuses a non-numeric value
    loudly rather than reading it as a condition; this one has to go further,
    because `not_checked` is a state its own reader can produce and a step that
    fell through to "no reading lapses" would publish the absence as the answer.
    """

    workflow = WORKFLOW.read_text(encoding="utf-8")
    step = _workflow_step(workflow, "Note program-availability readings about to lapse")

    assert "if: always()" in step
    assert "program_availability_due=" in step
    assert "program_availability_records=" in step
    # Each of the four cases the value can take is handled by name.
    assert "not_checked)" in step
    assert "::warning title=Program availability not checked::" in step
    assert "::warning title=No program-availability signal::" in step
    assert "::warning title=Program availability reading due::" in step
    assert "*[!0-9]*)" in step
    # Report-only: the step must not exit nonzero for a due reading. The only
    # `exit 1` here is the unparseable-value refusal.
    assert step.count("exit 1") == 1
    assert "gh issue create" not in step
    assert "gh issue comment" not in step


def test_the_renewal_procedure_is_written_down_where_a_maintainer_will_look() -> None:
    """The fourth `Done when` bullet of #164, and the only one a grep can hold.

    Measured when the issue was filed: `grep -i recheck` over
    docs/BETA-OPERATIONS-RUNBOOK.md, docs/MANUAL-VALIDATION.md and
    CONTRIBUTING.md returned nothing, so the cadence existed in the data with no
    procedure anywhere for meeting it.

    It is in CONTRIBUTING.md rather than the runbook, which would be the obvious
    home, because the runbook's bytes are bound by
    `data/validation/beta-operations-readiness.json`. Writing the section there
    turned 100 tests red and `beta_gate_cli recompute` **refused** to re-pin it
    ("document_bindings[1].sha256: bound document bytes changed"). Editing that
    document is an attested act, and an agent may not perform it. The test below
    holds that refusal, so the reason this section lives here does not decay
    into an unexplained choice.
    """

    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    section_start = contributing.index("## Renew a program-availability reading")
    section = contributing[section_start:]

    assert "recheck_due_on" in section
    assert "manual_date_bound" in section
    assert "Do not move the date" in section
    # The two files that must move together, and the two commands that follow.
    assert "data/availability/" in section
    assert "data/validation/woodland-flagship-gate.json" in section
    assert "scripts/build_demo_bundle.py" in section
    assert "recompute --write" in section
    assert "BETA-OPERATIONS-RUNBOOK.md" in section


def test_the_runbook_is_a_bound_document_that_an_agent_may_not_edit() -> None:
    """Why the section above is not in the runbook, asserted rather than asserted-in-prose.

    If the runbook ever stops being bound, this test fails and the section can
    move to where it belongs.
    """

    import json

    readiness = json.loads(
        (ROOT / "data" / "validation" / "beta-operations-readiness.json").read_text(
            encoding="utf-8"
        )
    )
    bound = {binding["path"] for binding in readiness["document_bindings"]}

    assert "docs/BETA-OPERATIONS-RUNBOOK.md" in bound
    assert "CONTRIBUTING.md" not in bound
