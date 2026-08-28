/**
 * The browser's staleness rule and withdrawn-citation derivation, unit tested
 * against the shipped file.
 *
 * `ruleStatus()` decides whether a result card shows action copy or withholds
 * it. `citationLinkNotFound()` decides whether a citation is printed as a
 * link or as text (ADR 0005). Both are duplicated between `assets/demo.js`,
 * `demo/app.py`, and the Python harness. `tests/test_source_review_window.py`
 * already pins the 180-day constant across all four; these tests pin the
 * behaviour built on top of it, in the runtime a visitor actually runs.
 */

import { strict as assert } from "node:assert";
import { test, describe } from "node:test";
import { loadDemo, readJson } from "./load-demo.mjs";

/** An ISO date `days` before today, in UTC, as `ruleStatus` reads them. */
function daysAgo(days) {
  const now = new Date();
  const utc = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  return new Date(utc - days * 86400000).toISOString().slice(0, 10);
}

function ruleWith(verifiedOn, dependencies = ["ca-gov-66321"]) {
  return {
    rule_id: "test-rule",
    source_dependencies: dependencies,
    citation: {
      source: "Gov. Code § 66321",
      url: "https://example.invalid/66321",
      excerpt: "text",
      verified_on: verifiedOn,
    },
  };
}

describe("ruleStatus decides what a result card may show", () => {
  const demo = loadDemo();
  const ruleStatus = demo.get("ruleStatus");

  test("a source checked today is verified", () => {
    assert.equal(ruleStatus(ruleWith(daysAgo(0)), []), "verified");
  });

  test("the review window is inclusive at its last day", () => {
    // 180 is the shared constant. Inside stays verified; one day past does
    // not, and that boundary is the whole point of the window.
    assert.equal(ruleStatus(ruleWith(daysAgo(180)), []), "verified");
    assert.equal(ruleStatus(ruleWith(daysAgo(181)), []), "stale");
  });

  test("a future verification date is stale, not verified", () => {
    // A date the clock has not reached is not evidence. Treating it as fresh
    // would let a typo keep a rule green indefinitely.
    assert.equal(ruleStatus(ruleWith(daysAgo(-1)), []), "stale");
  });

  test("a malformed or missing date is unverified, not stale", () => {
    for (const value of ["", "2026-13-01", "27 July 2026", null, undefined]) {
      assert.equal(ruleStatus(ruleWith(value), []), "unverified");
    }
  });

  test("a changed dependency stales a rule whose own date is fresh", () => {
    assert.equal(ruleStatus(ruleWith(daysAgo(0)), ["ca-gov-66321"]), "stale");
  });

  test("an unrelated changed source leaves the rule alone", () => {
    assert.equal(ruleStatus(ruleWith(daysAgo(0)), ["ca-gov-66323"]), "verified");
  });

  test("a rule with no declared dependencies is never staled by one", () => {
    assert.equal(
      ruleStatus(ruleWith(daysAgo(0), []), ["ca-gov-66321"]),
      "verified",
    );
  });
});

describe("a withdrawn citation costs the link and nothing else", () => {
  const sources = readJson("data", "sources.json");
  const [citationUrl, sourceRecord] = Object.entries(sources)[0];

  /** Load the page with a source-state receipt already applied. */
  function demoWithSourceState(observations) {
    const demo = loadDemo();
    demo.evaluate(
      "globalThis.__setState = (sources, state) => { SOURCES = sources;" +
        " SOURCE_STATE = state; };",
    );
    demo.get("__setState")(sources, { observations, changed_source_ids: [] });
    return demo;
  }

  const notFound = {
    source_id: sourceRecord.source_id,
    status: "unverifiable",
    unverifiable_kind: "not_found",
  };
  const transport = {
    source_id: sourceRecord.source_id,
    status: "unverifiable",
    unverifiable_kind: "transport",
  };
  const cited = { citation: { url: citationUrl } };

  test("a 404 on a rule's own citation URL withdraws the link", () => {
    const demo = demoWithSourceState([notFound]);
    assert.deepEqual(demo.get("notFoundSourceIds")(), [sourceRecord.source_id]);
    assert.equal(demo.get("citationLinkNotFound")(cited), true);
  });

  test("a transport failure on the same source does not", () => {
    // ADR 0005: a refusal to answer is not an answer about the document.
    const demo = demoWithSourceState([transport]);
    assert.deepEqual(demo.get("notFoundSourceIds")(), []);
    assert.equal(demo.get("citationLinkNotFound")(cited), false);
  });

  test("a withdrawn source never stales a rule that depends on it", () => {
    // The retained copy and its recorded hash still stand. Only the link goes.
    const demo = demoWithSourceState([notFound]);
    const rule = {
      ...ruleWith(daysAgo(0), [sourceRecord.source_id]),
      citation: { ...ruleWith(daysAgo(0)).citation, url: citationUrl },
    };
    assert.equal(demo.get("ruleStatus")(rule, demo.get("committedChangedSourceIds")()), "verified");
    assert.equal(demo.get("citationLinkNotFound")(rule), true);
  });

  test("depending on a withdrawn source without citing it keeps the link", () => {
    // The result card's promise is about the single link it prints.
    const demo = demoWithSourceState([notFound]);
    assert.equal(
      demo.get("citationLinkNotFound")({
        citation: { url: "https://example.invalid/not-a-watched-source" },
      }),
      false,
    );
  });

  test("an unverifiable observation with no kind is not treated as not_found", () => {
    // A failure the reader cannot describe honestly is not one to render.
    const demo = demoWithSourceState([
      { source_id: sourceRecord.source_id, status: "unverifiable" },
    ]);
    assert.deepEqual(demo.get("notFoundSourceIds")(), []);
  });

  test("the committed receipt records no withdrawn citation today", () => {
    // Dormant on the committed state, per ADR 0005. If this ever fails, a
    // receipt carrying a 404 was adopted and the evidence page should say so.
    const receipt = readJson("data", "source-status", "current.json");
    const observations = receipt.observations ?? receipt.receipt?.observations ?? [];
    const withdrawn = observations.filter(
      (item) => item.unverifiable_kind === "not_found",
    );
    assert.deepEqual(withdrawn, []);
  });
});
