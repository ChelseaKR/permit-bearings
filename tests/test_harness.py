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


def _signals(output: str) -> dict[str, int]:
    fields = _signal_line(output).removeprefix("currency signals: ").split()
    parsed = {}
    for field in fields:
        name, _, value = field.partition("=")
        parsed[name] = int(value)
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
    }
    # The committed state is clean, and the line is printed anyway. A signal
    # that only appears on failure cannot be used to detect recovery.
    assert signals == {
        "changed_sources": 0,
        "stale_rules": 0,
        "golden_regressions": 0,
        "unverifiable_sources": 0,
    }


def test_signal_line_counts_a_simulated_changed_source(capsys):
    from permit_pathways.harness.__main__ import main

    exit_code = main(["--assume-changed", "ca-gov-66321"])
    signals = _signals(capsys.readouterr().out)
    assert exit_code == 1
    # `--assume-changed` stales dependents without claiming a fetch happened,
    # so the changed-source count stays at what was actually fetched.
    assert signals["changed_sources"] == 0
    assert signals["stale_rules"] > 0
    assert signals["golden_regressions"] == 0


def test_signal_line_is_greppable_with_a_fixed_prefix(capsys):
    # The workflow reads it with `sed -n 's/^currency signals: //p'`, so the
    # prefix has to start the line and appear exactly once.
    from permit_pathways.harness.__main__ import main

    main([])
    output = capsys.readouterr().out
    assert output.count("currency signals: ") == 1
    assert _signal_line(output).startswith("currency signals: changed_sources=")
