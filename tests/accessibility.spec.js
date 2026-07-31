const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

const pages = [
  "/index.html",
  "/prepare.html",
  "/review.html",
  "/evidence.html",
  "/check.html",
];

async function expectNoDocumentOverflow(page) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);
}

for (const path of pages) {
  test(`${path} has no automated WCAG violations`, async ({ page }) => {
    await page.goto(path);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag2aaa", "wcag21aa", "wcag22aa"])
      .analyze();

    expect(results.violations).toEqual([]);
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
      await expect(page.locator(".mobile-nav a[aria-current='page']")).toHaveCount(1);
      await expectNoDocumentOverflow(page);

      if (viewport.width === 320) {
        const results = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag2aaa", "wcag21aa", "wcag22aa"])
          .analyze();
        expect(results.violations).toEqual([]);
      }
    });
  }
}

test("populated applicant result reflows without automated WCAG violations", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/check.html?sample=adu");
  await expect(page.locator("#resultsHeading")).toBeVisible();
  await expectNoDocumentOverflow(page);

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag2aaa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(results.violations).toEqual([]);
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
