import assert from "node:assert/strict";
import { test } from "node:test";
import { shouldReconcile } from "../money-truth-wire.mjs";

test("money truth reconciliation is disabled unless explicitly enabled", () => {
  assert.equal(shouldReconcile({ enabled: "0", lastRunMs: 0, nowMs: 900_000 }), false);
  assert.equal(shouldReconcile({ enabled: undefined, lastRunMs: 0, nowMs: 900_000 }), false);
});

test("money truth reconciliation runs on first wake and then at the interval", () => {
  assert.equal(shouldReconcile({ enabled: "1", lastRunMs: 0, nowMs: 1 }), true);
  assert.equal(shouldReconcile({ enabled: "1", lastRunMs: 100, nowMs: 899_999 }), false);
  assert.equal(shouldReconcile({ enabled: "1", lastRunMs: 100, nowMs: 900_100 }), true);
});

