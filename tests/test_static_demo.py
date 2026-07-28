import json
import shutil
import subprocess

import pytest

from demo.app import ROOT, static_path
from scripts.build_demo_bundle import OUTPUT, build_bundle


def test_committed_demo_bundle_matches_canonical_json():
    assert OUTPUT.read_text(encoding="utf-8") == build_bundle()


def test_index_loads_offline_bundle_before_application_code():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    bundle_tag = '<script src="data/demo-data.js"></script>'
    application_start = "<script>\nconst STRINGS"

    assert bundle_tag in html
    assert application_start in html
    assert html.index(bundle_tag) < html.index(application_start)
    assert "globalThis.PERMIT_PATHWAYS_DEMO_DATA" in html


def test_static_result_cards_keep_explanations_separate_from_matching():
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "function screen(intake)" in html
    assert "function renderResultCard(rule, explanation)" in html
    assert "async function normalizeExplanations(payload, rules)" in html
    assert "Array.isArray(payload.entries)" in html
    assert "async function citationFingerprint(rule)" in html
    assert "async function ruleFingerprint(rule)" in html
    assert "function validHighlights(value)" in html
    assert "record.citation_fingerprint !== expectedFingerprint" in html
    assert "record.rule_fingerprint !== expectedRuleFingerprint" in html
    assert "if (!globalThis.crypto || !globalThis.crypto.subtle) return new Map()" in html
    assert "EXPLANATIONS.get(rule.rule_id)" in html
    assert "EXPLANATIONS = await normalizeExplanations" in html
    assert "data-rule-id=" in html
    assert "<details>" in html
    assert 'source: "Source"' in html
    assert "Draft explanation · made with AI · not reviewed by a person" in html
    assert "no revisado para comprobar su exactitud" in html
    assert "We are not showing next steps" in html
    assert "Check candidate pathways" in html
    assert "this prototype's encoded state rule set" in html
    assert 'id="resultStatus"' in html


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_static_explanation_normalizer_accepts_canonical_data_and_fails_closed():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    validation_source = html[
        html.index("function nonBlank"):
        html.index("function renderForm")
    ]
    bundle = json.loads(
        (ROOT / "data" / "explanations" / "plain-language.json").read_text(
            encoding="utf-8"
        )
    )
    rules = []
    for path in sorted((ROOT / "data" / "rules").glob("*.json")):
        rules.extend(json.loads(path.read_text(encoding="utf-8")))
    script = f"""
import {{webcrypto}} from "node:crypto";
Object.defineProperty(globalThis, "crypto",
  {{value: webcrypto, configurable: true}});
{validation_source}
const payload = {json.dumps(bundle)};
const rules = {json.dumps(rules)};
const canonical = await normalizeExplanations(payload, rules);
if (canonical.size !== rules.length) throw new Error(`canonical:${{canonical.size}}`);

const duplicate = structuredClone(payload);
duplicate.entries.push(structuredClone(duplicate.entries[0]));
const duplicateResult = await normalizeExplanations(duplicate, rules);
if (duplicateResult.has(duplicate.entries[0].source_rule_id))
  throw new Error("duplicate accepted");

const duplicateRules = [...rules, structuredClone(rules[0])];
const duplicateRuleResult = await normalizeExplanations(payload, duplicateRules);
if (duplicateRuleResult.size !== 0)
  throw new Error("duplicate canonical rule ID did not fail closed");

const changed = structuredClone(rules);
changed[0].notes += " changed";
const drifted = await normalizeExplanations(payload, changed);
if (drifted.has(changed[0].rule_id)) throw new Error("rule drift accepted");

const realCrypto = globalThis.crypto;
Object.defineProperty(globalThis, "crypto",
  {{value: undefined, configurable: true}});
const noCrypto = await normalizeExplanations(payload, rules);
if (noCrypto.size !== 0) throw new Error("no-WebCrypto did not fail closed");

Object.defineProperty(globalThis, "crypto", {{
  value: {{subtle: {{digest: async () => {{throw new Error("digest failed")}}}}}},
  configurable: true
}});
const rejectedDigest = await normalizeExplanations(payload, rules);
if (rejectedDigest.size !== 0)
  throw new Error("digest rejection did not fail closed");
Object.defineProperty(globalThis, "crypto",
  {{value: realCrypto, configurable: true}});
"""
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )


def test_demo_server_exposes_only_intended_static_files():
    assert static_path("/index.html") == ROOT / "index.html"
    assert static_path("/showcase") == ROOT / "index.html"
    assert static_path("/data/demo-data.js") == OUTPUT
    assert static_path("/data/explanations/plain-language.json") == (
        ROOT / "data" / "explanations" / "plain-language.json"
    )

    assert static_path("/README.md") is None
    assert static_path("/data/missing.json") is None
    assert static_path("/data/../README.md") is None
    assert static_path("/data/%2e%2e/README.md") is None
