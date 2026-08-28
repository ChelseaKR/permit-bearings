/**
 * The browser's screening matcher, unit tested against the shipped file.
 *
 * `docs/PRODUCT-CONTEXT.md` records this as known correctness risk 7:
 * "Screening, scanning, and clocks are duplicated without cross-runtime
 * contract tests." The scanner got one in
 * `tests/test_conformance_browser_parity.py`. This is the screening half.
 *
 * The 29 golden cases in `data/golden/example.json` are replayed through the
 * browser's own `screen()`, after the browser's own `normalizeRules()` has
 * accepted the committed rule files. Python replays the same fixtures against
 * the same expectations, so a matcher change that lands in one runtime and
 * not the other now fails here instead of shipping.
 */

import { strict as assert } from "node:assert";
import { test, describe } from "node:test";
import { loadDemo, readJson } from "./load-demo.mjs";

function committedRules() {
  const index = readJson("data", "rules", "index.json");
  return index.files.flatMap((name) => readJson("data", "rules", name));
}

/** A loaded page whose `RULES` are the committed rule files. */
function demoWithCommittedRules() {
  const demo = loadDemo();
  const normalize = demo.get("normalizeRules");
  const rules = normalize(committedRules());
  demo.evaluate("globalThis.__setRules = value => { RULES = value; };");
  demo.get("__setRules")(rules);
  return demo;
}

describe("the shipped rule validator accepts the shipped rule data", () => {
  test("normalizeRules() accepts every committed rule file", () => {
    const rules = committedRules();
    assert.ok(rules.length >= 19, `expected at least 19 rules, got ${rules.length}`);
    const demo = loadDemo();
    assert.equal(demo.get("normalizeRules")(rules).length, rules.length);
  });

  test("normalizeRules() rejects a duplicate rule id", () => {
    const rules = committedRules();
    const demo = loadDemo();
    assert.throws(
      () => demo.get("normalizeRules")([...rules, rules[0]]),
      /duplicate IDs/,
    );
  });
});

describe("golden cases replay identically in the browser", () => {
  const cases = readJson("data", "golden", "example.json");

  test("all 29 golden fixtures are present", () => {
    assert.equal(cases.length, 29);
  });

  for (const goldenCase of cases) {
    test(`${goldenCase.case_id}`, () => {
      const demo = demoWithCommittedRules();
      const matched = demo
        .get("screen")(goldenCase.intake)
        .map((rule) => rule.rule_id)
        .sort();
      assert.deepEqual(matched, [...goldenCase.expected_rule_ids].sort());
    });
  }
});

describe("criterion semantics match the Python matcher", () => {
  const demo = loadDemo();
  const matches = demo.get("matches");
  const rule = (criteria) => ({ criteria });

  test("a missing intake field never satisfies a criterion", () => {
    const criterion = { field: "project_type", op: "eq", value: "adu" };
    assert.equal(matches(rule([criterion]), {}), false);
  });

  test("an explicit null intake value never satisfies a criterion", () => {
    const criterion = { field: "project_type", op: "eq", value: "adu" };
    assert.equal(matches(rule([criterion]), { project_type: null }), false);
  });

  test("every criterion must hold, not just one", () => {
    const criteria = [
      { field: "project_type", op: "eq", value: "adu" },
      { field: "unpermitted_existing", op: "eq", value: "yes" },
    ];
    const intake = { project_type: "adu", unpermitted_existing: "no" };
    assert.equal(matches(rule(criteria), intake), false);
    assert.equal(
      matches(rule(criteria), { ...intake, unpermitted_existing: "yes" }),
      true,
    );
  });

  test("an empty criteria list never matches", () => {
    // A rule with no criteria would otherwise match every intake, which is
    // the failure mode where an unconfigured rule matches everyone.
    assert.equal(matches(rule([]), { project_type: "adu" }), false);
  });

  test("an unsupported operator fails closed", () => {
    const criterion = { field: "project_type", op: "regex", value: "adu" };
    assert.equal(matches(rule([criterion]), { project_type: "adu" }), false);
  });

  test("`in` accepts a listed value and rejects an unlisted one", () => {
    const criterion = {
      field: "primary_dwelling_status",
      op: "in",
      value: ["existing_single_family", "existing_multifamily"],
    };
    assert.equal(
      matches(rule([criterion]), {
        primary_dwelling_status: "existing_multifamily",
      }),
      true,
    );
    assert.equal(
      matches(rule([criterion]), { primary_dwelling_status: "vacant_lot" }),
      false,
    );
  });

  test("a string never satisfies a numeric comparison", () => {
    for (const op of ["lte", "gte"]) {
      const criterion = { field: "lot_size", op, value: 5000 };
      assert.equal(matches(rule([criterion]), { lot_size: "5000" }), false);
    }
  });

  test("lte and gte compare numbers inclusively", () => {
    const lte = { field: "lot_size", op: "lte", value: 5000 };
    const gte = { field: "lot_size", op: "gte", value: 5000 };
    assert.equal(matches(rule([lte]), { lot_size: 5000 }), true);
    assert.equal(matches(rule([lte]), { lot_size: 5001 }), false);
    assert.equal(matches(rule([gte]), { lot_size: 5000 }), true);
    assert.equal(matches(rule([gte]), { lot_size: 4999 }), false);
  });

  test("a malformed criterion fails closed rather than being skipped", () => {
    const malformed = [
      { field: "", op: "eq", value: "adu" },
      { field: "Project_Type", op: "eq", value: "adu" },
      { field: "project_type", op: "eq", value: "" },
      { field: "project_type", op: "in", value: [] },
      { field: "project_type", op: "in", value: ["adu", 5] },
      { field: "project_type", op: "in", value: ["adu", "adu"] },
    ];
    for (const criterion of malformed) {
      assert.equal(
        matches(rule([criterion]), { project_type: "adu", Project_Type: "adu" }),
        false,
        `expected ${JSON.stringify(criterion)} to fail closed`,
      );
    }
  });
});

describe("jurisdiction scope gates a local rule", () => {
  test("a local rule matches only its own jurisdiction", () => {
    const demo = demoWithCommittedRules();
    const screen = demo.get("screen");
    const intake = {
      project_type: "adu",
      primary_dwelling_status: "existing_single_family",
      adu_project_form: "new_detached",
      unpermitted_existing: "no",
    };
    const inDavis = screen({ ...intake, jurisdiction: "davis" }).map(
      (rule) => rule.rule_id,
    );
    const elsewhere = screen({ ...intake, jurisdiction: "example-city" }).map(
      (rule) => rule.rule_id,
    );
    assert.ok(inDavis.includes("davis-local-adu-process"));
    assert.ok(!elsewhere.includes("davis-local-adu-process"));
    assert.ok(!elsewhere.includes("woodland-adu-ordinance-2026"));
  });
});
