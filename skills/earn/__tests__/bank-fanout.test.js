import { test } from "node:test";
import assert from "node:assert/strict";
import { planBankFanout, groupByProvider } from "../lib/bank-fanout.mjs";

const r = (id, provider = "gmo", currency = "JPY") => ({ id, provider, currency, bank: { accountNumber: "123" } });

test("planBankFanout: splits pool equally as integer yen, keeps remainder as dust", () => {
  const p = planBankFanout({ pool: 10000, recipients: [r("a"), r("b"), r("c")] });
  assert.equal(p.outcome, "send");
  assert.equal(p.per, 3333);          // floor(10000/3)
  assert.equal(p.count, 3);
  assert.equal(p.payoutTotal, 9999);
  assert.equal(p.dust, 1);            // 10000 - 9999
  assert.equal(p.transfers.length, 3);
  assert.ok(p.transfers.every((t) => t.amount === 3333));
});

test("planBankFanout: fees are OUR cost on top, deducted before per-split", () => {
  // pool 10000, 2 recipients, fee 130 each → afterFees = 10000 - 260 = 9740, per = 4870
  const p = planBankFanout({ pool: 10000, recipients: [r("a"), r("b")], opts: { feePerTransfer: 130 } });
  assert.equal(p.per, 4870);
  assert.equal(p.payoutTotal, 9740);
  assert.equal(p.feeTotal, 260);
  assert.equal(p.spend, 10000);       // payout + fees
  assert.equal(p.dust, 0);
});

test("planBankFanout: reserve is kept back before distribution", () => {
  const p = planBankFanout({ pool: 10000, recipients: [r("a")], opts: { reserve: 2000 } });
  assert.equal(p.per, 8000);          // (10000-2000)/1
  assert.equal(p.reserve, 2000);
});

test("planBankFanout: skips on invalid pool / no recipients / below reserve / below min / fees>pool", () => {
  assert.equal(planBankFanout({ pool: 0, recipients: [r("a")] }).reason, "invalid_pool");
  assert.equal(planBankFanout({ pool: 1.5, recipients: [r("a")] }).reason, "invalid_pool");
  assert.equal(planBankFanout({ pool: 1000, recipients: [] }).reason, "no_recipients");
  assert.equal(planBankFanout({ pool: 1000, recipients: [r("a")], opts: { reserve: 1000 } }).reason, "below_reserve");
  assert.equal(planBankFanout({ pool: 100, recipients: [r("a")], opts: { minPer: 200 } }).reason, "below_min_per");
  assert.equal(planBankFanout({ pool: 200, recipients: [r("a"), r("b")], opts: { feePerTransfer: 130 } }).reason, "fees_exceed_pool");
});

test("planBankFanout: drops invalid recipients (missing bank/provider/currency)", () => {
  const recips = [r("a"), { id: "bad" }, { id: "c", provider: "gmo", currency: "JPY", bank: {} }];
  const p = planBankFanout({ pool: 6000, recipients: recips });
  assert.equal(p.count, 2);           // "bad" dropped; a + c kept
});

test("planBankFanout: balance guard blocks overspend", () => {
  const p = planBankFanout({ pool: 10000, recipients: [r("a"), r("b")], opts: { balance: 5000 } });
  assert.equal(p.reason, "insufficient_balance");
});

test("groupByProvider: batches transfers per rail", () => {
  const p = planBankFanout({ pool: 9000, recipients: [r("a", "gmo"), r("b", "rain"), r("c", "gmo")] });
  const g = groupByProvider(p.transfers);
  assert.equal(g.gmo.length, 2);
  assert.equal(g.rain.length, 1);
});
