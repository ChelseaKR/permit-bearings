.PHONY: install verify lint type test security bundle-check copy-check readability-check evidence-export-check browser-test require-node serve-ai ai-eval

install:
	uv sync --locked --python 3.12 --group dev --extra ai

# The Python tests that execute `assets/demo.js` under Node are guarded by
# `skipif(shutil.which("node") is None)`, and the browser unit suite needs Node
# outright. The count used to be written out here and had already drifted, so
# it is not written out any more. Without this target `make verify` passed with the entire browser
# runtime untested and said nothing about it, while CI called the same command
# "local-equivalent verification". Fail loudly instead.
require-node:
	@command -v node >/dev/null 2>&1 || { \
		printf '%s\n' \
			'make verify requires Node.js 24: the browser unit suite and the' \
			'eight cross-runtime contract tests cannot run without it, and' \
			'skipping them silently is what this check exists to prevent.' \
			'Install Node 24, or run the Python-only subset with `make test`.' >&2; \
		exit 1; \
	}

lint:
	.venv/bin/ruff check src tests scripts demo
	.venv/bin/ruff format --check src tests scripts demo

type:
	.venv/bin/mypy

test:
	.venv/bin/pytest

security:
	.venv/bin/bandit -q -r src scripts demo
	@set -eu; \
		runtime_requirements=$$(mktemp "$${TMPDIR:-/tmp}/permit-bearings-runtime.XXXXXX"); \
		trap 'rm -f "$$runtime_requirements"' EXIT; \
		UV_CACHE_DIR=/tmp/permit-bearings-uv-cache uv export --frozen --no-dev --extra ai \
			--no-emit-project --format requirements-txt \
			--output-file "$$runtime_requirements" >/dev/null; \
		.venv/bin/pip-audit --requirement "$$runtime_requirements" \
			--no-deps --disable-pip

bundle-check:
	.venv/bin/python scripts/gen_schemas.py --check
	.venv/bin/python scripts/build_demo_bundle.py --check
	.venv/bin/python scripts/scan_ordinances.py --check
	PYTHONPATH=src .venv/bin/python -m permit_pathways.harness

copy-check:
	node scripts/check_applicant_copy.mjs

# Unit tests over the shipped `assets/demo.js`, with a real coverage floor.
# The four duplicated domains (screening, staleness, withdrawn citations, and
# the review clocks) are what a drift between the runtimes would break first.
browser-test:
	node scripts/browser-coverage.mjs

# Enforced plain-language regression check: fails when English explanation
# copy becomes harder to read than the reviewed baseline. A score can flag a
# regression; it never replaces human readability review.
readability-check:
	.venv/bin/python scripts/readability_gate.py

evidence-export-check:
	@set -eu; \
		evidence_directory=$$(mktemp -d "$${TMPDIR:-/tmp}/permit-bearings-evidence-export.XXXXXX"); \
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
		signed="$$evidence_directory/public-synthetic-evidence-signed.zip"; \
		ssh-keygen -q -t ed25519 -N '' -C 'evidence-export-check@example.invalid' \
			-f "$$evidence_directory/key"; \
		printf 'evidence-export-check@example.invalid %s\n' \
			"$$(cut -d' ' -f1,2 "$$evidence_directory/key.pub")" \
			> "$$evidence_directory/allowed_signers"; \
		PYTHONPATH=src .venv/bin/python -m permit_pathways.evidence_export_cli build \
			--output "$$signed" \
			--freeze-id public-synthetic-evidence-freeze-2026-08-09 \
			--frozen-on 2026-08-09 \
			--repository-commit-sha "$$repository_commit_sha" \
			--sign-key "$$evidence_directory/key" >/dev/null; \
		cmp -s "$$archive" "$$signed" || { \
			printf '%s\n' 'signing changed the archive bytes' >&2; exit 1; }; \
		PYTHONPATH=src .venv/bin/python -m permit_pathways.evidence_export_cli verify \
			--archive "$$signed" \
			--allowed-signers "$$evidence_directory/allowed_signers" >/dev/null; \
		if PYTHONPATH=src .venv/bin/python -m permit_pathways.evidence_export_cli verify \
			--archive "$$archive" \
			--allowed-signers "$$evidence_directory/allowed_signers" >/dev/null 2>&1; then \
			printf '%s\n' 'an unsigned archive passed an authenticity check' >&2; \
			exit 1; \
		fi; \
		printf '%s\n' 'evidence export round trip: pass (unsigned and signed)'

serve-ai:
	PYTHONPATH=src .venv/bin/python -m permit_pathways.ai

# Live evaluation of the runtime AI layer; needs a configured provider.
# Results are dated and name the provider/model so a committed number is
# always traceable to one run (see evals/ai/README.md).
#
# `:` and `/` are substituted as well as `.` because open-weight model names
# carry them (`qwen2.5:14b`, `meta-llama/Llama-3.1-8B-Instruct`) and a `/`
# would make the output path a directory that does not exist rather than a
# file name.
AI_EVAL_MODEL_SLUG = $(subst /,-,$(subst :,-,$(subst .,-,$(or $(PERMIT_AI_MODEL),claude-sonnet-5))))
AI_EVAL_PREFIX ?= $(shell date -u +%Y-%m-%d)-$(or $(PERMIT_AI_PROVIDER),anthropic)-$(AI_EVAL_MODEL_SLUG)
ai-eval:
	PYTHONPATH=src .venv/bin/python -m permit_pathways.ai.eval intake \
		--cases evals/ai/intake-cases.json \
		--output evals/ai/results/$(AI_EVAL_PREFIX)-intake.json
	PYTHONPATH=src .venv/bin/python -m permit_pathways.ai.eval grounding \
		--cases evals/ai/grounding-cases.json \
		--output evals/ai/results/$(AI_EVAL_PREFIX)-grounding.json

verify: install require-node lint type test security bundle-check copy-check browser-test readability-check evidence-export-check
