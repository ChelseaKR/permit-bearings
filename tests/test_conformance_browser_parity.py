"""Parity gate for the ordinance screen the public actually runs.

`src/permit_pathways/conformance.py` carries the HCD re-derivation evidence:
six quoted Santa Clara County provisions produce six expected review flags in
`tests/test_conformance.py`. The browser runs a separate hand-port,
`scanOrdinance()` in `assets/demo.js`, and that is the code a visitor to
`review.html` executes when they paste ordinance text.

This test runs the deployed port under Node against the same fixtures the
Python test uses and requires identical output — check IDs, offsets and
excerpts, not just the flagged set. Both engines interpret `checks.json`
through different regex implementations and duplicate the exclusion,
context-window and overlap rules by hand, so a check edit or a fix applied to
one engine can silently diverge from the other. If it does, the sentence
"validated against HCD's own findings" would be true of the tested code and
false of the shipped code.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from permit_pathways.conformance import load_checks, scan

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "conformance"
VALIDATION = json.loads((DATA / "hcd-validation-santa-clara.json").read_text())

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js unavailable"
)


def _deployed_scanner_source() -> str:
    """The exact `scanOrdinance` the site ships, lifted from `assets/demo.js`.

    Reading the shipped file rather than a copy is the point: a port kept in
    the test would prove nothing about what is deployed.
    """
    source = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    start = source.index("function scanOrdinance")
    end = source.index("const scanButtonElement", start)
    return source[start:end]


def _cases() -> dict[str, str]:
    cases = {
        provision["hcd_finding"]: provision["text"]
        for provision in VALIDATION["provisions"]
    }
    cases["control (must stay quiet)"] = VALIDATION["control"]["text"]
    cases["full letter corpus"] = "\n\n".join(
        provision["text"] for provision in VALIDATION["provisions"]
    )
    cases["san-diego ordinance"] = (
        ROOT / "corpus" / "ordinances" / "san-diego.txt"
    ).read_text()
    return cases


def _browser_findings(
    cases: dict[str, str], source: str | None = None
) -> dict[str, list[dict[str, object]]]:
    script = "\n".join(
        [
            'import {readFileSync} from "node:fs";',
            'const CHECKS = JSON.parse(readFileSync(process.argv[1], "utf8"));',
            'const CASES = JSON.parse(readFileSync(process.argv[2], "utf8"));',
            source if source is not None else _deployed_scanner_source(),
            "const out = {};",
            "for (const [name, text] of Object.entries(CASES)) {",
            "  out[name] = scanOrdinance(text).map(f => ({",
            "    check_id: f.check.check_id, offset: f.offset, excerpt: f.excerpt,",
            "  }));",
            "}",
            "process.stdout.write(JSON.stringify(out));",
        ]
    )
    with tempfile.TemporaryDirectory() as directory:
        case_file = Path(directory) / "cases.json"
        case_file.write_text(json.dumps(cases), encoding="utf-8")
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                script,
                str(DATA / "checks.json"),
                str(case_file),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


@requires_node
def test_deployed_ordinance_screen_matches_the_validated_scanner():
    checks = load_checks(DATA / "checks.json")
    cases = _cases()
    browser = _browser_findings(cases)

    assert set(browser) == set(cases), "every fixture case ran in the browser engine"
    flagged = 0
    for name, text in cases.items():
        expected = [
            {
                "check_id": finding.check.check_id,
                "offset": finding.offset,
                "excerpt": finding.excerpt,
            }
            for finding in scan(text, checks)
        ]
        assert browser[name] == expected, (
            f"{name}: the deployed browser screen disagrees with the validated "
            f"Python scanner"
        )
        flagged += len(expected)
    # Guard against a vacuous pass: an empty fixture, a scanner that returns
    # nothing, or an extraction that grabbed the wrong function would all make
    # the comparison above trivially true.
    assert flagged >= 6, "the fixtures actually exercise the screen"


@requires_node
def test_deployed_screen_reproduces_each_hcd_finding():
    """The README claim, asserted against the shipped engine.

    `tests/test_conformance.py` makes this assertion about the Python
    scanner. The same assertion has to hold for the code the public runs, or
    the published evidence covers the wrong implementation.
    """
    browser = _browser_findings(_cases())
    for provision in VALIDATION["provisions"]:
        found = {f["check_id"] for f in browser[provision["hcd_finding"]]}
        missing = set(provision["expected_checks"]) - found
        assert not missing, (
            f"{provision['hcd_finding']}: browser screen missed {missing}"
        )
    assert browser["control (must stay quiet)"] == [], (
        "conformant control text must stay quiet in the browser screen too"
    )


@requires_node
def test_parity_harness_detects_a_divergent_port():
    """The gate must fail when the engines disagree, not merely run.

    A parity test that passes because it compares nothing is the failure
    mode worth guarding against. This drops one rule the port duplicates by
    hand — the context window that keeps the size-cap screen off text with
    no ADU language — and requires the comparison to notice. The Python
    scanner stays quiet on this text; a port without the rule does not.
    """
    checks = load_checks(DATA / "checks.json")
    case = {"warehouse": "A warehouse shall not exceed 1,200 square feet."}
    assert scan(case["warehouse"], checks) == []

    mutated = _deployed_scanner_source().replace(
        "if (check.context_patterns) {", "if (false) {"
    )
    assert "if (false) {" in mutated, "the mutation applied"

    divergent = _browser_findings(case, source=mutated)["warehouse"]
    assert [f["check_id"] for f in divergent] == ["size-cap-conflict"], (
        "a port that dropped the context rule flags unrelated text; the "
        "parity comparison is what catches that"
    )
    assert divergent != [
        {
            "check_id": f.check.check_id,
            "offset": f.offset,
            "excerpt": f.excerpt,
        }
        for f in scan(case["warehouse"], checks)
    ], "the comparison the gate performs would fail on this divergence"
