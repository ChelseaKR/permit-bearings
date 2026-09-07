"""Cross-runtime parity for the what-if explorer.

``src/permit_pathways/what_if.py`` and ``whatIfDeltas`` in ``assets/demo.js``
are two hand-written implementations of the same perturbation, and the browser
one is the code a visitor to ``check.html`` will run. The pattern is the one
``test_conformance_browser_parity.py`` already sets: lift the deployed function
out of the shipped file, run it under Node against the same fixtures, and
require identical output. Reading a copy kept in the test would prove nothing
about what is deployed.

Both runtimes are exercised twice over every Golden case: once with no
source-state snapshot, and once with a snapshot that puts a source on review
hold, because the withheld branch is the one where the two could most easily
disagree in a way nobody would notice -- ``null`` in one runtime and ``[]`` in
the other read the same in a rendered page and mean opposite things.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.ai.facts import FIELDS_BY_NAME, material_fields
from permit_pathways.screening import load_rules
from permit_pathways.what_if import what_if

ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "data" / "rules"
DEMO_JS = ROOT / "assets" / "demo.js"
RULES = load_rules(RULES_DIR)
GOLDEN: list[dict[str, Any]] = json.loads(
    (ROOT / "data" / "golden" / "example.json").read_text(encoding="utf-8")
)
AS_OF = "2026-09-07"

#: `ca-gov-66311-7` sits under both legalization rules, which between them read
#: `primary_dwelling_status` and `unpermitted_existing`.
HOLD_SNAPSHOT: dict[str, Any] = {
    "snapshot_id": "parity-hold",
    "checked_at": "2026-09-07T00:00:00Z",
    "changed_source_ids": ["ca-gov-66311-7"],
    "unverifiable_source_ids": [],
    "affected_rule_ids": [],
    "receipt": {"status": "reviewed"},
}

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js unavailable"
)


def _deployed_what_if_source(source_text: str | None = None) -> str:
    """The shipped matcher and what-if port, lifted from ``assets/demo.js``.

    The slice starts at the matcher's first helper so the perturbation runs
    through the same ``screen()`` the page uses, not a re-implementation.
    """
    source = (
        source_text if source_text is not None else DEMO_JS.read_text(encoding="utf-8")
    )
    matcher = source[
        source.index("function isJsonNumber") : source.index("function ruleStatus")
    ]
    # `validCriterion` calls this one helper from further down the file. It is
    # lifted from the shipped source too rather than re-typed here, for the
    # same reason the matcher is: a copy in the test proves nothing about what
    # is deployed.
    helper = source[
        source.index("function nonBlank") : source.index("function validIsoDate")
    ]
    return helper + matcher


def _rule_records() -> list[dict[str, Any]]:
    """The rule records the browser bundle carries, read from the canonical
    JSON rather than from ``data/demo-data.js`` so a stale bundle cannot make
    this test agree by accident."""
    records: list[dict[str, Any]] = []
    for path in sorted(RULES_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        records.extend(json.loads(path.read_text(encoding="utf-8")))
    return records


def _cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for record in GOLDEN:
        intake = record["intake"]
        fields = list(material_fields(intake["project_type"]))
        values = {name: list(FIELDS_BY_NAME[name].values) for name in fields}
        for label, changed in (
            ("no-snapshot", []),
            ("held", list(HOLD_SNAPSHOT["changed_source_ids"])),
        ):
            cases.append(
                {
                    "id": f"{record['case_id']}:{label}",
                    "intake": intake,
                    "fields": fields,
                    "values": values,
                    "changed_source_ids": changed,
                }
            )
    return cases


def _browser_output(
    cases: list[dict[str, Any]], source_text: str | None = None
) -> dict[str, Any]:
    script = "\n".join(
        [
            'import {readFileSync} from "node:fs";',
            'let RULES = JSON.parse(readFileSync(process.argv[2], "utf8"));',
            'const CASES = JSON.parse(readFileSync(process.argv[3], "utf8"));',
            "// `RULES` is the page's own mutable binding; `screen()` reads it.",
            _deployed_what_if_source(source_text),
            "const out = {};",
            "for (const item of CASES) {",
            "  out[item.id] = whatIfDeltas(",
            "    item.intake, item.fields, item.values, item.changed_source_ids",
            "  );",
            "}",
            "process.stdout.write(JSON.stringify(out));",
        ]
    )
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory)
        script_path = workspace / "parity.mjs"
        rules_path = workspace / "rules.json"
        cases_path = workspace / "cases.json"
        script_path.write_text(script, encoding="utf-8")
        rules_path.write_text(json.dumps(_rule_records()), encoding="utf-8")
        cases_path.write_text(json.dumps(cases), encoding="utf-8")
        completed = subprocess.run(
            ["node", str(script_path), str(rules_path), str(cases_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    return dict(json.loads(completed.stdout))


def _python_output(cases: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in cases:
        snapshot = HOLD_SNAPSHOT if item["changed_source_ids"] else None
        out[item["id"]] = what_if(
            intake=item["intake"],
            rules=RULES,
            as_of=AS_OF,
            source_state=snapshot,
        )["facts"]
    return out


@requires_node
def test_browser_and_python_what_if_agree_on_every_golden_case() -> None:
    cases = _cases()
    assert len(cases) == 2 * len(GOLDEN)
    browser = _browser_output(cases)
    python = _python_output(cases)
    assert set(browser) == set(python)
    for case_id in sorted(python):
        assert browser[case_id] == python[case_id], case_id


@requires_node
def test_the_held_cases_really_do_withhold_in_both_runtimes() -> None:
    """A parity test over two runtimes that both computed nothing would pass.

    This asserts the held half of the corpus actually reaches the withheld
    branch, so the agreement above is agreement about something.
    """
    cases = [item for item in _cases() if item["changed_source_ids"]]
    browser = _browser_output(cases)
    withheld = [
        entry
        for facts in browser.values()
        for entry in facts
        if entry["deltas_withheld"] == "source_on_review_hold"
    ]
    assert withheld, "no held case reached the withheld branch"
    for entry in withheld:
        assert entry["no_rule_reads_this_differently"] is None
        assert all(
            item["rules_added"] is None and item["candidate_routes"] is None
            for item in entry["alternatives"]
        )


@requires_node
def test_the_unheld_cases_really_do_produce_deltas() -> None:
    """The other half of the same worry: agreement on all-empty deltas."""
    cases = [item for item in _cases() if not item["changed_source_ids"]]
    browser = _browser_output(cases)
    changed = [
        item
        for facts in browser.values()
        for entry in facts
        for item in entry["alternatives"]
        if item["rules_added"] or item["rules_removed"]
    ]
    assert len(changed) > 20, len(changed)
