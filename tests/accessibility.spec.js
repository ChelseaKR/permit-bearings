const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

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
  await expect(page.locator("#journeyGateOutcome")).toContainText(
    "Is this packet using a City of Woodland preapproved ADU plan?",
  );

  await yes.check();
  let packetLink = page.locator(
    "#journeyGateOutcome a[href^='prepare.html?journey=']",
  );
  await expect(packetLink).toBeVisible();
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
  await expect(sources).toHaveCount(5);
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
    "Continúe de esta posible vía a la preparación del paquete",
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
