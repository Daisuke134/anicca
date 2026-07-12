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

// ── Open positions are NOT a loss ────────────────────────────────────────────
// The realized-only formula counts the cash spent opening a bet as if it were gone. That is wrong
// the moment the loop is actually betting: on 2026-07-12 claude-p showed realized -$9.16 while
// holding $19.33 of unsettled positions -- it was reported as LOSING $9 when its true economic
// position was +$10. Marking the open positions to Polymarket's own /value endpoint is what makes
// the number honest.
const { fetchTotalPnlUsd } = require("../polymarket-revenue-reader");

test("T2b: total P&L adds the mark-to-market value of unsettled positions", async () => {
  const activity = [
    { type: "TRADE", side: "BUY", usdcSize: 58.93 },
    { type: "REDEEM", usdcSize: 49.78 },
  ];
  const f = async (url) =>
    String(url).includes("/value")
      ? okJson([{ user: "0xabc", value: 19.33 }])
      : okJson(activity);

  const total = await fetchTotalPnlUsd("0xabc", f);
  assert.strictEqual(Math.round(total * 100) / 100, 10.18); // 49.78 - 58.93 + 19.33
});

test("T2b: with no open positions, total P&L equals realized P&L", async () => {
  const activity = [
    { type: "TRADE", side: "BUY", usdcSize: 10 },
    { type: "REDEEM", usdcSize: 15 },
  ];
  const f = async (url) =>
    String(url).includes("/value") ? okJson([]) : okJson(activity);

  assert.strictEqual(await fetchTotalPnlUsd("0xabc", f), 5);
});

test("T2b: a failed /value read throws rather than silently dropping the positions", async () => {
  // Falling back to realized-only here would report a LOSS on money that is still on the table.
  // Unverified is the honest answer; a confidently wrong negative is not.
  const activity = [{ type: "TRADE", side: "BUY", usdcSize: 20 }];
  const f = async (url) =>
    String(url).includes("/value")
      ? { ok: false, status: 503, json: async () => ({}) }
      : okJson(activity);

  await assert.rejects(() => fetchTotalPnlUsd("0xabc", f), /value/i);
});
