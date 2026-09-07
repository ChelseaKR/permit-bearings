"""Write ``schemas/*.schema.json`` from the Python definitions.

The published schemas are generated, never hand-edited: the fact vocabulary
lives in ``permit_pathways.ai.facts`` and the rule/result shapes live in
``permit_pathways.screening`` and ``permit_pathways.screening_contract``, and a
schema maintained beside them drifts the first time one of them changes.

    python scripts/gen_schemas.py            # write
    python scripts/gen_schemas.py --check    # fail if the committed files are stale

``--check`` is what CI runs; ``tests/test_screening_contract.py`` asserts the
same thing, so a stale schema fails in two places rather than none.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from permit_pathways.screening_contract import SCHEMAS, render_schema  # noqa: E402

SCHEMA_DIR = ROOT / "schemas"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare instead of writing; exit 1 when a committed schema is stale",
    )
    args = parser.parse_args(argv)

    SCHEMA_DIR.mkdir(exist_ok=True)
    stale: list[str] = []
    for name in sorted(SCHEMAS):
        rendered = render_schema(name)
        path = SCHEMA_DIR / name
        if args.check:
            current = path.read_text(encoding="utf-8") if path.is_file() else ""
            if current != rendered:
                stale.append(name)
            continue
        path.write_text(rendered, encoding="utf-8")
        print(f"wrote schemas/{name}")

    if args.check:
        if stale:
            print(
                "stale schema(s): " + ", ".join(stale) + "\n"
                "regenerate with `python scripts/gen_schemas.py`",
                file=sys.stderr,
            )
            return 1
        print(f"schemas current ({len(SCHEMAS)} checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
