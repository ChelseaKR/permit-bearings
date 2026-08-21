"""Grounded explanation and staff questions: citations verified, or withheld."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.ai.corpus import CorpusIndex
from permit_pathways.ai.explain import (
    AI_LABEL,
    ExplainError,
    MatcherDisagreement,
    explain_result,
    explanation_schema,
    grounding_passages,
    matched_rules,
    unresolved_facts,
)
from permit_pathways.ai.provider import ScriptedProvider
from permit_pathways.ai.staff_questions import (
    DRAFT_LABEL,
    draft_staff_questions,
    has_local_record,
    questions_schema,
)
from permit_pathways.screening import load_rules

ROOT = Path(__file__).resolve().parents[1]
RULES = load_rules(ROOT / "data" / "rules")
CORPUS = CorpusIndex.load(ROOT)
DAVIS_ADU = {
    "project_type": "adu",
    "jurisdiction": "davis",
    "primary_dwelling_status": "existing_single_family",
    "adu_project_form": "new_detached",
    "unpermitted_existing": "no",
}


def _real_quote(passage_id: str, words: int = 12) -> str:
    passage = CORPUS.passage(passage_id)
    assert passage is not None
    return " ".join(passage.text.split()[:words])


def _offered() -> list[str]:
    matched = matched_rules(DAVIS_ADU, RULES, None)
    return [p.passage_id for p in grounding_passages(matched, CORPUS)]


def test_grounding_is_scoped_to_the_matched_rules_sources() -> None:
    matched = matched_rules(DAVIS_ADU, RULES, None)
    passages = grounding_passages(matched, CORPUS)
    allowed = {source for rule in matched for source in rule.source_dependencies}
    assert passages and all(p.source_id in allowed for p in passages)
    assert len({p.passage_id for p in passages}) == len(passages)
    assert len(passages) <= 18
    # The rule's own recorded excerpt locates a passage when it verifies.
    ministerial = next(r for r in matched if r.rule_id == "adu-ministerial-review")
    located = CORPUS.locate_excerpt("ca-gov-66317", ministerial.citation.excerpt or "")
    assert located is not None and located.passage_id in {
        p.passage_id for p in passages
    }


def test_matcher_disagreement_is_refused_and_unknowns_are_sorted() -> None:
    with pytest.raises(MatcherDisagreement, match="different rule set"):
        matched_rules(DAVIS_ADU, RULES, ["adu-ministerial-review"])
    ids = sorted(r.rule_id for r in matched_rules(DAVIS_ADU, RULES, None))
    assert matched_rules(DAVIS_ADU, RULES, ids)
    assert unresolved_facts({"a": "unknown", "b": "yes", "c": "unknown"}) == ("a", "c")


def test_explanation_keeps_verified_claims_and_withholds_the_rest() -> None:
    offered = _offered()
    good_quote = _real_quote(offered[0])
    payload = {
        "claims": [
            {
                "text": "A supported claim.",
                "citations": [{"passage_id": offered[0], "quote": good_quote}],
            },
            {
                "text": "Two citations, one altered.",
                "citations": [
                    {"passage_id": offered[0], "quote": good_quote},
                    {
                        "passage_id": offered[1],
                        "quote": "words that are definitely not in this passage at all",
                    },
                ],
            },
            {
                "text": "Cites something never offered.",
                "citations": [
                    {
                        "passage_id": "ca-gov-66315#0",
                        "quote": _real_quote("ca-gov-66315#0"),
                    }
                ],
            },
            {"text": "No citation at all.", "citations": []},
            {
                "text": "",
                "citations": [{"passage_id": offered[0], "quote": good_quote}],
            },
            "not an object",
        ]
    }
    provider = ScriptedProvider([json.dumps(payload)])
    explanation = explain_result(
        intake=DAVIS_ADU, rules=RULES, corpus=CORPUS, provider=provider, language="en"
    )
    assert [c.text for c in explanation.claims] == ["A supported claim."]
    assert explanation.claims[0].citations[0].verified
    assert explanation.claims[0].citations[0].url.startswith("https://")
    reasons = {w.text: w.reasons for w in explanation.withheld}
    assert any("does not occur" in r for r in reasons["Two citations, one altered."])
    assert reasons["Cites something never offered."] == (
        "ca-gov-66315#0: passage was not offered",
    )
    assert reasons["No citation at all."] == ("no citation",)
    assert ("", ("empty claim",)) in [(w.text, w.reasons) for w in explanation.withheld]
    assert ("", ("malformed claim",)) in [
        (w.text, w.reasons) for w in explanation.withheld
    ]
    assert explanation.withheld_count == 5
    assert explanation.to_dict()["withheld_count"] == 5
    assert explanation.label == AI_LABEL["en"]
    assert explanation.offered_passage_ids == tuple(offered)
    assert explanation.prompt_version == "explain-v1"
    call = provider.calls[0]
    assert "Write the claims in English." in call.user
    assert all(pid in call.user for pid in offered)
    assert call.schema == explanation_schema()


def test_explanation_in_spanish_and_with_no_matching_rules() -> None:
    provider = ScriptedProvider(['{"claims": []}'])
    spanish = explain_result(
        intake={**DAVIS_ADU, "unpermitted_existing": "unknown"},
        rules=RULES,
        corpus=CORPUS,
        provider=provider,
        language="es",
    )
    assert spanish.label == AI_LABEL["es"]
    assert spanish.unresolved_facts == ("unpermitted_existing",)
    assert "Write the claims in Spanish." in provider.calls[0].user
    assert "unpermitted_existing" in provider.calls[0].user
    untouched = ScriptedProvider([])
    empty = explain_result(
        intake={"project_type": "two_unit", "jurisdiction": "davis", "sf_zone": "no"},
        rules=RULES,
        corpus=CORPUS,
        provider=untouched,
        language="en",
    )
    assert empty.rule_ids == () and empty.claims == () and not untouched.calls


def test_explanation_rejects_bad_language_and_bad_output() -> None:
    with pytest.raises(ExplainError, match="language"):
        explain_result(
            intake=DAVIS_ADU,
            rules=RULES,
            corpus=CORPUS,
            provider=ScriptedProvider([]),
            language="de",
        )
    with pytest.raises(ExplainError, match="did not return JSON"):
        explain_result(
            intake=DAVIS_ADU,
            rules=RULES,
            corpus=CORPUS,
            provider=ScriptedProvider(["x"]),
            language="en",
        )
    with pytest.raises(ExplainError, match="claims list"):
        explain_result(
            intake=DAVIS_ADU,
            rules=RULES,
            corpus=CORPUS,
            provider=ScriptedProvider(['{"claims": 3}']),
            language="en",
        )


def test_staff_questions_keep_only_resolvable_pointers() -> None:
    payload: dict[str, Any] = {
        "questions": [
            {
                "question": "Does the City treat my lot as eligible?",
                "why": "It changes the route.",
                "rule_id": "adu-ministerial-review",
                "fact": "unpermitted_existing",
            },
            {
                "question": "Which form do I file?",
                "why": "",
                "rule_id": "not-a-rule",
                "fact": "lot_size",
            },
            {"question": "", "why": "", "rule_id": None, "fact": None},
            "junk",
        ]
        + [
            {"question": f"Extra {i}?", "why": "", "rule_id": None, "fact": None}
            for i in range(10)
        ]
    }
    provider = ScriptedProvider([json.dumps(payload)])
    drafted = draft_staff_questions(
        intake={**DAVIS_ADU, "unpermitted_existing": "unknown"},
        rules=RULES,
        provider=provider,
        language="en",
    )
    assert len(drafted.questions) == 8
    first, second = drafted.questions[:2]
    assert (first.rule_id, first.fact) == (
        "adu-ministerial-review",
        "unpermitted_existing",
    )
    assert (second.rule_id, second.fact) == (None, None)
    assert drafted.local_record is True
    assert drafted.label == DRAFT_LABEL["en"]
    assert drafted.unresolved_facts == ("unpermitted_existing",)
    assert drafted.to_dict()["prompt_version"] == "staff-questions-v1"
    assert "bounded local record" in provider.calls[0].user
    assert provider.calls[0].schema == questions_schema()


def test_staff_questions_without_local_record_and_error_paths() -> None:
    provider = ScriptedProvider(['{"questions": []}'])
    drafted = draft_staff_questions(
        intake={**DAVIS_ADU, "jurisdiction": "albany"},
        rules=RULES,
        provider=provider,
        language="es",
    )
    assert drafted.local_record is False and drafted.questions == ()
    assert "no local record" in provider.calls[0].user
    assert "Write the questions in Spanish." in provider.calls[0].user
    assert has_local_record(None, RULES) is False
    with pytest.raises(ExplainError, match="language"):
        draft_staff_questions(
            intake=DAVIS_ADU, rules=RULES, provider=ScriptedProvider([]), language="xx"
        )
    with pytest.raises(ExplainError, match="did not return JSON"):
        draft_staff_questions(
            intake=DAVIS_ADU,
            rules=RULES,
            provider=ScriptedProvider(["?"]),
            language="en",
        )
    with pytest.raises(ExplainError, match="questions list"):
        draft_staff_questions(
            intake=DAVIS_ADU,
            rules=RULES,
            provider=ScriptedProvider(['{"questions": {}}']),
            language="en",
        )
    with pytest.raises(MatcherDisagreement):
        draft_staff_questions(
            intake=DAVIS_ADU,
            rules=RULES,
            provider=ScriptedProvider([]),
            language="en",
            expected_rule_ids=["nope"],
        )
