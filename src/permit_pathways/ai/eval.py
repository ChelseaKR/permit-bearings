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

A result file records provider, model, prompt versions, UTC date, and the
Git commit, so a number in the repository is always traceable to one run.
Numbers are committed only from a live run; the harness never invents them.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
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


def git_commit(root: Path) -> str:
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(root), "rev-parse", "HEAD"],  # noqa: S607
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
            "staff_questions": staff_module.PROMPT_VERSION,
        },
        "commit": git_commit(root),
        "scoring": {
            "field_exact_match": "predicted value equals gold, including unknown==unknown",
            "abstained_when_should": "gold is unknown and the model returned unknown",
            "filled_when_unknown": "gold is unknown and the model returned a concrete value (the defect)",
            "claims_all_citations_verified": "claim shown only if every cited quote occurs verbatim in the named corpus document",
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
    parser.add_argument("kind", choices=["intake", "grounding"])
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
