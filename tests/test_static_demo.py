import json
import re
import shutil
import subprocess
from io import BytesIO

import pytest

from demo.app import (
    Handler,
    MAX_BODY_BYTES,
    ROOT,
    STRINGS as DEMO_STRINGS,
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


def test_static_pages_load_only_the_assets_they_need():
    landing = (ROOT / "index.html").read_text(encoding="utf-8")
    bundle_tag = '<script src="data/demo-data.js"></script>'
    application_tag = '<script src="assets/demo.js"></script>'

    assert bundle_tag not in landing
    assert application_tag not in landing
    for page_name, page_id in {
        "check.html": "project",
        "review.html": "review",
        "evidence.html": "evidence",
    }.items():
        html = (ROOT / page_name).read_text(encoding="utf-8")
        assert f'<body data-page="{page_id}">' in html
        assert bundle_tag in html
        assert application_tag in html
        assert html.index(bundle_tag) < html.index(application_tag)

    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    assert "globalThis.PERMIT_PATHWAYS_DEMO_DATA" in application


def test_static_pages_have_consistent_navigation_and_resolvable_links():
    pages = [
        ROOT / "index.html",
        ROOT / "check.html",
        ROOT / "review.html",
        ROOT / "evidence.html",
    ]
    expected_nav = [
        "Home",
        "Check a project",
        "Review local rules",
        "Evidence &amp; updates",
    ]
    for path in pages:
        html = path.read_text(encoding="utf-8")
        assert html.count("<main ") == 1
        assert html.count("<h1") == 1
        assert 'href="#mainContent"' in html
        assert html.count('aria-current="page"') == 1
        assert 'http-equiv="Content-Security-Policy"' in html
        for label in expected_nav:
            assert f">{label}</a>" in html
        for target in re.findall(r'(?:href|src)="([^"]+)"', html):
            if target.startswith(("https://", "http://", "#", "data:")):
                continue
            assert not target.startswith("/")
            local_target = target.split("?", 1)[0].split("#", 1)[0]
            assert (ROOT / local_target).is_file(), (path.name, target)


def test_public_brand_name_and_tagline_are_consistent():
    public_files = {
        ROOT / "index.html",
        ROOT / "check.html",
        ROOT / "review.html",
        ROOT / "evidence.html",
        ROOT / "assets" / "demo.js",
        ROOT / "demo" / "app.py",
        ROOT / "README.md",
        ROOT / "docs" / "PRODUCT-CONTEXT.md",
        ROOT / "AGENTS.md",
        ROOT / "LICENSE",
        ROOT / "THIRD_PARTY_NOTICES.md",
        ROOT / "src" / "permit_pathways" / "__init__.py",
    }
    legacy_human_name = "Permit " + "Pathways"
    for path in public_files:
        assert legacy_human_name not in path.read_text(encoding="utf-8")

    landing = (ROOT / "index.html").read_text(encoding="utf-8")
    project = (ROOT / "check.html").read_text(encoding="utf-8")
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    tagline = (
        "Find a candidate route. See the sources behind it. "
        "Take open questions to staff."
    )
    assert (
        "<title>Permit Bearings | California housing permit guidance</title>"
        in landing
    )
    assert '<meta property="og:title" content="Permit Bearings">' in landing
    assert "Check a California housing project" in landing
    assert "Start a project check" in landing
    assert 'id="t-tagline"' in project
    assert tagline in application

    assert DEMO_STRINGS["en"]["title"] == "Permit Bearings | demo"
    assert DEMO_STRINGS["en"]["tagline"] == tagline
    assert DEMO_STRINGS["es"]["title"] == "Permit Bearings | demostración"
    assert DEMO_STRINGS["es"]["tagline"] == (
        "Encuentre una posible ruta. Vea las fuentes que la respaldan. "
        "Consulte las preguntas pendientes con el personal de la agencia."
    )
    rendered_page = result_page(
        {
            "jurisdiction": "Davis",
            "project_type": "adu",
            "primary_dwelling_status": "existing_single_family",
            "adu_project_form": "new_detached",
        },
        "en",
    )
    assert '<a href="/?lang=en">Permit Bearings</a>' in rendered_page

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "permit-pathways"' in pyproject
    assert "globalThis.PERMIT_PATHWAYS_DEMO_DATA" in application
    assert (ROOT / "src" / "permit_pathways").is_dir()


def test_public_interface_copy_uses_no_em_dashes():
    public_sources = [
        ROOT / "index.html",
        ROOT / "check.html",
        ROOT / "review.html",
        ROOT / "evidence.html",
        ROOT / "assets" / "demo.js",
        ROOT / "demo" / "app.py",
    ]
    em_dash = chr(0x2014)
    for path in public_sources:
        assert em_dash not in path.read_text(encoding="utf-8"), path

    rendered = result_page(
        {
            "jurisdiction": ["davis"],
            "project_type": ["adu"],
            "primary_dwelling_status": ["existing_single_family"],
            "adu_project_form": ["new_detached"],
            "unpermitted_existing": ["no"],
        },
        "en",
    )
    assert em_dash not in rendered


def test_static_site_uses_published_california_design_tokens():
    css = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")

    for token, value in {
        "--primary-900": "#003688",
        "--cagov-primary": "#004abc",
        "--cagov-highlight": "#fec02f",
        "--accent2-300": "#ecb32d",
        "--success-900": "#154425",
        "--danger-900": "#721923",
        "--w-lg": "73.5rem",
        "--w-page-content": "54.75rem",
    }.items():
        assert f"{token}: {value}" in css
    assert '--site-font: "Public Sans", "Noto Sans", Arial, sans-serif' in css
    assert "--paper: var(--gray-50)" in css
    assert "--blue: var(--primary-900)" in css
    assert "--yellow: var(--cagov-highlight)" in css
    assert "outline: 3px solid var(--accent2-300)" in css
    assert "Avenir" not in css


def test_static_result_cards_keep_explanations_separate_from_matching():
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    project = (ROOT / "check.html").read_text(encoding="utf-8")
    review = (ROOT / "review.html").read_text(encoding="utf-8")
    evidence = (ROOT / "evidence.html").read_text(encoding="utf-8")

    assert "function screen(intake)" in application
    assert "function renderResultCard(rule, explanation" in application
    assert "async function normalizeExplanations(payload, rules)" in application
    assert "Array.isArray(payload.entries)" in application
    assert "async function citationFingerprint(rule)" in application
    assert "async function ruleFingerprint(rule)" in application
    assert "async function localizedContentFingerprint" in application
    assert "source_dependencies: rule.source_dependencies" in application
    assert "function validHighlights(value)" in application
    assert "record.citation_fingerprint !== expectedFingerprint" in application
    assert "record.rule_fingerprint !== expectedRuleFingerprint" in application
    assert (
        "if (!globalThis.crypto || !globalThis.crypto.subtle) return new Map()"
        in application
    )
    assert "EXPLANATIONS.get(rule.rule_id)" in application
    assert "EXPLANATIONS = await normalizeExplanations" in application
    assert "data-rule-id=" in application
    assert "<details>" in application
    assert 'source: "Source"' in application
    assert "Draft explanation · made with AI · not reviewed by a person" in application
    assert "no revisado para comprobar su exactitud" in application
    assert "We are not showing next steps" in application
    assert "limited set of rules in this prototype" in application
    assert '"primary_dwelling_status"' in application
    assert '"adu_project_form"' in application
    assert '["yes","Yes"],["no","No"],["unknown","I\'m not sure"]' in application
    assert 'id="resultsHeading" tabindex="-1"' in application
    assert 'aria-invalid' in application
    assert 'name="has_primary_dwelling"' not in application
    assert (
        '"jadu")\n    return ["primary_dwelling_status", "unpermitted_existing"]'
        in application
    )
    assert "two_unit_contributing_historic_location" in application
    assert "lot_split_alters_historic_district_resource" in application
    assert "Supporting local information is shown below" in application
    assert 'fieldset data-question="${esc(name)}"${describedBy}' in application

    assert "Check candidate pathways" in project
    assert 'id="resultStatus"' in project
    assert 'id="clockBtn"' in project
    assert 'id="loadSample"' in review
    assert 'id="scanStatus"' in review
    assert 'id="simBtn"' in evidence
    assert 'id="sourceTable"' in evidence


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_static_explanation_normalizer_accepts_canonical_data_and_fails_closed():
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    validation_source = application[
        application.index("function isJsonNumber"):
        application.index("function renderForm")
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
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    matching_source = application[
        application.index("function isJsonNumber"):
        application.index("function esc")
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
    assert static_path("/check.html") == ROOT / "check.html"
    assert static_path("/review.html") == ROOT / "review.html"
    assert static_path("/evidence.html") == ROOT / "evidence.html"
    assert static_path("/showcase") == ROOT / "check.html"
    assert static_path("/assets/site.css") == ROOT / "assets" / "site.css"
    assert static_path("/assets/demo.js") == ROOT / "assets" / "demo.js"
    assert static_path("/data/demo-data.js") == OUTPUT
    assert static_path("/data/explanations/plain-language.json") == (
        ROOT / "data" / "explanations" / "plain-language.json"
    )

    assert static_path("/README.md") is None
    assert static_path("/assets/missing.css") is None
    assert static_path("/assets/../README.md") is None
    assert static_path("/assets/%2e%2e/README.md") is None
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
    assert "style-src 'self' 'unsafe-inline'" in headers["Content-Security-Policy"]
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
