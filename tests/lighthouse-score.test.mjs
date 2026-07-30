import assert from "node:assert/strict";
import test from "node:test";

import { median } from "../scripts/lighthouse-score.mjs";

test("median returns the middle score without mutating samples", () => {
  const samples = [0.85, 1, 0.96];

  assert.equal(median(samples), 0.96);
  assert.deepEqual(samples, [0.85, 1, 0.96]);
});

test("median rejects an empty sample", () => {
  assert.throws(() => median([]), /at least one score/);
});
