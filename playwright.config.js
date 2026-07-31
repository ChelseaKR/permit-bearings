const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests",
  testMatch: "accessibility.spec.js",
  use: {
    baseURL: "http://127.0.0.1:4173",
    browserName: "chromium",
  },
  webServer: {
    command: "node scripts/static-server.mjs 4173",
    url: "http://127.0.0.1:4173/index.html",
    reuseExistingServer: false,
  },
});
