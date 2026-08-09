import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _source_between(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_versioned_journey_browser_contract_fails_closed():
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    matching_source = _source_between(
        application,
        "function isJsonNumber",
        "function uiText",
    )
    validation_source = _source_between(
        application,
        "function nonBlank",
        "function validTextList",
    )
    journey_source = _source_between(
        application,
        "function stableJson",
        "async function normalizeExplanations",
    )
    readiness_source = _source_between(
        application,
        "const READINESS_FINDING_STATUSES",
        "function readinessParcelEvidenceMarkup",
    )
    readiness_current_source = _source_between(
        application,
        "function readinessSourceIsCurrent",
        "function readinessCount",
    )

    assertions = r"""
const bundleSource = readFileSync("data/demo-data.js", "utf8");
const assignment = "globalThis.PERMIT_PATHWAYS_DEMO_DATA=";
const assignmentIndex = bundleSource.indexOf(assignment);
if (assignmentIndex < 0) throw new Error("generated bundle assignment missing");
const bundle = JSON.parse(
  bundleSource.slice(assignmentIndex + assignment.length).trim().replace(/;$/, "")
);
const canonicalJourneys = bundle.journeys;
const canonicalReadiness = bundle.readiness;
const canonicalRules = bundle.rules;
const canonicalGolden = bundle.golden;
const canonicalProgramAvailability = bundle.program_availability;
SOURCE_STATE = bundle.source_state;

const NativeDate = Date;
let fixedNow = "2026-08-09T12:00:00Z";
class FixedDate extends NativeDate {
  constructor(...args) {
    super(...(args.length ? args : [fixedNow]));
  }
  static now() {
    return NativeDate.parse(fixedNow);
  }
  static parse(value) {
    return NativeDate.parse(value);
  }
  static UTC(...args) {
    return NativeDate.UTC(...args);
  }
}
globalThis.Date = FixedDate;

function check(condition, message) {
  if (!condition) throw new Error(message);
}

function noHref(state, label) {
  check(!Object.prototype.hasOwnProperty.call(state, "href"), `${label}: href leaked`);
}

async function normalizeAvailability(candidate = canonicalProgramAvailability) {
  return normalizeProgramAvailability(structuredClone(candidate));
}

PROGRAM_AVAILABILITY = await normalizeAvailability();
check(PROGRAM_AVAILABILITY !== null, "canonical program status rejected");
check(
  programAvailabilityIsCurrent(PROGRAM_AVAILABILITY),
  "canonical program status was not current",
);

async function expectAvailabilityRejection(label, mutate) {
  const candidate = structuredClone(canonicalProgramAvailability);
  await mutate(candidate);
  check(
    await normalizeProgramAvailability(candidate) === null,
    `${label}: program mutation accepted`,
  );
}

await expectAvailabilityRejection("unknown program field", candidate => {
  candidate.availability.unexpected = true;
});
await expectAvailabilityRejection("program excerpt fingerprint drift", candidate => {
  candidate.availability.source.excerpt_sha256 = `sha256:${"0".repeat(64)}`;
});
await expectAvailabilityRejection(
  "self-consistent semantic excerpt drift",
  async candidate => {
    candidate.availability.source.excerpt = "Preapproved ADU List: Available now!";
    candidate.availability.source.excerpt_sha256 = await sha256TextFingerprint(
      normalizeProgramExcerpt(candidate.availability.source.excerpt),
    );
  },
);
await expectAvailabilityRejection("overlong recheck window", candidate => {
  candidate.availability.source.recheck_due_on = "2026-10-09";
});

async function expectJourneyRejection(label, mutate) {
  const journeys = structuredClone(canonicalJourneys);
  const readiness = structuredClone(canonicalReadiness);
  const rules = structuredClone(canonicalRules);
  const golden = structuredClone(canonicalGolden);
  mutate({journeys, readiness, rules, golden});
  const normalized = await normalizeJourney(journeys, readiness, rules, golden);
  check(normalized === null, `${label}: mutation accepted`);
}

const canonicalJourney = await normalizeJourney(
  canonicalJourneys,
  canonicalReadiness,
  canonicalRules,
  canonicalGolden,
);
check(canonicalJourney !== null, "canonical generated journey rejected");
check(
  canonicalJourney.journey_id === "woodland-preapproved-detached-adu-synthetic",
  "unexpected canonical journey resolved",
);
check(
  generatedDataIsDeeplyFrozen(canonicalJourney),
  "normalized journey tree was not recursively frozen",
);
const originalRoutePathway = canonicalJourney.candidate_routes[0].pathway;
try {
  canonicalJourney.candidate_routes[0].pathway += " drift";
} catch {
  // ES modules throw on writes to frozen objects; classic scripts ignore the write.
}
check(
  canonicalJourney.candidate_routes[0].pathway === originalRoutePathway,
  "same-object mutation bypassed normalized journey integrity",
);

const malformedCases = [
  ["null screening intake", ({journeys}) => {
    journeys[0].screening_intake = null;
  }],
  ["array screening intake", ({journeys}) => {
    journeys[0].screening_intake = [];
  }],
  ["null candidate route", ({journeys}) => {
    journeys[0].candidate_routes = [null];
  }],
  ["array candidate route", ({journeys}) => {
    journeys[0].candidate_routes = [[]];
  }],
  ["null applicability fact", ({journeys}) => {
    journeys[0].applicability_facts = [null];
  }],
  ["null fact envelope", ({journeys}) => {
    journeys[0].fact_envelope = null;
  }],
  ["malformed readiness facts", ({readiness}) => {
    readiness.workflow.facts = null;
  }],
  ["malformed route dependencies", ({journeys}) => {
    journeys[0].candidate_routes[0].source_dependencies = null;
  }],
];
for (const [label, mutate] of malformedCases) {
  await expectJourneyRejection(label, mutate);
}

const contractMutations = [
  ["unknown journey field", ({journeys}) => {
    journeys[0].unexpected = true;
  }],
  ["journey schema", ({journeys}) => {
    journeys[0].schema_version = 2;
  }],
  ["journey version", ({journeys}) => {
    journeys[0].version = "1";
  }],
  ["journey status", ({journeys}) => {
    journeys[0].status = "published";
  }],
  ["journey synthetic boundary", ({journeys}) => {
    journeys[0].synthetic = false;
  }],
  ["journey workflow id", ({journeys}) => {
    journeys[0].readiness_workflow_id = "different-workflow";
  }],
  ["journey packet id", ({journeys}) => {
    journeys[0].readiness_packet_id = "different-packet";
  }],
  ["journey workflow fingerprint", ({journeys}) => {
    journeys[0].readiness_workflow_fingerprint = `sha256:${"0".repeat(64)}`;
  }],
  ["journey packet fingerprint", ({journeys}) => {
    journeys[0].readiness_packet_fingerprint = `sha256:${"0".repeat(64)}`;
  }],
  ["journey evidence manifest", ({journeys}) => {
    journeys[0].readiness_evidence_manifest.boundary += " drift";
  }],
  ["journey fingerprint", ({journeys}) => {
    journeys[0].journey_fingerprint = `sha256:${"0".repeat(64)}`;
  }],
  ["screening case fingerprint", ({journeys}) => {
    journeys[0].screening_case_fingerprint = `sha256:${"0".repeat(64)}`;
  }],
  ["fact envelope", ({journeys}) => {
    journeys[0].fact_envelope.screening_facts[0].value = "changed";
  }],
  ["fact envelope fingerprint", ({journeys}) => {
    journeys[0].fact_envelope_fingerprint = `sha256:${"0".repeat(64)}`;
  }],
  ["applicability provenance", ({journeys}) => {
    journeys[0].applicability_facts[0].provenance = "applicant_assertion";
  }],
  ["route source status", ({journeys}) => {
    journeys[0].route_source_status = "source_review_required";
  }],
  ["candidate route source status", ({journeys}) => {
    journeys[0].candidate_routes[0].source_status = "source_review_required";
  }],
  ["candidate route fingerprint", ({journeys}) => {
    journeys[0].candidate_routes[0].rule_fingerprint =
      `sha256:${"0".repeat(64)}`;
  }],
  ["candidate route ids omitted", ({journeys}) => {
    journeys[0].candidate_route_rule_ids = [];
  }],
  ["candidate routes omitted", ({journeys}) => {
    journeys[0].candidate_routes = [];
  }],
  ["candidate route rule omitted", ({rules, journeys}) => {
    const routeId = journeys[0].candidate_route_rule_ids[0];
    const index = rules.findIndex(rule => rule.rule_id === routeId);
    rules.splice(index, 1);
  }],
  ["canonical rule drift", ({rules, journeys}) => {
    const routeId = journeys[0].candidate_route_rule_ids[0];
    rules.find(rule => rule.rule_id === routeId).notes += " changed";
  }],
  ["canonical rule criteria drift", ({rules, journeys}) => {
    const routeId = journeys[0].candidate_route_rule_ids[0];
    rules.find(rule => rule.rule_id === routeId).criteria[0].value = "jadu";
  }],
  ["golden case intake drift", ({golden, journeys}) => {
    golden.find(record => record.case_id === journeys[0].screening_case_id)
      .intake.project_type = "jadu";
  }],
  ["golden case expected ids drift", ({golden, journeys}) => {
    golden.find(record => record.case_id === journeys[0].screening_case_id)
      .expected_rule_ids.pop();
  }],
  ["readiness workflow id", ({readiness}) => {
    readiness.workflow.workflow_id = "different-workflow";
  }],
  ["readiness workflow fingerprint", ({readiness}) => {
    readiness.result.workflow_fingerprint = `sha256:${"0".repeat(64)}`;
  }],
  ["readiness packet fingerprint", ({readiness}) => {
    readiness.result.packet_fingerprint = `sha256:${"0".repeat(64)}`;
  }],
  ["workflow payload drift under retained fingerprint", ({readiness}) => {
    readiness.workflow.scope += " drift";
  }],
  ["packet payload drift under retained fingerprint", ({readiness}) => {
    readiness.packet.label += " drift";
  }],
  ["packet inventory drift under retained fingerprint", ({readiness}) => {
    readiness.packet.inventory[0].status = "missing";
  }],
  ["result drift under retained manifest", ({readiness}) => {
    readiness.result.findings[0].reason += " drift";
  }],
  ["result and manifest drift under retained journey", ({readiness}) => {
    readiness.result.findings[0].reason += " drift";
    readiness.evidence_manifest.findings[0].reason += " drift";
  }],
  ["finding requirement fingerprint drift", ({readiness}) => {
    readiness.result.findings[0].requirement_fingerprint =
      `sha256:${"0".repeat(64)}`;
  }],
  ["remedy requirement fingerprint drift", ({readiness}) => {
    readiness.remedies.entries[0].requirement_fingerprint =
      `sha256:${"0".repeat(64)}`;
  }],
  ["remedy action drift under retained content fingerprint", ({readiness}) => {
    readiness.remedies.entries[0].action += " drift";
  }],
  ["remedy content fingerprint drift", ({readiness}) => {
    readiness.remedies.content_fingerprint = `sha256:${"0".repeat(64)}`;
  }],
  ["remedy trace fingerprint drift", ({readiness}) => {
    readiness.ai_trace.output_remedy_content_fingerprint =
      `sha256:${"0".repeat(64)}`;
  }],
  ["workflow trace fingerprint drift", ({readiness}) => {
    readiness.ai_trace.output_workflow_fingerprint =
      `sha256:${"0".repeat(64)}`;
  }],
  ["remedy trace version drift", ({readiness}) => {
    readiness.ai_trace.output_remedy_version = "9.9.9";
  }],
  ["remedy update after evaluation", ({readiness}) => {
    readiness.remedies.updated_on = "2026-07-31";
  }],
  ["review before remedy update", ({readiness}) => {
    readiness.remedies.review = {
      status: "human_reviewed",
      reviewer: "Named test reviewer",
      method: "Compared every action with its bound requirement.",
      reviewed_on: "2026-07-28",
      reviewed_version: readiness.remedies.version,
      content_fingerprint: readiness.remedies.content_fingerprint,
    };
  }],
  ["review after evaluation", ({readiness}) => {
    readiness.remedies.review = {
      status: "human_reviewed",
      reviewer: "Named test reviewer",
      method: "Compared every action with its bound requirement.",
      reviewed_on: "2026-07-31",
      reviewed_version: readiness.remedies.version,
      content_fingerprint: readiness.remedies.content_fingerprint,
    };
  }],
  ["completed review fingerprint mismatch", ({readiness}) => {
    readiness.remedies.review = {
      status: "human_reviewed",
      reviewer: "Named test reviewer",
      method: "Compared every action with its bound requirement.",
      reviewed_on: "2026-07-30",
      reviewed_version: readiness.remedies.version,
      content_fingerprint: `sha256:${"0".repeat(64)}`,
    };
  }],
  ["readiness evidence", ({readiness}) => {
    readiness.evidence_manifest.boundary += " drift";
  }],
  ["readiness source status", ({readiness}) => {
    readiness.result.source_status = "source_review_required";
  }],
  ["readiness applicability status", ({readiness}) => {
    readiness.result.applicability_status = "unknown";
  }],
];
for (const [label, mutate] of contractMutations) {
  await expectJourneyRejection(label, mutate);
}

const postValidationMutationTarget = structuredClone(canonicalReadiness);
const postValidationNormalized = await normalizeReadinessData(
  postValidationMutationTarget
);
check(postValidationNormalized !== null, "post-validation fixture was rejected");
check(
  generatedDataIsDeeplyFrozen(postValidationNormalized),
  "normalized readiness tree was not recursively frozen",
);
const originalAction = postValidationNormalized.remedies.entries[0].action;
try {
  postValidationNormalized.remedies.entries[0].action += " drift";
} catch {
  // ES modules throw on writes to frozen objects; classic scripts ignore the write.
}
check(
  postValidationNormalized.remedies.entries[0].action === originalAction,
  "same-object mutation bypassed normalized readiness integrity",
);
check(
  await normalizeReadinessData(postValidationNormalized)
    === postValidationNormalized,
  "recursively frozen normalized readiness did not remain reusable",
);

const realCrypto = globalThis.crypto;
Object.defineProperty(globalThis, "crypto", {
  value: {subtle: {digest: async () => { throw new Error("digest rejected"); }}},
  configurable: true,
});
const digestRejected = await normalizeJourney(
  canonicalJourneys,
  canonicalReadiness,
  canonicalRules,
  canonicalGolden,
);
check(digestRejected === null, "rejected WebCrypto digest escaped fail-closed gate");
Object.defineProperty(globalThis, "crypto", {
  value: realCrypto,
  configurable: true,
});

const expectedResults = canonicalRules.filter(rule =>
  canonicalJourney.screening_expected_rule_ids.includes(rule.rule_id)
);
function handoff(
  applicabilityValue,
  sampleState = "active",
  intake = canonicalJourney.screening_intake,
  results = expectedResults,
  readiness = canonicalReadiness,
  rules = canonicalRules,
) {
  return journeyHandoffState(
    canonicalJourney,
    readiness,
    intake,
    results,
    applicabilityValue,
    sampleState,
    rules,
  );
}

for (const [label, value] of [["initial", null], ["unknown", "unknown"]]) {
  const state = handoff(value);
  check(state.status === "unknown", `${label}: wrong handoff state`);
  check(
    state.question === canonicalJourney.applicability_facts[0].question,
    `${label}: exact staff question missing`,
  );
  noHref(state, label);
}
const blank = handoff("");
check(blank.status === "unknown", "blank applicability did not stay unknown");
noHref(blank, "blank applicability");

const ready = handoff("yes");
check(
  ready.status === "simulation_ready",
  "canonical yes did not unlock future-state simulation",
);
check(
  ready.href ===
    "prepare.html?journey=woodland-preapproved-detached-adu-synthetic&version=1.0.0",
  "ready handoff did not emit exact versioned two-parameter href",
);
const readyParams = new URLSearchParams(ready.href.split("?", 2)[1]);
check([...readyParams.keys()].length === 2, "ready href exposed extra parameters");
check(readyParams.getAll("journey").length === 1, "journey parameter duplicated");
check(readyParams.getAll("version").length === 1, "version parameter duplicated");

const canonicalAvailability = PROGRAM_AVAILABILITY;
PROGRAM_AVAILABILITY = null;
const missingProgram = handoff("yes");
check(
  missingProgram.status === "program_status_review_required",
  "missing program status unlocked handoff",
);
noHref(missingProgram, "missing program status");
PROGRAM_AVAILABILITY = canonicalAvailability;

fixedNow = "2026-09-09T12:00:00Z";
const expiredProgram = handoff("yes");
check(
  expiredProgram.status === "program_status_review_required",
  "expired program status unlocked handoff",
);
noHref(expiredProgram, "expired program status");
fixedNow = "2026-08-09T12:00:00Z";

SOURCE_STATE = {...bundle.source_state, changed_source_ids: ["ca-gov-66317"]};
const committedRouteChange = handoff("yes");
check(
  committedRouteChange.status === "source_review_required",
  "committed changed route source unlocked handoff",
);
noHref(committedRouteChange, "committed route change");
SOURCE_STATE = bundle.source_state;

const doesNotApply = handoff("no");
check(doesNotApply.status === "does_not_apply", "no did not hold the packet");
noHref(doesNotApply, "does not apply");
const arbitrary = handoff("sometimes");
check(arbitrary.status === "unavailable", "arbitrary applicability accepted");
noHref(arbitrary, "arbitrary applicability");

for (const sampleState of ["edited", "manual"]) {
  const state = handoff("yes", sampleState);
  check(state.status === "sample_required", `${sampleState}: wrong sample hold`);
  noHref(state, `${sampleState} sample`);
}
const changedIntake = structuredClone(canonicalJourney.screening_intake);
changedIntake.project_type = "jadu";
const intakeMismatch = handoff("yes", "active", changedIntake);
check(intakeMismatch.status === "intake_mismatch", "intake drift accepted");
noHref(intakeMismatch, "intake mismatch");

const missingResult = expectedResults.slice(1);
const resultMismatch = handoff("yes", "active", canonicalJourney.screening_intake,
  missingResult);
check(resultMismatch.status === "route_mismatch", "result omission accepted");
noHref(resultMismatch, "result mismatch");
const disguisedRoute = structuredClone(expectedResults);
disguisedRoute.find(
  rule => rule.rule_id === canonicalJourney.candidate_route_rule_ids[0]
).display_group = "standard";
const routeMismatch = handoff("yes", "active", canonicalJourney.screening_intake,
  disguisedRoute);
check(routeMismatch.status === "route_mismatch", "non-route result unlocked packet");
noHref(routeMismatch, "route classification mismatch");

const staleReadiness = structuredClone(canonicalReadiness);
staleReadiness.source_review_due_on = "2026-08-01";
staleReadiness.result.source_review_due_on = "2026-08-01";
staleReadiness.evidence_manifest.source_review_due_on = "2026-08-01";
const sourceMismatch = handoff(
  "yes",
  "active",
  canonicalJourney.screening_intake,
  expectedResults,
  staleReadiness,
);
check(
  sourceMismatch.status === "source_review_required",
  "stale readiness evidence unlocked handoff",
);
noHref(sourceMismatch, "source mismatch");

function query(value, journey = canonicalJourney, readiness = canonicalReadiness) {
  return journeyQueryState(
    new URLSearchParams(value),
    journey,
    readiness,
    canonicalRules,
  );
}
check(query("").status === "start_required", "direct entry did not require start");
const invalidQueries = [
  ["missing version", `journey=${canonicalJourney.journey_id}`],
  ["missing journey", `version=${canonicalJourney.version}`],
  ["empty journey", `journey=&version=${canonicalJourney.version}`],
  ["empty version", `journey=${canonicalJourney.journey_id}&version=`],
  ["duplicate journey",
    `journey=${canonicalJourney.journey_id}&journey=${canonicalJourney.journey_id}`
      + `&version=${canonicalJourney.version}`],
  ["duplicate version",
    `journey=${canonicalJourney.journey_id}&version=${canonicalJourney.version}`
      + `&version=${canonicalJourney.version}`],
  ["extra parameter",
    `journey=${canonicalJourney.journey_id}&version=${canonicalJourney.version}`
      + "&sample=adu"],
  ["wrong journey", `journey=wrong&version=${canonicalJourney.version}`],
  ["wrong version", `journey=${canonicalJourney.journey_id}&version=9.9.9`],
];
for (const [label, value] of invalidQueries) {
  check(query(value).status === "invalid", `${label}: query accepted`);
}
const canonicalQuery =
  `journey=${canonicalJourney.journey_id}&version=${canonicalJourney.version}`;
check(
  query(canonicalQuery).status === "simulation_ready",
  "canonical future-state query rejected",
);
PROGRAM_AVAILABILITY = null;
check(
  query(canonicalQuery).status === "program_status_review_required",
  "missing program status unlocked direct packet query",
);
PROGRAM_AVAILABILITY = canonicalAvailability;
check(
  query(canonicalQuery, null, canonicalReadiness).status === "invalid",
  "missing normalized journey accepted",
);
check(
  query(canonicalQuery, canonicalJourney, null).status === "invalid",
  "missing readiness accepted",
);
check(
  query(canonicalQuery, canonicalJourney, staleReadiness).status
    === "source_review_required",
  "stale source query did not hold packet",
);

fixedNow = `${canonicalJourney.route_source_review_due_on}T12:00:00Z`;
check(
  journeySourcesAreCurrent(
    canonicalJourney,
    canonicalReadiness,
    canonicalRules,
  ),
  "route source rejected on its review deadline",
);
check(
  !journeySourcesAreCurrent(
    canonicalJourney,
    canonicalReadiness,
    canonicalRules,
    ["ca-gov-66317"],
  ),
  "changed route dependency left journey current",
);
check(
  journeySourcesAreCurrent(
    canonicalJourney,
    canonicalReadiness,
    canonicalRules,
    ["ca-gov-66411-7"],
  ),
  "unrelated statewide source disabled Woodland journey",
);
check(
  !readinessSourceIsCurrent(
    canonicalReadiness,
    ["woodland-preapproved-adu-checklist"],
  ),
  "changed Woodland checklist left packet current",
);
check(
  !readinessSourceIsCurrent(
    canonicalReadiness,
    ["yolo-public-parcels-layer"],
  ),
  "changed parcel source left packet current",
);
check(
  readinessSourceIsCurrent(canonicalReadiness, ["ca-gov-66411-7"]),
  "unrelated statewide source disabled Woodland packet",
);
fixedNow = "2027-01-24T12:00:00Z";
check(
  !journeySourcesAreCurrent(
    canonicalJourney,
    canonicalReadiness,
    canonicalRules,
  ),
  "route source remained current after its review deadline",
);
fixedNow = `${canonicalReadiness.source_review_due_on}T12:00:00Z`;
check(
  readinessSourceIsCurrent(canonicalReadiness),
  "readiness source rejected on its review deadline",
);
fixedNow = "2027-01-26T12:00:00Z";
check(
  !readinessSourceIsCurrent(canonicalReadiness),
  "readiness source remained current after its review deadline",
);
globalThis.Date = NativeDate;
"""
    script = "\n".join(
        [
            'import {readFileSync} from "node:fs";',
            'import {webcrypto} from "node:crypto";',
            'Object.defineProperty(globalThis, "crypto", {',
            "  value: webcrypto, configurable: true,",
            "});",
            "let RULES = [];",
            "let SOURCE_STATE = null;",
            "let PROGRAM_AVAILABILITY = null;",
            "let JOURNEY = null;",
            "let simulating = false;",
            "const NORMALIZED_READINESS_DATA = new WeakSet();",
            "const NORMALIZED_PROGRAM_AVAILABILITY = new WeakSet();",
            matching_source,
            validation_source,
            journey_source,
            readiness_source,
            readiness_current_source,
            assertions,
        ]
    )

    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
