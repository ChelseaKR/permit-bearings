import json
import re
import shutil
import subprocess
from datetime import date
from io import BytesIO

import pytest
from demo.app import (
    MAX_BODY_BYTES,
    ROOT,
    Handler,
    result_page,
    static_path,
)
from demo.app import (
    STRINGS as DEMO_STRINGS,
)
from scripts.build_demo_bundle import (
    OUTPUT,
    build_bundle,
    build_readiness_payload,
)


def test_committed_demo_bundle_matches_canonical_json():
    assert OUTPUT.read_text(encoding="utf-8") == build_bundle()


def test_python_trust_rehearsal_uses_human_readable_source_label():
    html = (ROOT / "demo" / "app.py").read_text(encoding="utf-8")
    assert '"Gov. Code § 66321"' in html
    assert "Gov. Code § {html.escape(changed[0])}" not in html


def test_static_pages_load_only_the_assets_they_need():
    landing = (ROOT / "index.html").read_text(encoding="utf-8")
    bundle_tag = '<script src="data/demo-data.js" defer></script>'
    application_src = 'src="assets/demo.js'

    assert bundle_tag not in landing
    assert application_src not in landing
    for page_name, page_id in {
        "check.html": "project",
        "prepare.html": "readiness",
        "review.html": "review",
        "evidence.html": "evidence",
    }.items():
        html = (ROOT / page_name).read_text(encoding="utf-8")
        assert f'<body data-page="{page_id}">' in html
        assert bundle_tag in html
        assert application_src in html
        assert html.index(bundle_tag) < html.index(application_src)

    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    assert "globalThis.PERMIT_PATHWAYS_DEMO_DATA" in application


def test_static_pages_have_consistent_navigation_and_resolvable_links():
    pages = [
        ROOT / "index.html",
        ROOT / "check.html",
        ROOT / "prepare.html",
        ROOT / "review.html",
        ROOT / "evidence.html",
    ]
    expected_nav = [
        "Home",
        "Check a project",
        "Packet sample",
        "Review local rules",
        "Evidence &amp; updates",
    ]
    for path in pages:
        html = path.read_text(encoding="utf-8")
        assert html.count("<main ") == 1
        assert html.count("<h1") == 1
        assert 'href="#mainContent"' in html
        assert html.count('aria-current="page"') == 2
        assert html.count('class="mobile-menu"') == 1
        assert html.count('aria-label="Mobile primary"') == 1
        assert "<summary>Sections</summary>" in html
        assert (
            '<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">' in html
        )
        assert 'http-equiv="Content-Security-Policy"' in html
        for label in expected_nav:
            assert f">{label}</a>" in html
        for target in re.findall(r'(?:href|src)="([^"]+)"', html):
            if target.startswith(("https://", "http://", "#", "data:")):
                continue
            assert not target.startswith("/")
            local_target = target.split("?", 1)[0].split("#", 1)[0]
            assert (ROOT / local_target).is_file(), (path.name, target)


def test_landing_scope_matches_the_current_bounded_davis_record():
    landing = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "Davis source record is explicitly unverified" not in landing
    assert (
        "Davis record reports only the City\u2019s published processing categories"
        in landing
    )
    assert "HCD\u2019s unresolved ordinance-status warning" in landing


def test_showcase_submission_draft_preserves_portal_word_limits():
    draft = (ROOT / "docs" / "SHOWCASE-SUBMISSION-DRAFT.md").read_text(encoding="utf-8")
    bounded_responses = [
        ("### Company description", "## Section 2", 43, 50),
        ("### Solution description", "### AI technical workflow", 189, 200),
        ("### AI technical workflow", "### Maturity", 145, 150),
        ("### Maturity", "## Section 4", 89, 100),
        (
            "### Work required from jurisdiction staff",
            "### Source data and integrations",
            89,
            100,
        ),
        (
            "### Source data and integrations",
            "### Known exceptions",
            95,
            100,
        ),
        (
            "### Known exceptions",
            "### Large jurisdiction experience",
            95,
            100,
        ),
    ]
    for start, end, expected_words, word_limit in bounded_responses:
        section = draft[draft.index(start) : draft.index(end)]
        answer = " ".join(
            line[1:].strip()
            for line in section.splitlines()
            if line.startswith(">") and line[1:].strip()
        )
        assert len(answer.split()) == expected_words, start
        assert expected_words <= word_limit - 5, start
        assert f"Draft count: {expected_words} words by whitespace." in section, start

    assert "Status: working draft, not submitted." in draft
    assert "[LEGAL ENTITY OR INDIVIDUAL APPLICANT NAME]" in draft
    normalized = re.sub(r"\s+", " ", draft.replace(">", " "))
    assert "No applicant, planner, counsel, translator, or jurisdiction" in normalized


def test_public_brand_name_and_tagline_are_consistent():
    public_files = {
        ROOT / "index.html",
        ROOT / "check.html",
        ROOT / "prepare.html",
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
        "<title>Permit Bearings | California ADU, JADU, and SB 9 prototype</title>"
        in landing
    )
    assert (
        '<meta property="og:title" content="Permit Bearings | California ADU, '
        'JADU, and SB 9 prototype">' in landing
    )
    assert (
        '<meta property="og:url" '
        'content="https://chelseakr.github.io/permit-pathways/">' in landing
    )
    assert (
        '<meta property="og:image" content="https://chelseakr.github.io/'
        'permit-pathways/assets/social-card.png">' in landing
    )
    assert '<meta name="twitter:card" content="summary_large_image">' in landing
    assert "Check an ADU, JADU, or SB 9 project" in landing
    assert "Start a project check" in landing
    assert 'href="check.html?sample=adu"' in landing
    social_card = (ROOT / "assets" / "social-card.png").read_bytes()
    assert social_card[:8] == b"\x89PNG\r\n\x1a\n"
    assert int.from_bytes(social_card[16:20], "big") == 1200
    assert int.from_bytes(social_card[20:24], "big") == 630
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
        ROOT / "prepare.html",
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


def test_mobile_navigation_and_evidence_records_have_responsive_hooks():
    css = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")

    assert ".mobile-menu" in css
    assert '.mobile-nav a[aria-current="page"]' in css
    assert ".table-scroll td::before" in css
    for label in (
        "Rule",
        "Scope",
        "Status",
        "Source",
        "Monitoring",
        "Recorded",
        "SHA-256",
    ):
        assert f'data-label="{label}"' in application


def test_section_headings_use_interface_type_instead_of_utility_mono():
    css = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")

    for selector in (
        ".result-group > h3",
        ".result-card h5",
        ".scanner-notes h3",
    ):
        match = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>[^}}]+)\}}", css)
        assert match, selector
        declarations = match.group("body")
        assert "font-family: var(--display);" in declarations
        assert "font-family: var(--utility);" not in declarations
        assert "text-transform: uppercase;" not in declarations


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
    assert '<details class="rule-details"' in application
    assert 'source: "Source"' in application
    assert "Draft explanation · made with AI · not reviewed by a person" in application
    assert "no revisado para comprobar su exactitud" in application
    assert "We are not showing next steps" in application
    assert "limited rules in this prototype" in application
    assert '"primary_dwelling_status"' in application
    assert '"adu_project_form"' in application
    assert '["yes","Yes"],["no","No"],["unknown","I\'m not sure"]' in application
    assert 'id="resultsHeading" tabindex="-1"' in application
    assert 'class="edit-answers" href="#screenHeading"' in application
    assert 'id="screenHeading" tabindex="-1"' in project
    assert "heading.focus()" in application
    assert "aria-invalid" in application
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
    assert 'href="check.html?sample=adu"' in project
    assert 'id="projectSampleNotice"' in project
    assert 'id="resultStatus"' in project
    assert 'id="clockBtn"' in project
    assert 'id="loadSample"' in review
    assert 'id="scanStatus"' in review
    assert 'id="simBtn"' in evidence
    assert 'id="sourceTable"' in evidence


def test_packet_sample_renders_only_the_generated_python_result():
    readiness, _ = build_readiness_payload()
    page = (ROOT / "prepare.html").read_text(encoding="utf-8")
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")

    assert readiness["packet"]["synthetic"] is True
    assert readiness["result"]["overall_status"] == "known_gaps"
    assert readiness["counts"] == {
        "present": 14,
        "missing": 3,
        "not_applicable": 3,
        "conflicting": 0,
        "needs_staff_review": 5,
        "not_evaluated": 0,
    }
    assert readiness["remedies"]["review"]["status"] == ("prototype_review_pending")
    assert readiness["ai_trace"]["runtime_model_call"] is False
    assert readiness["ai_trace"]["applicant_data_sent_to_model"] is False
    assert readiness["ai_trace"]["mapping_version"] == "1.1.0"
    assert readiness["ai_trace"]["mapping_review_status"] == (
        "prototype_review_pending"
    )
    assert readiness["ai_trace"]["mapping_provider"] == "unknown"
    assert readiness["ai_trace"]["mapping_model"] == "unknown"
    assert readiness["ai_trace"]["mapping_run_record_status"] == ("not_recorded")
    assert readiness["ai_trace"]["remedy_review_status"] == ("prototype_review_pending")
    assert readiness["ai_trace"]["remedy_reviewer"] is None
    assert readiness["source_review_due_on"] == "2027-01-25"
    parcel_facts = [
        fact
        for fact in readiness["packet"]["facts"]
        if fact["provenance"] == "synthetic_public_record_fixture"
    ]
    assert [fact["source_field"] for fact in parcel_facts] == [
        "CITY",
        "LU_Descr",
    ]
    assert {fact["source_id"] for fact in parcel_facts} == {"yolo-public-parcels-layer"}

    assert '<body data-page="readiness">' in page
    assert "This is a synthetic packet." in page
    assert re.search(r"certify\s+completeness", page)
    assert 'id="readinessOutput"' in page
    assert re.search(r"No model\s+runs in the public browser\.", page)
    assert "function renderReadiness(data)" in application
    assert "data.result.findings.filter" in application
    assert "function evaluateReadiness" not in application
    assert "function readinessSourceIsCurrent(data)" in application
    assert "function readinessParcelEvidenceMarkup(data, current)" in application
    assert "no address, APN, or live parcel was" in application
    assert "Action copy is" in application
    assert "withheld." in application
    assert "data.readiness" in application


def test_packet_build_explicitly_replays_canonical_evaluation_date(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "permit_pathways.dates.utc_today",
        lambda: date(2027, 1, 26),
    )

    readiness, _ = build_readiness_payload()

    assert readiness["packet"]["evaluated_on"] == "2026-07-30"
    assert readiness["result"]["evaluated_on"] == "2026-07-30"
    assert readiness["result"]["source_status"] == "current"
    assert readiness["result"]["source_status_as_of"] == "2026-07-30"
    assert readiness["result"]["source_review_due_on"] == "2027-01-25"
    assert readiness["evidence_manifest"]["source_status_as_of"] == ("2026-07-30")
    assert readiness["evidence_manifest"]["source_review_due_on"] == ("2027-01-25")


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_packet_renderer_honors_trust_states_and_conflicts():
    readiness, _ = build_readiness_payload()
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    renderer_source = application[
        application.index("const READINESS_FINDING_STATUSES") : application.index(
            "function fetchJson"
        )
    ]
    script = f"""
function nonBlank(value) {{
  return typeof value === "string" && value.trim().length > 0;
}}
function validStableId(value) {{
  return /^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$/.test(value || "");
}}
function validIsoDate(value) {{
  if (!/^\\d{{4}}-\\d{{2}}-\\d{{2}}$/.test(value || "")) return false;
  const parsed = new Date(`${{value}}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime())
    && parsed.toISOString().slice(0, 10) === value;
}}
function validHttpsUrl(value) {{
  try {{
    return new URL(value).protocol === "https:";
  }} catch {{
    return false;
  }}
}}
function safeExternalUrl(value) {{
  return validHttpsUrl(value) ? value : null;
}}
function formatSourceDate(value) {{
  return value;
}}
function esc(value) {{
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}}
let READINESS = null;
const nodes = {{
  readinessOutput: {{
    innerHTML: "",
    attributes: {{}},
    setAttribute(name, value) {{ this.attributes[name] = value; }},
  }},
  readinessPacketId: {{textContent: ""}},
  readinessDate: {{textContent: ""}},
}};
const document = {{
  getElementById(id) {{ return nodes[id] || null; }},
}};
{renderer_source}
const canonical = {json.dumps(readiness)};

function check(condition, message) {{
  if (!condition) throw new Error(message);
}}
function render(payload) {{
  nodes.readinessOutput.innerHTML = "";
  renderReadiness(payload);
  return nodes.readinessOutput.innerHTML;
}}
function setDueDate(payload, value) {{
  payload.source_review_due_on = value;
  payload.result.source_review_due_on = value;
  payload.evidence_manifest.source_review_due_on = value;
}}
function setAllFindings(payload, status) {{
  for (const finding of payload.result.findings) finding.status = status;
  for (const key of Object.keys(payload.counts)) payload.counts[key] = 0;
  payload.counts[status] = payload.result.findings.length;
}}

check(validReadinessData(canonical), "canonical readiness data rejected");
const canonicalHtml = render(structuredClone(canonical));
check(
  canonicalHtml.includes("3 reported missing items in this bounded checklist"),
  "known-gaps headline ignored the overall status"
);
check(
  canonicalHtml.includes("3 direct questions for staff are included"),
  "staff questions were omitted from the summary"
);
check(
  canonicalHtml.includes("Which parcel fields shaped this sample")
    && canonicalHtml.includes("<code>CITY</code>")
    && canonicalHtml.includes("<code>LU_Descr</code>"),
  "source-shaped parcel fixture evidence was omitted"
);

const invalidOverall = structuredClone(canonical);
invalidOverall.result.overall_status = "complete";
check(
  !validReadinessData(invalidOverall),
  "unknown overall readiness status accepted"
);

const mismatchedParcelField = structuredClone(canonical);
mismatchedParcelField.packet.facts[0].source_field = "LU_Descr";
check(
  !validReadinessData(mismatchedParcelField),
  "mismatched parcel source field accepted"
);

const assertionWithSourceClaim = structuredClone(canonical);
assertionWithSourceClaim.packet.facts[2].source_id =
  "yolo-public-parcels-layer";
check(
  !validReadinessData(assertionWithSourceClaim),
  "applicant assertion with source claim accepted"
);

const conflict = structuredClone(canonical);
const conflictFinding = conflict.result.findings.find(
  finding => finding.requirement_id === "plot-plan-address-apn"
);
conflictFinding.status = "conflicting";
conflict.counts.missing -= 1;
conflict.counts.conflicting += 1;
const missingAction = conflict.remedies.entries.find(
  entry => entry.requirement_id === "plot-plan-address-apn"
).action;
const conflictHtml = render(conflict);
check(
      conflictHtml.includes('<span>Reported conflict</span>')
    && conflictHtml.includes('id="conflictHeading">Reported conflicts'),
  "conflicting finding was not rendered distinctly"
);
check(
  conflictHtml.includes("Confirm which reported version is correct"),
  "conflicting finding omitted reconcile copy"
);
check(
  !conflictHtml.includes(missingAction),
  "conflicting finding reused its missing-item remedy"
);

const outside = structuredClone(canonical);
outside.result.overall_status = "outside_bounded_workflow";
outside.result.staff_questions = [
  "Ask Woodland staff which current checklist applies to this project.",
];
setAllFindings(outside, "not_evaluated");
const outsideHtml = render(outside);
check(
  outsideHtml.includes("This packet is outside the encoded Woodland workflow"),
  "outside-workflow status was reduced to a gap count"
);
check(
  outsideHtml.includes("25 checklist items were not evaluated")
    && outsideHtml.includes(outside.result.staff_questions[0]),
  "outside-workflow summary omitted unevaluated items or staff routing"
);
check(
  !outsideHtml.includes('id="missingHeading"'),
  "outside-workflow result rendered a missing-item ledger"
);

const needsReview = structuredClone(canonical);
needsReview.result.overall_status = "needs_review";
needsReview.result.staff_questions = [
  "Does this project use the City preapproved plan workflow?",
];
setAllFindings(needsReview, "not_evaluated");
const needsReviewHtml = render(needsReview);
check(
  needsReviewHtml.includes(
    "Confirm the workflow before using this checklist result"
  ),
  "needs-review status was reduced to a gap count"
);
check(
  needsReviewHtml.includes("25 items were not evaluated")
    && needsReviewHtml.includes("1 direct question for staff is included"),
  "needs-review summary omitted unresolved state"
);

const sourceReview = structuredClone(canonical);
sourceReview.result.overall_status = "source_review_required";
sourceReview.result.source_status = "source_review_required";
sourceReview.evidence_manifest.source_status = "source_review_required";
sourceReview.result.staff_questions = [
  "Ask the City to confirm the current checklist.",
];
setAllFindings(sourceReview, "needs_staff_review");
const sourceReviewHtml = render(sourceReview);
check(
  sourceReviewHtml.includes(
    "Source review is required before using this packet result"
  ),
  "source-review status was reduced to a finding count"
);
check(
  sourceReviewHtml.includes("1 direct question for staff is included"),
  "source-review summary omitted the staff question"
);

const runtimeStale = structuredClone(canonical);
setDueDate(runtimeStale, "2000-01-01");
const staleHtml = render(runtimeStale);
check(
  staleHtml.includes("Open the historical generated evidence manifest"),
  "stale runtime kept a current-looking manifest link"
);
check(
  staleHtml.includes("source status")
    && staleHtml.includes("as of")
    && staleHtml.includes("It is not a current source"),
  "stale manifest did not disclose its historical source status"
);
check(
  !staleHtml.includes('id="missingHeading"'),
  "stale runtime exposed action-oriented findings"
);
"""
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_static_sample_uses_canonical_golden_case_and_normal_submission_path():
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    helper_source = application[
        application.index("const SB9_BASE_FIELDS") : application.index(
            "function renderProjectQuestions"
        )
    ]
    apply_source = application[
        application.index("function applyRequestedProjectSample") : application.index(
            'if (pageIs("project") && intakeFormElement)'
        )
    ]
    golden = json.loads(
        (ROOT / "data" / "golden" / "example.json").read_text(encoding="utf-8")
    )
    registry = json.loads(
        (ROOT / "data" / "jurisdictions" / "registry.json").read_text(encoding="utf-8")
    )["jurisdictions"]
    script = f"""
function nonBlank(value) {{
  return typeof value === "string" && value.trim().length > 0;
}}
{helper_source}
const golden = {json.dumps(golden)};
const jurisdictions = {json.dumps(registry)};
const prepared = prepareProjectSample(
  new URLSearchParams("sample=adu"),
  golden,
  jurisdictions
);
if (!prepared) throw new Error("canonical sample rejected");
if (prepared.caseId !== "woodland-new-detached-adu-local-layer")
  throw new Error("wrong fixture selected");
if (prepared.intake.jurisdiction !== "woodland")
  throw new Error("wrong jurisdiction selected");
prepared.intake.project_type = "changed";
const canonical = golden.find(item => item.case_id === prepared.caseId);
if (canonical.intake.project_type !== "adu")
  throw new Error("sample mutated canonical fixture");
if (prepareProjectSample(
  new URLSearchParams("sample=adu&sample=adu"), golden, jurisdictions
)) throw new Error("duplicate sample parameter accepted");
if (prepareProjectSample(
  new URLSearchParams("sample=missing"), golden, jurisdictions
)) throw new Error("unknown sample accepted");
const incomplete = structuredClone(golden);
incomplete.find(item =>
  item.case_id === "woodland-new-detached-adu-local-layer"
).intake.adu_project_form = "unknown";
if (prepareProjectSample(
  new URLSearchParams("sample=adu"), incomplete, jurisdictions
)) throw new Error("incomplete sample accepted");
"""
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "intakeFormElement.requestSubmit()" in apply_source
    assert "screen(" not in apply_source
    assert "renderResults(" not in apply_source
    assert "function deactivateProjectSample()" in application
    assert "function removeProjectSampleFromUrl()" in application
    assert 'updatedUrl.searchParams.delete("sample")' in application
    assert "function invalidateRenderedProjectResult(" in application
    assert 'if (results) results.innerHTML = ""' in application
    assert 'projectSampleState = "unavailable"' in application


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_static_sample_renders_a_grouped_result_packet_with_visible_sources():
    application_path = ROOT / "assets" / "demo.js"
    rule_paths = sorted(
        path
        for path in (ROOT / "data" / "rules").glob("*.json")
        if path.name != "index.json"
    )
    script = f"""
import fs from "node:fs";
import vm from "node:vm";

const application = fs.readFileSync(
  {json.dumps(str(application_path))},
  "utf8"
);
const testRules = {json.dumps([str(path) for path in rule_paths])}
  .flatMap(path => JSON.parse(fs.readFileSync(path, "utf8")));
const testExplanations = JSON.parse(fs.readFileSync(
  {json.dumps(str(ROOT / "data" / "explanations" / "plain-language.json"))},
  "utf8"
));
const testGolden = JSON.parse(fs.readFileSync(
  {json.dumps(str(ROOT / "data" / "golden" / "example.json"))},
  "utf8"
));
const testJurisdictions = JSON.parse(fs.readFileSync(
  {json.dumps(str(ROOT / "data" / "jurisdictions" / "registry.json"))},
  "utf8"
)).jurisdictions;
const context = {{
  console,
  URL,
  URLSearchParams,
  TEST_RULES: testRules,
  TEST_EXPLANATIONS: testExplanations,
  TEST_GOLDEN: testGolden,
  TEST_JURISDICTIONS: testJurisdictions,
  document: {{
    body: {{dataset: {{}}}},
    createElement: () => {{
      let value = "";
      return {{
        set textContent(next) {{ value = String(next ?? ""); }},
        get innerHTML() {{
          return value
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;");
        }},
      }};
    }},
    getElementById: () => null,
  }},
}};
const assertions = `
function testAssert(condition, message) {{
  if (!condition) throw new Error(message);
}}
RULES = normalizeRules(TEST_RULES);
EXPLANATIONS = new Map(
  TEST_EXPLANATIONS.entries.map(record => [record.source_rule_id, record])
);
const testSample = TEST_GOLDEN.find(
  item => item.case_id === "woodland-new-detached-adu-local-layer"
);
const testJurisdiction = TEST_JURISDICTIONS.find(
  item => item.slug === testSample.intake.jurisdiction
);
lang = "en";
projectSampleState = "active";
const testMatches = screen(testSample.intake);
storeSubmittedProject(testSample.intake, testJurisdiction, testMatches);
const testGrouped = groupResultRecords(testMatches);
testAssert(testGrouped.get("route").length === 1, "wrong route count");
testAssert(testGrouped.get("standard").length === 5, "wrong standard count");
testAssert(
  testGrouped.get("local_process").length === 1,
  "wrong local information count"
);
testAssert(testGrouped.get("other").length === 0, "unexpected other group");
testAssert(
  resultSummaryText(testGrouped) ===
    "Based on these answers, this prototype shows 1 possible permit path, " +
    "5 other rules that may apply, and 1 local information record.",
  "wrong grouped result summary"
);

const testFacts = renderProjectFacts();
testAssert(
  (testFacts.match(/data-field=/g) || []).length === 5,
  "cover sheet does not show five submitted facts"
);
for (const field of [
  "jurisdiction",
  "project_type",
  "primary_dwelling_status",
  "adu_project_form",
  "unpermitted_existing",
]) testAssert(
  testFacts.includes('data-field="' + field + '"'),
  "missing cover-sheet field " + field
);
testAssert(
  testFacts.includes("Build a new detached ADU"),
  "cover sheet does not use the human ADU label"
);
testAssert(
  !testFacts.includes(">new_detached<"),
  "cover sheet exposes a raw intake value"
);

const testIndex = renderResultIndex(testGrouped);
for (const group of ["route", "standard", "local_process"])
  testAssert(
    testIndex.includes('href="#result-group-' + group + '"'),
    "missing result index link " + group
  );
testAssert(
  !testIndex.includes('href="#result-group-other"'),
  "empty result group was included"
);

const testCards = testMatches.map(rule =>
  renderResultCard(rule, EXPLANATIONS.get(rule.rule_id), {{
    suppressPendingReview: true,
  }})
);
testAssert(
  new Set(testCards.map(card =>
    card.match(/<article id="([^"]+)"/)[1]
  )).size === testCards.length,
  "rule anchors are not unique"
);
let testOpenCount = 0;
testCards.forEach(card => {{
  const detailsTag = card.match(/<details class="rule-details"[^>]*>/)[0];
  if (detailsTag.includes(" open")) testOpenCount += 1;
  const detailsCount = (card.match(/<details /g) || []).length;
  testAssert(
    detailsCount === 1,
    "a result contains " + detailsCount + " disclosures"
  );
  testAssert(
    card.indexOf('class="source-basis"') < card.indexOf(detailsTag),
    "citation is hidden inside the disclosure"
  );
  testAssert(
    card.indexOf('class="badge') < card.indexOf(detailsTag),
    "source status is hidden inside the disclosure"
  );
}});
testAssert(testOpenCount === 1, "exactly one route should start open");
testAssert(
  OPEN_RULE_IDS.has("adu-ministerial-review"),
  "the configured ADU route did not start open"
);
const testAduRouteCard = testCards.find(card =>
  card.includes('data-rule-id="adu-ministerial-review"')
);
testAssert(
  testAduRouteCard.includes('href="#clocks"'),
  "the ADU route did not link to the ADU date tool"
);

const testSecondaryRoute = RULES.find(
  rule => rule.rule_id === "adu-unpermitted-legalization"
);
const testSecondaryRouteCard = renderResultCard(
  testSecondaryRoute,
  EXPLANATIONS.get(testSecondaryRoute.rule_id)
);
testAssert(
  testSecondaryRouteCard.includes("result-card-compact")
    && !testSecondaryRouteCard.includes("result-route"),
  "an additional matching route was not compact"
);

for (const [projectType, ruleId] of [
  ["jadu", "jadu-ministerial-review"],
  ["two_unit", "sb9-two-unit-ministerial"],
  ["lot_split", "sb9-urban-lot-split"],
]) {{
  LAST_INTAKE = {{project_type: projectType}};
  const routeRule = RULES.find(rule => rule.rule_id === ruleId);
  const routeCard = renderResultCard(
    routeRule,
    EXPLANATIONS.get(routeRule.rule_id)
  );
  testAssert(
    !routeCard.includes('href="#clocks"'),
    projectType + " route incorrectly linked to the ADU date tool"
  );
}}

LAST_INTAKE = {{...testSample.intake}};
simulating = true;
const testStaleRule = RULES.find(
  rule => rule.rule_id === "adu-multifamily-66323"
);
const testStaleCard = renderResultCard(
  testStaleRule,
  EXPLANATIONS.get(testStaleRule.rule_id)
);
testAssert(
  testStaleCard.includes(STRINGS.en.stale)
    && testStaleCard.includes(STRINGS.en.withheldStale),
  "stale result did not show its source warning"
);
testAssert(
  testStaleCard.includes('class="source-basis"')
    && !testStaleCard.includes('class="plain-layer"')
    && !testStaleCard.includes(STRINGS.en.docs)
    && !testStaleCard.includes("result-tool-link"),
  "stale result exposed action-oriented explanation content"
);

simulating = false;
const testCurrentRoute = RULES.find(
  rule => rule.rule_id === "adu-ministerial-review"
);
const testUnverifiedRoute = {{
  ...testCurrentRoute,
  citation: {{...testCurrentRoute.citation, verified_on: ""}},
}};
const testUnverifiedCard = renderResultCard(
  testUnverifiedRoute,
  EXPLANATIONS.get(testUnverifiedRoute.rule_id)
);
testAssert(
  testUnverifiedCard.includes(STRINGS.en.unverified)
    && testUnverifiedCard.includes(STRINGS.en.withheldUnverified),
  "unverified result did not show its source warning"
);
testAssert(
  testUnverifiedCard.includes('class="source-basis"')
    && !testUnverifiedCard.includes('class="plain-layer"')
    && !testUnverifiedCard.includes(STRINGS.en.docs)
    && !testUnverifiedCard.includes("result-tool-link"),
  "unverified result exposed action-oriented explanation content"
);

const englishAnchors = testCards.map(card =>
  card.match(/<article id="([^"]+)"/)[1]
);
lang = "es";
const spanishFacts = renderProjectFacts();
const spanishSummary = resultSummaryText(testGrouped);
const spanishCards = testMatches.map(rule =>
  renderResultCard(rule, EXPLANATIONS.get(rule.rule_id), {{
    suppressPendingReview: true,
  }})
);
const spanishAnchors = spanishCards.map(card =>
  card.match(/<article id="([^"]+)"/)[1]
);
testAssert(
  spanishFacts.includes("Construir una ADU nueva y separada"),
  "Spanish cover sheet did not translate the submitted value"
);
testAssert(
  spanishSummary.includes("1 posible vía de permiso") &&
    spanishSummary.includes("5 reglas adicionales"),
  "Spanish grouped count is missing"
);
testAssert(
  JSON.stringify(spanishAnchors) === JSON.stringify(englishAnchors),
  "localized rule anchors changed"
);

lang = "en";
const resultNode = {{innerHTML: "old result"}};
const statusNode = {{textContent: "old status"}};
document.getElementById = id => ({{
  results: resultNode,
  resultStatus: statusNode,
}}[id] || null);
projectSampleState = null;
deactivateProjectSample();
testAssert(resultNode.innerHTML === "", "ordinary edit kept an old result");
testAssert(
  statusNode.textContent === STRINGS.en.resultCleared,
  "ordinary edit did not announce that the old result was cleared"
);
testAssert(LAST_INTAKE === null, "ordinary edit kept submitted facts");
testAssert(OPEN_RULE_IDS.size === 0, "ordinary edit kept disclosure state");
`;
vm.runInNewContext(application + "\\n" + assertions, context);
"""
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_static_explanation_normalizer_accepts_canonical_data_and_fails_closed():
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    validation_source = application[
        application.index("function isJsonNumber") : application.index(
            "function renderForm"
        )
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
        application.index("function isJsonNumber") : application.index("function esc")
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
    assert static_path("/prepare.html") == ROOT / "prepare.html"
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
    handler.send_header = lambda name, value: handler.response_headers.__setitem__(
        name, value
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
