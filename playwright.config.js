const { defineConfig } = require("@playwright/test");
const port = process.env.PERMIT_BEARINGS_TEST_PORT || "4173";
const baseURL = `http://127.0.0.1:${port}`;

module.exports = defineConfig({
  testDir: "./tests",
  testMatch: "accessibility.spec.js",
  use: {
    baseURL,
    browserName: "chromium",
  },
  webServer: {
    command: `node scripts/static-server.mjs ${port}`,
    url: `${baseURL}/index.html`,
    reuseExistingServer: false,
  },
});
