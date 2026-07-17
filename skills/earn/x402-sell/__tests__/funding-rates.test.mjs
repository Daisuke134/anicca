// node:test — funding-rates.mjs normalization + divergence math. Fixture-based, NO network (the
// network-fetching wrappers in funding-rates.mjs are I/O and are proven live in T9-1's manual E2E
// check instead; this file exercises only the pure/deterministic core per T9-1 requirement #6).
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  baseSymbol, toFundingRate8h, annualizedBps, normalizeBinance, normalizeBybit,
  normalizeHyperliquid, computeDivergence, buildFundingRatesResponse,
} from "../funding-rates.mjs";

test("baseSymbol strips USDT/USDC/USD quote suffixes", () => {
  assert.equal(baseSymbol("BTCUSDT"), "BTC");
  assert.equal(baseSymbol("ethusdc"), "ETH");
  assert.equal(baseSymbol("XRPUSD"), "XRP");
  assert.equal(baseSymbol("BTC"), "BTC"); // Hyperliquid: already bare
});

test("toFundingRate8h rebases native rate by interval ratio", () => {
  assert.equal(toFundingRate8h(0.0001, 8), 0.0001); // already 8h, no change
  assert.equal(toFundingRate8h(0.0000125, 1), 0.0001); // HL hourly * 8 = 8h-equivalent
  assert.equal(toFundingRate8h(0.00005, 4), 0.0001); // 4h * 2 = 8h-equivalent
});

test("annualizedBps: 0.0001 per 8h * 1095 periods/yr == 1095 bps/yr", () => {
  assert.ok(Math.abs(annualizedBps(0.0001) - 1095) < 1e-9);
});

// ---- normalizeBinance --------------------------------------------------
test("normalizeBinance: default 8h when symbol absent from fundingInfo", () => {
  const premiumIndex = [
    { symbol: "BTCUSDT", markPrice: "63577.7", lastFundingRate: "0.0001", nextFundingTime: 1784275200000 },
  ];
  const rows = normalizeBinance(premiumIndex, []); // fundingInfo empty -> default 8h
  assert.equal(rows.length, 1);
  assert.equal(rows[0].exchange, "binance");
  assert.equal(rows[0].baseSymbol, "BTC");
  assert.equal(rows[0].fundingIntervalHoursNative, 8);
  assert.equal(rows[0].fundingRate8h, 0.0001);
  assert.equal(rows[0].markPrice, 63577.7);
});

test("normalizeBinance: uses fundingInfo interval when the symbol is listed (non-default)", () => {
  const premiumIndex = [
    { symbol: "LPTUSDT", markPrice: "10", lastFundingRate: "0.00005", nextFundingTime: 1784275200000 },
  ];
  const fundingInfo = [{ symbol: "LPTUSDT", fundingIntervalHours: 4 }];
  const rows = normalizeBinance(premiumIndex, fundingInfo);
  assert.equal(rows[0].fundingIntervalHoursNative, 4);
  assert.equal(rows[0].fundingRate8h, 0.0001); // 0.00005 * (8/4)
});

// ---- normalizeBybit ------------------------------------------------------
test("normalizeBybit: reads fundingIntervalHour straight off the ticker row", () => {
  const tickers = [
    { symbol: "BTCUSDT", markPrice: "63570.8", fundingRate: "0.0001", nextFundingTime: "1784275200000", fundingIntervalHour: "8" },
    { symbol: "0GUSDT", markPrice: "0.1886", fundingRate: "0.00005", nextFundingTime: "1784260800000", fundingIntervalHour: "4" },
  ];
  const rows = normalizeBybit(tickers);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].fundingRate8h, 0.0001);
  assert.equal(rows[1].fundingIntervalHoursNative, 4);
  assert.equal(rows[1].fundingRate8h, 0.0001); // 0.00005 * (8/4)
});

// ---- normalizeHyperliquid -------------------------------------------------
test("normalizeHyperliquid: hourly funding * 8 -> 8h-equivalent; skips delisted", () => {
  const universe = [
    { name: "BTC" }, { name: "MATIC", isDelisted: true }, { name: "ETH" },
  ];
  const ctxs = [
    { funding: "0.0000125", markPx: "63608.0" },
    { funding: "0.0", markPx: "0.5" },
    { funding: "-0.0000200", markPx: "3200.0" },
  ];
  const now = Date.UTC(2026, 0, 1, 10, 15, 0); // 10:15 -> next settlement 11:00
  const rows = normalizeHyperliquid(universe, ctxs, now);
  assert.equal(rows.length, 2); // MATIC (delisted) skipped
  assert.equal(rows[0].symbol, "BTC");
  assert.ok(Math.abs(rows[0].fundingRate8h - 0.0001) < 1e-12); // 0.0000125 * 8
  assert.equal(rows[0].nextFundingTime, Date.UTC(2026, 0, 1, 11, 0, 0));
  assert.equal(rows[1].symbol, "ETH");
  assert.ok(Math.abs(rows[1].fundingRate8h - (-0.00016)) < 1e-12); // -0.00002 * 8
});

// ---- computeDivergence -----------------------------------------------------
test("computeDivergence: picks high/low exchange per symbol, sorts desc, needs >=2 exchanges", () => {
  const rows = [
    { baseSymbol: "BTC", exchange: "binance", fundingRate8h: 0.0001 },   // 109.5 bps/yr
    { baseSymbol: "BTC", exchange: "bybit", fundingRate8h: 0.00005 },    // 54.75 bps/yr
    { baseSymbol: "BTC", exchange: "hyperliquid", fundingRate8h: -0.0001 }, // -109.5 bps/yr (extreme low)
    { baseSymbol: "ETH", exchange: "binance", fundingRate8h: 0.0002 },   // only 1 exchange -> excluded
  ];
  const out = computeDivergence(rows, 20);
  assert.equal(out.length, 1); // ETH excluded (single exchange)
  assert.equal(out[0].symbol, "BTC");
  assert.equal(out[0].short.exchange, "binance");
  assert.equal(out[0].long.exchange, "hyperliquid");
  assert.ok(Math.abs(out[0].divergenceBps - 2190) < 1); // 1095 - (-1095) = 2190
});

test("computeDivergence: respects topN and descending order", () => {
  const mk = (sym, hi, lo) => [
    { baseSymbol: sym, exchange: "binance", fundingRate8h: hi },
    { baseSymbol: sym, exchange: "bybit", fundingRate8h: lo },
  ];
  const rows = [...mk("A", 0.0005, 0), ...mk("B", 0.0001, 0), ...mk("C", 0.0009, 0)];
  const out = computeDivergence(rows, 2);
  assert.equal(out.length, 2);
  assert.equal(out[0].symbol, "C"); // biggest spread first
  assert.equal(out[1].symbol, "A");
});

// ---- buildFundingRatesResponse ---------------------------------------------
test("buildFundingRatesResponse: symbol filter + shape + degraded flag", () => {
  const rows = [
    { exchange: "binance", symbol: "BTCUSDT", baseSymbol: "BTC", fundingRateNative: 0.0001, fundingIntervalHoursNative: 8, fundingRate8h: 0.0001, nextFundingTime: 1, markPrice: 100 },
    { exchange: "bybit", symbol: "ETHUSDT", baseSymbol: "ETH", fundingRateNative: 0.0002, fundingIntervalHoursNative: 8, fundingRate8h: 0.0002, nextFundingTime: 1, markPrice: 50 },
  ];
  const all = buildFundingRatesResponse(rows, {});
  assert.equal(all.rates.length, 2);
  assert.equal(all.degraded, false);
  assert.deepEqual(all.errors, []);

  const filtered = buildFundingRatesResponse(rows, { symbol: "btc" });
  assert.equal(filtered.rates.length, 1);
  assert.equal(filtered.rates[0].baseSymbol, "BTC");
  assert.equal(filtered.rates[0].normalization, "fundingRate8h = fundingRateNative * (8 / fundingIntervalHoursNative)");
  assert.ok(typeof filtered.generatedAt === "string" && filtered.generatedAt.length > 0);

  const degraded = buildFundingRatesResponse(rows, { errors: [{ exchange: "hyperliquid", error: "timeout" }] });
  assert.equal(degraded.degraded, true);
  assert.equal(degraded.errors[0].exchange, "hyperliquid");
});

console.log("funding-rates.test.mjs: all assertions passed");
