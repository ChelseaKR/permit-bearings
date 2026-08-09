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
def test_reviewed_source_state_browser_contract_fails_closed_and_is_exact():
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    source_state = _source_between(
        application,
        "const SOURCE_STATE_KEYS",
        "function expectedJourneyFactEnvelope",
    )
    exact_keys = _source_between(
        application,
        "function hasExactKeys",
        "function sameScalar",
    )
    browser_validation = _source_between(
        application,
        "function safeExternalUrl",
        "function validTextList",
    )
    stable_json = _source_between(
        application,
        "function stableJson",
        "async function sha256Fingerprint",
    )
    program_availability = _source_between(
        application,
        "const PROGRAM_AVAILABILITY_URL",
        "const RULE_VERIFICATION_TOP_LEVEL_KEYS",
    )
    freeze_helpers = _source_between(
        application,
        "function deepFreezeGeneratedData",
        "function readinessParcelEvidenceMarkup",
    )
    same_string_set = _source_between(
        application,
        "function sameStringSet",
        "const SOURCE_STATE_KEYS",
    )
    rule_state = _source_between(
        application,
        "function ruleStatus",
        "function uiText",
    )
    journey_current = _source_between(
        application,
        "function journeySourcesAreCurrent",
        "function journeyHandoffState",
    )
    journey_gate = _source_between(
        application,
        "function journeyHandoffState",
        "function journeyEntryHoldMarkup",
    )
    readiness_due = _source_between(
        application,
        "function readinessReviewDueOn",
        "function readinessSourceStatusAsOf",
    )
    readiness_current = _source_between(
        application,
        "function readinessSourceIsCurrent",
        "function readinessCount",
    )
    assert ".localeCompare(" not in source_state
    script = "\n".join(
        [
            'import {readFileSync} from "node:fs";',
            "let RULES = [];",
            "let SOURCE_STATE = null;",
            "let PROGRAM_AVAILABILITY = null;",
            "let simulating = false;",
            "const NORMALIZED_PROGRAM_AVAILABILITY = new WeakSet();",
            "function check(condition, message) {",
            "  if (!condition) throw new Error(message);",
            "}",
            "const MAX_AGE_DAYS = 180;",
            exact_keys,
            browser_validation,
            stable_json,
            program_availability,
            freeze_helpers,
            rule_state,
            same_string_set,
            source_state,
            readiness_due,
            journey_current,
            journey_gate,
            readiness_current,
            r"""
const bundleSource = readFileSync("data/demo-data.js", "utf8");
const assignment = "globalThis.PERMIT_PATHWAYS_DEMO_DATA=";
const assignmentIndex = bundleSource.indexOf(assignment);
if (assignmentIndex < 0) throw new Error("generated bundle assignment missing");
const bundle = JSON.parse(
  bundleSource.slice(assignmentIndex + assignment.length).trim().replace(/;$/, "")
);
const NativeDate = Date;
class FixedDate extends NativeDate {
  constructor(...args) {
    super(...(args.length ? args : ["2026-08-09T12:00:00Z"]));
  }
  static now() { return NativeDate.parse("2026-08-09T12:00:00Z"); }
  static parse(value) { return NativeDate.parse(value); }
  static UTC(...args) { return NativeDate.UTC(...args); }
}
globalThis.Date = FixedDate;
PROGRAM_AVAILABILITY = bundle.program_availability.availability;
NORMALIZED_PROGRAM_AVAILABILITY.add(PROGRAM_AVAILABILITY);

function normalize(candidate) {
  return normalizeSourceState(
    candidate,
    bundle.sources,
    bundle.rules,
    bundle.golden,
    bundle._meta.generated_from,
  );
}

function reject(label, mutate) {
  const candidate = structuredClone(bundle.source_state);
  mutate(candidate);
  check(normalize(candidate) === null, `${label}: mutation accepted`);
}

const canonical = normalize(structuredClone(bundle.source_state));
check(canonical !== null, "canonical source state rejected");
check(generatedDataIsDeeplyFrozen(canonical), "normalized source state not frozen");
check(canonical.receipt.status === "reviewed", "canonical receipt is not reviewed");

reject("unknown top-level field", state => { state.extra = true; });
reject("proposed public receipt", state => { state.receipt.status = "proposed"; });
reject("credential-bearing receipt URL", state => {
  state.receipt.run_url = "https://github.com@evil.example/run";
});
reject("source registry drift", state => {
  state.source_registry_sha256 = "0".repeat(64);
});
reject("observation digest contradiction", state => {
  state.observations[0].observed_sha256 = "0".repeat(64);
});
reject("changed summary contradiction", state => {
  state.changed_source_ids = ["ca-gov-66317"];
});
reject("derived impact drift", state => { state.unaffected_rule_ids.pop(); });

function setImpact(state, changedSourceIds) {
  const impact = sourceImpactLists(changedSourceIds, bundle.rules, bundle.golden);
  state.affected_rule_ids = impact.affectedRules;
  state.unaffected_rule_ids = impact.unaffectedRules;
  state.affected_golden_case_ids = impact.affectedCases;
  state.unaffected_golden_case_ids = impact.unaffectedCases;
}

function changedReceipt(sourceId) {
  const changed = structuredClone(bundle.source_state);
  const observation = changed.observations.find(
    item => item.source_id === sourceId,
  );
  observation.status = "changed";
  observation.observed_sha256 = "0".repeat(64);
  changed.changed_source_ids = [sourceId];
  setImpact(changed, changed.changed_source_ids);
  return changed;
}

const changed = changedReceipt("ca-gov-66317");
const normalizedChanged = normalize(changed);
check(normalizedChanged !== null, "valid changed-source receipt rejected");
check(
  normalizedChanged.affected_rule_ids.includes("adu-ministerial-review"),
  "exact dependent route missing from changed-source impact",
);
check(
  normalizedChanged.unaffected_rule_ids.includes("sb9-two-unit-ministerial"),
  "unrelated statewide rule missing from unaffected controls",
);
RULES = bundle.rules;
SOURCE_STATE = normalizedChanged;
const journey = bundle.journeys[0];
const expectedResults = RULES.filter(rule =>
  journey.screening_expected_rule_ids.includes(rule.rule_id)
);
const routeRule = RULES.find(rule => rule.rule_id === "adu-ministerial-review");
check(
  ruleStatus(routeRule, activeChangedSourceIds()) === "stale",
  "normalized committed state did not stale exact statewide rule",
);
check(
  !journeySourcesAreCurrent(bundle.journeys[0], bundle.readiness),
  "normalized committed route change did not block Woodland handoff",
);
const blockedHandoff = journeyHandoffState(
  journey,
  bundle.readiness,
  journey.screening_intake,
  expectedResults,
  "yes",
  "active",
  RULES,
);
check(
  blockedHandoff.status === "source_review_required" && !blockedHandoff.href,
  "changed route source bypassed applicant handoff gate",
);
const canonicalQuery = new URLSearchParams(
  `journey=${journey.journey_id}&version=${journey.version}`,
);
check(
  journeyQueryState(canonicalQuery, journey, bundle.readiness, RULES).status
    === "source_review_required",
  "changed route source bypassed direct packet query gate",
);

const normalizedChecklistChange = normalize(
  changedReceipt("woodland-preapproved-adu-checklist"),
);
check(normalizedChecklistChange !== null, "valid checklist change rejected");
SOURCE_STATE = normalizedChecklistChange;
check(
  !readinessSourceIsCurrent(bundle.readiness, activeChangedSourceIds()),
  "normalized committed checklist change did not block packet",
);

const normalizedParcelChange = normalize(
  changedReceipt("yolo-public-parcels-layer"),
);
check(normalizedParcelChange !== null, "valid parcel-source change rejected");
SOURCE_STATE = normalizedParcelChange;
check(
  !readinessSourceIsCurrent(bundle.readiness, activeChangedSourceIds()),
  "normalized committed parcel-source change did not block packet",
);
check(
  journeyQueryState(canonicalQuery, journey, bundle.readiness, RULES).status
    === "source_review_required",
  "changed parcel source bypassed direct packet query gate",
);

const normalizedStandardChange = normalize(changedReceipt("ca-gov-66321"));
check(normalizedStandardChange !== null, "valid standard change rejected");
SOURCE_STATE = normalizedStandardChange;
const heightRule = RULES.find(rule => rule.rule_id === "adu-height-standards");
check(
  ruleStatus(heightRule, activeChangedSourceIds()) === "stale",
  "changed standard source did not stale its statewide record",
);
check(
  journeySourcesAreCurrent(journey, bundle.readiness),
  "changed non-route standard incorrectly disabled Woodland journey",
);

const normalizedUnrelated = normalize(changedReceipt("ca-gov-66411-7"));
check(normalizedUnrelated !== null, "valid unrelated change rejected");
SOURCE_STATE = normalizedUnrelated;
check(
  journeySourcesAreCurrent(bundle.journeys[0], bundle.readiness),
  "unrelated normalized source disabled Woodland journey",
);
check(
  readinessSourceIsCurrent(bundle.readiness, activeChangedSourceIds()),
  "unrelated normalized source disabled Woodland packet",
);

const unverifiable = structuredClone(bundle.source_state);
const unverifiableObservation = unverifiable.observations.find(
  item => item.source_id === "ca-gov-66317",
);
unverifiableObservation.status = "unverifiable";
unverifiableObservation.observed_sha256 = null;
unverifiableObservation.reason = "HTTP 403 Forbidden";
unverifiable.unverifiable_source_ids = ["ca-gov-66317"];
setImpact(unverifiable, []);
const normalizedUnverifiable = normalize(unverifiable);
check(normalizedUnverifiable !== null, "valid unverifiable receipt rejected");
check(
  normalizedUnverifiable.affected_rule_ids.length === 0,
  "unverifiable source incorrectly staled dependents",
);
SOURCE_STATE = normalizedUnverifiable;
check(
  journeySourcesAreCurrent(bundle.journeys[0], bundle.readiness),
  "unverifiable source incorrectly blocked Woodland journey",
);
globalThis.Date = NativeDate;
""",
        ]
    )

    result = subprocess.run(
        ["node", "--input-type=module"],
        cwd=ROOT,
        input=script,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
