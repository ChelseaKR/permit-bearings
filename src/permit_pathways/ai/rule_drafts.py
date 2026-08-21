"""Ordinance-to-rule drafting: unreviewed proposals for a person to review.

Given an ordinance text, ask the model to propose rule entries in the
``data/rules`` schema. Three controls keep a proposal from becoming a rule:

1. Every proposed ``citation.excerpt`` must occur verbatim in the ordinance
   text the caller supplied (the same normalization the explanation verifier
   uses). A draft whose excerpt does not occur is rejected, with the reason.
2. Every accepted draft must load through :func:`permit_pathways.screening.load_rules`
   from a scratch directory, so it satisfies the real schema, and its
   criteria must use only the intake vocabulary.
3. The output is a wrapper document whose top level is an object with
   ``status: unreviewed_ai_draft`` — not the rules-file array — written to a
   directory outside ``data/rules`` (``ai-drafts/`` by default, which is
   ignored by Git). The matcher cannot load it; a person has to read it,
   decide, and author the real rule with its own source registry entry and
   review metadata.

``verified_on`` is always ``null`` on a draft. A draft is a reading
suggestion, never evidence.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..screening import DISPLAY_GROUPS, ROUTE_CLASSES, load_rules
from . import facts
from .corpus import MIN_QUOTE_CHARS, normalize_for_match
from .provider import Provider, ProviderError, provider_from_env

PROMPT_VERSION = "rule-drafts-v1"
MAX_OUTPUT_TOKENS = 8000
MAX_ORDINANCE_CHARS = 120_000
MAX_DRAFTS = 8
DRAFT_STATUS = "unreviewed_ai_draft"
DEFAULT_OUTPUT_DIR = "ai-drafts"
BOUNDARY = (
    "These are AI-proposed readings of one ordinance text. They are not rules, "
    "have not been reviewed by any person, jurisdiction, or counsel, carry no "
    "source-check date, and cannot be loaded by the matcher in this form. A person "
    "must decide whether each proposal is a correct reading, register the source, "
    "and author the rule with its own review metadata."
)
_RULE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")


class RuleDraftError(ValueError):
    """The request or the model output could not be used."""


@dataclass(frozen=True)
class RejectedDraft:
    proposal: dict[str, Any]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RuleDraftResult:
    jurisdiction: str
    source_id: str
    accepted: tuple[dict[str, Any], ...]
    rejected: tuple[RejectedDraft, ...]
    provider: str
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int

    def to_document(self) -> dict[str, Any]:
        return {
            "status": DRAFT_STATUS,
            "boundary": BOUNDARY,
            "drafted_on": dt.datetime.now(dt.UTC).date().isoformat(),
            "jurisdiction": self.jurisdiction,
            "source_id": self.source_id,
            "provider": self.provider,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "proposed_rules": list(self.accepted),
            "rejected_proposals": [asdict(r) for r in self.rejected],
        }


_SYSTEM_PROMPT = """You read one local ordinance text and propose candidate rule entries for a deterministic permit-screening tool. A person will review every proposal; nothing you write is published. Propose only what the text states as an objective, testable standard or a process fact, and only where it can be expressed with the intake vocabulary below. Do not propose a rule the text does not support, do not generalize from state law you remember, and do not invent section numbers.

Each proposal must have exactly these keys:
- rule_id: lowercase identifier starting with the jurisdiction slug and "-draft-" (for example "capitola-draft-adu-parking").
- pathway: a short plain-language title.
- display_group: one of route, standard, local_process.
- route_class: one of ministerial, discretionary, mixed.
- jurisdiction_scope: exactly the jurisdiction slug given.
- source_dependencies: exactly the one source ID given, in a list.
- criteria: a non-empty list of {field, op, value}. "field" must be one of the vocabulary fields; "op" is "eq" or "in"; "value" must be an allowed value for that field (a list of allowed values for "in").
- citation: {source: "<source label>, <section as written>", url: "<the URL given>", excerpt: "<a verbatim passage of at least 25 words copied exactly from the ordinance text that states the standard>", verified_on: null}.
- required_documents: a list of document names only if the text names them; otherwise an empty list.
- notes: one or two sentences, plain language, saying what the passage provides and what a reviewer should check.

The excerpt must be copied exactly from the ordinance text; a proposal whose excerpt is not an exact substring will be rejected. Propose at most the number of rules requested. If the text supports nothing expressible in the vocabulary, return an empty list.
"""


def _vocabulary_block() -> str:
    lines = [f"- project_type: {', '.join(facts.PROJECT_TYPES)}"]
    for field in facts.FACT_FIELDS:
        lines.append(
            f"- {field.name}: {', '.join(field.concrete_values)} ({field.meaning})"
        )
    return "Intake vocabulary (field: allowed values):\n" + "\n".join(lines)


def drafts_schema() -> dict[str, Any]:
    criterion = {
        "type": "object",
        "properties": {
            "field": {"type": "string"},
            "op": {"type": "string", "enum": ["eq", "in"]},
            "value": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["field", "op", "value"],
        "additionalProperties": False,
    }
    citation = {
        "type": "object",
        "properties": {
            "source": {"type": "string"},
            "url": {"type": "string"},
            "excerpt": {"type": "string"},
        },
        "required": ["source", "url", "excerpt"],
        "additionalProperties": False,
    }
    rule = {
        "type": "object",
        "properties": {
            "rule_id": {"type": "string"},
            "pathway": {"type": "string"},
            "display_group": {"type": "string", "enum": list(DISPLAY_GROUPS)},
            "route_class": {"type": "string", "enum": list(ROUTE_CLASSES)},
            "jurisdiction_scope": {"type": "string"},
            "source_dependencies": {"type": "array", "items": {"type": "string"}},
            "criteria": {"type": "array", "items": criterion},
            "citation": citation,
            "required_documents": {"type": "array", "items": {"type": "string"}},
            "notes": {"type": "string"},
        },
        "required": [
            "rule_id",
            "pathway",
            "display_group",
            "route_class",
            "jurisdiction_scope",
            "source_dependencies",
            "criteria",
            "citation",
            "required_documents",
            "notes",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"proposals": {"type": "array", "items": rule}},
        "required": ["proposals"],
        "additionalProperties": False,
    }


def _normalize_proposal(raw: dict[str, Any]) -> dict[str, Any]:
    """Turn the schema's uniform shapes back into the rules-file shape."""
    criteria = []
    for item in raw.get("criteria", []):
        values = list(item.get("value", []))
        if item.get("op") == "eq":
            criteria.append(
                {
                    "field": item.get("field"),
                    "op": "eq",
                    "value": values[0] if values else "",
                }
            )
        else:
            criteria.append({"field": item.get("field"), "op": "in", "value": values})
    citation = dict(raw.get("citation", {}))
    return {
        "rule_id": raw.get("rule_id"),
        "pathway": raw.get("pathway"),
        "display_group": raw.get("display_group"),
        "route_class": raw.get("route_class"),
        "jurisdiction_scope": raw.get("jurisdiction_scope"),
        "source_dependencies": list(raw.get("source_dependencies", [])),
        "criteria": criteria,
        "citation": {
            "source": citation.get("source"),
            "url": citation.get("url"),
            "excerpt": citation.get("excerpt"),
            "verified_on": None,
        },
        "required_documents": list(raw.get("required_documents", [])),
        "notes": raw.get("notes"),
    }


def _vocabulary_problems(proposal: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for criterion in proposal["criteria"]:
        field = criterion.get("field")
        allowed = facts.allowed_values(str(field))
        if not allowed:
            problems.append(
                f"criterion field {field!r} is not in the intake vocabulary"
            )
            continue
        values = (
            criterion["value"]
            if isinstance(criterion["value"], list)
            else [criterion["value"]]
        )
        for value in values:
            if value not in allowed or value == facts.UNKNOWN:
                problems.append(
                    f"criterion {field}={value!r} is not an allowed concrete value"
                )
    return problems


def _schema_problems(proposal: dict[str, Any]) -> list[str]:
    """Prove the proposal loads through the real rule loader."""
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / "draft.json"
        path.write_text(json.dumps([proposal]), encoding="utf-8")
        try:
            load_rules(path.parent)
        except (ValueError, TypeError, KeyError) as exc:
            return [f"rule schema: {exc}"]
    return []


def validate_proposal(
    raw: Any, *, ordinance_text: str, jurisdiction: str, source_id: str
) -> dict[str, Any] | RejectedDraft:
    if not isinstance(raw, dict):
        return RejectedDraft({}, ("malformed proposal",))
    proposal = _normalize_proposal(raw)
    reasons: list[str] = []
    rule_id = str(proposal.get("rule_id") or "")
    if not _RULE_ID.match(rule_id) or not rule_id.startswith(f"{jurisdiction}-draft-"):
        reasons.append(f"rule_id {rule_id!r} must start with {jurisdiction}-draft-")
    if proposal.get("jurisdiction_scope") != jurisdiction:
        reasons.append("jurisdiction_scope must equal the jurisdiction slug")
    if proposal.get("source_dependencies") != [source_id]:
        reasons.append("source_dependencies must be exactly the given source ID")
    excerpt = proposal["citation"].get("excerpt")
    needle = normalize_for_match(str(excerpt or ""))
    if len(needle) < MIN_QUOTE_CHARS or needle not in normalize_for_match(
        ordinance_text
    ):
        reasons.append("excerpt does not occur verbatim in the ordinance text")
    reasons.extend(_vocabulary_problems(proposal))
    if not reasons:
        reasons.extend(_schema_problems(proposal))
    if reasons:
        return RejectedDraft(proposal, tuple(reasons))
    return proposal


def draft_rules(
    ordinance_text: str,
    *,
    jurisdiction: str,
    source_id: str,
    source_label: str,
    url: str,
    provider: Provider,
    max_rules: int = MAX_DRAFTS,
) -> RuleDraftResult:
    text = ordinance_text.strip()
    if not text:
        raise RuleDraftError("the ordinance text is empty")
    if len(text) > MAX_ORDINANCE_CHARS:
        raise RuleDraftError(
            f"the ordinance text is longer than {MAX_ORDINANCE_CHARS} characters"
        )
    if not _RULE_ID.match(jurisdiction) or not _RULE_ID.match(source_id):
        raise RuleDraftError("jurisdiction and source_id must be lowercase identifiers")
    if not url.startswith("https://"):
        raise RuleDraftError("url must be https")
    user = "\n\n".join(
        [
            f"Jurisdiction slug: {jurisdiction}\nSource ID: {source_id}\n"
            f"Source label: {source_label}\nURL: {url}\n"
            f"Propose at most {max(1, min(max_rules, MAX_DRAFTS))} rules.",
            _vocabulary_block(),
            f"<ordinance>\n{text}\n</ordinance>",
        ]
    )
    completion = provider.complete_json(
        system=_SYSTEM_PROMPT,
        user=user,
        schema=drafts_schema(),
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    try:
        parsed = json.loads(completion.text)
    except ValueError as exc:
        raise RuleDraftError("the model did not return JSON") from exc
    proposals = parsed.get("proposals") if isinstance(parsed, dict) else None
    if not isinstance(proposals, list):
        raise RuleDraftError("the model did not return a proposals list")
    accepted: list[dict[str, Any]] = []
    rejected: list[RejectedDraft] = []
    seen: set[str] = set()
    for raw in proposals[:MAX_DRAFTS]:
        outcome = validate_proposal(
            raw, ordinance_text=text, jurisdiction=jurisdiction, source_id=source_id
        )
        if isinstance(outcome, RejectedDraft):
            rejected.append(outcome)
        elif outcome["rule_id"] in seen:
            rejected.append(RejectedDraft(outcome, ("duplicate rule_id",)))
        else:
            seen.add(outcome["rule_id"])
            accepted.append(outcome)
    return RuleDraftResult(
        jurisdiction=jurisdiction,
        source_id=source_id,
        accepted=tuple(accepted),
        rejected=tuple(rejected),
        provider=completion.provider,
        model=completion.model,
        prompt_version=PROMPT_VERSION,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
    )


def write_draft_document(result: RuleDraftResult, output_dir: Path) -> Path:
    """Write the wrapper document outside data/rules; refuse that directory."""
    resolved = output_dir.resolve()
    if "rules" in resolved.parts and "data" in resolved.parts:
        raise RuleDraftError("drafts may not be written under data/rules")
    resolved.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H%M%SZ")
    path = resolved / f"{result.jurisdiction}-{stamp}-unreviewed.json"
    path.write_text(
        json.dumps(result.to_document(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - CLI wrapper
    parser = argparse.ArgumentParser(
        description="Propose unreviewed rule drafts from an ordinance text (ADR 0004)."
    )
    parser.add_argument(
        "--ordinance", type=Path, required=True, help="plain-text ordinance file"
    )
    parser.add_argument(
        "--jurisdiction", required=True, help="registry slug, e.g. capitola"
    )
    parser.add_argument(
        "--source-id", required=True, help="source ID the reviewer will register"
    )
    parser.add_argument("--source-label", required=True)
    parser.add_argument("--url", required=True, help="https URL of the official text")
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--max-rules", type=int, default=MAX_DRAFTS)
    args = parser.parse_args(argv)
    try:
        provider = provider_from_env()
        result = draft_rules(
            args.ordinance.read_text(encoding="utf-8"),
            jurisdiction=args.jurisdiction,
            source_id=args.source_id,
            source_label=args.source_label,
            url=args.url,
            provider=provider,
            max_rules=args.max_rules,
        )
        path = write_draft_document(result, args.output_dir)
    except (ProviderError, RuleDraftError, OSError) as exc:
        print(f"rule-drafts: {exc}")
        return 2
    print(
        f"rule-drafts: {len(result.accepted)} proposal(s) accepted for review, "
        f"{len(result.rejected)} rejected; written to {path} ({DRAFT_STATUS})"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
