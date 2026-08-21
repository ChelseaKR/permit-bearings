.PHONY: install verify lint type test security bundle-check copy-check evidence-export-check serve-ai ai-eval

install:
	uv sync --locked --python 3.12 --group dev --extra ai

lint:
	.venv/bin/ruff check src tests
	.venv/bin/ruff format --check src tests

type:
	.venv/bin/mypy

test:
	.venv/bin/pytest

security:
	.venv/bin/bandit -q -r src
	@set -eu; \
		runtime_requirements=$$(mktemp "$${TMPDIR:-/tmp}/permit-pathways-runtime.XXXXXX"); \
		trap 'rm -f "$$runtime_requirements"' EXIT; \
		UV_CACHE_DIR=/tmp/permit-pathways-uv-cache uv export --frozen --no-dev --extra ai \
			--no-emit-project --format requirements-txt \
			--output-file "$$runtime_requirements" >/dev/null; \
		.venv/bin/pip-audit --requirement "$$runtime_requirements" \
			--no-deps --disable-pip

bundle-check:
	.venv/bin/python scripts/build_demo_bundle.py --check
	.venv/bin/python scripts/scan_ordinances.py --check
	PYTHONPATH=src .venv/bin/python -m permit_pathways.harness

copy-check:
	node scripts/check_applicant_copy.mjs

evidence-export-check:
	@set -eu; \
		evidence_directory=$$(mktemp -d "$${TMPDIR:-/tmp}/permit-pathways-evidence-export.XXXXXX"); \
		trap 'rm -rf "$$evidence_directory"' EXIT; \
		repository_commit_sha=$$(git rev-parse HEAD); \
		archive="$$evidence_directory/public-synthetic-evidence.zip"; \
		restored="$$evidence_directory/restored"; \
		PYTHONPATH=src .venv/bin/python -m permit_pathways.evidence_export_cli build \
			--output "$$archive" \
			--freeze-id public-synthetic-evidence-freeze-2026-08-09 \
			--frozen-on 2026-08-09 \
			--repository-commit-sha "$$repository_commit_sha" >/dev/null; \
		PYTHONPATH=src .venv/bin/python -m permit_pathways.evidence_export_cli verify \
			--archive "$$archive" >/dev/null; \
		PYTHONPATH=src .venv/bin/python -m permit_pathways.evidence_export_cli restore \
			--archive "$$archive" \
			--destination "$$restored" >/dev/null; \
		printf '%s\n' 'evidence export round trip: pass'

serve-ai:
	PYTHONPATH=src .venv/bin/python -m permit_pathways.ai

# Live evaluation of the runtime AI layer; needs a configured provider.
# Results are dated and name the provider/model so a committed number is
# always traceable to one run (see evals/ai/README.md).
AI_EVAL_PREFIX ?= $(shell date -u +%Y-%m-%d)-$(or $(PERMIT_AI_PROVIDER),anthropic)-$(subst .,-,$(or $(PERMIT_AI_MODEL),claude-sonnet-5))
ai-eval:
	PYTHONPATH=src .venv/bin/python -m permit_pathways.ai.eval intake \
		--cases evals/ai/intake-cases.json \
		--output evals/ai/results/$(AI_EVAL_PREFIX)-intake.json
	PYTHONPATH=src .venv/bin/python -m permit_pathways.ai.eval grounding \
		--cases evals/ai/grounding-cases.json \
		--output evals/ai/results/$(AI_EVAL_PREFIX)-grounding.json

verify: install lint type test security bundle-check copy-check evidence-export-check
