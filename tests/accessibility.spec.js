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
  const storage = await page.evaluate(() => ({
    local: Object.keys(localStorage),
    session: Object.keys(sessionStorage),
  }));
  expect(storage).toEqual({ local: [], session: [] });
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
  await expect(page.locator("#readinessMethod")).toBeVisible();
  await expect(page.locator("#readinessVerdictHeading")).toBeVisible();
  await expectBrowserStorageEmpty(page);
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
