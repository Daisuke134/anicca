import { test } from "node:test";
import assert from "node:assert/strict";
import { bankWatcherPass } from "../bank-watcher.mjs";

const r = (id, provider = "gmo") => ({ id, provider, currency: "JPY", bank: { bankCode: "0005", branchCode: "001", accountNumber: "1", beneficiaryName: "ﾅ" } });

test("bankWatcherPass: idle when no bank recipients (no pool read, no pay)", async () => {
  let pooled = false;
  const out = await bankWatcherPass({ readBankRecipients: async () => [], getPool: async () => { pooled = true; return 9000; }, markPaid: async () => {}, adapters: {} });
  assert.equal(out.outcome, "idle");
  assert.equal(out.paid.length, 0);
});

test("bankWatcherPass: pays + marks ONLY recipients whose rail succeeded", async () => {
  const marked = [];
  const adapters = { gmo: async () => ({ apptransferNo: "G1" }), rain: async () => { throw new Error("rain down"); } };
  const out = await bankWatcherPass({
    readBankRecipients: async () => [r("a", "gmo"), r("b", "rain"), r("c", "gmo")],
    getPool: async () => 9000,
    markPaid: async (id, info) => marked.push({ id, info }),
    adapters,
  });
  assert.equal(out.outcome, "partial");                 // gmo ok, rain failed
  assert.deepEqual(out.paid.sort(), ["a", "c"]);        // only gmo recipients marked
  assert.ok(!out.paid.includes("b"));                   // rain failed → NOT marked (no fake)
  assert.equal(marked.length, 2);
  assert.equal(marked[0].info.amount, 3000);            // 9000/3
});

test("bankWatcherPass: claims BEFORE submit + reverts ONLY failed rails (FIND-002 idempotency)", async () => {
  const order = [];
  const claimed = [];
  const reverted = [];
  const adapters = {
    gmo: async () => { order.push("gmo-submit"); return { ok: 1 }; },
    rain: async () => { order.push("rain-submit"); throw new Error("rain 500"); },
  };
  const out = await bankWatcherPass({
    readBankRecipients: async () => [r("a", "gmo"), r("b", "rain")],
    getPool: async () => 9000,
    markPaid: async () => {},
    claim: async (ids) => { order.push("claim"); claimed.push(...ids); },
    revert: async (id) => { reverted.push(id); },
    adapters,
  });
  assert.equal(order[0], "claim");                 // claim happens BEFORE any submit
  assert.deepEqual(claimed.sort(), ["a", "b"]);    // all claimed before dispatch
  assert.deepEqual(reverted, ["b"]);               // only the failed rail (rain) reverted to queued
  assert.equal(out.paid.length, 1);                // gmo recipient paid
});

test("bankWatcherPass: balance guard is WIRED + active (FIND-003) — explicit balance below spend skips", async () => {
  let submitted = false;
  const out = await bankWatcherPass({
    readBankRecipients: async () => [r("a"), r("b")],
    getPool: async () => 9000,
    markPaid: async () => {},
    adapters: { gmo: async () => { submitted = true; } },
    opts: { balance: 100 },                          // explicit balance < spend → guard must fire
  });
  assert.equal(out.outcome, "skipped");
  assert.equal(out.reason, "insufficient_balance");
  assert.equal(submitted, false);
});

test("bankWatcherPass: skipped plan (pool below reserve) marks nobody", async () => {
  let markedAny = false;
  const out = await bankWatcherPass({
    readBankRecipients: async () => [r("a")],
    getPool: async () => 500,
    markPaid: async () => { markedAny = true; },
    adapters: { gmo: async () => ({}) },
    opts: { reserve: 1000 },
  });
  assert.equal(out.outcome, "skipped");
  assert.equal(out.reason, "below_reserve");
  assert.equal(markedAny, false);
});
