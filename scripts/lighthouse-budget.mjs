import { execFileSync, spawn } from "node:child_process";
import { readFileSync, unlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const pages = [
  "index.html",
  "prepare.html",
  "review.html",
  "evidence.html",
  "check.html",
];
const minimums = {
  accessibility: 1,
  "best-practices": 0.9,
  performance: 0.9,
  seo: 0.9,
};
const server = spawn(process.execPath, ["scripts/static-server.mjs", "4174"], {
  stdio: "ignore",
});

async function waitForServer() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch("http://127.0.0.1:4174/index.html");
      if (response.ok) return;
    } catch {
      // The server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("local Lighthouse server did not start");
}

let failed = false;
try {
  await waitForServer();
  for (const page of pages) {
    const report = join(tmpdir(), `permit-pathways-${page}.json`);
    execFileSync(
      process.execPath,
      [
        "node_modules/lighthouse/cli/index.js",
        `http://127.0.0.1:4174/${page}`,
        "--quiet",
        "--output=json",
        `--output-path=${report}`,
        "--chrome-flags=--headless --no-sandbox",
      ],
      { stdio: "inherit" },
    );
    const result = JSON.parse(readFileSync(report, "utf8"));
    unlinkSync(report);

    for (const [category, minimum] of Object.entries(minimums)) {
      const score = result.categories[category].score;
      console.log(`${page} ${category}: ${score}`);
      if (score < minimum) {
        console.error(`${page} ${category} is below ${minimum}`);
        failed = true;
      }
    }
  }
} finally {
  server.kill();
}

if (failed) process.exit(1);
