"""The optional runtime AI service (ADR 0004).

A small FastAPI application that the static project-check page calls when it
is running. It exposes natural-language intake extraction, grounded
explanation, and staff-question drafting over the committed rules and
corpus. It keeps no applicant content: request bodies live in process memory
for one request and are never written to disk or logs.

Run locally with ``python -m permit_pathways.ai`` (or ``make serve-ai``).
The provider credential is read from the environment by the ``anthropic``
SDK; see ``ProviderSettings`` for the ``PERMIT_AI_*`` variables.
"""

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..screening import Rule, load_rules
from . import explain as explain_module
from . import facts
from . import intake as intake_module
from . import staff_questions as staff_module
from .corpus import CorpusIndex
from .intake import IntakeError
from .provider import Provider, ProviderError, ProviderSettings, provider_from_settings

DEFAULT_ORIGINS = ("http://localhost:8765", "http://127.0.0.1:8765", "null")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
MAX_INTAKE_VALUE_CHARS = 64
INTAKE_KEYS = frozenset({"project_type", "jurisdiction", *facts.FACT_NAMES})


def repository_root() -> Path:
    override = os.environ.get("PERMIT_AI_ROOT", "").strip()
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ServiceContext:
    root: Path
    rules: tuple[Rule, ...]
    corpus: CorpusIndex
    registry: tuple[intake_module.JurisdictionEntry, ...]
    provider: Provider
    allowed_origins: tuple[str, ...]

    @classmethod
    def load(
        cls,
        *,
        root: Path,
        provider: Provider,
        allowed_origins: tuple[str, ...] = DEFAULT_ORIGINS,
    ) -> "ServiceContext":
        import json

        rules = tuple(load_rules(root / "data" / "rules"))
        corpus = CorpusIndex.load(root)
        registry_payload = json.loads(
            (root / "data" / "jurisdictions" / "registry.json").read_text(
                encoding="utf-8"
            )
        )
        registry = intake_module.load_jurisdictions(registry_payload["jurisdictions"])
        return cls(root, rules, corpus, registry, provider, allowed_origins)

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "permit-bearings-ai",
            "provider": self.provider.name,
            "model": self.provider.model,
            "prompt_versions": {
                "intake": intake_module.PROMPT_VERSION,
                "explain": explain_module.PROMPT_VERSION,
                "staff_questions": staff_module.PROMPT_VERSION,
            },
            "rules": len(self.rules),
            "corpus_documents": len(self.corpus.documents),
            "corpus_skipped": sorted(self.corpus.skipped),
            "stores_applicant_content": False,
        }


class RequestError(ValueError):
    """A request body the service will not act on."""


def validate_intake(payload: Mapping[str, Any]) -> dict[str, str]:
    """Accept only the matcher's own fact names with allowed values."""
    cleaned: dict[str, str] = {}
    for key, value in payload.items():
        if key not in INTAKE_KEYS:
            raise RequestError(f"unknown intake field: {key}")
        if not isinstance(value, str) or len(value) > MAX_INTAKE_VALUE_CHARS:
            raise RequestError(f"intake field {key} must be a short string")
        if key != "jurisdiction" and value not in facts.allowed_values(key):
            raise RequestError(
                f"intake field {key} has a value outside the allowed list"
            )
        cleaned[key] = value
    if "project_type" not in cleaned:
        raise RequestError("intake must include project_type")
    return cleaned


def allowed_origins_from_env(
    environ: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    env = os.environ if environ is None else environ
    raw = env.get("PERMIT_AI_ALLOWED_ORIGINS", "").strip()
    if not raw:
        return DEFAULT_ORIGINS
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


def _http_error(exception_type: Any, status: int, exc: Exception, code: str) -> Any:
    return exception_type(
        status_code=status, detail={"error": code, "message": str(exc)}
    )


def guarded(
    compute: Callable[[], dict[str, Any]], exception_type: Any
) -> dict[str, Any]:
    """Run one request; translate domain errors to HTTP status codes without
    echoing request content into the response beyond the validation message."""
    try:
        return compute()
    except explain_module.MatcherDisagreement as exc:
        raise _http_error(exception_type, 409, exc, "matcher_disagreement") from exc
    except (RequestError, explain_module.ExplainError, IntakeError) as exc:
        raise _http_error(exception_type, 400, exc, "invalid_request") from exc
    except ProviderError as exc:
        raise _http_error(exception_type, 502, exc, "provider_unavailable") from exc


def run_intake(context: ServiceContext, text: str, language: str) -> dict[str, Any]:
    extraction = intake_module.extract_intake(
        text, language=language, provider=context.provider, registry=context.registry
    )
    payload = extraction.to_dict()
    payload["draft_intake"] = extraction.draft_intake()
    return payload


def run_explain(
    context: ServiceContext,
    intake: Mapping[str, Any],
    language: str,
    matched_rule_ids: list[str] | None,
) -> dict[str, Any]:
    return explain_module.explain_result(
        intake=validate_intake(intake),
        rules=context.rules,
        corpus=context.corpus,
        provider=context.provider,
        language=language,
        expected_rule_ids=matched_rule_ids,
    ).to_dict()


def run_staff_questions(
    context: ServiceContext,
    intake: Mapping[str, Any],
    language: str,
    matched_rule_ids: list[str] | None,
) -> dict[str, Any]:
    return staff_module.draft_staff_questions(
        intake=validate_intake(intake),
        rules=context.rules,
        provider=context.provider,
        language=language,
        expected_rule_ids=matched_rule_ids,
    ).to_dict()


def create_app(context: ServiceContext) -> Any:
    """Build the FastAPI app around a loaded context. FastAPI is imported
    lazily so the rest of the package works without the `ai` extra."""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field

    class IntakeRequest(BaseModel):
        text: str = Field(min_length=1, max_length=intake_module.MAX_TEXT_CHARS)
        language: str = "en"

    class ResultRequest(BaseModel):
        intake: dict[str, str]
        language: str = "en"
        matched_rule_ids: list[str] | None = None

    app = FastAPI(
        title="Permit Bearings AI service",
        version=f"{intake_module.PROMPT_VERSION}+{explain_module.PROMPT_VERSION}",
        docs_url=None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(context.allowed_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return context.health()

    @app.post("/intake/extract")
    def intake_extract(request: IntakeRequest) -> dict[str, Any]:
        return guarded(
            lambda: run_intake(context, request.text, request.language), HTTPException
        )

    @app.post("/explain")
    def explain(request: ResultRequest) -> dict[str, Any]:
        return guarded(
            lambda: run_explain(
                context, request.intake, request.language, request.matched_rule_ids
            ),
            HTTPException,
        )

    @app.post("/staff-questions")
    def staff_questions(request: ResultRequest) -> dict[str, Any]:
        return guarded(
            lambda: run_staff_questions(
                context, request.intake, request.language, request.matched_rule_ids
            ),
            HTTPException,
        )

    return app


def load_context_from_env(environ: Mapping[str, str] | None = None) -> ServiceContext:
    settings = ProviderSettings.from_environ(environ)
    provider = provider_from_settings(settings)
    return ServiceContext.load(
        root=repository_root(),
        provider=provider,
        allowed_origins=allowed_origins_from_env(environ),
    )


def main(
    argv: list[str] | None = None,
) -> int:  # pragma: no cover - process entry point
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Run the Permit Bearings AI service.")
    parser.add_argument(
        "--host", default=os.environ.get("PERMIT_AI_HOST", DEFAULT_HOST)
    )
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PERMIT_AI_PORT", DEFAULT_PORT))
    )
    args = parser.parse_args(argv)
    try:
        context = load_context_from_env()
    except Exception as exc:
        print(f"permit-bearings-ai: cannot start: {exc}")
        return 2
    print(
        f"permit-bearings-ai: provider={context.provider.name} model={context.provider.model} "
        f"rules={len(context.rules)} corpus_documents={len(context.corpus.documents)} "
        f"origins={','.join(context.allowed_origins)}"
    )
    uvicorn.run(
        create_app(context), host=args.host, port=args.port, log_level="warning"
    )
    return 0
