import { execFileSync, spawn } from "node:child_process";
import { existsSync, readFileSync, unlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { median } from "./lighthouse-score.mjs";

const pages = [
  { label: "index.html", url: "index.html" },
  { label: "prepare.html", url: "prepare.html" },
  { label: "review.html", url: "review.html" },
  { label: "evidence.html", url: "evidence.html" },
  { label: "check.html", url: "check.html" },
  { label: "check-sample", url: "check.html?sample=adu" },
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

function runAudit(page, sample) {
  const report = join(
    tmpdir(),
    `permit-pathways-${page.label}-${process.pid}-${sample}.json`,
  );
  try {
    execFileSync(
      process.execPath,
      [
        "node_modules/lighthouse/cli/index.js",
        `http://127.0.0.1:4174/${page.url}`,
        "--quiet",
        "--output=json",
        `--output-path=${report}`,
        "--chrome-flags=--headless --no-sandbox",
      ],
      { stdio: "inherit" },
    );
    return JSON.parse(readFileSync(report, "utf8"));
  } finally {
    if (existsSync(report)) unlinkSync(report);
  }
}

let failed = false;
try {
  await waitForServer();
  for (const page of pages) {
    const results = [runAudit(page, 1)];
    const firstPerformance = results[0].categories.performance.score;
    if (firstPerformance < minimums.performance) {
      console.log(
        `${page.label} performance first sample ${firstPerformance}; collecting two confirmation samples`,
      );
      results.push(runAudit(page, 2), runAudit(page, 3));
    }

    for (const [category, minimum] of Object.entries(minimums)) {
      const samples = results.map((result) => result.categories[category].score);
      const score = median(samples);
      const sampleDetail =
        samples.length > 1 ? ` (median of ${samples.join(", ")})` : "";
      console.log(`${page.label} ${category}: ${score}${sampleDetail}`);
      if (score < minimum) {
        console.error(`${page.label} ${category} is below ${minimum}`);
        failed = true;
      }
    }
  }
} finally {
  server.kill();
}

if (failed) process.exit(1);
