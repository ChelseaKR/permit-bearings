/**
 * Run the browser unit suite and report real coverage of `assets/demo.js`.
 *
 * Why this exists: `assets/demo.js` is 5,255 lines carrying the second
 * implementation of this product's rule logic, and until now no coverage gate
 * of any kind applied to it. `--cov=permit_pathways` measures one Python
 * package; the 85 percent figure never described this file in either
 * direction.
 *
 * Node's own `--experimental-test-coverage` reports nothing here, because the
 * suite evaluates the shipped file through `node:vm` rather than importing it,
 * and that indirection is deliberate: the alternative is testing a copy. Raw
 * V8 coverage does see it, so this reads `NODE_V8_COVERAGE` output directly.
 * No new dependency; the numbers come from V8.
 *
 * Metrics, and what they mean:
 *   functions  fraction of the file's functions entered at least once
 *   lines      fraction of non-blank, non-comment-only lines with at least one
 *              byte inside a range V8 recorded as executed
 *
 * A percentage here is coverage, which is not correctness. It says which lines
 * ran, not that what they did was right.
 *
 * Usage: node scripts/browser-coverage.mjs [--min-lines N] [--min-functions N]
 */

import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const TARGET = "assets/demo.js";

function parseArgs(argv) {
  // Floors are set at what the suite actually reaches, as a ratchet. They
  // are far below the Python package's 85 percent and are not presented as
  // equivalent: this file had no coverage gate at all until now.
  const options = { minLines: 20, minFunctions: 17 };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--min-lines") options.minLines = Number(argv[++i]);
    else if (argv[i] === "--min-functions") options.minFunctions = Number(argv[++i]);
    else {
      console.error(`unknown argument: ${argv[i]}`);
      process.exit(2);
    }
  }
  for (const [name, value] of Object.entries(options)) {
    if (!Number.isFinite(value) || value < 0 || value > 100) {
      console.error(`${name} must be a percentage between 0 and 100`);
      process.exit(2);
    }
  }
  return options;
}

/** Merge every V8 coverage file into one script record for the target. */
function targetCoverage(directory) {
  const collected = [];
  for (const name of readdirSync(directory)) {
    if (!name.endsWith(".json")) continue;
    const payload = JSON.parse(readFileSync(join(directory, name), "utf8"));
    for (const script of payload.result ?? []) {
      if (script.url && script.url.endsWith(TARGET)) collected.push(script);
    }
  }
  return collected;
}

/**
 * Byte-level executed map.
 *
 * V8 emits each function's outermost range first and its nested blocks after,
 * so applying ranges in order lets an uncovered inner block correctly override
 * the covered function body around it.
 */
function executedBytes(scripts, length) {
  const executed = new Uint8Array(length);
  for (const script of scripts) {
    for (const fn of script.functions) {
      for (const range of fn.ranges) {
        const value = range.count > 0 ? 1 : 0;
        const end = Math.min(range.endOffset, length);
        for (let offset = range.startOffset; offset < end; offset += 1) {
          executed[offset] = value;
        }
      }
    }
  }
  return executed;
}

/** Lines that can meaningfully be covered: not blank, not comment-only. */
function countableLines(source) {
  const lines = [];
  let offset = 0;
  for (const text of source.split("\n")) {
    const trimmed = text.trim();
    const countable =
      trimmed !== "" &&
      !trimmed.startsWith("//") &&
      !trimmed.startsWith("*") &&
      !trimmed.startsWith("/*") &&
      trimmed !== "}" &&
      trimmed !== "};" &&
      trimmed !== "*/";
    lines.push({ start: offset, end: offset + text.length, countable });
    offset += text.length + 1;
  }
  return lines;
}

function report(scripts, source) {
  const executed = executedBytes(scripts, source.length);
  const lines = countableLines(source);
  let coveredLines = 0;
  let totalLines = 0;
  const uncovered = [];
  lines.forEach((line, index) => {
    if (!line.countable) return;
    totalLines += 1;
    let hit = false;
    for (let offset = line.start; offset < line.end; offset += 1) {
      if (executed[offset]) {
        hit = true;
        break;
      }
    }
    if (hit) coveredLines += 1;
    else uncovered.push(index + 1);
  });

  const names = new Map();
  for (const script of scripts) {
    for (const fn of script.functions) {
      const key = `${fn.functionName}@${fn.ranges[0].startOffset}`;
      names.set(key, (names.get(key) ?? 0) + (fn.ranges[0].count > 0 ? 1 : 0));
    }
  }
  const totalFunctions = names.size;
  const coveredFunctions = [...names.values()].filter((count) => count > 0).length;

  return {
    lines: { covered: coveredLines, total: totalLines, uncovered },
    functions: { covered: coveredFunctions, total: totalFunctions },
  };
}

const percent = (covered, total) => (total === 0 ? 0 : (covered / total) * 100);

function main() {
  const options = parseArgs(process.argv.slice(2));
  const coverageDirectory = mkdtempSync(join(tmpdir(), "permit-browser-coverage-"));
  try {
    const run = spawnSync(
      process.execPath,
      ["--test", "tests/browser/*.test.mjs"],
      {
        cwd: ROOT,
        stdio: "inherit",
        env: { ...process.env, NODE_V8_COVERAGE: coverageDirectory },
      },
    );
    if (run.status !== 0) {
      console.error("browser unit tests failed; coverage not reported");
      return run.status ?? 1;
    }
    const scripts = targetCoverage(coverageDirectory);
    if (scripts.length === 0) {
      console.error(
        `no V8 coverage recorded for ${TARGET}. The suite did not load the ` +
          "shipped file, so its numbers would describe nothing.",
      );
      return 2;
    }
    const source = readFileSync(join(ROOT, TARGET), "utf8");
    const result = report(scripts, source);
    const linePercent = percent(result.lines.covered, result.lines.total);
    const functionPercent = percent(
      result.functions.covered,
      result.functions.total,
    );
    console.log(
      `\n${TARGET} coverage from the browser unit suite:\n` +
        `  lines     ${linePercent.toFixed(2)}%  ` +
        `(${result.lines.covered}/${result.lines.total}, floor ${options.minLines}%)\n` +
        `  functions ${functionPercent.toFixed(2)}%  ` +
        `(${result.functions.covered}/${result.functions.total}, ` +
        `floor ${options.minFunctions}%)\n` +
        "  Coverage is which lines ran, not that what they did was right.",
    );
    const failures = [];
    if (linePercent < options.minLines) {
      failures.push(
        `line coverage ${linePercent.toFixed(2)}% is below ${options.minLines}%`,
      );
    }
    if (functionPercent < options.minFunctions) {
      failures.push(
        `function coverage ${functionPercent.toFixed(2)}% is below ` +
          `${options.minFunctions}%`,
      );
    }
    if (failures.length) {
      for (const failure of failures) console.error(`browser coverage: ${failure}`);
      return 1;
    }
    console.log("browser coverage: pass");
    return 0;
  } finally {
    rmSync(coverageDirectory, { recursive: true, force: true });
  }
}

process.exit(main());
