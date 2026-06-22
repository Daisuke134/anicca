// VSDD guard-rail: the phantom bug lives in the WIRING (was recordDeposit gated on tx status vs on a
// real read-after-write?). A pure-unit test of depositLanded() cannot catch a regression that re-wires
// the call site back to `if (r.status === "success") recordDeposit(...)`. So we assert the SOURCE of
// execute-yield.mjs keeps the guard wired. This is a static contract test, not a runtime one.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "fs";
import { fileURLToPath } from "url";
import path from "path";

const SRC = fs.readFileSync(
  path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../execute-yield.mjs"),
  "utf8",
);

test("execute-yield imports the deposit guard", () => {
  assert.match(SRC, /import\s*\{\s*depositLanded\s*\}\s*from\s*["'].\/lib\/deposit-guard\.mjs["']/);
});

test("deposit cost-basis is gated on `landed` (read-after-write), not on tx status", () => {
  // the recording line must be guarded by the landed flag
  assert.match(SRC, /if\s*\(\s*landed\s*\)\s*recordDeposit/);
  // and the OLD phantom-prone pattern must be gone from the deposit path
  assert.doesNotMatch(SRC, /if\s*\(\s*r\.status\s*===\s*["']success["']\s*\)\s*recordDeposit/);
});

test("recorded basis is the ACTUAL moved amount (liquid - liqAfter), not the blind surplus", () => {
  assert.match(SRC, /recordDeposit\([^)]*Number\(\s*liquid\s*-\s*liqAfter\s*\)\s*\/\s*1e6\s*\)/);
  // liqAfter must be read after the deposit (a balanceOf read assigned to liqAfter exists)
  assert.match(SRC, /const\s+liqAfter\s*=\s*await\s+pub\.readContract/);
});
