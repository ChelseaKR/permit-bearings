from __future__ import annotations

import json
from pathlib import Path

import pytest

from permit_pathways.readability import (
    METRIC_ID,
    build_baseline,
    explanation_scores,
    load_baseline,
    regressions,
    text_score,
)
from permit_pathways.readability_cli import main as readability_main

ROOT = Path(__file__).resolve().parents[1]
EXPLANATIONS = ROOT / "data" / "explanations" / "plain-language.json"
BASELINE = ROOT / "data" / "explanations" / "readability-baseline.json"


def _entry(summary: str, rule_id: str = "rule-one") -> dict:
    return {
        "source_rule_id": rule_id,
        "en": {
            "title": "Title.",
            "summary": summary,
            "highlights": {"title": "Facts.", "items": []},
            "next_steps": [],
            "confirm_with_staff": [],
        },
    }


def test_simple_text_scores_higher_than_dense_text() -> None:
    simple = text_score("The cat sat. It saw a dog. The dog ran away.")
    dense = text_score(
        "Notwithstanding the aforementioned considerations, the "
        "interdisciplinary characterization of jurisdictional "
        "incomprehensibility presupposes an extraordinarily sophisticated "
        "conceptualization."
    )
    assert simple is not None and dense is not None
    assert simple > dense


def test_score_is_deterministic_and_handles_unpunctuated_text() -> None:
    text = "One short sentence here."
    assert text_score(text) == text_score(text)
    assert text_score("no terminator at all") is not None
    assert text_score("") is None
    assert text_score("!!! ... ???") is None


def test_explanation_scores_key_by_rule_and_reject_duplicates() -> None:
    scores = explanation_scores([_entry("Short words help."), _entry("More.", "two")])
    assert set(scores) == {"rule-one", "two"}
    with pytest.raises(ValueError, match="duplicate"):
        explanation_scores([_entry("a"), _entry("b")])
    with pytest.raises(ValueError, match="source_rule_id"):
        explanation_scores([{"en": {}}])


def test_committed_baseline_passes_against_current_copy() -> None:
    baseline = load_baseline(BASELINE)
    current = explanation_scores(
        json.loads(EXPLANATIONS.read_text(encoding="utf-8"))["entries"]
    )
    assert regressions(baseline, current) == []
    assert baseline["metric_id"] == METRIC_ID


def test_regressions_flag_drops_and_new_or_missing_rules() -> None:
    baseline = {
        "schema_version": 1,
        "metric_id": METRIC_ID,
        "generated_on": "2026-08-22",
        "scores": {
            "kept": {"en": 60.0},
            "dropped": {"en": 40.0},
        },
    }
    findings = regressions(
        baseline,
        {"kept": {"en": 60.1}, "added": {"en": 55.0}, "dropped": {"en": 40.0}},
    )
    assert findings == [
        "added: new explanation has no baseline score; run the "
        "readability CLI to extend the baseline deliberately"
    ]

    harder = regressions(baseline, {"kept": {"en": 59.9}, "dropped": {"en": 40.0}})
    assert harder == [
        "kept: reading ease fell from 60.0 to 59.9; simplify the copy or "
        "re-baseline as a recorded decision"
    ]
    equal = regressions(baseline, {"kept": {"en": 60.0}, "dropped": {"en": 40.0}})
    assert equal == []
    easier = regressions(baseline, {"kept": {"en": 61.0}, "dropped": {"en": 40.5}})
    assert easier == []


def test_missing_english_copy_is_a_finding_not_a_crash() -> None:
    baseline = {
        "schema_version": 1,
        "metric_id": METRIC_ID,
        "generated_on": "2026-08-22",
        "scores": {"kept": {"en": 50.0}},
    }
    assert regressions(baseline, {"kept": {"en": None}}) == [
        "kept: English copy disappeared"
    ]


def test_build_baseline_rounds_sorts_and_refuses_unscored_entries() -> None:
    payload = build_baseline({"z-rule": {"en": 51.234}, "a-rule": {"en": 62.0}})
    assert list(payload["scores"]) == ["a-rule", "z-rule"]
    assert payload["scores"]["z-rule"]["en"] == 51.2
    with pytest.raises(ValueError, match="English copy"):
        build_baseline({"x": {"en": None}})


def test_load_baseline_rejects_drifted_schema_metric_and_scores(tmp_path) -> None:
    path = tmp_path / "baseline.json"
    good = {
        "schema_version": 1,
        "metric_id": METRIC_ID,
        "generated_on": "2026-08-22",
        "scores": {"r": {"en": 50.0}},
    }
    path.write_text(json.dumps(good), encoding="utf-8")
    assert load_baseline(path)["scores"] == {"r": {"en": 50.0}}

    bad_records = [
        {**good, "schema_version": 2},
        {**good, "metric_id": "other"},
        {**good, "generated_on": "22-08-2026"},
        {**good, "generated_on": 20260822},
        {**good, "scores": {"r": {"es": 1.0}}},
        {**good, "scores": {"r": {"en": True}}},
        {**good, "scores": {"r": {"en": "50"}}},
        # A bare number where a score record belongs used to raise TypeError,
        # which is not the loader's contract and is not caught by callers.
        {**good, "scores": {"r": 50.0}},
        {**good, "scores": {"r": None}},
        {**good, "scores": {}},
        {**good, "scores": []},
        {**good, "unexpected": True},
        {k: v for k, v in good.items() if k != "metric_id"},
    ]
    for record in bad_records:
        path.write_text(json.dumps(record), encoding="utf-8")
        with pytest.raises(ValueError):
            load_baseline(path)


def test_cli_check_fails_on_regression_and_regenerate_rebaselines(
    tmp_path,
    capsys,
) -> None:
    root = tmp_path / "repo"
    (root / "data" / "explanations").mkdir(parents=True)
    explanations = json.loads(EXPLANATIONS.read_text(encoding="utf-8"))
    target = root / "data" / "explanations" / "plain-language.json"
    target.write_text(json.dumps(explanations), encoding="utf-8")

    assert readability_main(["--repository-root", str(root), "regenerate"]) == 0
    out = capsys.readouterr().out
    assert "19 entries scored" in out
    assert (root / "data/explanations/readability-baseline.json").exists()

    assert readability_main(["--repository-root", str(root), "check"]) == 0

    simplified = json.loads(target.read_text(encoding="utf-8"))
    entry = simplified["entries"][0]
    en = entry["en"]
    en["summary"] = (
        "Notwithstanding the aforementioned jurisdictional considerations, "
        "any extraordinary incomprehensibility characterization "
        "presupposes sophisticated conceptualization."
    )
    en["next_steps"] = [
        "Facilitate the interdisciplinary institutionalization of "
        "extraordinarily characterized supplementary documentation "
        "prerequisites immediately."
    ]
    target.write_text(json.dumps(simplified), encoding="utf-8")

    current = explanation_scores(simplified["entries"])
    pinned = json.loads(
        (root / "data/explanations/readability-baseline.json").read_text()
    )["scores"][entry["source_rule_id"]]["en"]
    assert current[entry["source_rule_id"]]["en"] < pinned

    assert readability_main(["--repository-root", str(root), "check"]) == 1
    assert "reading ease fell" in capsys.readouterr().err


def _explanation_entries() -> list[dict]:
    return list(json.loads(EXPLANATIONS.read_text(encoding="utf-8"))["entries"])


def test_baseline_scores_exactly_the_published_explanations() -> None:
    """No orphan pins, no unscored rule. Either would be a silent hole."""

    baseline = load_baseline(BASELINE)
    published = {entry["source_rule_id"] for entry in _explanation_entries()}
    assert set(baseline["scores"]) == published


def test_baseline_is_a_tight_floor_not_a_vacuous_one() -> None:
    """A pinned floor far under current copy is a gate that cannot fire.

    ``check`` compares each recomputed score against its pin, so a baseline
    written low enough absorbs any regression and still reports pass. This
    fails if a pin drifts outside the meaningful Flesch range, or if it sits
    more than ten points of slack below the copy it is supposed to hold.
    """

    baseline = load_baseline(BASELINE)
    current = explanation_scores(_explanation_entries())
    for rule_id, pinned in baseline["scores"].items():
        score = current[rule_id]["en"]
        assert score is not None
        assert 0.0 <= pinned["en"] <= 100.0, f"{rule_id}: pin outside Flesch range"
        assert pinned["en"] >= round(score, 1) - 10.0, (
            f"{rule_id}: baseline {pinned['en']} is slack under current "
            f"{round(score, 1)}; re-baseline deliberately instead"
        )


def test_unscored_english_copy_key_is_a_hard_error() -> None:
    """New applicant copy must not enter unmeasured while the gate stays green."""

    entry = _entry("Short words help.")
    entry["en"]["action"] = "Some new applicant-facing sentence nobody scores."
    with pytest.raises(ValueError, match="unscored copy key"):
        explanation_scores([entry])


def test_unscored_highlight_keys_are_hard_errors() -> None:
    entry = _entry("Short words help.")
    entry["en"]["highlights"] = {"title": "Facts.", "items": [], "footnote": "Hi."}
    with pytest.raises(ValueError, match="unscored copy key"):
        explanation_scores([entry])

    item_entry = _entry("Short words help.")
    item_entry["en"]["highlights"] = {
        "title": "Facts.",
        "items": [{"label": "A", "text": "B", "aside": "C"}],
    }
    with pytest.raises(ValueError, match="unscored copy key"):
        explanation_scores([item_entry])


def test_malformed_english_shapes_raise_rather_than_score_nothing() -> None:
    for mutate in (
        lambda entry: entry["en"].__setitem__("highlights", "Facts."),
        lambda entry: entry["en"].__setitem__("highlights", {"items": "no"}),
        lambda entry: entry["en"].__setitem__("next_steps", "not a list"),
    ):
        entry = _entry("Short words help.")
        mutate(entry)
        with pytest.raises(ValueError):
            explanation_scores([entry])

    absent = {"source_rule_id": "rule-one"}
    assert explanation_scores([absent]) == {"rule-one": {"en": None}}

    not_an_object = {"source_rule_id": "rule-one", "en": "copy"}
    with pytest.raises(ValueError, match="en must be an object"):
        explanation_scores([not_an_object])


def test_highlight_and_list_copy_actually_reaches_the_score() -> None:
    """Every scored field must move the number, or it is not really scored."""

    base = _entry("Short.")
    baseline_score = explanation_scores([base])["rule-one"]["en"]
    assert baseline_score is not None

    for mutate in (
        lambda entry: entry["en"].__setitem__(
            "highlights",
            {"title": "Extraordinarily sophisticated conceptualization.", "items": []},
        ),
        lambda entry: entry["en"].__setitem__(
            "highlights",
            {
                "title": "Facts.",
                "items": [
                    {
                        "label": "Incomprehensibility.",
                        "text": "Notwithstanding jurisdictional considerations.",
                    }
                ],
            },
        ),
        lambda entry: entry["en"].__setitem__(
            "next_steps", ["Facilitate interdisciplinary institutionalization."]
        ),
        lambda entry: entry["en"].__setitem__(
            "confirm_with_staff", ["Presupposes extraordinarily sophisticated review."]
        ),
    ):
        entry = _entry("Short.")
        mutate(entry)
        changed = explanation_scores([entry])["rule-one"]["en"]
        assert changed is not None and changed != baseline_score
