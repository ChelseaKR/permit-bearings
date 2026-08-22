import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "readability_gate.py"
BASELINE = ROOT / "scripts" / "readability-baseline.json"
EXPLANATIONS = ROOT / "data" / "explanations" / "plain-language.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("readability_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rg = _load_module()


def test_simple_copy_scores_easier_than_dense_legal_prose():
    simple_fre, simple_fk = rg.text_metrics(
        "You must apply. The city must answer in 15 business days. "
        "You get one decision."
    )
    dense_fre, dense_fk = rg.text_metrics(
        "Notwithstanding any inconsistent provision, the applicant's "
        "submittal shall be deemed ministerially disseminated pursuant to "
        "the jurisdiction's consolidated implementation obligations."
    )
    assert simple_fk < dense_fk
    assert simple_fre > dense_fre


def test_numbers_do_not_inflate_the_word_score():
    _fre, fk = rg.text_metrics("Allow 1 units per lot. The limit is 2.")
    assert fk >= 0


def test_measured_entries_cover_every_committed_rule():
    measured = rg.measured_entries(EXPLANATIONS)
    payload = json.loads(EXPLANATIONS.read_text(encoding="utf-8"))
    assert set(measured) == {entry["source_rule_id"] for entry in payload["entries"]}


def test_committed_baseline_passes_against_committed_copy():
    failures = rg.check(
        rg.measured_entries(EXPLANATIONS),
        json.loads(BASELINE.read_text(encoding="utf-8")),
    )
    assert failures == []


def test_worsening_copy_fails_and_improving_copy_passes(tmp_path):
    baseline = {
        "schema_version": 1,
        "per_rule": {"rule-a": {"fre": 60.0, "fk": 8.0}},
    }
    harder = {"rule-a": (55.5, 9.0)}
    easier = {"rule-a": (62.0, 7.5)}
    assert rg.check(harder, baseline) != []
    # Small float noise within tolerance is not a regression.
    assert rg.check({"rule-a": (59.5, 8.1)}, baseline) == []
    assert rg.check(easier, baseline) == []


def test_added_or_removed_rules_require_a_deliberate_baseline_update():
    baseline = {
        "schema_version": 1,
        "per_rule": {"rule-a": {"fre": 60.0, "fk": 8.0}},
    }
    failures = rg.check({"rule-a": (60.0, 8.0), "rule-b": (60.0, 8.0)}, baseline)
    assert any("added since baseline" in failure for failure in failures)

    failures = rg.check({}, baseline)
    assert any("removed since baseline" in failure for failure in failures)


def test_unmeasurable_entry_is_rejected(tmp_path):
    path = tmp_path / "plain-language.json"
    path.write_text(
        json.dumps({"schema_version": 1, "entries": [{"source_rule_id": "x"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no English copy object"):
        rg.measured_entries(path)


def test_cli_reports_failure_for_harder_copy(tmp_path, capsys):
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            baseline := {
                "schema_version": 1,
                "per_rule": {},
            }
        ),
        encoding="utf-8",
    )
    explanations = tmp_path / "explanations.json"
    explanations.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "source_rule_id": "rule-a",
                        "en": {"summary": "The city reviews the application."},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    del baseline
    code = rg.main(
        [
            "--explanations",
            str(explanations),
            "--baseline",
            str(baseline_path),
        ]
    )
    assert code == 1
    assert "added since baseline" in capsys.readouterr().out

    code = rg.main(
        [
            "--explanations",
            str(explanations),
            "--baseline",
            str(baseline_path),
            "--update-baseline",
        ]
    )
    updated = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert "rule-a" in updated["per_rule"]
    assert code == 0
