"""Evaluation harness: case-file contracts and model-independent scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.ai import facts
from permit_pathways.ai.corpus import CorpusIndex
from permit_pathways.ai.eval import (
    OUTCOME_ABSTAINED,
    OUTCOME_EXACT,
    OUTCOME_FILLED,
    OUTCOME_MISSED,
    OUTCOME_WRONG,
    EvalError,
    IntakeCase,
    field_outcome,
    git_commit,
    load_grounding_cases,
    load_intake_cases,
    run_grounding_eval,
    run_intake_eval,
    run_metadata,
    summarize_intake,
    write_result,
)
from permit_pathways.ai.intake import load_jurisdictions
from permit_pathways.ai.provider import ScriptedProvider
from permit_pathways.screening import load_rules

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "ai" / "intake-cases.json"
GROUNDING = ROOT / "evals" / "ai" / "grounding-cases.json"
REGISTRY = load_jurisdictions(
    json.loads(
        (ROOT / "data" / "jurisdictions" / "registry.json").read_text(encoding="utf-8")
    )["jurisdictions"]
)


def _extraction_payload(case: IntakeCase, **overrides: dict[str, str]) -> str:
    """A model reply that reproduces the gold values with quotes from the text."""
    words = case.text.split()
    quote = " ".join(words[:4])
    payload: dict[str, Any] = {
        "detected_language": case.language,
        "project_type": {
            "value": case.gold["project_type"],
            "quote": quote if case.gold["project_type"] != "unknown" else "",
        },
        "jurisdiction_name": {"value": "", "quote": ""},
        "unmapped_details": [],
    }
    gold_slug = case.gold["jurisdiction"]
    if gold_slug:
        name = next(e.name for e in REGISTRY if e.slug == gold_slug)
        payload["jurisdiction_name"] = {"value": name, "quote": name}
    for field in facts.FACT_FIELDS:
        value = str(case.gold.get(field.name, "unknown"))
        payload[field.name] = {
            "value": value,
            "quote": quote if value != "unknown" else "",
        }
    payload.update(overrides)
    return json.dumps(payload)


def test_committed_case_files_are_valid_and_bilingual() -> None:
    cases = load_intake_cases(CASES)
    assert len(cases) >= 30
    languages = {c.language for c in cases}
    assert languages == {"en", "es"}
    assert sum(1 for c in cases if c.gold["project_type"] == "unknown") >= 2
    assert sum(1 for c in cases if c.gold["jurisdiction"] is None) >= 3
    assert all(
        any(v == "unknown" for v in c.gold.values())
        for c in cases
        if "abstain" in c.tags
    )
    grounding = load_grounding_cases(GROUNDING)
    assert {c.language for c in grounding} == {"en", "es"}
    assert {c.intake["project_type"] for c in grounding} == set(facts.PROJECT_TYPES)


def test_case_loader_rejects_bad_gold(tmp_path: Path) -> None:
    def write(cases: list[dict[str, Any]]) -> Path:
        path = tmp_path / "cases.json"
        path.write_text(json.dumps({"cases": cases}), encoding="utf-8")
        return path

    base = {
        "case_id": "a",
        "language": "en",
        "text": "t",
        "gold": {
            "project_type": "jadu",
            "jurisdiction": None,
            "primary_dwelling_status": "unknown",
            "unpermitted_existing": "no",
        },
    }
    assert load_intake_cases(write([base]))[0].gold["unpermitted_existing"] == "no"
    with pytest.raises(EvalError, match="duplicate"):
        load_intake_cases(write([base, base]))
    with pytest.raises(EvalError, match="not allowed"):
        load_intake_cases(
            write([{**base, "gold": {**base["gold"], "project_type": "house"}}])
        )
    with pytest.raises(EvalError, match="must be exactly"):
        load_intake_cases(write([{**base, "gold": {**base["gold"], "sf_zone": "yes"}}]))
    with pytest.raises(EvalError, match="not an allowed value"):
        load_intake_cases(
            write([{**base, "gold": {**base["gold"], "unpermitted_existing": "maybe"}}])
        )
    with pytest.raises(EvalError, match="no cases"):
        load_intake_cases(write([]))
    empty = tmp_path / "g.json"
    empty.write_text(json.dumps({"cases": []}), encoding="utf-8")
    with pytest.raises(EvalError, match="no cases"):
        load_grounding_cases(empty)
    empty.write_text(
        json.dumps({"cases": [{"case_id": "x", "language": "en", "intake": {}}] * 2}),
        encoding="utf-8",
    )
    with pytest.raises(EvalError, match="duplicate"):
        load_grounding_cases(empty)


def test_field_outcomes_separate_abstention_from_accuracy() -> None:
    assert field_outcome("unknown", "unknown") == OUTCOME_ABSTAINED
    assert field_outcome("unknown", "yes") == OUTCOME_FILLED
    assert field_outcome("yes", "yes") == OUTCOME_EXACT
    assert field_outcome("yes", "unknown") == OUTCOME_MISSED
    assert field_outcome("yes", "no") == OUTCOME_WRONG


def test_intake_eval_scores_a_perfect_and_an_imperfect_reply() -> None:
    cases = load_intake_cases(CASES)[:3]
    first, second, third = cases
    replies = [
        _extraction_payload(first),
        _extraction_payload(
            second,
            unpermitted_existing={"value": "yes", "quote": second.text.split()[0]},
        ),
        "not json",
    ]
    result = run_intake_eval(
        cases, provider=ScriptedProvider(replies), registry=REGISTRY
    )
    assert [row["case_id"] for row in result["cases"]] == [
        first.case_id,
        second.case_id,
    ]
    assert result["errors"] == [
        {"case_id": third.case_id, "error": "the model did not return JSON"}
    ]
    perfect = result["cases"][0]
    assert perfect["project_type"]["outcome"] == OUTCOME_EXACT
    assert perfect["jurisdiction"]["correct"] is True
    assert all(
        f["outcome"] in {OUTCOME_EXACT, OUTCOME_ABSTAINED}
        for f in perfect["fields"].values()
    )
    flawed = result["cases"][1]
    assert flawed["fields"]["unpermitted_existing"]["outcome"] == OUTCOME_WRONG
    summary = result["summary"]["all"]
    assert summary["cases"] == 2
    assert summary["cases_fully_correct"] == 0.5
    assert summary["project_type_accuracy"] == 1.0
    assert summary["known_field_wrong"] is not None and summary["known_field_wrong"] > 0
    assert set(result["summary"]["by_language"]) == {"en"}


def test_summary_handles_empty_input_and_unknown_project_type() -> None:
    empty = summarize_intake([])
    assert empty["all"]["cases"] == 0 and empty["all"]["field_exact_match"] is None
    case = IntakeCase(
        "u", "es", "texto", {"project_type": "unknown", "jurisdiction": None}, ()
    )
    scripted = ScriptedProvider([_extraction_payload(case)])
    result = run_intake_eval([case], provider=scripted, registry=REGISTRY)
    row = result["cases"][0]
    assert row["project_type"]["outcome"] == OUTCOME_ABSTAINED and row["fields"] == {}
    assert result["summary"]["all"]["cases_fully_correct"] == 1.0


def test_grounding_eval_counts_verified_and_withheld_claims() -> None:
    rules = load_rules(ROOT / "data" / "rules")
    corpus = CorpusIndex.load(ROOT)
    cases = load_grounding_cases(GROUNDING)[:2]
    passage = corpus.documents["ca-gov-66317"].passages[1]
    good = " ".join(passage.text.split()[:12])
    replies = [
        json.dumps(
            {
                "claims": [
                    {
                        "text": "ok",
                        "citations": [
                            {"passage_id": passage.passage_id, "quote": good}
                        ],
                    },
                    {
                        "text": "bad",
                        "citations": [
                            {
                                "passage_id": passage.passage_id,
                                "quote": "this is not in the statute at all whatsoever",
                            }
                        ],
                    },
                ]
            }
        ),
        json.dumps(
            {
                "questions": [
                    {
                        "question": "Q?",
                        "why": "w",
                        "rule_id": "adu-ministerial-review",
                        "fact": None,
                    }
                ]
            }
        ),
        "not json",
    ]
    result = run_grounding_eval(
        cases, provider=ScriptedProvider(replies), rules=rules, corpus=corpus
    )
    assert len(result["cases"]) == 1
    row = result["cases"][0]
    assert (row["claims_generated"], row["claims_shown"], row["claims_withheld"]) == (
        2,
        1,
        1,
    )
    assert row["claims_all_citations_verified"] == 0.5
    assert row["withheld_texts"] == ["bad"]
    assert result["summary"]["fraction_claims_with_verified_citations"] == 0.5
    assert result["summary"]["cases_with_no_withheld_claims"] == 0.0
    assert result["staff_questions_summary"] == {
        "cases": 1,
        "questions": 1,
        "fraction_with_resolvable_pointer": 1.0,
    }
    assert result["errors"][0]["stage"] == "explain"
    without = run_grounding_eval(
        cases[:1],
        provider=ScriptedProvider(['{"claims": []}']),
        rules=rules,
        corpus=corpus,
        with_staff_questions=False,
    )
    assert (
        without["staff_questions"] == [] and without["summary"]["claims_generated"] == 0
    )
    staff_error = run_grounding_eval(
        cases[:1],
        provider=ScriptedProvider(['{"claims": []}', "?"]),
        rules=rules,
        corpus=corpus,
    )
    assert staff_error["errors"][0]["stage"] == "staff_questions"


def test_metadata_and_result_writer(tmp_path: Path) -> None:
    provider = ScriptedProvider([])
    metadata = run_metadata(provider, ROOT, "intake")
    assert (
        metadata["status"] == "recorded_live_run" and metadata["provider"] == "scripted"
    )
    assert len(metadata["commit"]) == 40
    assert metadata["prompt_versions"]["intake"] == "intake-v1"
    assert git_commit(tmp_path) == "unknown"
    target = tmp_path / "out" / "r.json"
    write_result(target, {"a": "ñ"})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": "ñ"}


def test_committed_results_are_traceable_live_runs() -> None:
    results = sorted((ROOT / "evals" / "ai" / "results").glob("*.json"))
    assert results, (
        "at least one recorded result or an explicit not_run record is expected"
    )
    for path in results:
        payload = json.loads(path.read_text(encoding="utf-8"))
        run = payload["run"]
        assert run["status"] in {"recorded_live_run", "not_run"}
        if run["status"] == "recorded_live_run":
            assert run["provider"] in {"anthropic", "bedrock"}
            assert run["model"] and len(run["commit"]) == 40
            assert (
                payload["summary"]["cases"]
                if run["kind"] == "grounding"
                else payload["summary"]["all"]["cases"]
            )
