.PHONY: install verify lint type test security bundle-check readability-check copy-check evidence-export-check

install:
	uv sync --frozen --python 3.12 --group dev

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
		UV_CACHE_DIR=/tmp/permit-pathways-uv-cache uv export --frozen --no-dev \
			--no-emit-project --format requirements-txt \
			--output-file "$$runtime_requirements" >/dev/null; \
		.venv/bin/pip-audit --requirement "$$runtime_requirements" \
			--no-deps --disable-pip

bundle-check:
	.venv/bin/python scripts/build_demo_bundle.py --check
	PYTHONPATH=src .venv/bin/python -m permit_pathways.harness

readability-check:
	PYTHONPATH=src .venv/bin/python -m permit_pathways.readability_cli check

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
			--freeze-id public-synthetic-evidence-freeze-2026-08-22 \
			--frozen-on 2026-08-22 \
			--repository-commit-sha "$$repository_commit_sha" >/dev/null; \
		PYTHONPATH=src .venv/bin/python -m permit_pathways.evidence_export_cli verify \
			--archive "$$archive" >/dev/null; \
		PYTHONPATH=src .venv/bin/python -m permit_pathways.evidence_export_cli restore \
			--archive "$$archive" \
			--destination "$$restored" >/dev/null; \
		printf '%s\n' 'evidence export round trip: pass'

verify: install lint type test security bundle-check readability-check copy-check evidence-export-check
