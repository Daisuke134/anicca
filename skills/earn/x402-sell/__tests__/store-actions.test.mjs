// node:test — SELF-STORE-1: pure decision/aggregation logic behind the x402_sell loop slot's
// review/ensure/update actions. No disk, no network, no live registration — see store-review.mjs
// and store-ensure-register.mjs for the (thin) I/O wrappers around these functions.
import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { aggregateStore } from "../lib/store-metrics.mjs";
import { shouldReregister } from "../store-ensure-register.mjs";
import { SELF_WALLETS } from "../lib/self-wallets.mjs";

describe("aggregateStore", () => {
  const SELF_SET = new Set(SELF_WALLETS);
  const now = Date.parse("2026-07-18T12:00:00.000Z");

  test("empty logs -> all zeros, honest demand-problem verdict", () => {
    const out = aggregateStore([], [], SELF_SET, now);
    assert.deepEqual(out, {
      settledCount: 0,
      settledUsd: 0,
      externalCount: 0,
      externalUsd: 0,
      topRoutes: [],
      attempts24h: 0,
      lastSaleTs: null,
      verdict: "no external sales yet — demand problem",
    });
  });

  test("only self-pay rows (incl. 0xb9dd automaton) -> settled but externalCount 0", () => {
    const sales = [
      { ts: "2026-07-17T10:49:39.652Z", route: "/calc", price: "$0.001", payer: "0x810F6D61F7606dEEE2657d3083E150a222Bc29C5", settled: true },
      { ts: "2026-07-17T21:18:01.545Z", route: "/mortgage", price: "$0.001", payer: "0xb9DD3b67921B354C656523D6851537988f31Dd56", settled: true }, // automaton self-probe
    ];
    const out = aggregateStore(sales, [], SELF_SET, now);
    assert.equal(out.settledCount, 2);
    assert.equal(out.settledUsd, 0.002);
    assert.equal(out.externalCount, 0);
    assert.equal(out.externalUsd, 0);
    assert.equal(out.verdict, "no external sales yet — demand problem");
  });

  test("a genuinely external payer counts as revenue and flips the verdict", () => {
    const sales = [
      { ts: "2026-07-18T01:00:00.000Z", route: "/calc", price: "$0.001", payer: "0x810F6D61F7606dEEE2657d3083E150a222Bc29C5", settled: true }, // self
      { ts: "2026-07-18T02:00:00.000Z", route: "/funding-rates", price: "$0.003", payer: "0x00000000000000000000000000000000000dead", settled: true }, // external
      { ts: "2026-07-18T02:30:00.000Z", route: "/calc", price: "$0.001", payer: null, settled: false }, // unsettled attempt row mixed into the sales file — must be excluded
    ];
    const out = aggregateStore(sales, [], SELF_SET, now);
    assert.equal(out.settledCount, 2);
    assert.equal(out.settledUsd, 0.004);
    assert.equal(out.externalCount, 1);
    assert.equal(out.externalUsd, 0.003);
    assert.equal(out.verdict, "external sales present");
    assert.equal(out.lastSaleTs, "2026-07-18T02:00:00.000Z");
  });

  test("topRoutes ranks by settled count, capped at 5", () => {
    const mkRow = (route, i) => ({ ts: `2026-07-18T00:00:${String(i).padStart(2, "0")}.000Z`, route, price: "$0.001", payer: "0xdead", settled: true });
    const sales = [
      ...Array(3).fill(0).map((_, i) => mkRow("/calc", i)),
      ...Array(2).fill(0).map((_, i) => mkRow("/mortgage", i + 3)),
      mkRow("/roi", 5), mkRow("/npv", 6), mkRow("/dcf", 7), mkRow("/irr", 8), mkRow("/cagr", 9), mkRow("/kelly", 10),
    ];
    const out = aggregateStore(sales, [], SELF_SET, now);
    assert.equal(out.topRoutes.length, 5);
    assert.deepEqual(out.topRoutes[0], { route: "/calc", count: 3 });
    assert.deepEqual(out.topRoutes[1], { route: "/mortgage", count: 2 });
  });

  test("attempts24h counts only rows within the trailing 24h window", () => {
    const attempts = [
      { ts: new Date(now - 1000).toISOString(), route: "/calc", price: "$0.001", payer: null, settled: false }, // inside window
      { ts: new Date(now - 23 * 60 * 60 * 1000).toISOString(), route: "/calc", price: "$0.001", payer: null, settled: false }, // inside window
      { ts: new Date(now - 25 * 60 * 60 * 1000).toISOString(), route: "/calc", price: "$0.001", payer: null, settled: false }, // outside window
    ];
    const out = aggregateStore([], attempts, SELF_SET, now);
    assert.equal(out.attempts24h, 2);
  });
});

describe("shouldReregister", () => {
  const now = Date.parse("2026-07-18T12:00:00.000Z");

  test("missing state -> true (never registered)", () => {
    assert.equal(shouldReregister(null, now, 5), true);
  });

  test("product count changed since last register -> true", () => {
    const state = { ts: now - 60_000, productCount: 4, origin: "https://x" };
    assert.equal(shouldReregister(state, now, 5), true);
  });

  test("fresh (well under 7 days) + same product count -> false", () => {
    const state = { ts: now - 60_000, productCount: 5, origin: "https://x" };
    assert.equal(shouldReregister(state, now, 5), false);
  });

  test("last register more than 7 days ago -> true even if count unchanged", () => {
    const eightDaysMs = 8 * 24 * 60 * 60 * 1000;
    const state = { ts: now - eightDaysMs, productCount: 5, origin: "https://x" };
    assert.equal(shouldReregister(state, now, 5), true);
  });

  test("exactly 7 days ago (boundary, not over) -> false when count unchanged", () => {
    const sevenDaysMs = 7 * 24 * 60 * 60 * 1000;
    const state = { ts: now - sevenDaysMs, productCount: 5, origin: "https://x" };
    assert.equal(shouldReregister(state, now, 5), false);
  });
});
