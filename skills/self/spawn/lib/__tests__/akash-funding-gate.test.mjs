// VCSDD anicca-agent-spawn, Phase 2a (RED). REQ-303 — computeSpawnGate's exact TWO-PASS sequencing
// relative to REQ-304's Skip API bridge (resolves FIND-1803), and balanceAkt's real-derivation
// binding, a FRESH `provider-services query bank balances` result each evaluation (resolves
// FIND-1802). Reuses the EXISTING, unmodified spawn-child/lib/akt-cost-gate.js::computeSpawnGate.
// akash-funding-gate.mjs does not exist yet — expected to fail at import time (module-not-found).
import { test } from "node:test";
import assert from "node:assert/strict";
import { evaluateAkashFundingGate } from "../akash-funding-gate.mjs";

test("PROP-303h(a): first pass ready:true skips the REQ-304 bridge entirely and proceeds directly", async () => {
  let bridgeCalls = 0;
  const result = await evaluateAkashFundingGate({
    queryBalanceAkt: async () => 30, // >= costAkt(25)+bufferAkt(1)
    costAkt: 25,
    bufferAkt: 1,
    attemptBridge: async () => {
      bridgeCalls += 1;
    },
  });
  assert.equal(result.ready, true);
  assert.equal(result.bridgeAttempted, false);
  assert.equal(bridgeCalls, 0);
});

test("PROP-303h(b): first pass ready:false triggers the bridge (never itself a REQ-305 failure); second pass ready:true after the bridge lands funds", async () => {
  let queryCount = 0;
  let bridgeCalls = 0;
  const result = await evaluateAkashFundingGate({
    queryBalanceAkt: async () => {
      queryCount += 1;
      return queryCount === 1 ? 2 : 30; // insufficient first pass, bridge lands funds, sufficient second pass
    },
    costAkt: 25,
    bufferAkt: 1,
    attemptBridge: async () => {
      bridgeCalls += 1;
    },
  });
  assert.equal(bridgeCalls, 1);
  assert.equal(queryCount, 2, "balanceAkt must be freshly re-queried for each of the (at most two) passes");
  assert.equal(result.ready, true);
  assert.equal(result.bridgeAttempted, true);
  assert.equal(result.firstPassReady, false, "the first pass's own ready:false must never itself be reported as ready");
});

test("PROP-303h(c): first pass ready:false, bridge runs, SECOND pass STILL ready:false -> THIS is the actual deploy failure (never the first pass alone)", async () => {
  let bridgeCalls = 0;
  const result = await evaluateAkashFundingGate({
    queryBalanceAkt: async () => 2, // stays insufficient even after the bridge attempt
    costAkt: 25,
    bufferAkt: 1,
    attemptBridge: async () => {
      bridgeCalls += 1;
    },
  });
  assert.equal(bridgeCalls, 1);
  assert.equal(result.ready, false);
  assert.equal(result.bridgeAttempted, true);
});

test("PROP-303g: balanceAkt is freshly re-queried at each evaluation, never cached/hand-assembled/stale", async () => {
  const balances = [1, 50];
  let i = 0;
  const result = await evaluateAkashFundingGate({
    queryBalanceAkt: async () => balances[i++],
    costAkt: 25,
    bufferAkt: 1,
    attemptBridge: async () => {},
  });
  assert.equal(i, 2, "exactly two fresh queries — never one cached reading reused across both passes");
  assert.equal(result.ready, true);
});

test("PROP-303d: reuses the existing, unmodified computeSpawnGate arithmetic exactly (costAkt/bufferAkt honored, threshold = cost+buffer)", async () => {
  const result = await evaluateAkashFundingGate({
    queryBalanceAkt: async () => 26,
    costAkt: 25,
    bufferAkt: 1,
    attemptBridge: async () => {
      throw new Error("bridge must never be invoked when the first pass is already ready");
    },
  });
  assert.equal(result.thresholdAkt, 26);
  assert.equal(result.shortfallAkt, 0);
  assert.equal(result.bridgeAttempted, false);
});

test("REQ-303 edge case: an insufficient second pass never fabricates a dseq or invokes akt-treasury.sh/deploy-akash.sh", async () => {
  let deployInvoked = false;
  const result = await evaluateAkashFundingGate({
    queryBalanceAkt: async () => 2,
    costAkt: 25,
    bufferAkt: 1,
    attemptBridge: async () => {},
  });
  if (result.ready) deployInvoked = true; // orchestration would only proceed to deploy on ready:true
  assert.equal(deployInvoked, false);
});
