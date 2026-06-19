import { test } from "node:test";
import assert from "node:assert/strict";
import { runBankPayout } from "../bank-payout.mjs";

const r = (id, provider) => ({ id, provider, currency: "JPY", bank: { bankCode: "0005", branchCode: "001", accountNumber: "123", beneficiaryName: "ﾅﾏｴ" } });

test("runBankPayout: plans + dispatches each rail's batch to its injected adapter", async () => {
  const calls = {};
  const adapters = {
    gmo: async (transfers) => { calls.gmo = transfers; return { apptransferNo: "G1" }; },
    rain: async (transfers) => { calls.rain = transfers; return { id: "R1" }; },
  };
  const out = await runBankPayout({ pool: 9000, recipients: [r("a", "gmo"), r("b", "rain"), r("c", "gmo")], adapters });
  assert.equal(out.outcome, "sent");
  assert.equal(calls.gmo.length, 2);            // a + c
  assert.equal(calls.rain.length, 1);           // b
  assert.equal(calls.gmo[0].amount, 3000);      // 9000/3
  assert.ok(out.results.every((x) => x.ok));
});

test("runBankPayout: missing adapter for a rail = that batch fails, outcome partial", async () => {
  const out = await runBankPayout({ pool: 6000, recipients: [r("a", "gmo"), r("b", "rain")], adapters: { gmo: async () => ({ ok: 1 }) } });
  assert.equal(out.outcome, "partial");
  const rain = out.results.find((x) => x.provider === "rain");
  assert.equal(rain.ok, false);
  assert.equal(rain.error, "no_adapter");
});

test("runBankPayout: adapter throw is captured per-rail (does not crash the run)", async () => {
  const out = await runBankPayout({ pool: 4000, recipients: [r("a", "gmo")], adapters: { gmo: async () => { throw new Error("GMO 503"); } } });
  assert.equal(out.outcome, "partial");
  assert.match(out.results[0].error, /GMO 503/);
});

test("runBankPayout: no-send plan (no recipients) returns skipped, no adapter calls", async () => {
  let called = false;
  const out = await runBankPayout({ pool: 9000, recipients: [], adapters: { gmo: async () => { called = true; } } });
  assert.equal(out.outcome, "skipped");
  assert.equal(out.reason, "no_recipients");
  assert.equal(called, false);
});
