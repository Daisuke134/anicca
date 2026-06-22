// VCSDD: aggregate Hyperliquid clearinghouseState into the two numbers the dashboard needs —
// accountValue (net worth contribution) and unrealizedPnl (revenue_by_source contribution). Fixture is a
// REAL live response (no mock shape invented): wallet 0xa3CDd4, ETH long 2x, entry 1735.4.
import { test } from "node:test";
import assert from "node:assert/strict";
import { aggregateHlState } from "../hl-state.mjs";

// verbatim from https://api.hyperliquid.xyz/info clearinghouseState (2026-06-22)
const LIVE = {
  marginSummary: { accountValue: "8.884869", totalNtlPos: "11.04516", totalMarginUsed: "5.52258" },
  assetPositions: [{ type: "oneWay", position: { coin: "ETH", szi: "0.0063", entryPx: "1735.4", positionValue: "11.04516", unrealizedPnl: "0.11214" } }],
  time: 1782126582007,
};

test("real fixture: accountValue + summed unrealizedPnl", () => {
  const s = aggregateHlState(LIVE);
  assert.equal(s.accountValue, 8.884869);
  assert.ok(Math.abs(s.unrealizedPnl - 0.11214) < 1e-9);
});

test("no positions (account funded but flat) → upnl 0, value kept", () => {
  const s = aggregateHlState({ marginSummary: { accountValue: "5.0" }, assetPositions: [] });
  assert.equal(s.accountValue, 5.0);
  assert.equal(s.unrealizedPnl, 0);
});

test("multiple positions sum their unrealizedPnl (incl. a loser)", () => {
  const s = aggregateHlState({ marginSummary: { accountValue: "10" }, assetPositions: [
    { position: { unrealizedPnl: "0.5" } }, { position: { unrealizedPnl: "-1.2" } } ] });
  assert.ok(Math.abs(s.unrealizedPnl - (-0.7)) < 1e-9);
});

test("empty / missing / malformed → zeros, never throws", () => {
  assert.deepEqual(aggregateHlState(null), { accountValue: 0, unrealizedPnl: 0 });
  assert.deepEqual(aggregateHlState({}), { accountValue: 0, unrealizedPnl: 0 });
  assert.deepEqual(aggregateHlState({ marginSummary: {}, assetPositions: "bad" }), { accountValue: 0, unrealizedPnl: 0 });
});
