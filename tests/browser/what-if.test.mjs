/**
 * The browser's what-if explorer, unit tested against the shipped file.
 *
 * `whatIfDeltas` is the browser half of `src/permit_pathways/what_if.py`:
 * it perturbs one material fact at a time through the deployed `screen()` and
 * reports which rules and route classes the encoded rule set attaches to each
 * allowed answer. `tests/test_what_if_browser_parity.py` holds the two
 * runtimes to identical output over every Golden case; this suite is the
 * browser-side unit coverage of the same code, and it checks the committed
 * Woodland expectations from the same fixture the Python test reads.
 *
 * The three assertions worth having are not "a delta was produced":
 *   - a branch that still leaves a material fact unanswered says
 *     needs_staff_review and shows no candidate route, even when the matched
 *     rules did not move at all;
 *   - a fact every rule reads the same way is reported saying so, not omitted;
 *   - a fact read by a rule on source hold gets `null` deltas, never `[]`,
 *     because an empty delta renders as "this answer changes nothing".
 */

import { strict as assert } from "node:assert";
import { test, describe } from "node:test";
import { loadDemo, readJson } from "./load-demo.mjs";

const GOLDEN = readJson("data", "golden", "example.json");
const WOODLAND = readJson("tests", "fixtures", "what-if-woodland.json");

/** `ca-gov-66311-7` sits under both legalization rules. */
const HELD_SOURCE_IDS = ["ca-gov-66311-7"];

function committedRules() {
  const index = readJson("data", "rules", "index.json");
  return index.files.flatMap((name) => readJson("data", "rules", name));
}

/** A loaded page whose `RULES` are the committed rule files. */
function demoWithCommittedRules() {
  const demo = loadDemo();
  const rules = demo.get("normalizeRules")(committedRules());
  demo.evaluate("globalThis.__setRules = value => { RULES = value; };");
  demo.get("__setRules")(rules);
  return demo;
}

/**
 * The values the form actually offers for a fact, read from the shipped copy
 * catalog rather than retyped here, so the branches explored are the branches
 * a visitor can choose.
 */
function allowedValues(demo, name) {
  const strings = demo.get("STRINGS").en;
  if (name === "primary_dwelling_status")
    return strings.primaryOptions.map(([value]) => value);
  if (name === "adu_project_form")
    return strings.aduFormOptions.map(([value]) => value);
  return strings.tri.map(([value]) => value);
}

/**
 * The vm context has its own `Array` and `Object` prototypes, so a value it
 * returns is never reference-equal to a host-realm literal under
 * `deepStrictEqual`. Round-tripping through JSON re-creates the structure in
 * this realm, and it also proves the payload is JSON-serialisable, which it
 * has to be for the disclosure to render it.
 */
function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function explore(demo, intake, changedSourceIds = []) {
  const fields = demo.get("fieldsForProject")(intake.project_type);
  const values = Object.fromEntries(
    fields.map((name) => [name, allowedValues(demo, name)]),
  );
  return plain(
    demo.get("whatIfDeltas")(intake, fields, values, changedSourceIds),
  );
}

function goldenIntake(caseId) {
  const matching = GOLDEN.filter((item) => item.case_id === caseId);
  assert.equal(matching.length, 1, caseId);
  return matching[0].intake;
}

function factEntry(facts, field) {
  const matching = facts.filter((entry) => entry.field === field);
  assert.equal(matching.length, 1, field);
  return matching[0];
}

function branch(entry, value) {
  const matching = entry.alternatives.filter((item) => item.value === value);
  assert.equal(matching.length, 1, value);
  return matching[0];
}

describe("the Woodland case matches the committed expectations", () => {
  test("every fact, value, and delta agrees with the fixture", () => {
    const demo = demoWithCommittedRules();
    const facts = explore(demo, goldenIntake(WOODLAND.case_id));
    assert.deepEqual(facts, WOODLAND.facts);
  });

  test("converting instead adds the conversion exemptions rule", () => {
    const demo = demoWithCommittedRules();
    const facts = explore(demo, goldenIntake(WOODLAND.case_id));
    const conversion = branch(
      factEntry(facts, "adu_project_form"),
      "conversion",
    );
    assert.deepEqual(conversion.rules_added, ["adu-conversion-exemptions"]);
    assert.deepEqual(conversion.rules_removed, []);
  });
});

describe("an unanswered branch withholds its route", () => {
  test("not answering matches the same rules and still costs the route", () => {
    const demo = demoWithCommittedRules();
    const facts = explore(demo, goldenIntake(WOODLAND.case_id));
    const unknown = branch(factEntry(facts, "adu_project_form"), "unknown");
    assert.deepEqual(unknown.rules_added, []);
    assert.deepEqual(unknown.rules_removed, []);
    assert.equal(unknown.decision_boundary, "needs_staff_review");
    assert.deepEqual(unknown.unresolved_facts, ["adu_project_form"]);
    assert.deepEqual(unknown.candidate_routes, []);
    assert.deepEqual(unknown.routes_removed, ["ministerial"]);
  });

  test("one answer does not clear a second unknown", () => {
    const demo = demoWithCommittedRules();
    const facts = explore(demo, goldenIntake("adu-primary-status-unknown"));
    const answered = branch(
      factEntry(facts, "primary_dwelling_status"),
      "existing_single_family",
    );
    assert.equal(answered.decision_boundary, "needs_staff_review");
    assert.deepEqual(answered.unresolved_facts, ["unpermitted_existing"]);
    assert.deepEqual(answered.candidate_routes, []);
    assert.ok(answered.rules_added.length > 0);
  });
});

describe("a fact no rule reads differently is reported, not dropped", () => {
  test("an already-disqualifying intake reports agreement, not silence", () => {
    const demo = demoWithCommittedRules();
    const facts = explore(demo, goldenIntake("sb9-duplex-tenant-occupied"));
    const entry = factEntry(facts, "in_urbanized_area");
    assert.equal(entry.no_rule_reads_this_differently, true);
    assert.ok(entry.read_by_rule_ids.length > 0);
    assert.ok(entry.alternatives.length > 0);
  });

  test("a fact that does change rules is not marked as agreeing", () => {
    const demo = demoWithCommittedRules();
    const facts = explore(demo, goldenIntake(WOODLAND.case_id));
    assert.equal(
      factEntry(facts, "adu_project_form").no_rule_reads_this_differently,
      false,
    );
  });
});

describe("a held source withholds the delta rather than emptying it", () => {
  test("null, never [], on every branch of a held fact", () => {
    const demo = demoWithCommittedRules();
    const facts = explore(
      demo,
      goldenIntake(WOODLAND.case_id),
      HELD_SOURCE_IDS,
    );
    const held = factEntry(facts, "unpermitted_existing");
    assert.equal(held.deltas_withheld, "source_on_review_hold");
    assert.deepEqual(held.rules_on_source_hold, [
      "adu-unpermitted-legalization",
      "jadu-unpermitted-legalization",
    ]);
    assert.equal(held.no_rule_reads_this_differently, null);
    for (const item of held.alternatives) {
      assert.equal(item.rules_added, null);
      assert.equal(item.rules_removed, null);
      assert.equal(item.routes_added, null);
      assert.equal(item.routes_removed, null);
      assert.equal(item.candidate_routes, null);
    }
    // The boundary is a property of the intake, so the hold cannot hide it.
    assert.equal(branch(held, "unknown").decision_boundary, "needs_staff_review");
  });

  test("a fact no held rule reads keeps its delta", () => {
    const demo = demoWithCommittedRules();
    const facts = explore(
      demo,
      goldenIntake(WOODLAND.case_id),
      HELD_SOURCE_IDS,
    );
    const unheld = factEntry(facts, "adu_project_form");
    assert.equal(unheld.deltas_withheld, null);
    assert.deepEqual(branch(unheld, "conversion").rules_added, [
      "adu-conversion-exemptions",
    ]);
  });

  test("an empty changed list holds nothing", () => {
    const demo = demoWithCommittedRules();
    const facts = explore(demo, goldenIntake(WOODLAND.case_id), []);
    assert.ok(facts.every((entry) => entry.deltas_withheld === null));
  });
});

describe("every golden case explores, and none of them ranks", () => {
  for (const goldenCase of GOLDEN) {
    test(`${goldenCase.case_id}`, () => {
      const demo = demoWithCommittedRules();
      const facts = explore(demo, goldenCase.intake);
      const fields = plain(
        demo.get("fieldsForProject")(goldenCase.intake.project_type),
      );
      assert.deepEqual(
        facts.map((entry) => entry.field),
        fields,
      );
      for (const entry of facts) {
        assert.ok(entry.alternatives.length > 0);
        const current = entry.alternatives.filter(
          (item) => item.is_current_answer,
        );
        assert.ok(current.length <= 1);
        for (const item of entry.alternatives) {
          if (item.decision_boundary === "needs_staff_review") {
            assert.ok(item.unresolved_facts.length > 0);
            assert.deepEqual(item.candidate_routes, []);
          } else {
            assert.deepEqual(item.unresolved_facts, []);
          }
        }
      }
    });
  }
});
