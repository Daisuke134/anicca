import { test } from "node:test";
import assert from "node:assert/strict";
import { bankWatcherPass } from "../bank-watcher.mjs";

const r = (id, provider = "gmo") => ({ id, provider, currency: "JPY", bank: { bankCode: "0005", branchCode: "001", accountNumber: "1234567", beneficiaryName: "ﾅ" } });
const claimAll = async (ids) => ids; // default: we win the claim on all

test("bankWatcherPass: idle when no bank recipients (no balance read, no pay)", async () => {
  let balanceRead = false;
  const out = await bankWatcherPass({ readBankRecipients: async () => [], getBalance: async () => { balanceRead = true; return 9000; }, claim: claimAll, markPaid: async () => {}, adapters: {} });
  assert.equal(out.outcome, "idle");
  assert.equal(balanceRead, false);
});

test("FIND-A atomic claim: ONLY the subset claim() returns is dispatched + paid (concurrent pass took 'b')", async () => {
  const marked = [];
  const out = await bankWatcherPass({
    readBankRecipients: async () => [r("a"), r("b"), r("c")],
    claim: async (ids) => ids.filter((id) => id !== "b"), // 'b' already flipped by another pass -> not ours
    getBalance: async () => 9000,
    markPaid: async (id) => marked.push(id),
    adapters: { gmo: async () => ({ apptransferNo: "G1" }) },
  });
  assert.equal(out.outcome, "sent");
  assert.deepEqual(out.paid.sort(), ["a", "c"]);
  assert.ok(!marked.includes("b")); // never double-submitted
});

test("FIND-A: nothing_claimed -> idle (a concurrent pass claimed them all)", async () => {
  let submitted = false;
  const out = await bankWatcherPass({
    readBankRecipients: async () => [r("a")],
    claim: async () => [],
    getBalance: async () => 9000,
    markPaid: async () => {},
    adapters: { gmo: async () => { submitted = true; } },
  });
  assert.equal(out.outcome, "idle");
  assert.equal(out.reason, "nothing_claimed");
  assert.equal(submitted, false);
});

test("FIND-B: adapter FAILURE leaves recipient 'processing' (NOT re-queued) — release only on skip", async () => {
  const released = [];
  const marked = [];
  const out = await bankWatcherPass({
    readBankRecipients: async () => [r("a", "gmo"), r("b", "rain")],
    claim: claimAll,
    getBalance: async () => 9000,
    markPaid: async (id) => marked.push(id),
    release: async (ids) => released.push(...ids),
    adapters: { gmo: async () => ({ apptransferNo: "G1" }), rain: async () => { throw new Error("timeout — maybe accepted"); } },
  });
  assert.equal(out.outcome, "partial");
  assert.deepEqual(out.paid, ["a"]);
  assert.deepEqual(out.failed, ["b"]);
  assert.deepEqual(released, []); // CRITICAL: never auto-requeue an unknown-outcome bank transfer
  assert.ok(!marked.includes("b"));
});

test("FIND-C: real balance drives the plan — below reserve -> skipped + claimed released (nothing sent)", async () => {
  const released = [];
  let submitted = false;
  const out = await bankWatcherPass({
    readBankRecipients: async () => [r("a"), r("b")],
    claim: claimAll,
    getBalance: async () => 500, // real GMO balance
    markPaid: async () => {},
    release: async (ids) => released.push(...ids),
    adapters: { gmo: async () => { submitted = true; } },
    opts: { reserve: 1000 },
  });
  assert.equal(out.outcome, "skipped");
  assert.equal(out.reason, "below_reserve");
  assert.equal(submitted, false);
  assert.deepEqual(released.sort(), ["a", "b"]); // safe: nothing dispatched
});

test("bankWatcherPass: all rails ok -> sent, per-amount from real balance", async () => {
  const marked = [];
  const out = await bankWatcherPass({
    readBankRecipients: async () => [r("a"), r("b")],
    claim: claimAll,
    getBalance: async () => 9000,
    markPaid: async (id, info) => marked.push(info.amount),
    adapters: { gmo: async () => ({ apptransferNo: "G1" }) },
  });
  assert.equal(out.outcome, "sent");
  assert.equal(marked[0], 4500); // 9000 / 2
});
