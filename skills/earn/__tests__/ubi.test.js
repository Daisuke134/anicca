import { test } from "node:test";
import assert from "node:assert/strict";
import { buildRecipients, planUbi, alreadyDone } from "../lib/ubi.mjs";

const AI1 = "0x1111111111111111111111111111111111111111";
const AI2 = "0x2222222222222222222222222222222222222222";
const HUMAN = "0x3333333333333333333333333333333333333333";
const SELF = "0x9999999999999999999999999999999999999999";
// A real GATE-0 external line shape (lib/ledger.mjs deriveLine + external:true).
const prof = { wallet: SELF, source: "0xwork", net_usdc: 1.0, tx: "0x" + "a".repeat(64), status: "0x1", external: true, wake: "w1" };

test("buildRecipients dedupes, drops invalid, excludes the sender's own wallet", () => {
  const r = buildRecipients({ childWallets: [AI1, AI2, SELF, "bad"], humanWallets: [HUMAN, AI1], sender: SELF });
  assert.deepEqual(r, [AI1, AI2, HUMAN]); // SELF excluded, AI1 deduped, "bad" dropped
});
test("planUbi: 10% of net split equally across recipients (integer base units)", () => {
  const plan = planUbi({ fundingLine: prof, recipients: [AI1, AI2, HUMAN], cfg: { shareBps: 1000, minPoolUsdc: 0.05 } });
  assert.equal(plan.outcome, "send");
  assert.equal(plan.pool_base, "100000");      // 10% of 1.0 USDC = 0.1 USDC = 100000 base units
  assert.equal(plan.per_base, "33333");        // floor(100000/3)
  assert.equal(plan.dust_base, "1");           // remainder kept by sender
  assert.equal(plan.transfers.length, 3);
});
test("planUbi: a non-profitable (swap / narrate) line never funds UBI", () => {
  const swap = { ...prof, source: "swap-eth-usdc", external: undefined };
  assert.equal(planUbi({ fundingLine: swap, recipients: [AI1] }).outcome, "skipped");
  assert.equal(planUbi({ fundingLine: { ...prof, status: "0x0" }, recipients: [AI1] }).outcome, "skipped");
});
test("planUbi: below-min pool, no recipients, and insufficient balance all skip (no send)", () => {
  assert.equal(planUbi({ fundingLine: prof, recipients: [AI1], cfg: { shareBps: 1, minPoolUsdc: 0.10 } }).reason, "below_min_pool");
  assert.equal(planUbi({ fundingLine: prof, recipients: [], cfg: { minPoolUsdc: 0.01 } }).reason, "no_recipients");
  assert.equal(planUbi({ fundingLine: prof, recipients: [AI1], cfg: { minPoolUsdc: 0.01, walletBalanceUsdc: 0 } }).reason, "insufficient_balance");
});
test("planUbi: dryRun computes the plan but marks it 'dry' (sends nothing)", () => {
  assert.equal(planUbi({ fundingLine: prof, recipients: [AI1], cfg: { minPoolUsdc: 0.01, dryRun: true } }).outcome, "dry");
});
test("idempotency: a wake already distributed is a no-op", () => {
  const done = [{ kind: "ubi", wake: "w1", outcome: "done" }];
  assert.equal(alreadyDone(done, "w1"), true);
  assert.equal(planUbi({ fundingLine: prof, recipients: [AI1], cfg: { minPoolUsdc: 0.01 }, ubiLines: done }).reason, "already_distributed");
});
