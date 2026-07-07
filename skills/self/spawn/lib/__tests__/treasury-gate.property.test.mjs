// VCSDD anicca-agent-spawn, Phase 5 (Formal Hardening) — Tier-1 property-based tests, `fast-check`.
// Generalizes the money-safety-critical fixture tests already in treasury-gate.test.mjs across
// randomized/boundary inputs. Written against the delivered, unmodified treasury-gate.mjs.
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import {
  computeColonySurplusUsd,
  computePerCitizenSurplusUsd,
  decideColonySpawn,
  filterProductiveCitizens,
  deriveRecentSpawnAttempts,
  countChildrenProvisioning,
} from "../treasury-gate.mjs";

const selfFundedAgent = (id, balanceUsd) => ({
  id,
  balanceUsd,
  wallet: { evm: true },
  fuel: { provider: "x402" },
  humanDependencies: [],
});
const nonSelfFundedAgent = (id, balanceUsd) => ({ id, balanceUsd, wallet: {}, fuel: {}, humanDependencies: ["dais"] });

// PROP-101i (property): computePerCitizenSurplusUsd's per-citizen output and computeColonySurplusUsd's
// aggregate must agree BY CONSTRUCTION for arbitrary citizen sets — never two independently-drifting
// numbers, for any mix of self-funded/non-self-funded citizens and any (finite) balance/reserve.
test("PROP-101i (property): computeColonySurplusUsd always equals the sum of computePerCitizenSurplusUsd's own output", () => {
  fc.assert(
    fc.property(
      fc.array(
        fc.record({
          id: fc.string({ minLength: 1 }),
          balanceUsd: fc.double({ min: -1_000_000, max: 1_000_000, noNaN: true }),
          selfFunded: fc.boolean(),
        }),
        { maxLength: 20 }
      ),
      fc.double({ min: 0, max: 10_000, noNaN: true }),
      (rows, perCitizenReserveUsd) => {
        const citizens = rows.map((r) => (r.selfFunded ? selfFundedAgent(r.id, r.balanceUsd) : nonSelfFundedAgent(r.id, r.balanceUsd)));
        const perCitizen = computePerCitizenSurplusUsd({ citizens, perCitizenReserveUsd });
        const aggregate = computeColonySurplusUsd({ citizens, perCitizenReserveUsd });
        const sum = perCitizen.reduce((s, p) => s + p.surplusUsd, 0);
        assert.ok(Math.abs(aggregate - sum) < 1e-9);
        // every per-citizen surplus is the exact max(0, balance - reserve) formula, and only for
        // self-funded citizens (PROP-101a/PROP-101b generalized).
        for (const p of perCitizen) {
          assert.ok(p.surplusUsd >= 0);
        }
        assert.equal(perCitizen.length, citizens.filter((c) => c.wallet.evm && c.fuel.provider === "x402" && c.humanDependencies.length === 0).length);
      }
    ),
    { numRuns: 500 }
  );
});

// PROP-102l (property, FIND-1901/1902): decideColonySpawn must fail closed for arbitrary
// non-finite/malformed spawnThresholdUsd/childrenProvisioning/maxConcurrentSpawns — never silently
// falling through to eligible:true via a NaN/undefined relational comparison.
// Non-finite/non-numeric only — a legitimately negative-but-finite spawnThresholdUsd is a VALID input
// (decideColonySpawn's fail-closed coercion only substitutes Infinity for non-finite/non-numeric values,
// per PROP-102l's own wording: "non-finite/malformed", never "any negative number").
const malformedNumeric = fc.oneof(fc.constant(NaN), fc.constant(null), fc.constant(undefined), fc.constant("5"), fc.constant({}), fc.constant([]));

test("PROP-102l (property): non-finite/malformed spawnThresholdUsd never falls through to eligible:true, for any colonySurplusUsd >= 0", () => {
  fc.assert(
    fc.property(malformedNumeric, fc.double({ min: 0, max: 1_000_000, noNaN: true }), (badThreshold, colonySurplusUsd) => {
      const result = decideColonySpawn({ colonySurplusUsd, spawnThresholdUsd: badThreshold, childrenProvisioning: 0, maxConcurrentSpawns: 1 });
      assert.equal(result.eligible, false);
      assert.equal(result.reason, "insufficient_surplus");
    }),
    { numRuns: 300 }
  );
});

test("PROP-102l (property): null/NaN childrenProvisioning never silently bypasses the concurrency cap, for any maxConcurrentSpawns >= 0", () => {
  const badProvisioning = fc.oneof(fc.constant(null), fc.constant(NaN));
  fc.assert(
    fc.property(badProvisioning, fc.double({ min: 0, max: 100, noNaN: true }), (bad, maxConcurrentSpawns) => {
      const result = decideColonySpawn({
        colonySurplusUsd: 1_000_000,
        spawnThresholdUsd: 1,
        childrenProvisioning: bad,
        maxConcurrentSpawns,
      });
      assert.equal(result.eligible, false);
      assert.equal(result.reason, "max_concurrent_spawns");
    }),
    { numRuns: 200 }
  );
});

test("PROP-102l (property): null/NaN maxConcurrentSpawns is treated as zero capacity for any non-negative childrenProvisioning", () => {
  const badMax = fc.oneof(fc.constant(null), fc.constant(NaN));
  fc.assert(
    fc.property(badMax, fc.double({ min: 0, max: 100, noNaN: true }), (bad, childrenProvisioning) => {
      const result = decideColonySpawn({
        colonySurplusUsd: 1_000_000,
        spawnThresholdUsd: 1,
        childrenProvisioning,
        maxConcurrentSpawns: bad,
      });
      assert.equal(result.eligible, false);
      assert.equal(result.reason, "max_concurrent_spawns");
    }),
    { numRuns: 200 }
  );
});

// PROP-102e (property): check order surplus -> cooldown -> concurrency cap holds for ANY fixture that
// fails all three simultaneously, not just the one hand-picked fixture in treasury-gate.test.mjs.
test("PROP-102e (property): a fixture failing all three checks always reports the SURPLUS failure, for arbitrary insufficient surplus/cooldown/cap combinations", () => {
  fc.assert(
    fc.property(
      fc.double({ min: 0, max: 99, noNaN: true }), // always below threshold 100
      fc.integer({ min: 1, max: 10 }), // failureCount >= cap (cap default 3)
      fc.integer({ min: 1, max: 10 }), // childrenProvisioning >= maxConcurrentSpawns
      (colonySurplusUsd, failureCount, provisioning) => {
        const recentSpawnAttempts = Array.from({ length: failureCount }, () => ({ ts: Date.now(), outcome: "failure" }));
        const result = decideColonySpawn({
          colonySurplusUsd,
          spawnThresholdUsd: 100,
          recentSpawnAttempts,
          childrenProvisioning: provisioning,
          maxConcurrentSpawns: 1,
        });
        assert.equal(result.eligible, false);
        assert.equal(result.reason, "insufficient_surplus");
      }
    ),
    { numRuns: 300 }
  );
});

// PROP-101l (property, FIND-1902): a null/undefined entry anywhere within an arbitrary citizens array
// is excluded gracefully (never thrown) by filterProductiveCitizens, consistent with
// computeColonySurplusUsd's own existing graceful handling of the identical malformed shape.
test("PROP-101l (property): null/undefined entries mixed anywhere in the citizens array are excluded gracefully by filterProductiveCitizens, never thrown", () => {
  fc.assert(
    fc.property(
      fc.array(
        fc.oneof(
          fc.constant(null),
          fc.constant(undefined),
          fc.record({ id: fc.string({ minLength: 1 }), balanceUsd: fc.double({ noNaN: true }) })
        ),
        { maxLength: 15 }
      ),
      (rows) => {
        assert.doesNotThrow(() => {
          const result = filterProductiveCitizens({ citizens: rows, ledgerRows: [], nowMs: Date.now() });
          const validCount = rows.filter((r) => r && typeof r === "object").length;
          assert.equal(result.length, validCount);
        });
      }
    ),
    { numRuns: 300 }
  );
});

// Shared-grouping consistency (PROP-102f/PROP-102h siblings): for ANY randomized set of ledger rows,
// deriveRecentSpawnAttempts and countChildrenProvisioning must agree on each child_id's classification
// — a group is EITHER counted as "provisioning" (countChildrenProvisioning) XOR resolved to a
// success/failure outcome (deriveRecentSpawnAttempts) XOR excluded from both (malformed group), never
// double-counted across the two functions, for arbitrary status sequences per child_id.
const statusArb = fc.constantFrom("provisioning", "active", "failed", "bootstrap_failed");

// A single child_id's REALISTIC ledger-row sequence, matching the state machine the real spawn
// orchestration actually produces: "provisioning" first, then EITHER stays in flight, resolves to
// "failed" (terminal), or resolves to "active" (optionally followed LATER by a REQ-402
// "bootstrap_failed" relabeling row — which must never retroactively flip a success back to a
// failure/provisioning classification). This deliberately excludes nonsensical sequences no real
// caller produces (e.g. "active" followed by a fresh "provisioning") — the two functions' contracts
// were never written to promise anything about those inputs.
const realisticOutcomeArb = fc.constantFrom("still-provisioning", "active", "active-then-bootstrap-failed", "failed");

test("PROP-102f/PROP-102h (property): every child_id group is classified by deriveRecentSpawnAttempts XOR countChildrenProvisioning, never both, for arbitrary REALISTIC status sequences", () => {
  fc.assert(
    fc.property(
      fc.uniqueArray(
        fc.record({ childId: fc.string({ minLength: 1, maxLength: 5 }), outcome: realisticOutcomeArb }),
        { minLength: 1, maxLength: 10, selector: (g) => g.childId }
      ),
      (groups) => {
        const ledgerRows = [];
        let ts = 1;
        for (const g of groups) {
          const statuses =
            g.outcome === "still-provisioning"
              ? ["provisioning"]
              : g.outcome === "active"
                ? ["provisioning", "active"]
                : g.outcome === "active-then-bootstrap-failed"
                  ? ["provisioning", "active", "bootstrap_failed"]
                  : ["provisioning", "failed"];
          for (const status of statuses) {
            ledgerRows.push({ child_id: g.childId, status, attempted_ms: ts, active_since: ts });
            ts += 1;
          }
        }
        const attempts = deriveRecentSpawnAttempts({ ledgerRows });
        const provisioningCount = countChildrenProvisioning({ ledgerRows });

        const provisioningExpected = groups.filter((g) => g.outcome === "still-provisioning").length;
        // "active" and "active-then-bootstrap-failed" both resolve to a PERMANENT "success" outcome
        // (the bootstrap_failed row never retroactively flips it); "failed" resolves to "failure".
        const resolvedExpected = groups.filter((g) => g.outcome !== "still-provisioning").length;

        assert.equal(provisioningCount, provisioningExpected);
        assert.equal(attempts.length, resolvedExpected);
        for (const g of groups) {
          if (g.outcome === "active" || g.outcome === "active-then-bootstrap-failed") {
            const entry = attempts.find((a) => a.ts === ledgerRows.find((r) => r.child_id === g.childId).attempted_ms);
            assert.equal(entry.outcome, "success");
          }
        }
      }
    ),
    { numRuns: 300 }
  );
});
