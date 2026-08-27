// node:test — spend-gate: pure money-safety gate mirroring caps.py's per-transfer/daily/
// cumulative semantics (translated to JS) plus balance sufficiency checks.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  outflowRows,
  checkSpendCaps,
  evaluateSpendGate,
  DEFAULT_MAX_SPEND_USD,
  DEFAULT_SOL_FEE_FLOOR,
} from "../spend-gate.mjs";

test("outflowRows keeps only pending/sent rows, dedupes by txHash keeping the most-terminal status", () => {
  const rows = outflowRows([
    { txHash: "0xa", status: "pending", amountUsd: 1, ts: 1 },
    { txHash: "0xa", status: "sent", amountUsd: 1, ts: 2 },
    { txHash: "0xb", status: "sent", amountUsd: 2, ts: 3 },
    { status: "sent", amountUsd: 3, ts: 4 }, // no txHash -> counted individually
    { txHash: "0xc", status: "failed", amountUsd: 99, ts: 5 }, // never counted
  ]);
  assert.equal(rows.length, 3);
  const byHash = rows.find((r) => r.txHash === "0xa");
  assert.equal(byHash.status, "sent"); // terminal wins over pending for the same hash
  assert.ok(rows.some((r) => r.txHash === "0xb"));
  assert.ok(rows.some((r) => !r.txHash && r.amountUsd === 3));
});

test("checkSpendCaps rejects a non-positive amount", () => {
  const d = checkSpendCaps({ amountUsd: 0, history: [], config: {}, nowTs: 1000 });
  assert.equal(d.allowed, false);
  assert.match(d.reason, /positive number/);
});

test("checkSpendCaps enforces the per-job cap", () => {
  const d = checkSpendCaps({ amountUsd: 1, history: [], config: { perJobUsdCap: 0.5 }, nowTs: 1000 });
  assert.equal(d.allowed, false);
  assert.match(d.reason, /exceeds per-job cap/);
});

test("checkSpendCaps enforces the rolling 24h daily cap using only the last 24h of outflow", () => {
  const now = 100000;
  const history = [
    { txHash: "old", status: "sent", amountUsd: 10, ts: now - 90000 }, // >24h ago, excluded
    { txHash: "recent", status: "sent", amountUsd: 0.4, ts: now - 1000 },
  ];
  const allowed = checkSpendCaps({ amountUsd: 0.05, history, config: { dailyUsdCap: 0.5 }, nowTs: now });
  assert.equal(allowed.allowed, true);
  const refused = checkSpendCaps({ amountUsd: 0.2, history, config: { dailyUsdCap: 0.5 }, nowTs: now });
  assert.equal(refused.allowed, false);
  assert.match(refused.reason, /daily cap/);
});

test("checkSpendCaps enforces the cumulative cap across all outflow, ignoring 24h window", () => {
  const now = 100000;
  const history = [{ txHash: "old", status: "sent", amountUsd: 0.45, ts: now - 1000000 }];
  const d = checkSpendCaps({ amountUsd: 0.1, history, config: { cumulativeUsdCap: 0.5 }, nowTs: now });
  assert.equal(d.allowed, false);
  assert.match(d.reason, /cumulative cap/);
});

test("checkSpendCaps allows a spend within all three caps", () => {
  const d = checkSpendCaps({
    amountUsd: 0.01,
    history: [],
    config: { perJobUsdCap: 0.5, dailyUsdCap: 1, cumulativeUsdCap: 10 },
    nowTs: 1000,
  });
  assert.equal(d.allowed, true);
});

test("evaluateSpendGate defaults perJobUsdCap to $0.50 and solFeeFloor to 0.005 SOL when unset", () => {
  assert.equal(DEFAULT_MAX_SPEND_USD, 0.5);
  assert.equal(DEFAULT_SOL_FEE_FLOOR, 0.005);
  const gate = evaluateSpendGate({
    costUsd: 0.6,
    costNos: 2,
    solBalance: 1,
    nosBalance: 10,
    history: [],
    config: {},
    nowTs: 1000,
  });
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /per-job cap \$0\.5/);
});

test("evaluateSpendGate refuses when NOS balance is insufficient", () => {
  const gate = evaluateSpendGate({
    costUsd: 0.01,
    costNos: 5,
    solBalance: 1,
    nosBalance: 1,
    history: [],
    config: {},
    nowTs: 1000,
  });
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /insufficient NOS balance/);
});

test("evaluateSpendGate refuses when SOL balance is below the fee floor", () => {
  const gate = evaluateSpendGate({
    costUsd: 0.01,
    costNos: 0.01,
    solBalance: 0.001,
    nosBalance: 100,
    history: [],
    config: {},
    nowTs: 1000,
  });
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /below the fee floor/);
});

test("evaluateSpendGate fails closed on a missing/NaN balance rather than treating it as zero-cost-ok", () => {
  const gateNos = evaluateSpendGate({
    costUsd: 0.01,
    costNos: 0.01,
    solBalance: 1,
    nosBalance: NaN,
    history: [],
    config: {},
    nowTs: 1000,
  });
  assert.equal(gateNos.allowed, false);
  assert.match(gateNos.reason, /nosBalance is unavailable/);

  const gateSol = evaluateSpendGate({
    costUsd: 0.01,
    costNos: 0.01,
    solBalance: undefined,
    nosBalance: 100,
    history: [],
    config: {},
    nowTs: 1000,
  });
  assert.equal(gateSol.allowed, false);
  assert.match(gateSol.reason, /solBalance is unavailable/);
});

test("evaluateSpendGate allows a tiny job well within cap and balances", () => {
  const gate = evaluateSpendGate({
    costUsd: 0.012,
    costNos: 0.047,
    solBalance: 0.0378,
    nosBalance: 1,
    history: [],
    config: {},
    nowTs: 1000,
  });
  assert.equal(gate.allowed, true);
});
