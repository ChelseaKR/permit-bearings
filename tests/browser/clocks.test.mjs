/**
 * The browser's review clocks, unit tested against the shipped file.
 *
 * The third duplicated domain. `src/permit_pathways/clocks.py` returns an
 * explicit unknown for the 15-business-day completeness notice unless a
 * deployment supplies the agency's closure calendar, and conditions the
 * 60-calendar-day decision date on a complete application and an existing
 * qualifying dwelling. The browser reimplements that policy inline in a click
 * handler on `check.html`, where nothing was executing it.
 *
 * These tests drive that handler through the stubbed page and assert the
 * conservative behaviour, so the browser cannot start showing a date the
 * Python module withholds.
 */

import { strict as assert } from "node:assert";
import { test, describe } from "node:test";
import { loadDemo, makeElement } from "./load-demo.mjs";

const CLOCK_IDS = [
  "clockBtn",
  "recvDate",
  "clockResults",
  "clockStatus",
  "clockComplete",
  "clockExisting",
];

/** A project page carrying only the clock controls. */
function clockPage({ received = "", complete = false, existing = false } = {}) {
  const elements = Object.fromEntries(
    CLOCK_IDS.map((id) => [id, makeElement(id)]),
  );
  elements.recvDate.value = received;
  elements.clockComplete.checked = complete;
  elements.clockExisting.checked = existing;
  const demo = loadDemo({ elements, page: "project" });
  return {
    elements,
    run() {
      elements.clockBtn.dispatch("click", { target: elements.clockBtn });
      return {
        html: elements.clockResults.innerHTML,
        status: elements.clockStatus.textContent,
      };
    },
  };
}

/** The `datetime` attribute the handler renders, if it rendered one. */
function renderedDate(html) {
  return html.match(/datetime="([0-9]{4}-[0-9]{2}-[0-9]{2})"/)?.[1] ?? null;
}

describe("the clock control is wired up on the project page", () => {
  test("the handler registers", () => {
    const page = clockPage();
    assert.equal(page.elements.clockBtn.listeners.get("click").length, 1);
  });

  test("no receipt date produces no output and asks for one", () => {
    const { html, status } = clockPage().run();
    assert.equal(html, "");
    assert.match(status, /receipt date/i);
  });
});

describe("the 60-calendar-day decision date", () => {
  test("is 60 calendar days after receipt when both facts are confirmed", () => {
    const { html } = clockPage({
      received: "2026-03-02",
      complete: true,
      existing: true,
    }).run();
    // 2026-03-02 plus 60 calendar days. Calendar days, so the answer does not
    // move with weekends or holidays.
    assert.equal(renderedDate(html), "2026-05-01");
  });

  test("counts calendar days across a leap day", () => {
    const { html } = clockPage({
      received: "2028-01-31",
      complete: true,
      existing: true,
    }).run();
    // 2028 is a leap year: 29 January days remain, then all of February (29),
    // leaving 2 days into March.
    assert.equal(renderedDate(html), "2028-03-31");
  });

  test("is withheld unless the application is confirmed complete", () => {
    const { html } = clockPage({
      received: "2026-03-02",
      complete: false,
      existing: true,
    }).run();
    assert.equal(renderedDate(html), null);
    assert.match(html, /Not shown/);
    assert.match(html, /Confirm both statements/);
  });

  test("is withheld unless an existing qualifying dwelling is confirmed", () => {
    const { html } = clockPage({
      received: "2026-03-02",
      complete: true,
      existing: false,
    }).run();
    assert.equal(renderedDate(html), null);
    assert.match(html, /Not shown/);
  });

  test("the status message says which dates were shown", () => {
    const shown = clockPage({
      received: "2026-03-02",
      complete: true,
      existing: true,
    }).run();
    assert.match(shown.status, /60-day date is shown/);
    assert.match(shown.status, /15-business-day date remains unknown/);

    const withheld = clockPage({ received: "2026-03-02" }).run();
    assert.match(withheld.status, /not shown until their required facts/);
  });
});

describe("the 15-business-day completeness notice is never calculated", () => {
  // `clocks.py` returns an explicit unknown without the agency's full-day
  // closure calendar, and the browser has no such calendar. A statewide
  // holiday approximation is not an agency calendar.
  for (const facts of [
    { received: "2026-03-02" },
    { received: "2026-03-02", complete: true, existing: true },
  ]) {
    test(`stays uncalculated with ${JSON.stringify(facts)}`, () => {
      const { html } = clockPage(facts).run();
      assert.match(html, /Completeness notice/);
      assert.match(html, /closure calendar/);
      const notCalculated = html.match(/Not calculated/g) ?? [];
      // Both the notice date and the deemed-complete-if-silent date depend on
      // it, so both must stay withheld.
      assert.equal(notCalculated.length, 2);
    });
  }

  test("the output says these are separate clocks and names what is not modeled", () => {
    const { html } = clockPage({
      received: "2026-03-02",
      complete: true,
      existing: true,
    }).run();
    assert.match(html, /separate clocks/);
    assert.match(html, /completeness notice is\s+not an approval/);
    assert.match(html, /Corrections, resubmittals, tolling, and local closures are\s+not modeled/);
  });
});
