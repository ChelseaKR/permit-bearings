const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");

const JOURNEY_ID = "woodland-preapproved-detached-adu-synthetic";
const JOURNEY_VERSION = "1.0.0";
const VALID_PACKET_PATH =
  `/prepare.html?journey=${JOURNEY_ID}&version=${JOURNEY_VERSION}`;
const WCAG_TAGS = [
  "wcag2a",
  "wcag2aa",
  "wcag2aaa",
  "wcag21aa",
  "wcag22aa",
];

const pages = {
  "/index.html": null,
  "/prepare.html": null,
  "/review.html": "For staff",
  "/evidence.html": "Sources & limits",
  "/check.html": "Start",
};

const DEMO_ASSIGNMENT = "globalThis.PERMIT_PATHWAYS_DEMO_DATA=";
const DEMO_SOURCE = readFileSync(resolve(__dirname, "../data/demo-data.js"), "utf8");
const DEMO_DATA = JSON.parse(
  DEMO_SOURCE.slice(DEMO_SOURCE.indexOf(DEMO_ASSIGNMENT)
    + DEMO_ASSIGNMENT.length).trim().replace(/;$/, ""),
);

function sourceStateFixture(status, sourceId) {
  const data = structuredClone(DEMO_DATA);
  const state = data.source_state;
  const observation = state.observations.find(item => item.source_id === sourceId);
  if (!observation) throw new Error(`unknown source fixture: ${sourceId}`);
  observation.status = status;
  if (status === "changed") {
    observation.observed_sha256 = "0".repeat(64);
    observation.reason = null;
    state.changed_source_ids = [sourceId];
    state.unverifiable_source_ids = [];
  } else if (status === "unverifiable") {
    observation.observed_sha256 = null;
    observation.reason = "HTTP 403 Forbidden";
    state.changed_source_ids = [];
    state.unverifiable_source_ids = [sourceId];
  } else {
    throw new Error(`unsupported source fixture status: ${status}`);
  }
  const changed = new Set(state.changed_source_ids);
  const affectedRules = data.rules.filter(rule =>
    rule.source_dependencies.some(id => changed.has(id))
  ).map(rule => rule.rule_id).sort();
  const affectedRuleSet = new Set(affectedRules);
  state.affected_rule_ids = affectedRules;
  state.unaffected_rule_ids = data.rules.map(rule => rule.rule_id)
    .filter(ruleId => !affectedRuleSet.has(ruleId)).sort();
  state.affected_golden_case_ids = data.golden.filter(record =>
    record.rule_dependency_ids.some(ruleId => affectedRuleSet.has(ruleId))
  ).map(record => record.case_id).sort();
  const affectedCaseSet = new Set(state.affected_golden_case_ids);
  state.unaffected_golden_case_ids = data.golden.map(record => record.case_id)
    .filter(caseId => !affectedCaseSet.has(caseId)).sort();
  return `/* test source-state fixture */\n${DEMO_ASSIGNMENT}${JSON.stringify(data)};\n`;
}

async function serveSourceStateFixture(page, status, sourceId) {
  const body = sourceStateFixture(status, sourceId);
  await page.route("**/data/demo-data.js*", route => route.fulfill({
    body,
    contentType: "application/javascript; charset=utf-8",
    status: 200,
  }));
}

async function expectNoDocumentOverflow(page) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);
}

async function expectNoAutomatedWcagViolations(page) {
  const results = await new AxeBuilder({ page })
    .withTags(WCAG_TAGS)
    .analyze();
  expect(results.violations).toEqual([]);
}

async function expectBrowserStorageEmpty(page) {
  const storage = await page.evaluate(async () => ({
    local: Object.keys(localStorage),
    session: Object.keys(sessionStorage),
    cookie: document.cookie,
    indexed: typeof indexedDB.databases === "function"
      ? (await indexedDB.databases()).map(database => database.name)
      : [],
  }));
  expect(storage).toEqual({
    local: [],
    session: [],
    cookie: "",
    indexed: [],
  });
}

async function openCanonicalJourney(page) {
  await page.goto("/check.html?sample=adu");
  await expect(page.locator("#resultsHeading")).toBeVisible();
  await expect(page.locator("#journeyGateHeading")).toBeVisible();
}

async function expectClosedDisclosure(details, body) {
  await expect(details).toBeVisible();
  await expect.poll(() => details.evaluate(element => ({
    open: element.open,
    tagName: element.tagName,
  }))).toEqual({open: false, tagName: "DETAILS"});
  await expect(body).toBeHidden();
}

async function expandDisclosureWithKeyboard(details, key = "Enter") {
  const summary = details.locator(":scope > summary");
  await summary.focus();
  await expect(summary).toBeFocused();
  await summary.press(key);
  await expect.poll(() => details.evaluate(element => element.open)).toBe(true);
  return summary;
}

for (const [path, currentMobileLabel] of Object.entries(pages)) {
  test(`${path} has no automated WCAG violations`, async ({ page }) => {
    await page.goto(path);
    if (path === "/prepare.html") {
      await expect(page.locator("#entryHoldHeading")).toBeVisible();
    }
    await expectNoAutomatedWcagViolations(page);
  });

  for (const viewport of [
    { label: "320px", width: 320, height: 720 },
    { label: "390px", width: 390, height: 844 },
  ]) {
    test(`${path} reflows at ${viewport.label}`, async ({ page }) => {
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      await page.goto(path);

      await expect(page.locator(".site-nav")).toBeHidden();
      await expect(page.locator(".mobile-menu")).toBeVisible();
      await page.locator(".mobile-menu summary").click();
      await expect(page.locator(".mobile-nav")).toBeVisible();
      const currentMobileLink = page.locator(
        ".mobile-nav a[aria-current='page']",
      );
      if (currentMobileLabel) {
        await expect(currentMobileLink).toHaveCount(1);
        await expect(currentMobileLink).toHaveText(currentMobileLabel);
      } else {
        await expect(currentMobileLink).toHaveCount(0);
      }
      await expectNoDocumentOverflow(page);

      if (viewport.width === 320) {
        await expectNoAutomatedWcagViolations(page);
      }
    });
  }
}

test("decorative illustrations decode and keep the tablet boundary first", async ({
  page,
}) => {
  await page.setViewportSize({width: 1280, height: 960});
  for (const [path, selector] of [
    ["/index.html", ".home-hero-visual img"],
    ["/check.html", ".project-hero-visual img"],
  ]) {
    await page.goto(path);
    const image = page.locator(selector);
    await expect(image).toHaveAttribute("alt", "");
    await expect(image.locator("xpath=..")).toHaveAttribute("aria-hidden", "true");
    await expect.poll(() => image.evaluate(element => ({
      complete: element.complete,
      decoded: element.naturalWidth > 0 && element.naturalHeight > 0,
    }))).toEqual({complete: true, decoded: true});
  }

  for (const width of [768, 928]) {
    await page.setViewportSize({width, height: 1024});
    await page.goto("/index.html");
    const boundary = await page.locator(".home-boundary").boundingBox();
    const visual = await page.locator(".home-hero-visual").boundingBox();
    expect(boundary).not.toBeNull();
    expect(visual).not.toBeNull();
    expect(boundary.y + boundary.height).toBeLessThanOrEqual(1024);
    expect(visual.y).toBeGreaterThanOrEqual(boundary.y + boundary.height);
    expect(visual.height).toBeLessThanOrEqual(288);
    await expectNoDocumentOverflow(page);
  }
});

test("canonical journey gates the packet link on the editable applicability fact", async ({
  page,
}) => {
  await openCanonicalJourney(page);
  const yes = page.locator(
    'input[name="journey_applicability"][value="yes"]',
  );
  const no = page.locator(
    'input[name="journey_applicability"][value="no"]',
  );
  const unknown = page.locator(
    'input[name="journey_applicability"][value="unknown"]',
  );

  await expect(yes).not.toBeChecked();
  await expect(no).not.toBeChecked();
  await expect(unknown).not.toBeChecked();
  await expect(page.locator("#journeyGateOutcome a")).toHaveCount(0);
  await expect(page.locator(".program-availability")).toContainText(
    "Preapproved ADU List: Coming soon!",
  );
  await expect(page.locator(".program-availability")).toContainText(
    "Future-state simulation only",
  );
  await expect(page.locator(".program-availability")).toContainText(
    "Checked August 9, 2026",
  );
  await expect(page.locator(".program-availability")).toContainText(
    "recheck due September 8, 2026",
  );
  await expect(
    page.locator(`.program-availability a[href="${
      DEMO_DATA.program_availability.availability.source.url
    }"]`),
  ).toBeVisible();
  await expect(page.locator("#journeyGateOutcome")).toContainText(
    "Is this packet using a City of Woodland preapproved ADU plan?",
  );

  await yes.check();
  let packetLink = page.locator(
    "#journeyGateOutcome a[href^='prepare.html?journey=']",
  );
  await expect(packetLink).toBeVisible();
  await expect(page.locator("#journeyGateOutcome")).toContainText(
    "future-state simulation is ready",
  );
  const href = await packetLink.getAttribute("href");
  const packetUrl = new URL(href, page.url());
  expect([...packetUrl.searchParams.keys()]).toEqual(["journey", "version"]);
  expect(packetUrl.searchParams.get("journey")).toBe(JOURNEY_ID);
  expect(packetUrl.searchParams.get("version")).toBe(JOURNEY_VERSION);

  await no.check();
  await expect(page.locator("#journeyGateOutcome a")).toHaveCount(0);
  await expect(page.locator("#journeyGateOutcome")).toContainText(
    "This packet example does not apply",
  );

  await unknown.check();
  await expect(page.locator("#journeyGateOutcome a")).toHaveCount(0);
  await expect(page.locator("#journeyGateOutcome")).toContainText(
    "Is this packet using a City of Woodland preapproved ADU plan?",
  );

  await yes.check();
  packetLink = page.locator(
    "#journeyGateOutcome a[href^='prepare.html?journey=']",
  );
  await expect(packetLink).toBeVisible();
  await expectBrowserStorageEmpty(page);

  await packetLink.click();
  await expect(page).toHaveURL(new RegExp(
    `/prepare\\.html\\?journey=${JOURNEY_ID}&version=${JOURNEY_VERSION}$`,
  ));
  await expect(page.locator("#journeyEntrySummary")).toBeVisible();
  await expect(page.getByRole("heading", {
    name: "Explore a future-state packet workflow",
  })).toBeVisible();
  await expect(page.locator("#programAvailabilityNotice")).toContainText(
    "Preapproved ADU List: Coming soon!",
  );
  await expect(page.locator("#journeyEntryId")).toHaveText(JOURNEY_ID);
  await expect(page.locator("#journeyEntryVersion")).toHaveText(JOURNEY_VERSION);
  await expect(page.locator("#packetCover")).toBeVisible();
  await expect(page.locator("#journeyEvidenceSummary")).toBeVisible();
  await expect(page.locator("#readinessMethod")).toBeVisible();
  await expect(page.locator("#readinessVerdictHeading")).toBeVisible();
  await expectBrowserStorageEmpty(page);
});

test("valid journey presents a bounded portable evidence summary and print action", async ({
  page,
}) => {
  await page.addInitScript(() => {
    window.__permitBearingsPrintCalls = 0;
    window.print = () => {
      window.__permitBearingsPrintCalls += 1;
    };
  });
  await page.goto(VALID_PACKET_PATH);

  const summary = page.locator("#journeyEvidenceSummary");
  await expect(summary).toBeVisible();
  await expect(summary.locator(".journey-evidence-route")).toContainText(
    "ADU — ministerial review and application timelines",
  );
  await expect(summary.locator(".journey-evidence-route")).toContainText(
    "Gov. Code § 66317",
  );
  await expect(summary.locator(".journey-evidence-facts")).toContainText(
    "Woodland",
  );
  await expect(summary.locator(".journey-evidence-facts")).toContainText(
    /new detached/i,
  );

  const actions = summary.locator("#journeyEvidenceActionsList > li");
  await expect(actions).toHaveCount(3);
  await expect(actions.nth(0)).toContainText("property address");
  await expect(actions.nth(0)).toContainText("page 1, Dimensioned Plot Plan");
  await expect(actions.nth(1)).toContainText("drainage");
  await expect(actions.nth(1)).toContainText("page 1, Dimensioned Plot Plan");
  await expect(actions.nth(2)).toContainText("electrical load calculations");
  await expect(actions.nth(2)).toContainText(
    "page 1, conditional checklist item",
  );
  await expect(page.locator("#journeyEvidenceActionsReview")).toContainText(
    /AI-assisted/i,
  );
  await expect(page.locator("#journeyEvidenceActionsReview")).toContainText(
    /review.pending/i,
  );
  await expect(page.locator("#journeyEvidenceActionsReview")).toContainText(
    /not human.reviewed/i,
  );

  const questions = summary.locator("#journeyEvidenceQuestionsList > li");
  await expect(questions).toHaveCount(3);
  await expect(questions.nth(0)).toContainText("solar plans");
  await expect(questions.nth(1)).toContainText("fire sprinkler plans");
  await expect(questions.nth(2)).toContainText("flood zone");

  const sources = summary.locator("#journeyEvidenceSourcesList > div");
  await expect(sources).toHaveCount(6);
  await expect(summary.locator(".journey-evidence-sources")).toContainText(
    "future-state simulation only",
  );
  await expect(summary.locator(".journey-evidence-sources")).toContainText(
    "Gov. Code § 66317",
  );
  await expect(summary.locator(".journey-evidence-sources")).toContainText(
    "City of Woodland",
  );
  await expect(summary.locator(".journey-evidence-sources")).toContainText(
    "Yolo County",
  );
  await expect(
    summary.locator(
      '#journeyEvidenceSourcesList a[href*="woodland-preapproved-adu-evidence.json"]',
    ),
  ).toBeVisible();

  await expect(summary.locator(".journey-evidence-boundary")).toContainText(
    "synthetic",
  );
  await expect(summary.locator(".journey-evidence-boundary")).toContainText(
    "does not",
  );
  await expect(summary.locator(".journey-evidence-meta")).toContainText(
    JOURNEY_ID,
  );
  await expect(summary.locator(".journey-evidence-meta")).toContainText(
    JOURNEY_VERSION,
  );

  await page.locator("#printJourneySummary").click();
  await expect.poll(
    () => page.evaluate(() => window.__permitBearingsPrintCalls),
  ).toBe(1);
  await expectBrowserStorageEmpty(page);
});

test("print media isolates the evidence summary without horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 816, height: 1056 });
  await page.goto(VALID_PACKET_PATH);
  await expect(page.locator("#journeyEvidenceSummary")).toBeVisible();
  await page.emulateMedia({ media: "print" });

  await expect(page.locator("#journeyEvidenceSummary")).toBeVisible();
  for (const selector of [
    ".site-header",
    ".readiness-hero",
    "#journeyEntrySummary",
    "#packetCover",
    "#dataLoadError",
    "#readinessOutput",
    "#readinessMethod",
    ".site-footer",
    "#printJourneySummary",
  ]) {
    await expect(page.locator(selector)).toBeHidden();
  }
  await expectNoDocumentOverflow(page);
});

test("Spanish journey handoff declares its language and preserves the English staff question", async ({
  page,
}) => {
  await openCanonicalJourney(page);
  await page.locator("#langToggle").click();

  const handoff = page.locator(".journey-handoff");
  await expect(handoff).toHaveAttribute("lang", "es");
  await expect(page.locator("#journeyGateOutcome p[lang='en']")).toHaveText(
    "Is this packet using a City of Woodland preapproved ADU plan?",
  );
  await expect(page.locator("#journeyGateHeading")).toHaveText(
    "Explore una simulación futura del paquete",
  );
  await expect(handoff.locator(".program-availability")).toHaveAttribute(
    "lang",
    "en",
  );
});

test("editing the canonical screening facts clears the result and packet handoff", async ({
  page,
}) => {
  await openCanonicalJourney(page);
  await page.locator(
    'input[name="unpermitted_existing"][value="yes"]',
  ).check();

  await expect(page.locator("#resultsHeading")).toHaveCount(0);
  await expect(page.locator("#journeyGateHeading")).toHaveCount(0);
  await expect(page.locator("#results")).toBeEmpty();
  await expect(page).toHaveURL(/\/check\.html$/);
  await expectBrowserStorageEmpty(page);
});

const invalidPacketEntries = [
  { label: "direct", path: "/prepare.html" },
  {
    label: "missing version",
    path: `/prepare.html?journey=${JOURNEY_ID}`,
  },
  {
    label: "duplicate version",
    path: `${VALID_PACKET_PATH}&version=${JOURNEY_VERSION}`,
  },
  {
    label: "extra parameter",
    path: `${VALID_PACKET_PATH}&sample=adu`,
  },
  {
    label: "wrong version",
    path: `/prepare.html?journey=${JOURNEY_ID}&version=9.9.9`,
  },
];

for (const entry of invalidPacketEntries) {
  test(`${entry.label} packet entry fails closed`, async ({ page }) => {
    await page.goto(entry.path);
    await expect(page.locator("#entryHoldHeading")).toBeVisible();
    await expect(page.locator("#journeyEntrySummary")).toBeHidden();
    await expect(page.locator("#journeyEvidenceSummary")).toBeHidden();
    await expect(page.locator("#printJourneySummary")).toBeHidden();
    await expect(page.locator("#packetCover")).toBeHidden();
    await expect(page.locator("#readinessMethod")).toBeHidden();
    await expect(page.locator("#readinessVerdictHeading")).toHaveCount(0);
    await expectBrowserStorageEmpty(page);
  });
}

for (const viewport of [
  { label: "320px", width: 320, height: 720 },
  { label: "390px", width: 390, height: 844 },
]) {
  test(`valid packet reflows at ${viewport.label} without WCAG violations`, async ({
    page,
  }) => {
    await page.setViewportSize({
      width: viewport.width,
      height: viewport.height,
    });
    await page.goto(VALID_PACKET_PATH);
    await expect(page.locator("#journeyEntrySummary")).toBeVisible();
    await expect(page.locator("#readinessVerdictHeading")).toBeVisible();
    await expectNoDocumentOverflow(page);
    await expectNoAutomatedWcagViolations(page);
  });
}

test("populated applicant result reflows without automated WCAG violations", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openCanonicalJourney(page);
  await expectNoDocumentOverflow(page);
  await expectNoAutomatedWcagViolations(page);
});

for (const viewport of [
  { label: "320px", width: 320, height: 720 },
  { label: "390px", width: 390, height: 844 },
]) {
  test(`support disclosures are keyboard-expandable and reflow at ${viewport.label}`, async ({
    page,
  }) => {
    await page.setViewportSize({width: viewport.width, height: viewport.height});
    await page.goto("/check.html");

    const clock = page.locator("#clocks");
    await expectClosedDisclosure(clock, clock.locator(".optional-tool-body"));
    await page.locator("#jurisInput").fill("Alameda (Alameda Co.)");
    const profile = page.locator("#jurisdictionProfile");
    await expectClosedDisclosure(
      profile,
      profile.locator(".jurisdiction-profile-body"),
    );
    await expectNoDocumentOverflow(page);
    await expectNoAutomatedWcagViolations(page);

    await expandDisclosureWithKeyboard(clock, "Enter");
    await expect(clock.locator(".optional-tool-body")).toBeVisible();
    await expandDisclosureWithKeyboard(profile, "Space");
    await expect(profile.locator(".jurisdiction-profile-body")).toBeVisible();
    await expectNoDocumentOverflow(page);
    await expectNoAutomatedWcagViolations(page);
  });
}

test("candidate route precedes supporting answers and statewide receipt in reading order", async ({
  page,
}) => {
  await openCanonicalJourney(page);

  expect(await page.evaluate(() => {
    const route = document.querySelector(".result-route");
    const facts = document.querySelector(".result-cover-sheet");
    const receipt = document.querySelector("#statewideOrientation");
    if (!route || !facts || !receipt) return null;
    return {
      routeBeforeFacts: Boolean(
        route.compareDocumentPosition(facts) & Node.DOCUMENT_POSITION_FOLLOWING,
      ),
      routeBeforeReceipt: Boolean(
        route.compareDocumentPosition(receipt) & Node.DOCUMENT_POSITION_FOLLOWING,
      ),
      factsBeforeReceipt: Boolean(
        facts.compareDocumentPosition(receipt) & Node.DOCUMENT_POSITION_FOLLOWING,
      ),
    };
  })).toEqual({
    routeBeforeFacts: true,
    routeBeforeReceipt: true,
    factsBeforeReceipt: true,
  });

  const ruleDetails = page.locator("#results details.rule-details");
  await expect(ruleDetails).not.toHaveCount(0);
  expect(await ruleDetails.evaluateAll(details =>
    details.every(disclosure => !disclosure.open)
  )).toBe(true);
  const route = page.locator(".result-route").first();
  await expect(route.locator(".result-title-visible")).toBeVisible();
  await expect(route.locator(".result-consequence")).toBeVisible();
  await expect(route.locator(".source-basis")).toBeVisible();
  await expect(route.locator("details.rule-details > summary")).toBeVisible();

  const clock = page.locator("#clocks");
  await expect.poll(() => clock.evaluate(element => element.open)).toBe(false);
  await route.locator("details.rule-details > summary").click();
  await page.locator('#results a[href="#clocks"]').first().click();
  await expect.poll(() => clock.evaluate(element => element.open)).toBe(true);
});

test("sample supporting answers stay collapsed until Edit restores intake focus", async ({
  page,
}) => {
  await openCanonicalJourney(page);
  const facts = page.locator("details.result-cover-sheet");
  await expectClosedDisclosure(facts, facts.locator(".result-support-body"));

  await expandDisclosureWithKeyboard(facts, "Enter");
  await expect(facts.locator(".result-support-body")).toBeVisible();
  await facts.locator(".edit-answers").click();
  await expect(page.locator("#intake")).toBeVisible();
  await expect(page.locator("#screenHeading")).toBeFocused();
});

test("decision boundary distinguishes candidate, unknown, and no-route results", async ({
  page,
}) => {
  await openCanonicalJourney(page);
  const boundary = page.locator("#decisionBoundary");
  await expect(page.locator("#resultsHeading + #decisionBoundary")).toHaveCount(1);
  await expect(boundary).toHaveAttribute("data-boundary-state", "candidate");
  await expect(boundary.locator("[data-boundary-part='shows'] dd")).toHaveText(
    "A candidate route to discuss with staff. It is not an approval.",
  );
  await expect(boundary.locator("[data-boundary-part='unconfirmed'] dd")).toHaveText(
    "Property facts, local rules, and a complete application checklist.",
  );
  await expect(page.locator(".result-route .result-title-visible")).toHaveText(
    "Candidate route to discuss with staff.",
  );
  await expect(page.locator(".result-route .candidate-route-record")).toContainText(
    "ADU — ministerial review and application timelines",
  );
  await expect(page.locator("#statewideOrientation .statewide-route-list strong"))
    .toHaveText("Candidate route to discuss with staff");
  await expect(page.locator("#statewideOrientation .statewide-route-list li"))
    .toContainText("ADU — ministerial review and application timelines");

  await page.locator(
    'input[name="primary_dwelling_status"][value="unknown"]',
  ).check();
  await page.locator("#t-submit").click();
  await expect(boundary).toHaveAttribute("data-boundary-state", "unknown");
  await expect(boundary.locator("[data-boundary-part='shows'] dd")).toHaveText(
    "Staff review is needed before this prototype can show a candidate route.",
  );

  await page.goto("/check.html");
  await page.locator("#jurisInput").fill("Woodland (Yolo Co.)");
  await page.locator('input[name="project_type"][value="two_unit"]').check();
  const noRouteFacts = {
    in_urbanized_area: "yes",
    sf_zone: "yes",
    demolishes_protected_housing: "no",
    tenant_occupied_last_3_years: "yes",
    ellis_withdrawal_last_15_years: "no",
    two_unit_contributing_historic_location: "no",
    two_unit_individually_listed_historic_property: "no",
    on_protected_site: "no",
  };
  for (const [name, value] of Object.entries(noRouteFacts)) {
    await page.locator(`input[name="${name}"][value="${value}"]`).check();
  }
  await page.locator("#t-submit").click();
  await expect(boundary).toHaveAttribute("data-boundary-state", "no-route");
  await expect(boundary.locator("[data-boundary-part='shows'] dd")).toHaveText(
    "No candidate route was identified in this limited rule set.",
  );
  await expect(boundary.locator("[data-boundary-part='next'] dd")).toContainText(
    "Woodland (Yolo Co.) staff",
  );
});

test("decision boundary holds affected candidate guidance for source review", async ({
  page,
}) => {
  await serveSourceStateFixture(page, "changed", "ca-gov-66317");
  await page.goto("/check.html?sample=adu");
  const boundary = page.locator("#decisionBoundary");
  await expect(boundary).toHaveAttribute(
    "data-boundary-state",
    "source-review-hold",
  );
  await expect(boundary.locator("[data-boundary-part='shows'] dd")).toHaveText(
    "Source review is needed. Guidance for affected records is withheld.",
  );
  await expect(boundary.locator("[data-boundary-part='unconfirmed'] dd")).toHaveText(
    "One or more matching source records need a source check before they can support guidance.",
  );
  await expect(page.locator(".result-route")).toHaveClass(/unverified/);
});

test("multi-route result headings expose distinct route identities", async ({
  page,
}) => {
  await page.goto("/check.html");
  await page.locator("#jurisInput").fill("Woodland (Yolo Co.)");
  await page.locator('input[name="project_type"][value="adu"]').check();
  const conversionFacts = {
    primary_dwelling_status: "existing_single_family",
    adu_project_form: "conversion",
    unpermitted_existing: "yes",
  };
  for (const [name, value] of Object.entries(conversionFacts)) {
    await page.locator(`input[name="${name}"][value="${value}"]`).check();
  }
  await page.locator("#t-submit").click();

  const routeCards = page.locator("[data-result-group='route']");
  await expect(routeCards).toHaveCount(2);
  await expect(page.locator(
    '[data-rule-id="adu-ministerial-review"] .result-title',
  )).toHaveAccessibleName(
    "Candidate route to discuss with staff. Route record: ADU — ministerial review and application timelines",
  );
  await expect(page.locator(
    '[data-rule-id="adu-unpermitted-legalization"] .result-title',
  )).toHaveAccessibleName(
    "Candidate route to discuss with staff. Route record: ADU — possible legalization of a unit built before 2020",
  );
  await expectNoAutomatedWcagViolations(page);
});

test("statewide orientation handoff works across city, county, and local-layer profiles", async ({
  page,
}) => {
  await page.addInitScript(() => {
    window.__permitBearingsPrintCalls = 0;
    window.print = () => {
      window.__permitBearingsPrintCalls += 1;
    };
  });
  const profiles = [
    { display: "Alameda (Alameda Co.)", slug: "alameda", local: "false" },
    { display: "Los Angeles County", slug: "los-angeles-county", local: "false" },
    { display: "Mountain House (San Joaquin Co.)", slug: "mountain-house", local: "false" },
    { display: "Davis (Yolo Co.)", slug: "davis", local: "true" },
  ];

  for (const profile of profiles) {
    await page.goto("/check.html?sample=adu");
    await page.locator("#jurisInput").fill(profile.display);
    await page.locator("#t-submit").click();
    const receipt = page.locator("#statewideOrientation");
    await expect(receipt).toBeVisible();
    await expect(receipt).toHaveAttribute("data-jurisdiction", profile.slug);
    await expect(receipt).toHaveAttribute("data-local-layer", profile.local);
    await expect(receipt).toContainText("541 California cities and counties");
    await expect(receipt.locator(".statewide-route-list > li")).not.toHaveCount(0);
    await expect(receipt).toContainText("Orientation only");
    await expectBrowserStorageEmpty(page);
  }

  await page.locator("#statewideOrientation > summary").click();
  await page.locator(".print-statewide-orientation").click();
  await expect.poll(
    () => page.evaluate(() => window.__permitBearingsPrintCalls),
  ).toBe(1);
  await page.emulateMedia({ media: "print" });
  await expect(page.locator("#statewideOrientation")).toBeVisible();
  await expect(page.locator(".site-header")).toBeHidden();
  await expect(page.locator("#intake")).toBeHidden();
  await expect(page.locator(".statewide-print-action")).toBeHidden();
  await expectNoDocumentOverflow(page);
});

test("jurisdiction coverage profile separates statewide, local, and HCD evidence", async ({
  page,
}) => {
  const profiles = [
    {
      display: "Albany (Alameda Co.)",
      slug: "albany",
      local: "false",
      hcd: "0",
      text: "No linked records in this dataset",
    },
    {
      display: "Alameda (Alameda Co.)",
      slug: "alameda",
      local: "false",
      hcd: "1",
      text: "1 linked public record",
    },
    {
      display: "Davis (Yolo Co.)",
      slug: "davis",
      local: "true",
      hcd: null,
      text: "1 limited jurisdiction-scoped source record",
    },
    {
      display: "Los Angeles County",
      slug: "los-angeles-county",
      local: "false",
      hcd: null,
      text: "Not encoded",
    },
  ];

  for (const profile of profiles) {
    await page.goto("/check.html");
    await expect(page.locator("#t-submit")).toBeEnabled();
    await page.locator("#jurisInput").fill(profile.display);
    const card = page.locator("#jurisdictionProfile");
    await expect(card).toBeVisible();
    await expect(card).toHaveAttribute("data-jurisdiction", profile.slug);
    await expect(card).toHaveAttribute("data-local-layer", profile.local);
    await expect(card).toContainText("17 bounded candidate-rule records");
    await expect(card).toContainText(profile.text);
    if (profile.hcd !== null) {
      await expect(card).toHaveAttribute("data-hcd-record-count", profile.hcd);
    }
    await expectBrowserStorageEmpty(page);
  }

  const zeroProfile = page.locator("#jurisdictionProfile");
  await page.locator("#jurisInput").fill("Albany (Alameda Co.)");
  await expect(zeroProfile).toContainText("This is not evidence of compliance");
  await page.locator("#jurisInput").fill("Alameda (Alameda Co.)");
  await zeroProfile.locator(":scope > summary").click();
  await zeroProfile.locator(".jurisdiction-profile-body details > summary").click();
  await expect(zeroProfile.locator(".jurisdiction-profile-letter-list")).toBeVisible();
  const hcdLink = zeroProfile.locator(
    ".jurisdiction-profile-letter-list a",
  ).first();
  await expect(hcdLink).toHaveAccessibleName(
    /HCD record for Alameda \(Alameda Co\.\); Technical Assistance Letter; 2021-11-29; Housing Element Law; HAU21-014/,
  );
  const summaryHeight = await zeroProfile.locator(":scope > summary").evaluate(
    summary => summary.getBoundingClientRect().height,
  );
  expect(summaryHeight).toBeGreaterThanOrEqual(44);
  await page.locator("#langToggle").click();
  await expect(zeroProfile).toHaveAttribute("lang", "es");
  await expect(zeroProfile).toContainText("Perfil de cobertura estatal");
  await expect(zeroProfile.locator(".jurisdiction-profile-letter-list [lang='en']"))
    .not.toHaveCount(0);
  await page.locator("#jurisInput").fill("");
  await expect(zeroProfile).toBeHidden();
  expect(await zeroProfile.evaluate(profile => ({...profile.dataset}))).toEqual({});
  await page.locator("#jurisInput").fill("Not a California jurisdiction");
  await expect(zeroProfile).toBeHidden();
  expect(await zeroProfile.evaluate(profile => ({...profile.dataset}))).toEqual({});
  await expectNoDocumentOverflow(page);
  await expectNoAutomatedWcagViolations(page);
});

test("coverage profile holds statewide inventory when a source changes", async ({
  page,
}) => {
  await serveSourceStateFixture(page, "changed", "ca-gov-66321");
  await page.goto("/check.html");
  await page.locator("#jurisInput").fill("Albany (Alameda Co.)");

  const profile = page.locator("#jurisdictionProfile");
  await expect(profile).toHaveAttribute("data-statewide-review-hold", "5");
  await expect(profile).toContainText(
    "5 of 17 candidate-rule records need a new source check",
  );
  await expect(profile).toContainText("This inventory is on a source-review hold");
  await expect(profile).toContainText("Do not treat it as ready to screen");
  await expectBrowserStorageEmpty(page);
  await expectNoAutomatedWcagViolations(page);
});

test("coverage profile holds an affected local source record", async ({ page }) => {
  await serveSourceStateFixture(page, "changed", "davis-adu-handout-2026");
  await page.goto("/check.html");
  await page.locator("#jurisInput").fill("Davis (Yolo Co.)");

  const profile = page.locator("#jurisdictionProfile");
  const localRecord = profile.locator(
    ".jurisdiction-profile-local-records li[data-rule-id='davis-local-adu-process']",
  );
  await expect(profile).toHaveAttribute("data-local-review-hold", "1");
  await expect(profile).toContainText("1 local source record needs a new check");
  await expect(profile).toContainText("local inventory is on a source-review hold");
  await expect(localRecord).toHaveAttribute("data-source-status", "stale");
  await expect(localRecord).toContainText("Source evidence needs a new check");
  await expectBrowserStorageEmpty(page);
  await expectNoAutomatedWcagViolations(page);
});

test("mobile evidence tables render as labeled records without page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/evidence.html");
  await expect(page.locator("#sourceTable tbody tr").first()).toBeVisible();
  await expect(page.locator("#sourceTable td[data-label='Source']").first()).toHaveCSS(
    "display",
    "grid",
  );
  await expectNoDocumentOverflow(page);
});

test("rule verification ledger distinguishes machine linking from named review", async ({
  page,
}) => {
  await page.goto("/evidence.html");
  await expect(page.locator("#verificationScore")).toHaveText(
    `0/${DEMO_DATA.rules.length}`,
  );
  await expect(page.locator("#verificationLine")).toHaveText(
    `${DEMO_DATA.rules.length} machine-linked; 0 human-reviewed; `
      + "0 jurisdiction-approved.",
  );
  const rows = page.locator("#ruleTable tbody tr");
  await expect(rows).toHaveCount(DEMO_DATA.rules.length);
  await expect(
    rows.locator('td[data-label="Interpretation review"]'),
  ).toHaveCount(DEMO_DATA.rules.length);
  await expect(
    rows.locator('td[data-label="Interpretation review"]').first(),
  ).toContainText("Machine-linked · no named review");
  await expect(
    page.locator('a[href="data/validation/rule-verification.json"]'),
  ).toBeVisible();
  await expectNoAutomatedWcagViolations(page);
});

test("reviewed source-state receipt is visible and separate from rehearsal", async ({
  page,
}) => {
  await page.goto("/evidence.html");

  await expect(page.locator("#sourceSnapshotSummary")).toHaveText(
    "Checked August 3, 2026: 19 unchanged; 0 changed; 0 could not be "
      + "re-fetched. This repository-adopted receipt is the source-state "
      + "overlay used by the applicant guide.",
  );
  await expect(page.locator("#sourceSnapshotRun")).toHaveAttribute(
    "href",
    "https://github.com/ChelseaKR/permit-pathways/actions/runs/30835371749",
  );
  await expect(page.locator("#sourceImpactQueue")).toContainText(
    "No source-triggered review queue is open.",
  );
  await expect(
    page.locator("#sourceTable .badge", { hasText: "unchanged in snapshot" }),
  ).toHaveCount(19);

  await page.locator("#simBtn").click();
  await expect(page.locator("#simNote")).toBeVisible();
  await expect(page.locator("#sourceSnapshotSummary")).toContainText(
    "19 unchanged; 0 changed",
  );
  await expect(page.locator("#sourceImpactQueue")).toContainText(
    "No source-triggered review queue is open.",
  );
  await expectBrowserStorageEmpty(page);
});

test("changed source receipt opens the exact visible review queue", async ({
  page,
}) => {
  await serveSourceStateFixture(page, "changed", "ca-gov-66317");
  await page.goto("/evidence.html");

  await expect(page.locator("#sourceSnapshotSummary")).toContainText(
    "18 unchanged; 1 changed; 0 could not be re-fetched",
  );
  await expect(page.locator("#sourceImpactQueue")).toContainText(
    "Review queue open.",
  );
  await expect(page.locator("#sourceImpactQueue")).toContainText(
    "1 rule record and 10 structured scenarios",
  );
  await expect(page.locator("#sourceImpactQueue")).toContainText(
    "the Woodland route-to-packet handoff",
  );
  const sourceRow = page.locator("#sourceTable tbody tr", {
    hasText: "Gov. Code § 66317",
  });
  await expect(sourceRow).toContainText("changed · review required");
  await expectNoAutomatedWcagViolations(page);
  await expectBrowserStorageEmpty(page);
});

test("unverifiable source receipt warns without staling dependents", async ({
  page,
}) => {
  await serveSourceStateFixture(page, "unverifiable", "ca-gov-66317");
  await page.goto("/evidence.html");

  await expect(page.locator("#sourceSnapshotSummary")).toContainText(
    "18 unchanged; 0 changed; 1 could not be re-fetched",
  );
  await expect(page.locator("#sourceImpactQueue")).toContainText(
    "No source-triggered review queue is open.",
  );
  await expect(page.locator("#sourceImpactQueue")).toContainText(
    "Watch warning.",
  );
  const sourceRow = page.locator("#sourceTable tbody tr", {
    hasText: "Gov. Code § 66317",
  });
  await expect(sourceRow).toContainText("could not re-fetch");
  const routeRow = page.getByRole("row", {
    name: /^ADU ministerial review and application timelines statewide/,
  });
  await expect(routeRow).toContainText("within review window");
  await expectNoAutomatedWcagViolations(page);
  await expectBrowserStorageEmpty(page);
});

test("external evidence gate stays visibly pending without success claims", async ({
  page,
}) => {
  await page.goto("/evidence.html");
  const gate = page.locator(".flagship-evidence-gate");

  await expect(gate).toBeVisible();
  await expect(gate.locator("h2")).toHaveText("Prepared, not run");
  await expect(gate.locator(".evidence-gate-status")).toHaveText([
    "Not run",
    "Not run",
    "Pending",
  ]);
  await expect(gate).toContainText("No external outcome is claimed");
  await expect(gate).toContainText("No applicant or practitioner session");
  await expect(gate).toContainText("No written next step");
  await expect(gate.locator('a[href$="woodland-flagship-gate.json"]')).toBeVisible();
  await expect(gate.locator('a[href$="woodland-content-review.json"]')).toBeVisible();
  await expect(gate.locator('a[href$="woodland-manual-evidence.json"]')).toBeVisible();
  await expect(
    gate.locator('a[href$="woodland-participant-sessions.json"]'),
  ).toBeVisible();
  await expect(
    gate.locator('a[href$="woodland-source-change-rehearsal.json"]'),
  ).toBeVisible();
  await expect(
    gate.getByRole("link", { name: "execution and claim protocol" }),
  ).toHaveAttribute(
    "href",
    "https://github.com/ChelseaKR/permit-pathways/blob/main/docs/VALIDATION-EVIDENCE.md",
  );
  await expectNoDocumentOverflow(page);
  await expectNoAutomatedWcagViolations(page);
  await expectBrowserStorageEmpty(page);
});

const HCD_VALIDATION = JSON.parse(
  readFileSync(
    resolve(__dirname, "../data/conformance/hcd-validation-santa-clara.json"),
    "utf8",
  ),
);
const CONFORMANCE_CHECKS = JSON.parse(
  readFileSync(resolve(__dirname, "../data/conformance/checks.json"), "utf8"),
);

// demo.js renders interface copy through uiText(), which drops em dashes for
// readability. Compare against the same transformation so the assertion is
// about the check's wording rather than its punctuation.
function asRendered(value) {
  return String(value).replace(/\s*—\s*/g, " ");
}

async function screenOrdinanceText(page, text) {
  await page.fill("#ordText", text);
  await page.click("#scanBtn");
  await expect(page.locator("#scanStatus")).not.toBeEmpty();
  return page.locator("#scanResults .card");
}

// The HCD re-derivation is this screen's headline evidence, and
// tests/test_conformance_browser_parity.py holds the browser engine to the
// validated Python scanner's exact output. This asserts the last link: that
// review.html, as served, runs that engine and renders the current
// checks.json text for each flag rather than a stale copy of it.
for (const provision of HCD_VALIDATION.provisions) {
  test(`review screen reproduces ${provision.hcd_finding}`, async ({ page }) => {
    await page.goto("/review.html");
    const cards = await screenOrdinanceText(page, provision.text);

    expect(provision.expected_checks.length).toBeGreaterThan(0);
    for (const checkId of provision.expected_checks) {
      const check = CONFORMANCE_CHECKS.find(entry => entry.check_id === checkId);
      if (!check) throw new Error(`unknown check in fixture: ${checkId}`);
      const matching = cards.filter({
        has: page.getByRole("heading", { name: check.title }),
      });
      // A provision can trip the same check more than once; every card the
      // screen renders for it must carry the check's current wording.
      const rendered = await matching.count();
      expect(rendered).toBeGreaterThan(0);
      for (let index = 0; index < rendered; index += 1) {
        await expect(matching.nth(index)).toContainText(
          asRendered(check.state_law),
        );
        await expect(matching.nth(index)).toContainText(
          asRendered(check.hcd_precedent),
        );
      }
    }
  });
}

test("conformant control text stays quiet on the review screen", async ({ page }) => {
  await page.goto("/review.html");
  const cards = await screenOrdinanceText(page, HCD_VALIDATION.control.text);
  await expect(cards).toHaveCount(0);
  await expect(page.locator("#scanResults")).toContainText(
    "No candidate provisions flagged",
  );
  await expect(page.locator("#scanResults")).toContainText(
    "not a certification of compliance",
  );
  await expectNoAutomatedWcagViolations(page);
  await expectBrowserStorageEmpty(page);
});

test("AI assistance stays inert until requested and degrades to the static form without the service", async ({
  page,
}) => {
  const offOrigin = [];
  const baseHost = new URL(test.info().project.use.baseURL).host;
  page.on("request", request => {
    if (new URL(request.url()).host !== baseHost) offOrigin.push(request.url());
  });
  // No service is reachable during this suite: abort every off-origin request
  // the way a closed port would, so the page must take its fallback path
  // whatever candidates the meta tag lists.
  await page.route(url => new URL(url).host !== baseHost, route => route.abort("connectionrefused"));
  await page.goto("/check.html");
  const candidates = (await page.getAttribute('meta[name="permit-ai-service"]', "content"))
    .split(",").map(s => s.trim()).filter(Boolean);

  const panel = page.locator("#aiAssistDetails");
  await expectClosedDisclosure(panel, panel.locator("#aiEnable"));
  await expect(page.locator("#aiDescription")).toHaveCount(0);
  expect(offOrigin).toEqual([]);
  await expectNoAutomatedWcagViolations(page);

  await expandDisclosureWithKeyboard(panel, "Enter");
  await page.locator("#aiEnable").click();
  await expect(page.locator("#aiStatus")).toContainText("need the Permit Bearings AI service running");
  await expect(page.locator("#aiDescription")).toHaveCount(0);
  expect(offOrigin.filter(url => url.endsWith("/health"))).toHaveLength(candidates.length);
  expect(offOrigin.every(url => candidates.some(c => url.startsWith(c)))).toBe(true);
  await expect(page.locator("#aiEnable")).toBeEnabled();
  await expectNoAutomatedWcagViolations(page);

  // The structured form is untouched and still screens deterministically.
  await page.locator("#jurisInput").fill("Davis (Yolo Co.)");
  await page.locator('input[name="project_type"][value="jadu"]').check();
  await page.locator('input[name="primary_dwelling_status"][value="existing_single_family"]').check();
  await page.locator('input[name="unpermitted_existing"][value="no"]').check();
  await page.locator("#t-submit").click();
  await expect(page.locator("#resultsHeading")).toBeVisible();
  await expect(page.locator("#aiResultPanel")).toHaveCount(0);
  expect(offOrigin).toHaveLength(candidates.length);

  await page.locator("#langToggle").click();
  await expect(page.locator("#aiAssistHeading")).toHaveText("Describa su proyecto con sus propias palabras");
  await expectNoDocumentOverflow(page);
});
