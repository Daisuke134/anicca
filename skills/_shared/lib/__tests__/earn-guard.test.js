// node:test — P1 fail-closed CUMULATIVE earn>spend guard (spec .vcsdd/features/anicca-agent-economy
// §3 P1 / §4). ledger.mjs already proves ONE pass profitable; this proves the CUMULATIVE
// invariant across many passes and the fail-closed HALT the instant it breaks.
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { appendLedger, deriveLine } from "../ledger.mjs";
import { cumulativeNet, evaluateScope, evaluateHalt, checkHalt, DEFAULT_RESERVE_USDC } from "../earn-guard.mjs";

async function tmpLedger() {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), "earn-guard-"));
  return path.join(d, "earn-ledger.jsonl");
}

function line(o) {
  return deriveLine(o);
}

// ---------------------------------------------------------------------------
// cumulativeNet: pure sum over a scope.
// ---------------------------------------------------------------------------
test("cumulativeNet sums net_usdc across matching lines only (wallet+source scope)", () => {
  const lines = [
    line({ wallet: "0xa", source: "polymarket-redeem", earn_usdc: 1, cost_usdc: 0.4 }), // net 0.6
    line({ wallet: "0xa", source: "polymarket-redeem", earn_usdc: 0.5, cost_usdc: 0.1 }), // net 0.4
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 5, cost_usdc: 0 }), // different source, excluded
    line({ wallet: "0xb", source: "polymarket-redeem", earn_usdc: 9, cost_usdc: 0 }), // different wallet, excluded
  ];
  const { cumulativeNet: net, trustworthy } = cumulativeNet(lines, { wallet: "0xa", source: "polymarket-redeem" });
  assert.equal(net, 1.0);
  assert.equal(trustworthy, true);
});

test("cumulativeNet with wallet-only scope aggregates every source for that agent", () => {
  const lines = [
    line({ wallet: "0xa", source: "polymarket-redeem", earn_usdc: 1, cost_usdc: 0.4 }), // net 0.6
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 0.2, cost_usdc: 0.1 }), // net 0.1
    line({ wallet: "0xb", source: "hl-trade", earn_usdc: 9, cost_usdc: 0 }), // different agent, excluded
  ];
  const { cumulativeNet: net } = cumulativeNet(lines, { wallet: "0xa" });
  assert.equal(net, 0.7);
});

// ---------------------------------------------------------------------------
// evaluateScope: positive cumulative net -> continue (no halt).
// ---------------------------------------------------------------------------
test("positive cumulative net -> no halt, reserve=0 default", () => {
  const lines = [
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 2, cost_usdc: 1 }), // net +1
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 3, cost_usdc: 2 }), // net +1 (cum +2)
  ];
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, false);
  assert.equal(r.reason, null);
  assert.equal(r.cumulativeNet, 2);
});

// ---------------------------------------------------------------------------
// evaluateScope: a pass that pushes cumulative net negative -> HALT (the spec's exact
// verification: "赤字になる pass が実際に停止").
// ---------------------------------------------------------------------------
test("a pass that pushes cumulative net negative -> HALT", () => {
  const lines = [
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 1, cost_usdc: 0 }), // net +1 (cum +1)
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 0, cost_usdc: 1.5 }), // net -1.5 (cum -0.5) <- this pass tips it
  ];
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "cumulative-net-below-reserve");
  assert.equal(r.cumulativeNet, -0.5);
});

test("still-positive-but-declining cumulative net does NOT halt (only actual deficit halts)", () => {
  const lines = [
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 5, cost_usdc: 0 }), // net +5
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 0, cost_usdc: 4 }), // net -4 (cum +1, still solvent)
  ];
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, false);
  assert.equal(r.cumulativeNet, 1);
});

// ---------------------------------------------------------------------------
// missing/malformed spend or income fields -> fail-closed HALT (never silently zero it).
// ---------------------------------------------------------------------------
test("malformed earn_usdc (non-numeric) -> fail-closed HALT even though prior passes were profitable", () => {
  const lines = [
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 10, cost_usdc: 1 }), // net +9, healthy
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: "oops", cost_usdc: 1 }), // malformed -> net NaN
  ];
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "malformed-ledger-data");
  assert.equal(r.cumulativeNet, null);
});

test("malformed cost_usdc (non-numeric) -> fail-closed HALT", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 5, cost_usdc: "???" })];
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "malformed-ledger-data");
});

test("a raw (non-derived) line with missing earn_usdc/cost_usdc entirely -> fail-closed HALT", () => {
  // simulate a line that never went through deriveLine (e.g. a hand-crafted/corrupt ledger row)
  const lines = [{ wallet: "0xa", source: "hl-trade", net_usdc: undefined }];
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "malformed-ledger-data");
});

// ---------------------------------------------------------------------------
// reserve-threshold boundary.
// ---------------------------------------------------------------------------
test("reserve boundary: cumulative net exactly AT the reserve -> NOT halted (inclusive)", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 2, cost_usdc: 1 })]; // net +1
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" }, 1);
  assert.equal(r.halt, false);
  assert.equal(r.cumulativeNet, 1);
});

test("reserve boundary: cumulative net one cent below the reserve -> HALT", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 2, cost_usdc: 1.01 })]; // net 0.99
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" }, 1);
  assert.equal(r.halt, true);
  assert.equal(r.reason, "cumulative-net-below-reserve");
});

test("DEFAULT_RESERVE_USDC is 0 (halt only on a true deficit, not on break-even)", () => {
  assert.equal(DEFAULT_RESERVE_USDC, 0);
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 1, cost_usdc: 1 })]; // net exactly 0
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, false);
});

// ---------------------------------------------------------------------------
// evaluateHalt: the per-skill (wallet+source) AND per-agent (wallet) union gate.
// ---------------------------------------------------------------------------
test("evaluateHalt: HALTs if the per-SKILL scope is insolvent even though the per-AGENT (wallet-wide) total is positive", () => {
  const lines = [
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 0, cost_usdc: 2 }), // this skill: net -2
    line({ wallet: "0xa", source: "polymarket-redeem", earn_usdc: 10, cost_usdc: 0 }), // other skill: net +10
  ];
  const r = evaluateHalt(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "cumulative-net-below-reserve");
  assert.equal(r.bySkill.halt, true);
  assert.equal(r.byAgent.halt, false, "wallet-wide total (+8) is still solvent");
});

test("evaluateHalt: HALTs if the per-AGENT (wallet) total is insolvent even though THIS skill alone is positive", () => {
  const lines = [
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 1, cost_usdc: 0 }), // this skill: net +1
    line({ wallet: "0xa", source: "sol-trade", earn_usdc: 0, cost_usdc: 5 }), // sibling skill: net -5
  ];
  const r = evaluateHalt(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.bySkill.halt, false, "this skill alone (+1) is fine");
  assert.equal(r.byAgent.halt, true, "wallet-wide total (-4) is insolvent");
});

test("evaluateHalt: source omitted -> only the per-agent (wallet) scope is evaluated, bySkill is null", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 0, cost_usdc: 1 })];
  const r = evaluateHalt(lines, { wallet: "0xa" });
  assert.equal(r.bySkill, null);
  assert.equal(r.byAgent.halt, true);
  assert.equal(r.halt, true);
});

test("evaluateHalt: both scopes solvent -> no halt", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 3, cost_usdc: 1 })];
  const r = evaluateHalt(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, false);
  assert.equal(r.reason, null);
});

// ---------------------------------------------------------------------------
// checkHalt: I/O wrapper reads the REAL ledger off disk (append-only, same file record.mjs writes).
// ---------------------------------------------------------------------------
test("checkHalt reads a real ledger file and halts once appended lines go net-negative", async () => {
  const f = await tmpLedger();
  await appendLedger(f, line({ wallet: "0xc", source: "x402-sell", earn_usdc: 1, cost_usdc: 0.2 })); // +0.8
  let r = await checkHalt(f, { wallet: "0xc", source: "x402-sell" });
  assert.equal(r.halt, false);

  await appendLedger(f, line({ wallet: "0xc", source: "x402-sell", earn_usdc: 0, cost_usdc: 2 })); // -2 (cum -1.2)
  r = await checkHalt(f, { wallet: "0xc", source: "x402-sell" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "cumulative-net-below-reserve");
  assert.equal(r.bySkill.cumulativeNet, -1.2);
});

test("checkHalt on a missing ledger file -> zero lines -> solvent (no halt, not fail-closed for absence)", async () => {
  const r = await checkHalt("/no/such/path/earn-ledger.jsonl", { wallet: "0xc", source: "x402-sell" });
  assert.equal(r.halt, false);
  assert.equal(r.bySkill.cumulativeNet, 0);
});
