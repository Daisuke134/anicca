// polymarket-revenue-reader.js unit tests. No network — fetchImpl is injected.
const { test } = require("node:test");
const assert = require("node:assert");
const { fetchRealizedPnlUsd } = require("../polymarket-revenue-reader");

const okJson = (body) => ({ ok: true, json: async () => body });

test("T2: realized P&L = sum(REDEEM.usdcSize) - sum(TRADE/BUY.usdcSize)", async () => {
  const list = [
    { type: "TRADE", side: "BUY", usdcSize: 10 },
    { type: "TRADE", side: "BUY", usdcSize: 5 },
    { type: "REDEEM", usdcSize: 20 },
  ];
  const f = async () => okJson(list);
  const pnl = await fetchRealizedPnlUsd("0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74", f);
  assert.strictEqual(pnl, 5); // 20 - (10+5)
});

test("T2: matches the exact worked example from the spec ($49.78 redeem - $39.97 buy = +$9.81)", async () => {
  const list = [
    { type: "REDEEM", usdcSize: 49.78 },
    { type: "TRADE", side: "BUY", usdcSize: 39.97 },
  ];
  const f = async () => okJson(list);
  const pnl = await fetchRealizedPnlUsd("0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74", f);
  assert.strictEqual(Math.round(pnl * 100) / 100, 9.81);
});

test("T2: a SELL trade is NOT netted (only REDEEM in / BUY out are unambiguous cash events)", async () => {
  const list = [
    { type: "TRADE", side: "BUY", usdcSize: 10 },
    { type: "TRADE", side: "SELL", usdcSize: 100 }, // must be ignored, not treated as +100 profit
    { type: "REDEEM", usdcSize: 3 },
  ];
  const f = async () => okJson(list);
  const pnl = await fetchRealizedPnlUsd("0xaddr", f);
  assert.strictEqual(pnl, 3 - 10);
});

test("T2: malformed entries (non-finite usdcSize) are skipped, never crash or count as NaN", async () => {
  const list = [
    { type: "REDEEM", usdcSize: "not-a-number" },
    { type: "REDEEM", usdcSize: 5 },
    null,
    { type: "TRADE", side: "BUY" }, // missing usdcSize
  ];
  const f = async () => okJson(list);
  const pnl = await fetchRealizedPnlUsd("0xaddr", f);
  assert.strictEqual(pnl, 5);
});

test("fail-closed: a non-ok HTTP response throws (never silently returns 0 as if verified)", async () => {
  const f = async () => ({ ok: false, status: 500, json: async () => ({}) });
  await assert.rejects(() => fetchRealizedPnlUsd("0xaddr", f));
});

test("fail-closed: a non-array body throws instead of guessing", async () => {
  const f = async () => okJson({ not: "an array" });
  await assert.rejects(() => fetchRealizedPnlUsd("0xaddr", f));
});

test("no revenue events => 0, not undefined/NaN", async () => {
  const f = async () => okJson([]);
  const pnl = await fetchRealizedPnlUsd("0xaddr", f);
  assert.strictEqual(pnl, 0);
});
