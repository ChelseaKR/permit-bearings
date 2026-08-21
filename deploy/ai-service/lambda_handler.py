"""AWS Lambda entry point for the optional AI service (ADR 0004).

The repository subset the service needs (rules, source registry,
jurisdiction registry, corpus text documents) is packaged beside this file by
``build.sh`` and named by ``PERMIT_AI_ROOT``. The context (rules, corpus
index, registry, provider, budget) is built once per cold start. Request
bodies are never written to disk or logs; the budget counter in DynamoDB
stores a per-day count and nothing else.
"""

from mangum import Mangum

from permit_pathways.ai.service import create_app, load_context_from_env

handler = Mangum(create_app(load_context_from_env()), lifespan="off")
