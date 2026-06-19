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
