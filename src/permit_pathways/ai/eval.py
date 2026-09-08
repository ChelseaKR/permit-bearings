"""Evaluation harness for the runtime AI layer.

Two measurements, both model-independent in their scoring:

* **Intake extraction** — bilingual natural-language cases with gold
  structured facts. Scored per field on exact match, and separately on
  abstention: when the gold value is ``unknown`` (the text did not say), did
  the model abstain, or did it fill the gap? A filled gap is the defect this
  portfolio cares most about, so it is reported as its own rate rather than
  folded into accuracy.
* **Citation grounding** — confirmed-fact intakes run through the matcher and
  the explanation prompt. Scored on how many generated claims carry citations
  that resolve verbatim against the committed corpus, and how many were
  withheld.
* **Follow-up answering (`ask`)** — one question per case against the same
  confirmed-fact intakes, each labelled with what the passages can support.
  The metric is grounding and *abstention*, not legal fidelity. Three labels:

  ``answerable_from_passages``  the offered passages settle it, and the case
                                records which ones. Answering is correct;
                                abstaining is a miss, not a defect.
  ``should_abstain``            the passages do not settle it — a fee no
                                committed source states, a fact the intake
                                records as unknown. Answering *without*
                                handing it to staff is the defect.
  ``should_refuse_scope``       the question is outside the matched result
                                (a valuation, a referral, a parking ticket).
                                **Zero tolerance:** any claim shown here is
                                an answer built from passages that were
                                retrieved for a different question.

  The most consequential failure of a question-answering surface is a
  confident answer the passages do not support, and this project's own
  earlier grounding runs found exactly that class — a paraphrase presented as
  a quote — before retrieval was interleaved across rules. The verifier, not
  the model, is the control; this suite measures how often the control has to
  fire and whether the model defers when it should.

A result file records provider, model, prompt versions, UTC date, and the
Git commit, so a number in the repository is always traceable to one run.
Numbers are committed only from a live run; the harness never invents them.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess  # nosec B404
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..screening import Rule, load_rules
from . import explain as explain_module
from . import facts
from . import intake as intake_module
from . import staff_questions as staff_module
from .corpus import CorpusIndex
from .provider import Provider, ProviderError, provider_from_env

OUTCOME_EXACT = "exact"
OUTCOME_ABSTAINED = "abstained_correctly"
OUTCOME_FILLED = "filled_when_unknown"
OUTCOME_MISSED = "missed"
OUTCOME_WRONG = "wrong"
OUTCOME_ERROR = "error"


class EvalError(ValueError):
    """The case file could not be used."""


@dataclass(frozen=True)
class IntakeCase:
    case_id: str
    language: str
    text: str
    gold: dict[str, str | None]
    tags: tuple[str, ...]


def load_intake_cases(path: Path) -> list[IntakeCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases: list[IntakeCase] = []
    seen: set[str] = set()
    for raw in payload.get("cases", []):
        case_id = str(raw["case_id"])
        if case_id in seen:
            raise EvalError(f"duplicate case_id {case_id}")
        seen.add(case_id)
        gold = dict(raw["gold"])
        project_type = gold.get("project_type")
        if project_type not in (*facts.PROJECT_TYPES, facts.UNKNOWN):
            raise EvalError(
                f"{case_id}: gold project_type {project_type!r} is not allowed"
            )
        expected = set(facts.material_fields(str(project_type))) | {
            "project_type",
            "jurisdiction",
        }
        if set(gold) != expected:
            raise EvalError(
                f"{case_id}: gold fields {sorted(gold)} must be exactly {sorted(expected)}"
            )
        for name, value in gold.items():
            if name == "jurisdiction":
                continue
            allowed = (
                (*facts.PROJECT_TYPES, facts.UNKNOWN)
                if name == "project_type"
                else facts.allowed_values(name)
            )
            if value not in allowed:
                raise EvalError(
                    f"{case_id}: gold {name}={value!r} is not an allowed value"
                )
        cases.append(
            IntakeCase(
                case_id,
                str(raw["language"]),
                str(raw["text"]),
                gold,
                tuple(str(t) for t in raw.get("tags", [])),
            )
        )
    if not cases:
        raise EvalError(f"no cases in {path}")
    return cases


def field_outcome(gold: str, predicted: str) -> str:
    if gold == facts.UNKNOWN:
        return OUTCOME_ABSTAINED if predicted == facts.UNKNOWN else OUTCOME_FILLED
    if predicted == gold:
        return OUTCOME_EXACT
    return OUTCOME_MISSED if predicted == facts.UNKNOWN else OUTCOME_WRONG


def score_intake_case(
    case: IntakeCase, extraction: intake_module.IntakeExtraction
) -> dict[str, Any]:
    draft = extraction.draft_intake()
    predicted_type = extraction.project_type.value
    gold_type = case.gold["project_type"]
    fields: dict[str, dict[str, str]] = {}
    for name in facts.material_fields(str(gold_type)):
        gold_value = str(case.gold[name])
        predicted = draft.get(name, facts.UNKNOWN)
        fields[name] = {
            "gold": gold_value,
            "predicted": predicted,
            "outcome": field_outcome(gold_value, predicted),
        }
    return {
        "case_id": case.case_id,
        "language": case.language,
        "tags": list(case.tags),
        "project_type": {
            "gold": gold_type,
            "predicted": predicted_type,
            "outcome": field_outcome(str(gold_type), predicted_type),
        },
        "jurisdiction": {
            "gold": case.gold["jurisdiction"],
            "predicted": extraction.jurisdiction.slug,
            "status": extraction.jurisdiction.status,
            "correct": extraction.jurisdiction.slug == case.gold["jurisdiction"],
        },
        "fields": fields,
        "unmapped_details": list(extraction.unmapped_details),
        "input_tokens": extraction.input_tokens,
        "output_tokens": extraction.output_tokens,
    }


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def summarize_intake(scored: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def bucket(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        outcomes = [f["outcome"] for row in rows for f in row["fields"].values()]
        gold_unknown = sum(
            1 for o in outcomes if o in {OUTCOME_ABSTAINED, OUTCOME_FILLED}
        )
        gold_known = len(outcomes) - gold_unknown
        type_exact = sum(
            1
            for row in rows
            if row["project_type"]["outcome"] in {OUTCOME_EXACT, OUTCOME_ABSTAINED}
        )
        case_exact = sum(
            1
            for row in rows
            if row["project_type"]["outcome"] in {OUTCOME_EXACT, OUTCOME_ABSTAINED}
            and row["jurisdiction"]["correct"]
            and all(
                f["outcome"] in {OUTCOME_EXACT, OUTCOME_ABSTAINED}
                for f in row["fields"].values()
            )
        )
        return {
            "cases": len(rows),
            "project_type_accuracy": _rate(type_exact, len(rows)),
            "jurisdiction_accuracy": _rate(
                sum(1 for r in rows if r["jurisdiction"]["correct"]), len(rows)
            ),
            "fields_scored": len(outcomes),
            "field_exact_match": _rate(
                sum(1 for o in outcomes if o in {OUTCOME_EXACT, OUTCOME_ABSTAINED}),
                len(outcomes),
            ),
            "gold_unknown_fields": gold_unknown,
            "abstained_when_should": _rate(
                sum(1 for o in outcomes if o == OUTCOME_ABSTAINED), gold_unknown
            ),
            "filled_when_unknown": _rate(
                sum(1 for o in outcomes if o == OUTCOME_FILLED), gold_unknown
            ),
            "gold_known_fields": gold_known,
            "known_field_exact": _rate(
                sum(1 for o in outcomes if o == OUTCOME_EXACT), gold_known
            ),
            "known_field_missed": _rate(
                sum(1 for o in outcomes if o == OUTCOME_MISSED), gold_known
            ),
            "known_field_wrong": _rate(
                sum(1 for o in outcomes if o == OUTCOME_WRONG), gold_known
            ),
            "cases_fully_correct": _rate(case_exact, len(rows)),
        }

    languages = sorted({row["language"] for row in scored})
    return {
        "all": bucket(scored),
        "by_language": {
            lang: bucket([r for r in scored if r["language"] == lang])
            for lang in languages
        },
    }


def run_intake_eval(
    cases: Sequence[IntakeCase],
    *,
    provider: Provider,
    registry: tuple[intake_module.JurisdictionEntry, ...],
) -> dict[str, Any]:
    scored: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for case in cases:
        try:
            extraction = intake_module.extract_intake(
                case.text, language=case.language, provider=provider, registry=registry
            )
        except (intake_module.IntakeError, ProviderError) as exc:
            errors.append({"case_id": case.case_id, "error": str(exc)})
            continue
        scored.append(score_intake_case(case, extraction))
    return {"summary": summarize_intake(scored), "cases": scored, "errors": errors}


@dataclass(frozen=True)
class GroundingCase:
    case_id: str
    language: str
    intake: dict[str, str]


def load_grounding_cases(path: Path) -> list[GroundingCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = [
        GroundingCase(str(raw["case_id"]), str(raw["language"]), dict(raw["intake"]))
        for raw in payload.get("cases", [])
    ]
    if not cases:
        raise EvalError(f"no cases in {path}")
    if len({c.case_id for c in cases}) != len(cases):
        raise EvalError("duplicate grounding case_id")
    return cases


def score_grounding(explanation: explain_module.Explanation) -> dict[str, Any]:
    shown = len(explanation.claims)
    withheld = explanation.withheld_count
    citations = [c for claim in explanation.claims for c in claim.citations]
    withheld_citations = sum(len(w.reasons) for w in explanation.withheld)
    return {
        "rule_ids": list(explanation.rule_ids),
        "offered_passages": len(explanation.offered_passage_ids),
        "claims_generated": shown + withheld,
        "claims_shown": shown,
        "claims_withheld": withheld,
        "claims_all_citations_verified": _rate(shown, shown + withheld),
        "citations_on_shown_claims": len(citations),
        "withheld_reasons": [list(w.reasons) for w in explanation.withheld],
        "withheld_citation_failures": withheld_citations,
        "claims": [
            {
                "text": claim.text,
                "citations": [
                    {"passage_id": c.passage_id, "quote": c.quote}
                    for c in claim.citations
                ],
            }
            for claim in explanation.claims
        ],
        "withheld_texts": [w.text for w in explanation.withheld],
        "input_tokens": explanation.input_tokens,
        "output_tokens": explanation.output_tokens,
    }


def summarize_grounding(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    generated = sum(int(r["claims_generated"]) for r in rows)
    shown = sum(int(r["claims_shown"]) for r in rows)
    return {
        "cases": len(rows),
        "claims_generated": generated,
        "claims_shown": shown,
        "claims_withheld": generated - shown,
        "fraction_claims_with_verified_citations": _rate(shown, generated),
        "cases_with_no_withheld_claims": _rate(
            sum(1 for r in rows if int(r["claims_withheld"]) == 0), len(rows)
        ),
        "mean_claims_shown_per_case": round(shown / len(rows), 2) if rows else None,
    }


def run_grounding_eval(
    cases: Sequence[GroundingCase],
    *,
    provider: Provider,
    rules: Sequence[Rule],
    corpus: CorpusIndex,
    with_staff_questions: bool = True,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    staff_rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for case in cases:
        try:
            explanation = explain_module.explain_result(
                intake=case.intake,
                rules=rules,
                corpus=corpus,
                provider=provider,
                language=case.language,
            )
        except (explain_module.ExplainError, ProviderError) as exc:
            errors.append(
                {"case_id": case.case_id, "stage": "explain", "error": str(exc)}
            )
            continue
        row = {
            "case_id": case.case_id,
            "language": case.language,
            **score_grounding(explanation),
        }
        rows.append(row)
        if not with_staff_questions:
            continue
        try:
            drafted = staff_module.draft_staff_questions(
                intake=case.intake,
                rules=rules,
                provider=provider,
                language=case.language,
            )
        except (explain_module.ExplainError, ProviderError) as exc:
            errors.append(
                {"case_id": case.case_id, "stage": "staff_questions", "error": str(exc)}
            )
            continue
        staff_rows.append(
            {
                "case_id": case.case_id,
                "language": case.language,
                "questions": len(drafted.questions),
                "with_rule_or_fact_pointer": sum(
                    1 for q in drafted.questions if q.rule_id or q.fact
                ),
                "local_record": drafted.local_record,
                "texts": [q.question for q in drafted.questions],
            }
        )
    staff_total = sum(int(r["questions"]) for r in staff_rows)
    staff_pointed = sum(int(r["with_rule_or_fact_pointer"]) for r in staff_rows)
    return {
        "summary": summarize_grounding(rows),
        "staff_questions_summary": {
            "cases": len(staff_rows),
            "questions": staff_total,
            "fraction_with_resolvable_pointer": _rate(staff_pointed, staff_total),
        },
        "cases": rows,
        "staff_questions": staff_rows,
        "errors": errors,
    }


EXPECT_ANSWERABLE = "answerable_from_passages"
EXPECT_ABSTAIN = "should_abstain"
EXPECT_REFUSE_SCOPE = "should_refuse_scope"
ASK_EXPECTATIONS = (EXPECT_ANSWERABLE, EXPECT_ABSTAIN, EXPECT_REFUSE_SCOPE)


@dataclass(frozen=True)
class AskCase:
    case_id: str
    language: str
    question: str
    expectation: str
    intake: dict[str, str]
    settling_passage_ids: tuple[str, ...]


def load_ask_cases(path: Path) -> list[AskCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases: list[AskCase] = []
    for raw in payload.get("cases", []):
        expectation = str(raw["expectation"])
        if expectation not in ASK_EXPECTATIONS:
            raise EvalError(
                f"{raw.get('case_id')}: expectation must be one of "
                f"{', '.join(ASK_EXPECTATIONS)}; got {expectation!r}"
            )
        settling = tuple(str(x) for x in raw.get("settling_passage_ids", ()))
        # An answerable case with no settling passage recorded is a case
        # nobody checked: it would score whatever the model did and call it
        # right. Refuse it rather than let it dilute the rate.
        if expectation == EXPECT_ANSWERABLE and not settling:
            raise EvalError(
                f"{raw.get('case_id')}: an answerable case must record the "
                "passage ids that would settle it"
            )
        if expectation != EXPECT_ANSWERABLE and settling:
            raise EvalError(
                f"{raw.get('case_id')}: only an answerable case may record "
                "settling passage ids"
            )
        cases.append(
            AskCase(
                str(raw["case_id"]),
                str(raw["language"]),
                str(raw["question"]),
                expectation,
                dict(raw["intake"]),
                settling,
            )
        )
    if not cases:
        raise EvalError(f"no cases in {path}")
    if len({c.case_id for c in cases}) != len(cases):
        raise EvalError("duplicate ask case_id")
    return cases


def score_ask_case(case: AskCase, answer: explain_module.Answer) -> dict[str, Any]:
    """Score one answered question against what the passages can support.

    `deferred_to_staff` is what a `should_abstain` case needs, and it is
    deliberately not the same thing as `abstained`. The live behaviour this
    project has already seen for a fee question was a *cited* statement that
    the sources set no fee, plus a staff question — which is a better answer
    than silence and must not be scored as a failure to abstain. What must
    never happen is claims shown with nothing handed to staff.
    """
    shown = len(answer.claims)
    cited = {
        citation.passage_id for claim in answer.claims for citation in claim.citations
    }
    deferred = bool(answer.staff_question)
    row: dict[str, Any] = {
        "case_id": case.case_id,
        "language": case.language,
        "expectation": case.expectation,
        "rule_ids": list(answer.rule_ids),
        "offered_passages": len(answer.offered_passage_ids),
        "claims_shown": shown,
        "claims_withheld": len(answer.withheld),
        "withheld_reasons": [list(w.reasons) for w in answer.withheld],
        "abstained": answer.abstained,
        "deferred_to_staff": deferred,
        "cited_passage_ids": sorted(cited),
        "input_tokens": answer.input_tokens,
        "output_tokens": answer.output_tokens,
    }
    if case.expectation == EXPECT_ANSWERABLE:
        row["settling_passage_ids"] = list(case.settling_passage_ids)
        row["cited_a_settling_passage"] = bool(cited & set(case.settling_passage_ids))
        row["answered_when_answerable"] = shown > 0
    elif case.expectation == EXPECT_ABSTAIN:
        row["abstained_when_expected"] = deferred
        # The defect: an answer given, and nothing flagged for a person.
        row["answered_when_should_abstain"] = shown > 0 and not deferred
    else:
        # Zero tolerance. Any claim shown is an answer assembled from
        # passages retrieved for a different question.
        row["refused_scope"] = shown == 0
        row["answered_out_of_scope"] = shown > 0
    return row


def summarize_ask(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def _of(expectation: str) -> list[Mapping[str, Any]]:
        return [r for r in rows if r["expectation"] == expectation]

    answerable = _of(EXPECT_ANSWERABLE)
    abstain = _of(EXPECT_ABSTAIN)
    scope = _of(EXPECT_REFUSE_SCOPE)
    shown = sum(int(r["claims_shown"]) for r in rows)
    withheld = sum(int(r["claims_withheld"]) for r in rows)
    return {
        "cases": len(rows),
        "claims_shown": shown,
        "claims_withheld": withheld,
        "fraction_claims_with_verified_citations": _rate(shown, shown + withheld),
        "answerable_cases": len(answerable),
        "answered_when_answerable": _rate(
            sum(1 for r in answerable if r["answered_when_answerable"]), len(answerable)
        ),
        "cited_a_settling_passage": _rate(
            sum(1 for r in answerable if r["cited_a_settling_passage"]), len(answerable)
        ),
        "should_abstain_cases": len(abstain),
        "abstained_when_expected": _rate(
            sum(1 for r in abstain if r["abstained_when_expected"]), len(abstain)
        ),
        "answered_when_should_abstain": _rate(
            sum(1 for r in abstain if r["answered_when_should_abstain"]), len(abstain)
        ),
        "scope_cases": len(scope),
        "scope_refusals": _rate(
            sum(1 for r in scope if r["refused_scope"]), len(scope)
        ),
        "answered_out_of_scope": sum(1 for r in scope if r["answered_out_of_scope"]),
    }


def run_ask_eval(
    cases: Sequence[AskCase],
    *,
    provider: Provider,
    rules: Sequence[Rule],
    corpus: CorpusIndex,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for case in cases:
        try:
            answer = explain_module.answer_question(
                question=case.question,
                intake=case.intake,
                rules=rules,
                corpus=corpus,
                provider=provider,
                language=case.language,
            )
        except (explain_module.ExplainError, ProviderError) as exc:
            errors.append({"case_id": case.case_id, "stage": "ask", "error": str(exc)})
            continue
        rows.append(score_ask_case(case, answer))
    if not rows:
        raise EvalError("every ask case errored; nothing was measured")
    return {"summary": summarize_ask(rows), "cases": rows, "errors": errors}


def git_commit(root: Path) -> str:
    """The HEAD commit of ``root``, or ``"unknown"``. Runs the resolved Git
    executable with a fixed argument list and no shell."""
    git = shutil.which("git")
    if git is None:
        return "unknown"
    try:
        completed = subprocess.run(  # noqa: S603  # nosec B603
            [git, "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return completed.stdout.strip() or "unknown"


def run_metadata(provider: Provider, root: Path, kind: str) -> dict[str, Any]:
    return {
        "status": "recorded_live_run",
        "kind": kind,
        "run_on": dt.datetime.now(dt.UTC).date().isoformat(),
        "provider": provider.name,
        "model": provider.model,
        "prompt_versions": {
            "intake": intake_module.PROMPT_VERSION,
            "explain": explain_module.PROMPT_VERSION,
            "ask": explain_module.ASK_PROMPT_VERSION,
            "staff_questions": staff_module.PROMPT_VERSION,
        },
        "commit": git_commit(root),
        "scoring": {
            "field_exact_match": "predicted value equals gold, including unknown==unknown",
            "abstained_when_should": "gold is unknown and the model returned unknown",
            "filled_when_unknown": "gold is unknown and the model returned a concrete value (the defect)",
            "claims_all_citations_verified": "claim shown only if every cited quote occurs verbatim in the named corpus document",
            "abstained_when_expected": "a should_abstain case that handed the question to staff, whether or not it also stated what the sources do say",
            "answered_when_should_abstain": "a should_abstain case answered with nothing flagged for a person (the defect)",
            "scope_refusals": "a should_refuse_scope case that showed no claim; zero tolerance on the complement",
        },
    }


def write_result(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - CLI wrapper
    parser = argparse.ArgumentParser(
        description="Evaluate the runtime AI layer against committed cases."
    )
    parser.add_argument("kind", choices=["intake", "grounding", "ask"])
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[3]
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="run only the first N cases"
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        provider = provider_from_env()
    except ProviderError as exc:
        print(f"eval: cannot start: {exc}")
        return 2
    if args.kind == "intake":
        cases = load_intake_cases(args.cases)
        registry_payload = json.loads(
            (root / "data" / "jurisdictions" / "registry.json").read_text(
                encoding="utf-8"
            )
        )
        registry = intake_module.load_jurisdictions(registry_payload["jurisdictions"])
        if args.limit:
            cases = cases[: args.limit]
        result = run_intake_eval(cases, provider=provider, registry=registry)
    elif args.kind == "ask":
        ask_cases = load_ask_cases(args.cases)
        if args.limit:
            ask_cases = ask_cases[: args.limit]
        result = run_ask_eval(
            ask_cases,
            provider=provider,
            rules=load_rules(root / "data" / "rules"),
            corpus=CorpusIndex.load(root),
        )
    else:
        grounding_cases = load_grounding_cases(args.cases)
        if args.limit:
            grounding_cases = grounding_cases[: args.limit]
        rules = load_rules(root / "data" / "rules")
        corpus = CorpusIndex.load(root)
        result = run_grounding_eval(
            grounding_cases, provider=provider, rules=rules, corpus=corpus
        )
    payload = {
        "run": run_metadata(provider, root, args.kind),
        "cases_file": str(args.cases),
        **result,
    }
    write_result(args.output, payload)
    print(json.dumps(payload["summary"], indent=2))
    if result["errors"]:
        print(f"eval: {len(result['errors'])} case(s) errored; see {args.output}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
