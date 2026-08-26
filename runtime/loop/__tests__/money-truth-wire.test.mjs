import assert from "node:assert/strict";
import { test } from "node:test";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
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

test("production loop wires verified transfer proof instead of status-only receipt checks", async () => {
  const source = await readFile(join(dirname(fileURLToPath(import.meta.url)), "..", "index.mjs"), "utf8");
  const block = source.slice(source.indexOf("async function reconcileMoneyTruthIfDue()"), source.indexOf("// ── franklin-alwaysact-skill-router", source.indexOf("async function reconcileMoneyTruthIfDue()")));
  assert.match(block, /verifyEvmReceipt/);
  assert.match(block, /verifyLedgerRow/);
  assert.doesNotMatch(block, /receiptStatus/);
  const moneyTruth = await readFile(join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..", "skills", "agent-economy", "lib", "money-truth.mjs"), "utf8");
  assert.match(moneyTruth, /expected_chain_id/);
  assert.match(moneyTruth, /expected_contract/);
  assert.match(moneyTruth, /expected_amount_atomic/);
  assert.match(moneyTruth, /expected_log_index/);
});
