.PHONY: install verify lint type test security bundle-check

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

verify: install lint type test security bundle-check
