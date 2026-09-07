/**
 * The rendered "see what would change" disclosure on `check.html`.
 *
 * `tests/browser/what-if.test.mjs` covers what `whatIfDeltas` computes.
 * This suite covers what a visitor is shown, and the assertions worth having
 * are the three places where rendering could quietly discard a distinction
 * the payload took care to make:
 *
 *   - a fact on source hold must render the hold and no branches at all. An
 *     empty delta drawn as a row saying "nothing would change" is the exact
 *     claim a held rule set cannot support.
 *   - a branch that leaves a material fact unanswered must say no path is
 *     shown for it *even when its rules did not move*. On the Woodland
 *     fixture, answering "I'm not sure" to the ADU-work question matches
 *     exactly the same rules as the real answer, so a disclosure that showed
 *     only rule deltas would tell an applicant that not answering is free.
 *     It costs the route.
 *   - a fact whose branches all agree must say so, rather than rendering as
 *     a column of identical rows a reader has to compare by eye.
 *
 * Copy is asserted through the shipped catalog rather than retyped here, so
 * the test cannot drift from the strings a visitor reads, and the Spanish
 * case asserts that a rule's own record name stays English and marked as
 * English rather than being passed through the interface translation.
 */

import { strict as assert } from "node:assert";
import { test, describe } from "node:test";
import { loadDemo, makeElement, readJson } from "./load-demo.mjs";

const GOLDEN = readJson("data", "golden", "example.json");
const WOODLAND_CASE_ID = "woodland-new-detached-adu-local-layer";

/** `ca-gov-66311-7` sits under both legalization rules. */
const HELD_SOURCE_IDS = ["ca-gov-66311-7"];

function committedRules() {
  const index = readJson("data", "rules", "index.json");
  return index.files.flatMap((name) => readJson("data", "rules", name));
}

function goldenIntake(caseId) {
  const matching = GOLDEN.filter((item) => item.case_id === caseId);
  assert.equal(matching.length, 1, caseId);
  return matching[0].intake;
}

/**
 * A loaded page holding the committed rules, one Golden intake, and a
 * jurisdiction record, ready to render a result.
 */
function loadedPage({
  caseId = WOODLAND_CASE_ID,
  changedSourceIds = [],
  language = "en",
  elements = {},
  withRules = true,
} = {}) {
  const demo = loadDemo({ elements });
  demo.evaluate(`globalThis.__seed = (rules, intake, changed, language) => {
    RULES = rules;
    SOURCE_STATE = {changed_source_ids: changed};
    LAST_INTAKE = intake;
    LAST_JURISDICTION = {
      county: "Yolo", has_local_layer: true, kind: "city",
      name: "City of Woodland", slug: intake.jurisdiction,
    };
    lang = language;
  };`);
  const intake = goldenIntake(caseId);
  demo.get("__seed")(
    withRules ? demo.get("normalizeRules")(committedRules()) : [],
    intake,
    changedSourceIds,
    language,
  );
  return demo;
}

function disclosure(demo) {
  return demo.get("whatIfDisclosureMarkup")();
}

/** The markup of one fact block, chosen by its `data-field`. */
function factBlock(markup, field) {
  const opening = `<div class="what-if-fact" data-field="${field}"`;
  const start = markup.indexOf(opening);
  assert.notEqual(start, -1, `no block for ${field}`);
  assert.equal(
    markup.indexOf(opening, start + 1),
    -1,
    `more than one block for ${field}`,
  );
  const next = markup.indexOf('<div class="what-if-fact"', start + 1);
  return markup.slice(start, next === -1 ? markup.length : next);
}

/** The markup of one answer row inside a fact block. */
function answerRow(block, value) {
  const opening = `<li class="what-if-answer" data-value="${value}"`;
  const start = block.indexOf(opening);
  assert.notEqual(start, -1, `no row for ${value}`);
  const next = block.indexOf('<li class="what-if-answer"', start + 1);
  return block.slice(start, next === -1 ? block.length : next);
}

function copy(demo, language, key) {
  return demo.get("STRINGS")[language].whatIf[key];
}

describe("the disclosure renders one branch per allowed answer", () => {
  test("every material fact is shown, in the form's order", () => {
    const demo = loadedPage();
    const markup = disclosure(demo);
    const order = demo.get("fieldsForProject")("adu");
    assert.deepEqual(
      [...markup.matchAll(/data-field="([a-z_]+)"/g)].map((match) => match[1]),
      [...order],
    );
  });

  test("each answer the form offers gets its own row", () => {
    const demo = loadedPage();
    const block = factBlock(disclosure(demo), "adu_project_form");
    const offered = demo
      .get("STRINGS")
      .en.aduFormOptions.map(([value]) => value);
    assert.deepEqual(
      [...block.matchAll(/data-value="([a-z_]+)"/g)].map((match) => match[1]),
      [...offered],
    );
  });

  test("the applicant's own answer is marked, and only that one", () => {
    const demo = loadedPage();
    const block = factBlock(disclosure(demo), "adu_project_form");
    const marked = [...block.matchAll(/data-current="(yes|no)"/g)].filter(
      (match) => match[1] === "yes",
    );
    assert.equal(marked.length, 1);
    assert.ok(answerRow(block, "new_detached").includes('data-current="yes"'));
  });

  test("a rule that would start matching is named by its record name", () => {
    const demo = loadedPage();
    const row = answerRow(
      factBlock(disclosure(demo), "adu_project_form"),
      "conversion",
    );
    assert.ok(row.includes(copy(demo, "en", "rulesAdded")));
    assert.ok(!row.includes(copy(demo, "en", "rulesRemoved")));
    assert.ok(
      row.includes("ADU — existing-space conversion"),
      "the rule's own pathway text should appear",
    );
  });
});

describe("an unanswered branch still says the route is gone", () => {
  test('"I\'m not sure" matches the same rules and shows no path', () => {
    const demo = loadedPage();
    const row = answerRow(
      factBlock(disclosure(demo), "adu_project_form"),
      "unknown",
    );
    // Both statements have to be on the row. Either one alone misleads.
    assert.ok(row.includes(copy(demo, "en", "sameRules")));
    assert.ok(row.includes(copy(demo, "en", "pathUnresolved")));
    assert.ok(!row.includes(copy(demo, "en", "pathNamed")));
  });

  test("an answered branch says a path is identified", () => {
    const demo = loadedPage();
    const row = answerRow(
      factBlock(disclosure(demo), "adu_project_form"),
      "conversion",
    );
    assert.ok(row.includes(copy(demo, "en", "pathNamed")));
    assert.ok(!row.includes(copy(demo, "en", "pathUnresolved")));
  });
});

describe("a fact every rule reads the same way says so once", () => {
  test("the agreement line replaces a column of identical rows", () => {
    const demo = loadedPage({ caseId: "sb9-duplex-tenant-occupied" });
    const block = factBlock(disclosure(demo), "in_urbanized_area");
    assert.ok(block.includes(copy(demo, "en", "agree")));
    assert.ok(!block.includes(copy(demo, "en", "unreadQuestion")));
    assert.ok(!block.includes(copy(demo, "en", "sameRules")));
    // The branches are still there, because their path state can differ.
    assert.equal([...block.matchAll(/data-value="/g)].length, 3);
  });

  test("a fact whose rules do move gets no agreement line", () => {
    const demo = loadedPage();
    const block = factBlock(disclosure(demo), "adu_project_form");
    assert.ok(!block.includes(copy(demo, "en", "agree")));
    assert.ok(!block.includes(copy(demo, "en", "unreadQuestion")));
  });
});

describe("a held source withholds the branches, not just the numbers", () => {
  test("the hold is stated and no answer row is drawn", () => {
    const demo = loadedPage({ changedSourceIds: HELD_SOURCE_IDS });
    const block = factBlock(disclosure(demo), "unpermitted_existing");
    assert.ok(block.includes('data-withheld="source_on_review_hold"'));
    assert.ok(block.includes(copy(demo, "en", "deltasWithheld")));
    assert.equal([...block.matchAll(/data-value="/g)].length, 0);
    assert.ok(!block.includes(copy(demo, "en", "sameRules")));
    assert.ok(!block.includes(copy(demo, "en", "pathNamed")));
  });

  test("the held rules are named so they can be taken to staff", () => {
    const demo = loadedPage({ changedSourceIds: HELD_SOURCE_IDS });
    const block = factBlock(disclosure(demo), "unpermitted_existing");
    assert.ok(block.includes(copy(demo, "en", "withheldRules")));
    assert.ok(block.includes("ADU — possible legalization"));
  });

  test("a fact no held rule reads keeps its branches", () => {
    const demo = loadedPage({ changedSourceIds: HELD_SOURCE_IDS });
    const block = factBlock(disclosure(demo), "adu_project_form");
    assert.ok(block.includes('data-withheld="no"'));
    assert.ok(!block.includes(copy(demo, "en", "deltasWithheld")));
    assert.equal([...block.matchAll(/data-value="/g)].length, 5);
  });
});

describe("the disclosure says nothing rather than something wrong", () => {
  test("no rendered project means no disclosure", () => {
    const demo = loadDemo();
    assert.equal(demo.get("whatIfDisclosureMarkup")(), "");
  });

  test("an unloaded rule set is not reported as rules with no conditions", () => {
    const demo = loadedPage({ withRules: false });
    assert.equal(disclosure(demo), "");
  });
});

describe("the Spanish page translates the copy and not the records", () => {
  test("interface copy is Spanish and the rule record stays English", () => {
    const demo = loadedPage({ language: "es" });
    const markup = disclosure(demo);
    assert.ok(markup.includes(copy(demo, "es", "heading")));
    assert.ok(markup.includes(copy(demo, "es", "intro")));
    assert.ok(!markup.includes(copy(demo, "en", "heading")));
    const row = answerRow(
      factBlock(markup, "adu_project_form"),
      "conversion",
    );
    assert.ok(row.includes(copy(demo, "es", "rulesAdded")));
    assert.ok(
      row.includes('<li lang="en">ADU — existing-space conversion'),
      "a rule record name is not interface copy and is marked English",
    );
  });

  test("the same answers are explored in either language", () => {
    const english = disclosure(loadedPage({ language: "en" }));
    const spanish = disclosure(loadedPage({ language: "es" }));
    const values = (markup) =>
      [...markup.matchAll(/data-value="([a-z_]+)"/g)].map((match) => match[1]);
    assert.deepEqual(values(spanish), values(english));
  });
});

describe("both result pages carry the disclosure", () => {
  test("a screened result renders it after the answers cover sheet", () => {
    const elements = { results: makeElement("results"), resultStatus: makeElement("resultStatus") };
    const demo = loadedPage({ elements });
    const matched = demo.get("screen")(goldenIntake(WOODLAND_CASE_ID));
    assert.ok(matched.length > 0);
    demo.get("renderResults")(matched);
    const markup = elements.results.innerHTML;
    assert.ok(markup.includes('<details class="what-if result-support ca-box"'));
    assert.ok(
      markup.indexOf('class="result-cover-sheet') <
        markup.indexOf('class="what-if result-support'),
    );
  });

  test("a staff-review result renders it too", () => {
    const elements = { results: makeElement("results"), resultStatus: makeElement("resultStatus") };
    const demo = loadedPage({ caseId: "adu-primary-status-unknown", elements });
    demo.get("renderNeedsStaffReview")(["primary_dwelling_status"]);
    const markup = elements.results.innerHTML;
    assert.ok(markup.includes('<details class="what-if result-support ca-box"'));
  });

  test("the disclosure is collapsed, like every other support section", () => {
    const demo = loadedPage();
    assert.ok(!disclosure(demo).includes('class="what-if result-support ca-box" open'));
  });
});
