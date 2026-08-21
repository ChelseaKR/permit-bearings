"""Grounded explanation: the model narrates, the corpus is the evidence.

The flow is deliberately ordered so that nothing the model says can reach
the applicant without a committed document standing behind it:

1. Re-run the deterministic matcher on the confirmed facts. If the caller
   claims a different matched set, refuse — the explanation must describe
   the result the Python matcher produced, not the one the caller asserts.
2. Offer the model passages only from the corpus documents the matched rules
   already depend on, ranked lexically, plus each rule's recorded excerpt.
3. Require every claim to cite passage IDs with verbatim quotes.
4. Verify every quote against the extracted text of the named source. A
   claim with any citation that does not resolve is withheld and counted.

What survives is a list of plain-language sentences each tied to text a
reader can open in ``corpus/``. That is evidence that the passages exist and
say those words; it is not evidence that the sentence is legally correct, and
the output says so.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from ..screening import Rule, screen
from .corpus import CorpusIndex, Passage
from .provider import Provider
from .retrieval import rank_passages

PROMPT_VERSION = "explain-v1"
ASK_PROMPT_VERSION = "ask-v1"
MAX_OUTPUT_TOKENS = 4000
MAX_QUESTION_CHARS = 500
QUESTION_PASSAGES = 6
PASSAGES_PER_RULE = 3
MAX_PASSAGES = 18
LANGUAGES = ("en", "es")
AI_LABEL = {
    "en": "AI-generated explanation. Every statement shown cites source text that "
    "was checked against the committed corpus; that check proves the passage "
    "exists, not that the statement is legally correct. This is not legal advice, "
    "an eligibility determination, or an approval. Confirm with local staff.",
    "es": "Explicación generada por IA. Cada enunciado mostrado cita un texto fuente "
    "verificado contra el corpus publicado; esa verificación prueba que el pasaje "
    "existe, no que el enunciado sea jurídicamente correcto. No es asesoría legal, "
    "una determinación de elegibilidad ni una aprobación. Confirme con el personal local.",
}


class ExplainError(ValueError):
    """The request or the model output could not be used."""


class MatcherDisagreement(ExplainError):
    """The caller's matched rule set differs from the Python matcher's."""


@dataclass(frozen=True)
class Citation:
    passage_id: str
    source_id: str | None
    source_label: str | None
    url: str | None
    quote: str
    verified: bool
    reason: str | None


@dataclass(frozen=True)
class Claim:
    text: str
    citations: tuple[Citation, ...]


@dataclass(frozen=True)
class WithheldClaim:
    text: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Explanation:
    language: str
    rule_ids: tuple[str, ...]
    claims: tuple[Claim, ...]
    withheld: tuple[WithheldClaim, ...]
    offered_passage_ids: tuple[str, ...]
    unresolved_facts: tuple[str, ...]
    label: str
    provider: str
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int

    @property
    def withheld_count(self) -> int:
        return len(self.withheld)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["withheld_count"] = self.withheld_count
        return payload


_SYSTEM_PROMPT = """You write a plain-language explanation of a deterministic screening result for a California housing project. The screening tool has already decided which candidate rules match the applicant's confirmed facts; your job is only to explain what those matched rules say, using the source passages provided.

Hard rules:
1. Write only claims you can support with the provided passages. Each claim must cite one or more passages by passage_id, and for each citation copy a verbatim quote of at least eight consecutive words from that exact passage. Do not alter, abbreviate, or paraphrase inside a quote. A quote that is not an exact substring of the cited passage will cause the whole claim to be withheld.
2. Do not cite a passage that was not provided. Do not invent section numbers, deadlines, sizes, or conditions.
3. Do not give advice, predict approval, or say the project qualifies. Describe what the rule provides and what still depends on facts the applicant has not confirmed. Refer to "the matched rule" or the source by name; never call the result a determination.
4. Plain language: start each claim with the practical consequence for the applicant; one condition or number per sentence; define an unavoidable legal term the first time; keep sentences short.
5. Write between three and eight claims, in the requested language. Quotes stay in the language of the source passage (do not translate a quote).
6. If the applicant left material facts unknown, include at least one claim explaining what turns on such a fact, citing the passage that sets the condition.
"""


def _rules_block(rules: Sequence[Rule]) -> str:
    lines = ["Matched rules (deterministic result; do not re-evaluate):"]
    for rule in rules:
        lines.append(
            f"- rule_id={rule.rule_id}; pathway={rule.pathway}; route_class={rule.route_class}; "
            f"group={rule.display_group}; citation={rule.citation.source}; "
            f"sources={', '.join(rule.source_dependencies)}\n  notes: {rule.notes}"
        )
    return "\n".join(lines)


def _facts_block(intake: dict[str, Any], unresolved: Sequence[str]) -> str:
    facts = "\n".join(f"- {k}: {v}" for k, v in sorted(intake.items()))
    unknowns = ", ".join(unresolved) if unresolved else "none"
    return f"Applicant's confirmed facts:\n{facts}\nFacts the applicant marked unknown: {unknowns}"


def _passages_block(passages: Sequence[Passage], corpus: CorpusIndex) -> str:
    lines = ["Source passages (cite by passage_id; quote verbatim):"]
    for passage in passages:
        document = corpus.documents[passage.source_id]
        lines.append(
            f'<passage id="{passage.passage_id}" source="{document.label}">\n'
            f"{passage.text}\n</passage>"
        )
    return "\n".join(lines)


def explanation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "citations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "passage_id": {"type": "string"},
                                    "quote": {"type": "string"},
                                },
                                "required": ["passage_id", "quote"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["text", "citations"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["claims"],
        "additionalProperties": False,
    }


def grounding_passages(
    rules: Sequence[Rule],
    corpus: CorpusIndex,
    *,
    per_rule: int = PASSAGES_PER_RULE,
    limit: int = MAX_PASSAGES,
) -> list[Passage]:
    """Passages from the matched rules' own source documents, most relevant first.

    Each rule contributes the passage holding its recorded excerpt (when that
    excerpt locates in the corpus) and the top lexical matches for the rule's
    pathway, citation, and notes. Scope is the rules' declared
    ``source_dependencies``; nothing outside those documents is offered.
    The ``limit`` is filled round-robin across rules — every rule's first
    passage before any rule's second — so a long match list cannot starve
    the last rules of grounding text.
    """
    per_rule_lists: list[list[Passage]] = []
    for rule in rules:
        ordered: dict[str, Passage] = {}
        candidates = corpus.passages_for(rule.source_dependencies)
        excerpt = rule.citation.excerpt
        if excerpt:
            for source_id in rule.source_dependencies:
                match = corpus.locate_excerpt(source_id, excerpt)
                if match and match.passage_id:
                    passage = corpus.passage(match.passage_id)
                    if passage:
                        ordered.setdefault(passage.passage_id, passage)
                    break
        query = " ".join(
            [
                rule.pathway,
                rule.citation.source,
                rule.notes,
                rule.citation.excerpt or "",
            ]
        )
        for ranked in rank_passages(query, candidates, per_rule):
            ordered.setdefault(ranked.passage.passage_id, ranked.passage)
        per_rule_lists.append(list(ordered.values()))
    chosen: dict[str, Passage] = {}
    depth = max((len(lst) for lst in per_rule_lists), default=0)
    for position in range(depth):
        for lst in per_rule_lists:
            if position < len(lst):
                chosen.setdefault(lst[position].passage_id, lst[position])
    return list(chosen.values())[:limit]


def unresolved_facts(intake: dict[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(k for k, v in intake.items() if v == "unknown"))


def _verify_claim(
    raw: Any, offered: dict[str, Passage], corpus: CorpusIndex
) -> Claim | WithheldClaim:
    if not isinstance(raw, dict) or not isinstance(raw.get("text"), str):
        return WithheldClaim("", ("malformed claim",))
    text = raw["text"].strip()
    raw_citations = raw.get("citations")
    if not text:
        return WithheldClaim("", ("empty claim",))
    if not isinstance(raw_citations, list) or not raw_citations:
        return WithheldClaim(text, ("no citation",))
    citations: list[Citation] = []
    reasons: list[str] = []
    for item in raw_citations:
        citation = _verify_citation(item, offered, corpus)
        citations.append(citation)
        if not citation.verified:
            reasons.append(
                f"{citation.passage_id}: {citation.reason} (quote: {citation.quote[:120]!r})"
            )
    if reasons:
        return WithheldClaim(text, tuple(reasons))
    return Claim(text, tuple(citations))


def _verify_citation(
    item: Any, offered: dict[str, Passage], corpus: CorpusIndex
) -> Citation:
    passage_id = str(item.get("passage_id", "")) if isinstance(item, dict) else ""
    quote = str(item.get("quote", "")) if isinstance(item, dict) else ""
    passage = offered.get(passage_id)
    if passage is None:
        return Citation(
            passage_id, None, None, None, quote, False, "passage was not offered"
        )
    document = corpus.documents[passage.source_id]
    match = corpus.verify_quote(passage.source_id, quote)
    if match is None:
        return Citation(
            passage_id,
            passage.source_id,
            document.label,
            document.url,
            quote,
            False,
            "quote does not occur in the source text",
        )
    return Citation(
        passage_id, passage.source_id, document.label, document.url, quote, True, None
    )


def matched_rules(
    intake: dict[str, Any],
    rules: Iterable[Rule],
    expected_rule_ids: Sequence[str] | None,
) -> list[Rule]:
    results = screen(intake, list(rules))
    matched = [result.rule for result in results]
    if expected_rule_ids is not None:
        expected = sorted(set(expected_rule_ids))
        actual = sorted({rule.rule_id for rule in matched})
        if expected != actual:
            raise MatcherDisagreement(
                "the deterministic matcher produced a different rule set than the "
                f"request claimed: matcher={actual}, request={expected}"
            )
    return matched


def explain_result(
    *,
    intake: dict[str, Any],
    rules: Sequence[Rule],
    corpus: CorpusIndex,
    provider: Provider,
    language: str,
    expected_rule_ids: Sequence[str] | None = None,
) -> Explanation:
    if language not in LANGUAGES:
        raise ExplainError(f"language must be one of {', '.join(LANGUAGES)}")
    matched = matched_rules(intake, rules, expected_rule_ids)
    rule_ids = tuple(rule.rule_id for rule in matched)
    unresolved = unresolved_facts(intake)
    if not matched:
        return Explanation(
            language,
            (),
            (),
            (),
            (),
            unresolved,
            AI_LABEL[language],
            provider.name,
            provider.model,
            PROMPT_VERSION,
            0,
            0,
        )
    passages = grounding_passages(matched, corpus)
    offered = {p.passage_id: p for p in passages}
    language_name = "Spanish" if language == "es" else "English"
    user = "\n\n".join(
        [
            f"Write the claims in {language_name}.",
            _rules_block(matched),
            _facts_block(intake, unresolved),
            _passages_block(passages, corpus),
        ]
    )
    completion = provider.complete_json(
        system=_SYSTEM_PROMPT,
        user=user,
        schema=explanation_schema(),
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    try:
        parsed = json.loads(completion.text)
    except ValueError as exc:
        raise ExplainError("the model did not return JSON") from exc
    raw_claims = parsed.get("claims") if isinstance(parsed, dict) else None
    if not isinstance(raw_claims, list):
        raise ExplainError("the model did not return a claims list")
    claims: list[Claim] = []
    withheld: list[WithheldClaim] = []
    for raw in raw_claims:
        outcome = _verify_claim(raw, offered, corpus)
        if isinstance(outcome, Claim):
            claims.append(outcome)
        else:
            withheld.append(outcome)
    return Explanation(
        language=language,
        rule_ids=rule_ids,
        claims=tuple(claims),
        withheld=tuple(withheld),
        offered_passage_ids=tuple(offered),
        unresolved_facts=unresolved,
        label=AI_LABEL[language],
        provider=completion.provider,
        model=completion.model,
        prompt_version=PROMPT_VERSION,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
    )


@dataclass(frozen=True)
class Answer:
    language: str
    question: str
    rule_ids: tuple[str, ...]
    claims: tuple[Claim, ...]
    withheld: tuple[WithheldClaim, ...]
    abstained: bool
    staff_question: str | None
    offered_passage_ids: tuple[str, ...]
    label: str
    provider: str
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["withheld_count"] = len(self.withheld)
        return payload


_ASK_SYSTEM_PROMPT = """You answer one follow-up question from a California housing applicant about a deterministic screening result, using only the source passages provided. The screening tool has already decided which candidate rules match; you do not re-evaluate anything.

Hard rules:
1. Answer only with claims you can support from the provided passages. Each claim must cite one or more passages by passage_id with a verbatim quote of at least eight consecutive words from that exact passage. Do not alter or paraphrase inside a quote. An inexact quote causes the whole claim to be withheld.
2. If the passages do not answer the question (for example fees, forms, timelines, or local standards they do not state), return an empty claims list and set "abstain" to true. Always fill "staff_question": if any part of the question is not settled by the passages, one sentence the applicant can ask their planning counter, in the requested language; otherwise an empty string. Do not answer from memory, and do not guess local rules, fees, or deadlines.
3. Never give advice, predict approval, or say the project qualifies. Describe what the cited passage provides and what still depends on unconfirmed facts.
4. Plain language, short sentences, at most five claims, in the requested language. Quotes stay in the source language.
"""


def answer_schema() -> dict[str, Any]:
    schema = explanation_schema()
    schema["properties"]["abstain"] = {"type": "boolean"}
    schema["properties"]["staff_question"] = {"type": "string"}
    schema["required"] = ["claims", "abstain", "staff_question"]
    return schema


def question_passages(
    question: str, rules: Sequence[Rule], corpus: CorpusIndex
) -> list[Passage]:
    """The rule-scoped grounding set plus the passages that best match the
    question itself, still only from the matched rules' source documents."""
    chosen = {p.passage_id: p for p in grounding_passages(rules, corpus)}
    candidates: dict[str, Passage] = {}
    for rule in rules:
        for passage in corpus.passages_for(rule.source_dependencies):
            candidates.setdefault(passage.passage_id, passage)
    for ranked in rank_passages(question, list(candidates.values()), QUESTION_PASSAGES):
        chosen.setdefault(ranked.passage.passage_id, ranked.passage)
    return list(chosen.values())[: MAX_PASSAGES + QUESTION_PASSAGES]


def answer_question(
    *,
    question: str,
    intake: dict[str, Any],
    rules: Sequence[Rule],
    corpus: CorpusIndex,
    provider: Provider,
    language: str,
    expected_rule_ids: Sequence[str] | None = None,
) -> Answer:
    if language not in LANGUAGES:
        raise ExplainError(f"language must be one of {', '.join(LANGUAGES)}")
    cleaned = " ".join(question.split())
    if not cleaned:
        raise ExplainError("the question is empty")
    if len(cleaned) > MAX_QUESTION_CHARS:
        raise ExplainError(
            f"the question is longer than {MAX_QUESTION_CHARS} characters"
        )
    matched = matched_rules(intake, rules, expected_rule_ids)
    rule_ids = tuple(rule.rule_id for rule in matched)
    unresolved = unresolved_facts(intake)
    if not matched:
        return Answer(
            language,
            cleaned,
            (),
            (),
            (),
            True,
            None,
            (),
            AI_LABEL[language],
            provider.name,
            provider.model,
            ASK_PROMPT_VERSION,
            0,
            0,
        )
    passages = question_passages(cleaned, matched, corpus)
    offered = {p.passage_id: p for p in passages}
    language_name = "Spanish" if language == "es" else "English"
    user = "\n\n".join(
        [
            f"Answer in {language_name}.",
            f"Applicant's question: {cleaned}",
            _rules_block(matched),
            _facts_block(intake, unresolved),
            _passages_block(passages, corpus),
        ]
    )
    completion = provider.complete_json(
        system=_ASK_SYSTEM_PROMPT,
        user=user,
        schema=answer_schema(),
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    try:
        parsed = json.loads(completion.text)
    except ValueError as exc:
        raise ExplainError("the model did not return JSON") from exc
    if not isinstance(parsed, dict) or not isinstance(parsed.get("claims"), list):
        raise ExplainError("the model did not return a claims list")
    claims: list[Claim] = []
    withheld: list[WithheldClaim] = []
    for raw in parsed["claims"][:5]:
        outcome = _verify_claim(raw, offered, corpus)
        if isinstance(outcome, Claim):
            claims.append(outcome)
        else:
            withheld.append(outcome)
    staff_question = parsed.get("staff_question")
    staff_text = staff_question.strip() if isinstance(staff_question, str) else ""
    abstained = not claims
    return Answer(
        language=language,
        question=cleaned,
        rule_ids=rule_ids,
        claims=tuple(claims),
        withheld=tuple(withheld),
        abstained=abstained,
        staff_question=staff_text or None,
        offered_passage_ids=tuple(offered),
        label=AI_LABEL[language],
        provider=completion.provider,
        model=completion.model,
        prompt_version=ASK_PROMPT_VERSION,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
    )
