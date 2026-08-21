"""Ordinance-to-rule drafting: verbatim excerpts, real schema, never data/rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.ai.provider import ScriptedProvider
from permit_pathways.ai.rule_drafts import (
    DRAFT_STATUS,
    MAX_ORDINANCE_CHARS,
    RejectedDraft,
    RuleDraftError,
    draft_rules,
    drafts_schema,
    validate_proposal,
    write_draft_document,
)
from permit_pathways.screening import load_rules

ROOT = Path(__file__).resolve().parents[1]
ORDINANCE = (ROOT / "corpus" / "ordinances" / "capitola.txt").read_text(
    encoding="utf-8"
)
URL = "https://www.codepublishing.com/CA/Capitola/html/Capitola17/Capitola1774.html"
EXCERPT = " ".join(ORDINANCE.split()[200:240])


def _proposal(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "rule_id": "capitola-draft-adu-example",
        "pathway": "Capitola example draft",
        "display_group": "local_process",
        "route_class": "ministerial",
        "jurisdiction_scope": "capitola",
        "source_dependencies": ["capitola-muni-code-17-74"],
        "criteria": [{"field": "project_type", "op": "in", "value": ["adu", "jadu"]}],
        "citation": {
            "source": "Capitola Municipal Code, 17.74.030",
            "url": URL,
            "excerpt": EXCERPT,
        },
        "required_documents": [],
        "notes": "What the passage provides; what to check.",
    }
    base.update(overrides)
    return base


def _draft(proposals: list[dict[str, Any]], text: str = ORDINANCE) -> Any:
    provider = ScriptedProvider([json.dumps({"proposals": proposals})])
    return draft_rules(
        text,
        jurisdiction="capitola",
        source_id="capitola-muni-code-17-74",
        source_label="Capitola Municipal Code, Title 17, Ch. 17.74",
        url=URL,
        provider=provider,
    )


def test_accepted_proposal_loads_through_the_real_rule_loader(tmp_path: Path) -> None:
    result = _draft([_proposal()])
    assert len(result.accepted) == 1 and result.rejected == ()
    rule = result.accepted[0]
    assert rule["citation"]["verified_on"] is None
    (tmp_path / "draft.json").write_text(json.dumps([rule]), encoding="utf-8")
    loaded = load_rules(tmp_path)
    assert loaded[0].rule_id == "capitola-draft-adu-example"
    assert loaded[0].citation.is_verified is False
    document = result.to_document()
    assert document["status"] == DRAFT_STATUS and document["proposed_rules"] == [rule]
    assert "not rules" in document["boundary"]


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        (
            {
                "citation": {
                    "source": "s",
                    "url": URL,
                    "excerpt": "words that are not in the ordinance at all whatsoever",
                }
            },
            "verbatim",
        ),
        ({"citation": {"source": "s", "url": URL, "excerpt": "short"}}, "verbatim"),
        ({"rule_id": "capitola-adu-example"}, "must start with capitola-draft-"),
        ({"rule_id": "Capitola-draft-X"}, "must start with"),
        ({"jurisdiction_scope": "davis"}, "jurisdiction_scope"),
        ({"source_dependencies": ["other"]}, "source_dependencies"),
        (
            {"criteria": [{"field": "lot_size", "op": "eq", "value": ["5000"]}]},
            "not in the intake vocabulary",
        ),
        (
            {"criteria": [{"field": "sf_zone", "op": "eq", "value": ["unknown"]}]},
            "not an allowed concrete value",
        ),
        ({"criteria": []}, "rule schema"),
        (
            {
                "citation": {
                    "source": "s",
                    "url": "http://insecure.test",
                    "excerpt": EXCERPT,
                }
            },
            "rule schema",
        ),
    ],
)
def test_rejected_proposals_carry_the_reason(
    overrides: dict[str, Any], reason: str
) -> None:
    result = _draft([_proposal(**overrides)])
    assert result.accepted == ()
    assert len(result.rejected) == 1
    assert any(reason in r for r in result.rejected[0].reasons), result.rejected[
        0
    ].reasons


def test_malformed_and_duplicate_proposals_are_rejected() -> None:
    result = _draft([_proposal(), _proposal(), "junk"])  # type: ignore[list-item]
    assert len(result.accepted) == 1
    reasons = [r.reasons for r in result.rejected]
    assert ("duplicate rule_id",) in reasons
    assert ("malformed proposal",) in reasons
    outcome = validate_proposal(
        None, ordinance_text="x", jurisdiction="j", source_id="s"
    )
    assert isinstance(outcome, RejectedDraft)


def test_request_validation_and_bad_model_output() -> None:
    kwargs = {
        "jurisdiction": "capitola",
        "source_id": "capitola-muni-code-17-74",
        "source_label": "label",
        "url": URL,
    }
    with pytest.raises(RuleDraftError, match="empty"):
        draft_rules("   ", provider=ScriptedProvider([]), **kwargs)
    with pytest.raises(RuleDraftError, match="longer than"):
        draft_rules(
            "x" * (MAX_ORDINANCE_CHARS + 1), provider=ScriptedProvider([]), **kwargs
        )
    with pytest.raises(RuleDraftError, match="identifiers"):
        draft_rules(
            ORDINANCE,
            provider=ScriptedProvider([]),
            **{**kwargs, "jurisdiction": "Capitola!"},
        )
    with pytest.raises(RuleDraftError, match="https"):
        draft_rules(
            ORDINANCE, provider=ScriptedProvider([]), **{**kwargs, "url": "http://x"}
        )
    with pytest.raises(RuleDraftError, match="did not return JSON"):
        draft_rules(ORDINANCE, provider=ScriptedProvider(["?"]), **kwargs)
    with pytest.raises(RuleDraftError, match="proposals list"):
        draft_rules(
            ORDINANCE, provider=ScriptedProvider(['{"proposals": 1}']), **kwargs
        )
    schema = drafts_schema()
    assert schema["properties"]["proposals"]["items"]["additionalProperties"] is False


def test_draft_document_is_written_outside_data_rules(tmp_path: Path) -> None:
    result = _draft([_proposal()])
    path = write_draft_document(result, tmp_path / "ai-drafts")
    assert path.name.startswith("capitola-") and path.name.endswith("-unreviewed.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == DRAFT_STATUS
    # The wrapper is an object, so the rule loader refuses it even if copied.
    with pytest.raises((ValueError, TypeError)):
        load_rules(path.parent)
    with pytest.raises(RuleDraftError, match="data/rules"):
        write_draft_document(result, tmp_path / "data" / "rules")
    assert not (tmp_path / "data" / "rules").exists()
