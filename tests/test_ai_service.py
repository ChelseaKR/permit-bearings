"""The optional AI service: request validation, error translation, no storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from permit_pathways.ai import facts
from permit_pathways.ai import service as service_module
from permit_pathways.ai.provider import ProviderError, ScriptedProvider
from permit_pathways.ai.service import (
    DEFAULT_ORIGINS,
    RequestError,
    ServiceContext,
    allowed_origins_from_env,
    create_app,
    repository_root,
    validate_intake,
)

ROOT = Path(__file__).resolve().parents[1]
DAVIS_ADU = {
    "project_type": "adu",
    "jurisdiction": "davis",
    "primary_dwelling_status": "existing_single_family",
    "adu_project_form": "new_detached",
    "unpermitted_existing": "no",
}


def _context(responses: list[str]) -> ServiceContext:
    return ServiceContext.load(root=ROOT, provider=ScriptedProvider(responses))


def _client(responses: list[str]) -> TestClient:
    return TestClient(create_app(_context(responses)))


def _intake_payload() -> str:
    base: dict[str, Any] = {
        "detected_language": "en",
        "project_type": {"value": "adu", "quote": "a detached unit"},
        "jurisdiction_name": {"value": "Davis", "quote": "Davis"},
        "unmapped_details": [],
    }
    for field in facts.FACT_FIELDS:
        base[field.name] = {"value": "unknown", "quote": ""}
    return json.dumps(base)


def test_validate_intake_accepts_only_the_vocabulary() -> None:
    assert validate_intake(DAVIS_ADU) == DAVIS_ADU
    with pytest.raises(RequestError, match="unknown intake field"):
        validate_intake({**DAVIS_ADU, "lot_size": "5000"})
    with pytest.raises(RequestError, match="allowed list"):
        validate_intake({**DAVIS_ADU, "adu_project_form": "tiny"})
    with pytest.raises(RequestError, match="short string"):
        validate_intake({**DAVIS_ADU, "jurisdiction": "x" * 65})
    with pytest.raises(RequestError, match="short string"):
        validate_intake({**DAVIS_ADU, "jurisdiction": 5})
    with pytest.raises(RequestError, match="project_type"):
        validate_intake({"jurisdiction": "davis"})


def test_origins_and_root_come_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert allowed_origins_from_env({}) == DEFAULT_ORIGINS
    assert allowed_origins_from_env(
        {"PERMIT_AI_ALLOWED_ORIGINS": " https://a.test , https://b.test ,"}
    ) == (
        "https://a.test",
        "https://b.test",
    )
    monkeypatch.delenv("PERMIT_AI_ROOT", raising=False)
    assert repository_root() == ROOT
    monkeypatch.setenv("PERMIT_AI_ROOT", str(ROOT / "data"))
    assert repository_root() == ROOT / "data"


def test_health_reports_boundary_and_versions() -> None:
    response = _client([]).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok" and body["provider"] == "scripted"
    assert body["stores_applicant_content"] is False
    assert body["rules"] == 19 and body["corpus_documents"] == 18
    assert body["prompt_versions"] == {
        "intake": "intake-v1",
        "explain": "explain-v1",
        "ask": "ask-v1",
        "staff_questions": "staff-questions-v1",
    }
    assert body["daily_cap"] is None
    assert body["corpus_skipped"] == [
        "davis-code-40-26-450",
        "yolo-public-parcels-layer",
    ]


def test_intake_endpoint_returns_a_draft_and_rejects_bad_input() -> None:
    client = _client([_intake_payload()])
    response = client.post(
        "/intake/extract",
        json={"text": "I want a detached unit in Davis.", "language": "en"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["draft_intake"]["project_type"] == "adu"
    assert body["jurisdiction"]["slug"] == "davis"
    assert "unpermitted_existing" in body["unanswered"]
    assert (
        client.post("/intake/extract", json={"text": "", "language": "en"}).status_code
        == 422
    )
    bad_language = client.post(
        "/intake/extract", json={"text": "hello", "language": "fr"}
    )
    assert bad_language.status_code == 400
    assert bad_language.json()["detail"]["error"] == "invalid_request"


def test_explain_endpoint_verifies_and_translates_errors() -> None:
    context = _context(['{"claims": []}'])
    client = TestClient(create_app(context))
    ok = client.post("/explain", json={"intake": DAVIS_ADU, "language": "en"})
    assert ok.status_code == 200
    assert ok.json()["withheld_count"] == 0 and ok.json()["rule_ids"]
    disagreement = client.post(
        "/explain",
        json={
            "intake": DAVIS_ADU,
            "language": "en",
            "matched_rule_ids": ["adu-ministerial-review"],
        },
    )
    assert disagreement.status_code == 409
    assert disagreement.json()["detail"]["error"] == "matcher_disagreement"
    invalid = client.post(
        "/explain", json={"intake": {**DAVIS_ADU, "extra": "x"}, "language": "en"}
    )
    assert invalid.status_code == 400
    exhausted = client.post("/explain", json={"intake": DAVIS_ADU, "language": "en"})
    assert exhausted.status_code == 502
    assert exhausted.json()["detail"]["error"] == "provider_unavailable"


def test_staff_questions_endpoint() -> None:
    client = _client(
        [
            '{"questions": [{"question": "Which category applies?", "why": "Routing.", "rule_id": "davis-local-adu-process", "fact": null}]}'
        ]
    )
    response = client.post(
        "/staff-questions", json={"intake": DAVIS_ADU, "language": "es"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["questions"][0]["rule_id"] == "davis-local-adu-process"
    assert body["local_record"] is True
    assert (
        client.post(
            "/staff-questions", json={"intake": {}, "language": "en"}
        ).status_code
        == 400
    )


def test_cors_allows_only_configured_origins() -> None:
    context = ServiceContext.load(
        root=ROOT,
        provider=ScriptedProvider([]),
        allowed_origins=("https://allowed.test",),
    )
    client = TestClient(create_app(context))
    allowed = client.get("/health", headers={"Origin": "https://allowed.test"})
    assert allowed.headers.get("access-control-allow-origin") == "https://allowed.test"
    denied = client.get("/health", headers={"Origin": "https://other.test"})
    assert "access-control-allow-origin" not in denied.headers


def test_load_context_from_env_uses_provider_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_provider(settings: Any) -> ScriptedProvider:
        captured["settings"] = settings
        return ScriptedProvider([])

    monkeypatch.setattr(service_module, "provider_from_settings", fake_provider)
    context = service_module.load_context_from_env(
        {"PERMIT_AI_PROVIDER": "bedrock", "PERMIT_AI_ALLOWED_ORIGINS": "https://x.test"}
    )
    assert captured["settings"].provider == "bedrock"
    assert context.allowed_origins == ("https://x.test",)
    assert context.provider.name == "scripted"

    def failing(settings: Any) -> ScriptedProvider:
        raise ProviderError("no credential")

    monkeypatch.setattr(service_module, "provider_from_settings", failing)
    with pytest.raises(ProviderError):
        service_module.load_context_from_env({})


def test_ask_endpoint_answers_abstains_and_validates() -> None:
    from permit_pathways.ai.corpus import CorpusIndex

    corpus = CorpusIndex.load(ROOT)
    passage = corpus.documents["ca-gov-66317"].passages[1]
    quote = " ".join(passage.text.split()[:12])
    answer = json.dumps(
        {
            "claims": [
                {
                    "text": "Within 60 days.",
                    "citations": [{"passage_id": passage.passage_id, "quote": quote}],
                }
            ],
            "abstain": False,
            "staff_question": "",
        }
    )
    abstain = json.dumps(
        {"claims": [], "abstain": True, "staff_question": "Ask staff about fees."}
    )
    client = _client([answer, abstain])
    ok = client.post(
        "/ask",
        json={
            "intake": DAVIS_ADU,
            "language": "en",
            "question": "How long does review take?",
        },
    )
    assert ok.status_code == 200
    body = ok.json()
    assert (
        body["abstained"] is False
        and body["claims"][0]["citations"][0]["verified"] is True
    )
    assert body["prompt_version"] == "ask-v1" and body["withheld_count"] == 0
    abstained = client.post(
        "/ask",
        json={"intake": DAVIS_ADU, "language": "es", "question": "¿Cuánto cuesta?"},
    )
    assert abstained.status_code == 200
    assert abstained.json()["abstained"] is True
    assert abstained.json()["staff_question"] == "Ask staff about fees."
    assert (
        client.post(
            "/ask", json={"intake": DAVIS_ADU, "language": "en", "question": ""}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/ask", json={"intake": DAVIS_ADU, "language": "en", "question": "x" * 501}
        ).status_code
        == 422
    )


def test_budget_limits_model_backed_routes_only() -> None:
    from permit_pathways.ai.budget import Budget, MemoryCounter

    context = ServiceContext.load(
        root=ROOT,
        provider=ScriptedProvider(['{"claims": []}'] * 5),
        budget=Budget(daily_cap=2, per_client_per_minute=5, counter=MemoryCounter()),
    )
    client = TestClient(create_app(context))
    assert client.get("/health").json()["daily_cap"] == 2
    assert (
        client.post(
            "/explain", json={"intake": DAVIS_ADU, "language": "en"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/explain", json={"intake": DAVIS_ADU, "language": "en"}
        ).status_code
        == 200
    )
    refused = client.post("/explain", json={"intake": DAVIS_ADU, "language": "en"})
    assert refused.status_code == 429
    assert refused.json()["detail"]["error"] == "budget_exhausted"
    assert client.get("/health").status_code == 200
    per_client = ServiceContext.load(
        root=ROOT,
        provider=ScriptedProvider(['{"claims": []}'] * 5),
        budget=Budget(daily_cap=50, per_client_per_minute=1, counter=MemoryCounter()),
    )
    forwarded = TestClient(create_app(per_client))
    first = forwarded.post(
        "/explain",
        json={"intake": DAVIS_ADU, "language": "en"},
        headers={"X-Forwarded-For": "203.0.113.9, 10.0.0.1"},
    )
    second = forwarded.post(
        "/explain",
        json={"intake": DAVIS_ADU, "language": "en"},
        headers={"X-Forwarded-For": "203.0.113.9"},
    )
    other = forwarded.post(
        "/explain",
        json={"intake": DAVIS_ADU, "language": "en"},
        headers={"X-Forwarded-For": "198.51.100.2"},
    )
    assert (first.status_code, second.status_code, other.status_code) == (200, 429, 200)
