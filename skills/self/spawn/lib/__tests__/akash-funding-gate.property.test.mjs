// VCSDD anicca-agent-spawn, Phase 5 (Formal Hardening) — Tier-1 property-based tests, `fast-check`.
// Generalizes akash-funding-gate.test.mjs's hand-picked fixtures (PROP-303g/PROP-303h) across
// randomized costAkt/bufferAkt/balance sequences: the two-pass sequencing invariant must hold no
// matter WHAT the actual numbers are, not just the one fixture pair already on file.
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import { evaluateAkashFundingGate } from "../akash-funding-gate.mjs";

// PROP-303h (property): exactly one query+zero bridge calls when the first pass is already
// sufficient; exactly two query+one bridge call when it is not — for arbitrary non-negative
// costAkt/bufferAkt/balance combinations, never a third query, never a second bridge attempt.
test("PROP-303h (property): query/bridge call counts are exactly {1,0} when sufficient, {2,1} when insufficient, for arbitrary AKT amounts", async () => {
  await fc.assert(
    fc.asyncProperty(
      fc.double({ min: 0, max: 1000, noNaN: true }), // costAkt
      fc.double({ min: 0, max: 100, noNaN: true }), // bufferAkt
      fc.double({ min: 0, max: 1000, noNaN: true }), // firstBalanceAkt
      fc.double({ min: 0, max: 1000, noNaN: true }), // secondBalanceAkt (only used if first insufficient)
      async (costAkt, bufferAkt, firstBalanceAkt, secondBalanceAkt) => {
        let queryCount = 0;
        let bridgeCalls = 0;
        const balances = [firstBalanceAkt, secondBalanceAkt];
        const result = await evaluateAkashFundingGate({
          queryBalanceAkt: async () => balances[queryCount++],
          costAkt,
          bufferAkt,
          attemptBridge: async () => {
            bridgeCalls += 1;
          },
        });
        const firstSufficient = firstBalanceAkt >= costAkt + bufferAkt;
        if (firstSufficient) {
          assert.equal(queryCount, 1, "sufficient first pass must query exactly once");
          assert.equal(bridgeCalls, 0, "sufficient first pass must never invoke the bridge");
          assert.equal(result.bridgeAttempted, false);
          assert.equal(result.firstPassReady, true);
          assert.equal(result.ready, true);
        } else {
          assert.equal(queryCount, 2, "insufficient first pass must trigger exactly one fresh second query");
          assert.equal(bridgeCalls, 1, "insufficient first pass must trigger exactly one bridge attempt");
          assert.equal(result.bridgeAttempted, true);
          assert.equal(result.firstPassReady, false);
          assert.equal(result.ready, secondBalanceAkt >= costAkt + bufferAkt);
        }
      }
    ),
    { numRuns: 300 }
  );
});

// PROP-303g (property): balanceAkt is always the FRESH per-pass query result, never the other
// pass's value — for arbitrary DIFFERING first/second balances, the two passes' own thresholdAkt
// stays derived from the SAME costAkt/bufferAkt while readiness tracks each pass's OWN query.
test("PROP-303g (property): each pass's readiness is derived from that pass's own fresh query, never the other pass's stale value", async () => {
  await fc.assert(
    fc.asyncProperty(
      fc.double({ min: 1, max: 100, noNaN: true }), // costAkt
      fc.double({ min: 0, max: 10, noNaN: true }), // bufferAkt
      async (costAkt, bufferAkt) => {
        const threshold = costAkt + bufferAkt;
        // Construct first-insufficient, second-sufficient: proves the second pass's readiness can only
        // come from ITS OWN fresh query, never a cached/reused first-pass value (which was insufficient).
        const queries = [Math.max(0, threshold - 1), threshold + 1];
        let i = 0;
        const result = await evaluateAkashFundingGate({
          queryBalanceAkt: async () => queries[i++],
          costAkt,
          bufferAkt,
          attemptBridge: async () => {},
        });
        assert.equal(result.ready, true, "second pass's own fresh (sufficient) query must be reflected, never the first pass's insufficient one");
        assert.equal(i, 2);
      }
    ),
    { numRuns: 200 }
  );
});
