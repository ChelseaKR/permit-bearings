import json
from datetime import date
from pathlib import Path

import pytest

from permit_pathways.harness import verify_rules
from permit_pathways.harness.runner import load_golden
from permit_pathways.screening import load_rules

DATA = Path(__file__).parent.parent / "data"
RULES = DATA / "rules"
GOLDEN = DATA / "golden" / "example.json"
AS_OF = date(2026, 7, 30)


def test_report_accepts_the_bounded_davis_record_with_dated_evidence():
    report = verify_rules(RULES, GOLDEN, today=AS_OF)
    # The Davis record verifies only the City's published processing
    # categories. Its notes preserve HCD's unresolved ordinance-status warning
    # instead of treating the handout as operative law or an eligibility test.
    assert report.unverified == []
    assert report.stale == []
    assert len(report.verified) == 19
    assert report.golden_failed == []
    assert report.automated_checks_pass


def test_changed_source_flips_dependent_rules_to_stale():
    # Rehearse a legislative amendment touching Gov. Code § 66321
    # (ADU size/setback/height standards): both dependent rules must go
    # stale; unrelated rules stay verified.
    report = verify_rules(RULES, GOLDEN, today=AS_OF, changed_sources=["ca-gov-66321"])
    assert set(report.stale) == {
        "adu-protected-minimum",
        "adu-height-standards",
        "adu-size-allowances",
        "adu-multifamily-66323",
        "adu-multifamily-proposed-66323",
    }
    assert "sb9-two-unit-ministerial" in report.verified
    assert not report.automated_checks_pass


def test_verification_goes_stale_after_max_age():
    report = verify_rules(RULES, GOLDEN, today=date(2027, 7, 27))
    assert report.verified == []
    assert len(report.stale) == 19


def test_jurisdiction_layers_ride_on_the_statewide_base():
    report = verify_rules(RULES, GOLDEN, today=AS_OF)
    assert {
        "davis-new-detached-adu-local-layer",
        "woodland-new-detached-adu-local-layer",
    } <= set(report.golden_passed)


def test_golden_rule_dependencies_are_explicit_and_cover_expected_rules():
    rules = load_rules(RULES, today=AS_OF)
    cases = load_golden(GOLDEN, rules)

    assert len(cases) == 29
    assert all(
        case.rule_dependency_ids == sorted(case.rule_dependency_ids) for case in cases
    )
    assert all(case.rule_dependency_ids for case in cases)
    assert all(
        set(case.expected_rule_ids) <= set(case.rule_dependency_ids) for case in cases
    )
    assert {
        "sb9-adu-interaction",
        "sb9-two-unit-ministerial",
    } == set(
        next(
            case.rule_dependency_ids
            for case in cases
            if case.case_id == "sb9-duplex-tenant-occupied"
        )
    )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda record: record.pop("rule_dependency_ids"),
            "exactly the Golden case fields",
        ),
        (
            lambda record: record.update(
                {"rule_dependency_ids": list(reversed(record["rule_dependency_ids"]))}
            ),
            "sorted unique list",
        ),
        (
            lambda record: record.update(
                {
                    "rule_dependency_ids": [
                        *record["rule_dependency_ids"],
                        "unknown-rule",
                    ]
                }
            ),
            "unknown rule IDs",
        ),
        (
            lambda record: record.update(
                {
                    "rule_dependency_ids": [
                        rule_id
                        for rule_id in record["rule_dependency_ids"]
                        if rule_id != record["expected_rule_ids"][0]
                    ]
                }
            ),
            "must include expected rule IDs",
        ),
    ],
)
def test_golden_loader_rejects_unbound_rule_dependencies(
    tmp_path,
    mutate,
    message,
):
    payload = json.loads(GOLDEN.read_text(encoding="utf-8"))
    mutate(payload[0])
    path = tmp_path / "golden.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_golden(path, load_rules(RULES, today=AS_OF))


# --- The machine-readable signal line ------------------------------------
#
# `python -m permit_pathways.harness` exits 1 for three different conditions:
# a fetched source whose hash moved, a rule aged out of its review window, and
# a golden regression. They have different owners and different urgency, and
# the weekly workflow could only report "one of these happened" (issue #70).
# The counts are printed so the workflow can name the condition without
# parsing prose.


def _signal_line(output: str) -> str:
    lines = [
        line for line in output.splitlines() if line.startswith("currency signals: ")
    ]
    assert len(lines) == 1, f"expected exactly one signal line, got {lines}"
    return lines[0]


def _signals(output: str) -> dict[str, str]:
    fields = _signal_line(output).removeprefix("currency signals: ").split()
    parsed = {}
    for field in fields:
        name, _, value = field.partition("=")
        parsed[name] = value
    return parsed


def test_harness_prints_one_machine_readable_signal_line(capsys):
    from permit_pathways.harness.__main__ import main

    exit_code = main([])
    signals = _signals(capsys.readouterr().out)
    assert exit_code == 0
    assert set(signals) == {
        "changed_sources",
        "stale_rules",
        "golden_regressions",
        "unverifiable_sources",
        "program_availability_due",
        "program_availability_records",
    }
    # The line is printed on a clean run too: a signal that only appears on
    # failure cannot be used to detect recovery.
    #
    # No `--fetch`, so nothing was downloaded. The two counts a download is
    # the only source of say so, rather than reporting `0` — which is the
    # same string a watch that ran and found everything current prints, and
    # which would contradict the withdrawn-citation report above it whenever
    # the committed receipt records one.
    assert signals["changed_sources"] == "not_checked"
    assert signals["unverifiable_sources"] == "not_checked"
    assert signals["stale_rules"] == "0"
    assert signals["golden_regressions"] == "0"
    # The two availability counts are deliberately NOT pinned to a literal
    # here. They are read off `data/availability/`, whose one record has a
    # dated deadline, so a literal would make this test's verdict depend on
    # the calendar — which is the exact shape that turned one lapsed reading
    # into seven failures with no commit behind them (#164). What is pinned is
    # that both are printed and that each is either a count or `not_checked`;
    # `tests/test_availability_watch.py` pins the reading itself against
    # injected dates.
    for key in ("program_availability_due", "program_availability_records"):
        assert signals[key].isdigit() or signals[key] == "not_checked", signals[key]


def test_signal_line_does_not_report_a_fetch_count_without_a_fetch(capsys):
    """The regression this guards: `0` for a check that never ran.

    `0` is what a completed, clean watch reports. Printing it for a run that
    downloaded nothing publishes an absence as a measurement, and a reader —
    or the weekly workflow's recovery check — cannot tell the two apart.
    """

    from permit_pathways.harness.__main__ import main

    main([])
    signals = _signals(capsys.readouterr().out)
    assert signals["changed_sources"] != "0"
    assert signals["unverifiable_sources"] != "0"
    # The other two are derived from the committed rule and Golden records,
    # which every run reads, so they stay real numbers.
    assert signals["stale_rules"].isdigit()
    assert signals["golden_regressions"].isdigit()


def test_signal_line_counts_a_simulated_changed_source(capsys):
    from permit_pathways.harness.__main__ import main

    exit_code = main(["--assume-changed", "ca-gov-66321"])
    signals = _signals(capsys.readouterr().out)
    assert exit_code == 1
    # `--assume-changed` stales dependents without claiming a fetch happened,
    # so the changed-source count reports that no fetch was made rather than
    # borrowing the simulated ID.
    assert signals["changed_sources"] == "not_checked"
    assert int(signals["stale_rules"]) > 0
    assert signals["golden_regressions"] == "0"


def test_signal_line_reports_real_counts_when_a_fetch_happened(capsys, monkeypatch):
    """`not_checked` is about the fetch, not a blanket refusal to count.

    With a watch result in hand both fields are numbers again, including the
    honest `0` for a source set that came back entirely unchanged.
    """

    from permit_pathways.harness import watch as watch_module
    from permit_pathways.harness.__main__ import main

    def _fake_check_sources(path, *, today, rules=None):
        return watch_module.WatchResult(
            unchanged=["ca-gov-66321"],
            changed=[],
            unverifiable={},
        )

    def _fake_load_sources(path, *, today):
        return {}

    monkeypatch.setattr(watch_module, "check_sources", _fake_check_sources)
    monkeypatch.setattr(watch_module, "load_sources", _fake_load_sources)

    exit_code = main(["--fetch"])
    signals = _signals(capsys.readouterr().out)
    assert exit_code == 0
    assert signals["changed_sources"] == "0"
    assert signals["unverifiable_sources"] == "0"


def test_signal_line_counts_a_fetched_unverifiable_source(capsys, monkeypatch):
    from permit_pathways.harness import watch as watch_module
    from permit_pathways.harness.__main__ import main

    failure = watch_module.UnverifiableSource(
        source_id="davis-adu-handout-2026",
        reason="HTTP 404 Not Found",
        last_verified_on="2026-07-30",
        attempts=1,
        kind="not_found",
    )

    def _fake_check_sources(path, *, today, rules=None):
        return watch_module.WatchResult(
            unchanged=["ca-gov-66321"],
            changed=[],
            unverifiable={"davis-adu-handout-2026": failure},
        )

    monkeypatch.setattr(watch_module, "check_sources", _fake_check_sources)
    monkeypatch.setattr(watch_module, "load_sources", lambda path, *, today: {})

    exit_code = main(["--fetch"])
    signals = _signals(capsys.readouterr().out)
    # A source that could not be verified never escalates as a change.
    assert exit_code == 2
    assert signals["changed_sources"] == "0"
    assert signals["unverifiable_sources"] == "1"
    assert signals["stale_rules"] == "0"


def test_signal_line_is_greppable_with_a_fixed_prefix(capsys):
    # The workflow reads it with `sed -n 's/^currency signals: //p'`, so the
    # prefix has to start the line and appear exactly once.
    from permit_pathways.harness.__main__ import main

    main([])
    output = capsys.readouterr().out
    assert output.count("currency signals: ") == 1
    assert _signal_line(output).startswith("currency signals: changed_sources=")
