"""Evaluation harness: case-file contracts and model-independent scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.ai import facts
from permit_pathways.ai import provider as provider_module
from permit_pathways.ai.corpus import CorpusIndex
from permit_pathways.ai.eval import (
    ASK_EXPECTATIONS,
    EXPECT_ABSTAIN,
    EXPECT_ANSWERABLE,
    EXPECT_REFUSE_SCOPE,
    OUTCOME_ABSTAINED,
    OUTCOME_EXACT,
    OUTCOME_FILLED,
    OUTCOME_MISSED,
    OUTCOME_WRONG,
    EvalError,
    IntakeCase,
    field_outcome,
    git_commit,
    load_ask_cases,
    load_grounding_cases,
    load_intake_cases,
    run_ask_eval,
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
ASK = ROOT / "evals" / "ai" / "ask-cases.json"
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
    assert metadata["prompt_versions"]["intake"] == "intake-v2"
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
            # `local` joins the two hosted providers here because the service
            # can now run against a self-hosted endpoint. Leaving it out would
            # have made this contract reject the first honest local result,
            # which is the opposite of what it is for. It stays an allowlist:
            # a result naming a provider this package cannot build is a
            # result nothing produced.
            assert run["provider"] in set(provider_module.PROVIDER_NAMES)
            assert run["model"] and len(run["commit"]) == 40
            assert (
                payload["summary"]["cases"]
                if run["kind"] == "grounding"
                else payload["summary"]["all"]["cases"]
            )


# --- The `ask` suite: grounding and abstention, not legal fidelity --------


def _ask_cases() -> list[Any]:
    return load_ask_cases(ASK)


def test_committed_ask_cases_are_valid_bilingual_and_cover_all_three_labels() -> None:
    cases = _ask_cases()
    assert len(cases) >= 40
    assert {c.language for c in cases} == {"en", "es"}
    labels = {c.expectation for c in cases}
    assert labels == set(ASK_EXPECTATIONS)
    # Every label needs Spanish too, or the suite measures abstention in one
    # language and grounding in the other.
    for label in ASK_EXPECTATIONS:
        languages = {c.language for c in cases if c.expectation == label}
        assert languages == {"en", "es"}, label
    # Each question is asked against one of the eight committed confirmed-fact
    # intakes, so the ask suite and the grounding suite describe the same
    # eight results.
    grounding = {
        json.dumps(g.intake, sort_keys=True) for g in load_grounding_cases(GROUNDING)
    }
    assert all(json.dumps(c.intake, sort_keys=True) in grounding for c in cases)


def test_every_settling_passage_is_one_the_retrieval_actually_offers() -> None:
    """Otherwise the fixture sits where the failure is impossible.

    A case labelled answerable records the passages that would settle it. If
    retrieval never offers those passages, the model cannot cite them, and
    `cited_a_settling_passage` would measure the retrieval's silence while
    reading as a statement about the model. This is the check that keeps the
    label honest as retrieval changes.
    """
    from permit_pathways.ai.explain import matched_rules, question_passages

    rules = load_rules(ROOT / "data" / "rules")
    corpus = CorpusIndex.load(ROOT)
    missing: list[str] = []
    for case in _ask_cases():
        if case.expectation != EXPECT_ANSWERABLE:
            continue
        matched = matched_rules(case.intake, rules, None)
        offered = {
            p.passage_id for p in question_passages(case.question, matched, corpus)
        }
        absent = sorted(set(case.settling_passage_ids) - offered)
        if absent:
            missing.append(f"{case.case_id}: {absent}")
    assert missing == [], missing


def test_ask_case_loader_refuses_labels_and_settling_ids_that_contradict(
    tmp_path: Path,
) -> None:
    base = {
        "case_id": "c1",
        "language": "en",
        "question": "How tall?",
        "intake": {"project_type": "adu", "jurisdiction": "davis"},
    }

    def write(**overrides: Any) -> Path:
        path = tmp_path / "ask.json"
        path.write_text(
            json.dumps({"cases": [{**base, **overrides}]}), encoding="utf-8"
        )
        return path

    with pytest.raises(EvalError, match="expectation must be one of"):
        load_ask_cases(write(expectation="probably_fine"))
    # An answerable case with nothing recorded would score whatever the model
    # did and call it right.
    with pytest.raises(EvalError, match="must record the"):
        load_ask_cases(write(expectation=EXPECT_ANSWERABLE, settling_passage_ids=[]))
    with pytest.raises(EvalError, match="only an answerable case"):
        load_ask_cases(
            write(expectation=EXPECT_ABSTAIN, settling_passage_ids=["ca-gov-66321#3"])
        )
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"cases": []}), encoding="utf-8")
    with pytest.raises(EvalError, match="no cases"):
        load_ask_cases(empty)
    duplicate = tmp_path / "dupe.json"
    duplicate.write_text(
        json.dumps(
            {
                "cases": [
                    {**base, "expectation": EXPECT_ABSTAIN},
                    {**base, "expectation": EXPECT_ABSTAIN},
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(EvalError, match="duplicate ask case_id"):
        load_ask_cases(duplicate)


def _ask_reply(
    *,
    claims: list[dict[str, Any]] | None = None,
    staff_question: str | None = None,
) -> str:
    payload: dict[str, Any] = {"claims": claims or []}
    if staff_question is not None:
        payload["staff_question"] = staff_question
    return json.dumps(payload)


def _one_case(expectation: str) -> Any:
    return next(c for c in _ask_cases() if c.expectation == expectation)


def test_a_fabricated_citation_is_withheld_rather_than_shown() -> None:
    """The verifier, not the model, is the control."""
    rules = load_rules(ROOT / "data" / "rules")
    corpus = CorpusIndex.load(ROOT)
    case = _one_case(EXPECT_ANSWERABLE)
    settling = case.settling_passage_ids[0]
    document = corpus.documents[settling.split("#", 1)[0]]
    real = " ".join(
        next(p for p in document.passages if p.passage_id == settling).text.split()[:12]
    )
    reply = _ask_reply(
        claims=[
            {
                "text": "grounded",
                "citations": [{"passage_id": settling, "quote": real}],
            },
            {
                "text": "invented",
                "citations": [
                    {
                        "passage_id": settling,
                        "quote": "the statute plainly permits a fourth storey",
                    }
                ],
            },
        ]
    )
    result = run_ask_eval(
        [case], provider=ScriptedProvider([reply]), rules=rules, corpus=corpus
    )
    row = result["cases"][0]
    assert (row["claims_shown"], row["claims_withheld"]) == (1, 1)
    assert row["cited_a_settling_passage"] is True
    assert row["answered_when_answerable"] is True
    assert result["summary"]["fraction_claims_with_verified_citations"] == 0.5
    assert result["summary"]["claims_withheld"] == 1


def test_a_should_abstain_case_that_states_the_gap_and_asks_staff_is_correct() -> None:
    """The live behaviour for a fee question was a *cited* statement that the
    sources set no fee plus a staff question. That is a better answer than
    silence, and scoring it as a failure to abstain would push the model
    towards saying nothing."""
    rules = load_rules(ROOT / "data" / "rules")
    corpus = CorpusIndex.load(ROOT)
    case = _one_case(EXPECT_ABSTAIN)
    reply = _ask_reply(
        claims=[],
        staff_question="Which fee schedule applies to this application?",
    )
    result = run_ask_eval(
        [case], provider=ScriptedProvider([reply]), rules=rules, corpus=corpus
    )
    row = result["cases"][0]
    assert row["abstained"] is True
    assert row["deferred_to_staff"] is True
    assert row["abstained_when_expected"] is True
    assert row["answered_when_should_abstain"] is False
    assert result["summary"]["abstained_when_expected"] == 1.0
    assert result["summary"]["answered_when_should_abstain"] == 0.0


def test_an_answer_with_no_staff_question_is_the_should_abstain_defect() -> None:
    rules = load_rules(ROOT / "data" / "rules")
    corpus = CorpusIndex.load(ROOT)
    case = _one_case(EXPECT_ABSTAIN)
    matched_passage = "ca-gov-66317"
    document = corpus.documents[matched_passage]
    quote = " ".join(document.passages[1].text.split()[:10])
    reply = _ask_reply(
        claims=[
            {
                "text": "The fee is $1,200.",
                "citations": [
                    {"passage_id": document.passages[1].passage_id, "quote": quote}
                ],
            }
        ]
    )
    result = run_ask_eval(
        [case], provider=ScriptedProvider([reply]), rules=rules, corpus=corpus
    )
    row = result["cases"][0]
    assert row["claims_shown"] == 1
    assert row["deferred_to_staff"] is False
    assert row["answered_when_should_abstain"] is True
    assert result["summary"]["answered_when_should_abstain"] == 1.0


def test_a_scope_question_answered_at_all_is_counted_with_zero_tolerance() -> None:
    rules = load_rules(ROOT / "data" / "rules")
    corpus = CorpusIndex.load(ROOT)
    case = _one_case(EXPECT_REFUSE_SCOPE)
    refused = run_ask_eval(
        [case],
        provider=ScriptedProvider([_ask_reply(claims=[], staff_question="Ask staff.")]),
        rules=rules,
        corpus=corpus,
    )
    assert refused["cases"][0]["refused_scope"] is True
    assert refused["summary"]["scope_refusals"] == 1.0
    assert refused["summary"]["answered_out_of_scope"] == 0

    document = corpus.documents["ca-gov-66317"]
    quote = " ".join(document.passages[1].text.split()[:10])
    answered = run_ask_eval(
        [case],
        provider=ScriptedProvider(
            [
                _ask_reply(
                    claims=[
                        {
                            "text": "answered anyway",
                            "citations": [
                                {
                                    "passage_id": document.passages[1].passage_id,
                                    "quote": quote,
                                }
                            ],
                        }
                    ]
                )
            ]
        ),
        rules=rules,
        corpus=corpus,
    )
    assert answered["cases"][0]["answered_out_of_scope"] is True
    assert answered["summary"]["scope_refusals"] == 0.0
    # Counted, not rated: one is one too many.
    assert answered["summary"]["answered_out_of_scope"] == 1


def test_a_case_that_errors_is_recorded_and_an_all_error_run_measures_nothing() -> None:
    rules = load_rules(ROOT / "data" / "rules")
    corpus = CorpusIndex.load(ROOT)
    cases = _ask_cases()[:2]
    partial = run_ask_eval(
        cases,
        provider=ScriptedProvider(
            [_ask_reply(staff_question="Ask staff."), "not json"]
        ),
        rules=rules,
        corpus=corpus,
    )
    assert len(partial["cases"]) == 1 and partial["errors"][0]["stage"] == "ask"
    with pytest.raises(EvalError, match="nothing was measured"):
        run_ask_eval(
            cases[:1],
            provider=ScriptedProvider(["not json"]),
            rules=rules,
            corpus=corpus,
        )


def test_the_ask_run_metadata_names_the_ask_prompt_version() -> None:
    metadata = run_metadata(ScriptedProvider([]), ROOT, "ask")
    assert metadata["kind"] == "ask"
    assert metadata["prompt_versions"]["ask"] == "ask-v1"
    assert "answered_when_should_abstain" in metadata["scoring"]


def test_a_not_run_record_cannot_carry_numbers() -> None:
    """A placeholder is a statement that nothing was measured.

    `status: not_run` was previously unchecked beyond the status string, so a
    record could have said `not_run` and still published a summary full of
    figures — the shape this repository keeps finding, one level up from the
    data. A `not_run` record must carry no numeric summary at all.
    """
    for path in sorted((ROOT / "evals" / "ai" / "results").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["run"]["status"] != "not_run":
            continue
        summary = payload.get("summary") or {}
        numbers = {
            key: value
            for key, value in summary.items()
            if isinstance(value, int | float) and not isinstance(value, bool)
        }
        assert numbers == {}, f"{path.name} is not_run but reports {numbers}"
        assert not payload.get("cases"), f"{path.name} is not_run but lists cases"
