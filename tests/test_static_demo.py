import json
import shutil
import subprocess
from io import BytesIO

import pytest

from demo.app import (
    Handler,
    MAX_BODY_BYTES,
    ROOT,
    result_page,
    static_path,
)
from scripts.build_demo_bundle import OUTPUT, build_bundle


def test_committed_demo_bundle_matches_canonical_json():
    assert OUTPUT.read_text(encoding="utf-8") == build_bundle()


def test_python_trust_rehearsal_uses_human_readable_source_label():
    html = (ROOT / "demo" / "app.py").read_text(encoding="utf-8")
    assert '"Gov. Code § 66321"' in html
    assert "Gov. Code § {html.escape(changed[0])}" not in html


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
    assert "function renderResultCard(rule, explanation" in html
    assert "async function normalizeExplanations(payload, rules)" in html
    assert "Array.isArray(payload.entries)" in html
    assert "async function citationFingerprint(rule)" in html
    assert "async function ruleFingerprint(rule)" in html
    assert "async function localizedContentFingerprint" in html
    assert "source_dependencies: rule.source_dependencies" in html
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
    assert "limited set of rules in this prototype" in html
    assert 'id="resultStatus"' in html
    assert '"primary_dwelling_status"' in html
    assert '"adu_project_form"' in html
    assert '["yes","Yes"],["no","No"],["unknown","I\'m not sure"]' in html
    assert 'id="loadSample"' in html and "<button" in html
    assert 'id="resultsHeading" tabindex="-1"' in html
    assert 'aria-invalid' in html
    assert 'name="has_primary_dwelling"' not in html
    assert '"jadu")\n    return ["primary_dwelling_status", "unpermitted_existing"]' in html
    assert "two_unit_contributing_historic_location" in html
    assert "lot_split_alters_historic_district_resource" in html
    assert "Supporting local information is shown below" in html
    assert 'fieldset data-question="${esc(name)}"${describedBy}' in html
    assert "ADU review-clock illustration" in html


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_static_explanation_normalizer_accepts_canonical_data_and_fails_closed():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    validation_source = html[
        html.index("function isJsonNumber"):
        html.index("function renderForm")
    ]
    bundle = json.loads(
        (ROOT / "data" / "explanations" / "plain-language.json").read_text(
            encoding="utf-8"
        )
    )
    rules = []
    for path in sorted((ROOT / "data" / "rules").glob("*.json")):
        if path.name == "index.json":
            continue
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
if (normalizeRules(rules).length !== rules.length)
  throw new Error("canonical rules rejected");

function expectRuleRejection(mutator, label) {{
  const invalid = structuredClone(rules);
  mutator(invalid[0]);
  try {{
    normalizeRules(invalid);
    throw new Error(`${{label}} accepted`);
  }} catch (error) {{
    if (String(error.message) === `${{label}} accepted`) throw error;
  }}
}}
expectRuleRejection(rule => {{ rule.unknown_field = true; }}, "unknown field");
expectRuleRejection(
  rule => {{ rule.citation.verified_on = "2099-01-01"; }},
  "future citation date"
);
expectRuleRejection(
  rule => {{ delete rule.required_documents; }},
  "missing required_documents"
);
expectRuleRejection(
  rule => {{ rule.criteria[0].value = Number.MAX_SAFE_INTEGER + 1; }},
  "unsafe numeric criterion"
);

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


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_static_matcher_is_type_strict_and_source_changes_use_exact_ids():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    matching_source = html[
        html.index("function isJsonNumber"):
        html.index("function esc")
    ]
    script = f"""
function nonBlank(value) {{
  return typeof value === "string" && value.trim().length > 0;
}}
function validIsoDate(value) {{
  if (!/^\\d{{4}}-\\d{{2}}-\\d{{2}}$/.test(value || "")) return false;
  const parsed = new Date(`${{value}}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime())
    && parsed.toISOString().slice(0, 10) === value;
}}
{matching_source}
const boolRule = {{
  criteria: [{{field: "confirmed", op: "eq", value: true}}]
}};
if (!matches(boolRule, {{confirmed: true}})) throw new Error("true rejected");
if (matches(boolRule, {{confirmed: 1}})) throw new Error("boolean coerced");
if (matches(boolRule, {{confirmed: "unknown"}})) throw new Error("unknown matched");
if (matches(boolRule, {{}})) throw new Error("missing matched");
const today = new Date().toISOString().slice(0, 10);
const sourceRule = {{
  citation: {{verified_on: today}},
  source_dependencies: ["ca-gov-66321"]
}};
if (ruleStatus(sourceRule, ["66321"]) !== "verified")
  throw new Error("substring source ID matched");
if (ruleStatus(sourceRule, ["ca-gov-66321"]) !== "stale")
  throw new Error("exact source ID did not match");
const futureRule = {{
  citation: {{verified_on: "2099-01-01"}},
  source_dependencies: []
}};
if (ruleStatus(futureRule, []) !== "stale")
  throw new Error("future source date accepted");
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


def _capturing_handler(path="/", *, body=b"", headers=None):
    handler = Handler.__new__(Handler)
    handler.path = path
    handler.headers = headers or {}
    handler.rfile = BytesIO(body)
    handler.wfile = BytesIO()
    handler.close_connection = False
    handler.status = None
    handler.response_headers = {}
    handler.send_response = lambda status: setattr(handler, "status", status)
    handler.send_header = (
        lambda name, value: handler.response_headers.__setitem__(name, value)
    )
    handler.end_headers = lambda: None
    return handler


def test_demo_server_sets_security_headers_and_limits_post_routes():
    handler = _capturing_handler()
    handler._send("<h1>ok</h1>")
    assert handler.status == 200
    headers = handler.response_headers
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"

    wrong_route = _capturing_handler(
        "/trust",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": "0",
        },
    )
    wrong_route.do_POST()
    assert wrong_route.status == 405
    assert wrong_route.response_headers["Allow"] == "GET"

    oversized = _capturing_handler(
        "/screen",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": str(MAX_BODY_BYTES + 1),
        },
    )
    oversized.do_POST()
    assert oversized.status == 413
    assert b"Request is too large" in oversized.wfile.getvalue()


def test_demo_server_unknown_material_fact_routes_to_staff():
    body = result_page(
        {
            "project_type": ["adu"],
            "jurisdiction": ["davis"],
            "primary_dwelling_status": ["existing_single_family"],
            "adu_project_form": ["new_detached"],
            "unpermitted_existing": ["unknown"],
        },
        "en",
    )
    assert "Staff review is needed" in body
    assert "data-rule-id=" not in body


def test_python_demo_exposes_jadu_legalization_and_route_specific_sb9_fields():
    source = (ROOT / "demo" / "app.py").read_text(encoding="utf-8")
    assert '"jadu": ("primary_dwelling_status", "unpermitted_existing")' in source
    assert '"two_unit_contributing_historic_location"' in source
    assert '"lot_split_alters_historic_district_resource"' in source
    assert 's["unpermitted_questions"]["adu"]' in source
    assert 's["unpermitted_questions"]["jadu"]' in source
    assert 'projects="jadu"' in source
    assert 'f"{described_by}>"' in source

    result = result_page(
        {
            "project_type": ["jadu"],
            "jurisdiction": ["davis"],
            "primary_dwelling_status": ["existing_single_family"],
            "unpermitted_existing": ["yes"],
        },
        "en",
    )
    assert 'data-rule-id="jadu-unpermitted-legalization"' in result


def test_python_demo_warns_when_only_local_process_information_matches():
    result = result_page(
        {
            "project_type": ["adu"],
            "jurisdiction": ["woodland"],
            "primary_dwelling_status": ["none"],
            "adu_project_form": ["new_detached"],
            "unpermitted_existing": ["no"],
        },
        "en",
    )
    assert "do not identify a possible path" in result
    assert "Supporting local information is shown below" in result
    assert 'data-rule-id="woodland-adu-ordinance-2026"' in result
