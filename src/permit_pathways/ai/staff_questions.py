"""Tailored questions to take to local staff, drafted by the model.

The generic trio the static page shows ("is the local ordinance current",
"do these facts hold", "what is the process") is replaced, when the service
runs, by questions drafted for this applicant: the facts they could not
answer, the matched rules whose conditions turn on those facts, and whether
the repository has any local record for the jurisdiction. The output is a
labeled draft. Each question may point at a matched rule or an unresolved
fact; pointers that do not resolve are dropped rather than shown.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from ..screening import Rule
from . import facts
from .explain import LANGUAGES, ExplainError, matched_rules, unresolved_facts
from .provider import Provider

PROMPT_VERSION = "staff-questions-v1"
MAX_OUTPUT_TOKENS = 2000
MAX_QUESTIONS = 8
DRAFT_LABEL = {
    "en": "AI-drafted questions for local staff. They are prompts for a "
    "conversation, not a checklist of requirements; staff may ask for other "
    "things and may answer differently than the matched rules suggest.",
    "es": "Preguntas redactadas por IA para el personal local. Son un punto de "
    "partida para la conversación, no una lista de requisitos; el personal puede "
    "pedir otras cosas y responder de forma distinta a lo que sugieren las reglas.",
}


@dataclass(frozen=True)
class StaffQuestion:
    question: str
    why: str
    rule_id: str | None
    fact: str | None


@dataclass(frozen=True)
class StaffQuestions:
    language: str
    rule_ids: tuple[str, ...]
    unresolved_facts: tuple[str, ...]
    local_record: bool
    questions: tuple[StaffQuestion, ...]
    label: str
    provider: str
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SYSTEM_PROMPT = """You draft questions a California housing applicant should ask their city or county planning counter before filing. A deterministic screening tool has already matched candidate rules to the applicant's confirmed facts; some facts are unknown. Your questions help the applicant resolve what the tool could not, and confirm local specifics the statewide rules do not settle.

Rules:
1. Write between three and eight questions, each one sentence, in the requested language, addressed to staff in the applicant's voice ("Does the City...", "¿La Ciudad...?").
2. Each question must be specific to this applicant: tie it to an unknown fact (set "fact" to that fact name) or to a matched rule whose condition needs local confirmation (set "rule_id" to that rule_id). Use only the fact names and rule_ids provided; set them to null when a question is general.
3. "why" is one short sentence saying what the answer changes for the applicant. Do not state legal conclusions, fees, or deadlines that the provided rules do not contain.
4. If the repository has no local record for the jurisdiction, include one question asking staff for the current local ADU/SB 9 ordinance, application form, checklist, and fee schedule.
5. Do not promise outcomes or say the project qualifies.
"""


def questions_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "why": {"type": "string"},
                        "rule_id": {"type": ["string", "null"]},
                        "fact": {"type": ["string", "null"]},
                    },
                    "required": ["question", "why", "rule_id", "fact"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["questions"],
        "additionalProperties": False,
    }


def has_local_record(jurisdiction: str | None, rules: Sequence[Rule]) -> bool:
    return bool(jurisdiction) and any(
        r.jurisdiction_scope == jurisdiction for r in rules
    )


def _user_prompt(
    intake: dict[str, Any],
    matched: Sequence[Rule],
    unresolved: Sequence[str],
    local_record: bool,
    language: str,
) -> str:
    language_name = "Spanish" if language == "es" else "English"
    rule_lines = (
        "\n".join(
            f"- {r.rule_id}: {r.pathway} ({r.route_class}); {r.citation.source}; notes: {r.notes}"
            for r in matched
        )
        or "- none matched"
    )
    fact_lines = "\n".join(f"- {k}: {v}" for k, v in sorted(intake.items()))
    unknown_lines = (
        "\n".join(
            f"- {name}: {facts.FIELDS_BY_NAME[name].meaning}"
            if name in facts.FIELDS_BY_NAME
            else f"- {name}"
            for name in unresolved
        )
        or "- none"
    )
    local = (
        "The repository has a bounded local record for this jurisdiction; it is not "
        "comprehensive local-code coverage."
        if local_record
        else "The repository has no local record for this jurisdiction."
    )
    return "\n\n".join(
        [
            f"Write the questions in {language_name}.",
            f"Matched rules:\n{rule_lines}",
            f"Confirmed facts:\n{fact_lines}",
            f"Unknown facts:\n{unknown_lines}",
            local,
        ]
    )


def draft_staff_questions(
    *,
    intake: dict[str, Any],
    rules: Sequence[Rule],
    provider: Provider,
    language: str,
    expected_rule_ids: Sequence[str] | None = None,
) -> StaffQuestions:
    if language not in LANGUAGES:
        raise ExplainError(f"language must be one of {', '.join(LANGUAGES)}")
    matched = matched_rules(intake, rules, expected_rule_ids)
    rule_ids = tuple(r.rule_id for r in matched)
    unresolved = unresolved_facts(intake)
    jurisdiction = intake.get("jurisdiction")
    local_record = has_local_record(
        jurisdiction if isinstance(jurisdiction, str) else None, rules
    )
    completion = provider.complete_json(
        system=_SYSTEM_PROMPT,
        user=_user_prompt(intake, matched, unresolved, local_record, language),
        schema=questions_schema(),
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    try:
        parsed = json.loads(completion.text)
    except ValueError as exc:
        raise ExplainError("the model did not return JSON") from exc
    raw = parsed.get("questions") if isinstance(parsed, dict) else None
    if not isinstance(raw, list):
        raise ExplainError("the model did not return a questions list")
    known_facts = set(unresolved) | set(
        facts.material_fields(str(intake.get("project_type", "")))
    )
    questions: list[StaffQuestion] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        if not question:
            continue
        rule_id = item.get("rule_id")
        fact = item.get("fact")
        questions.append(
            StaffQuestion(
                question=question,
                why=str(item.get("why", "")).strip(),
                rule_id=rule_id
                if isinstance(rule_id, str) and rule_id in rule_ids
                else None,
                fact=fact if isinstance(fact, str) and fact in known_facts else None,
            )
        )
        if len(questions) == MAX_QUESTIONS:
            break
    return StaffQuestions(
        language=language,
        rule_ids=rule_ids,
        unresolved_facts=unresolved,
        local_record=local_record,
        questions=tuple(questions),
        label=DRAFT_LABEL[language],
        provider=completion.provider,
        model=completion.model,
        prompt_version=PROMPT_VERSION,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
    )
