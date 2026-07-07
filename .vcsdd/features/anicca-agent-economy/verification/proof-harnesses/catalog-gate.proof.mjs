// Proof harness — anicca-agent-economy Phase 5 (formal hardening), sprint 1.
// Property-based tests (fast-check) for PROP-201a/b/c/d/e/f, PROP-202a, and PROP-201h against the REAL
// exported filterCatalog(...) and hasOpenRiskPositionOfYield(...) in
// ~/anicca/runtime/loop/catalog-gate.mjs.
//
// Why this harness exists: runtime/loop/__tests__/catalog-gate.test.mjs (the Phase 2 handwritten suite)
// exercises these properties against ONE fixed 17-name slot list (ALL_SLOTS) with a small, fixed set of
// tag/threshold/balance combinations. This harness generates thousands of RANDOM slot-name lists, random
// per-slot risk-tag/alwaysAvailable/openPosition assignments, and random balances/thresholds/ledgers to
// prove the documented contract holds across the input space filterCatalog is declared pure over, not
// just the sampled fixture.
//
// Run: node --test .vcsdd/features/anicca-agent-economy/verification/proof-harnesses/catalog-gate.proof.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import {
  filterCatalog,
  DEFAULT_BOOTSTRAP_RESERVE_USDC,
  hasOpenRiskPositionOfYield,
} from "/Users/anicca/anicca/runtime/loop/catalog-gate.mjs";

const slotNameArb = fc.stringMatching(/^[a-z][a-z0-9_]{1,10}$/);
const riskTagArb = fc.constantFrom("safe", "capital", undefined);

// One slot record per generated slot: independent random tag/alwaysAvailable/openPosition assignment,
// deduplicated by name (fc.uniqueArray's selector) so riskTagOf/alwaysAvailableOf/hasOpenRiskPositionOf
// (plain-object-lookup-shaped closures below) stay well-defined per slot name.
const slotRecordsArb = fc.uniqueArray(
  fc.record({
    name: slotNameArb,
    tag: riskTagArb,
    alwaysAvail: fc.boolean(),
    hasOpenPos: fc.boolean(),
  }),
  { selector: (r) => r.name, minLength: 1, maxLength: 15 }
);

function buildLookups(records) {
  const byName = new Map(records.map((r) => [r.name, r]));
  return {
    slots: records.map((r) => r.name),
    riskTagOf: (name) => byName.get(name)?.tag,
    alwaysAvailableOf: (name) => byName.get(name)?.alwaysAvail === true,
    hasOpenRiskPositionOf: (name) => byName.get(name)?.hasOpenPos === true,
  };
}

// ── PROP-201a + PROP-201d + PROP-201e + PROP-201f (combined spec-level property) ──────────────────────
// Below threshold, a slot survives filterCatalog IFF at least one of the three carve-outs applies:
// alwaysAvailable===true, OR an explicit "safe" tag (untagged/other counts as capital-risking, PROP-201d),
// OR hasOpenRiskPositionOf===true (PROP-201f). This is the exact disjunction filterCatalog's own filter
// callback implements -- verified here as an independent oracle re-derivation, not a copy-paste of the
// implementation, across randomized slot sets instead of the one fixed ALL_SLOTS fixture.
test("PROP-201a/201d/201e/201f (fast-check): below threshold, survival == alwaysAvailable OR tag==='safe' OR hasOpenRiskPosition", () => {
  fc.assert(
    fc.property(slotRecordsArb, (records) => {
      const { slots, riskTagOf, alwaysAvailableOf, hasOpenRiskPositionOf } = buildLookups(records);
      const result = filterCatalog({
        balanceUsdc: 0, // deliberately far below any positive threshold
        allSlotNames: slots,
        riskTagOf,
        alwaysAvailableOf,
        hasOpenRiskPositionOf,
        reserveThresholdUsdc: 20,
      });
      for (const r of records) {
        const shouldSurvive = r.alwaysAvail === true || r.tag === "safe" || r.hasOpenPos === true;
        assert.equal(
          result.includes(r.name),
          shouldSurvive,
          `slot "${r.name}" (tag=${r.tag}, alwaysAvail=${r.alwaysAvail}, hasOpenPos=${r.hasOpenPos}) expected survive=${shouldSurvive}`
        );
      }
      // no extraneous names invented
      assert.ok(result.every((name) => slots.includes(name)));
    }),
    { numRuns: 3000 }
  );
});

// ── PROP-201b ────────────────────────────────────────────────────────────────────────────────────────
// At or above threshold, filterCatalog NEVER filters anything, no matter what the bookkeeping inputs say
// (a buggy implementation that also checked tags above threshold would fail this across random tags).
test("PROP-201b (fast-check): at or above threshold, the full unfiltered slot list is returned regardless of tags/carve-outs", () => {
  fc.assert(
    fc.property(
      slotRecordsArb,
      fc.integer({ min: 0, max: 1000 }), // threshold
      fc.integer({ min: 0, max: 1000 }), // extra >= 0, so balance = threshold + extra is always >= threshold
      (records, threshold, extra) => {
        const { slots, riskTagOf, alwaysAvailableOf, hasOpenRiskPositionOf } = buildLookups(records);
        const result = filterCatalog({
          balanceUsdc: threshold + extra,
          allSlotNames: slots,
          riskTagOf,
          alwaysAvailableOf,
          hasOpenRiskPositionOf,
          reserveThresholdUsdc: threshold,
        });
        assert.deepEqual([...result].sort(), [...slots].sort());
      }
    ),
    { numRuns: 2000 }
  );
});

// ── PROP-201c ────────────────────────────────────────────────────────────────────────────────────────
// An unset/non-finite/negative reserveThresholdUsdc always falls back to DEFAULT_BOOTSTRAP_RESERVE_USDC
// (20), and the gate is never silently disabled -- checked here against random invalid threshold values
// (not just the 4 hardcoded ones -- undefined/NaN/-5/Infinity -- in the handwritten test).
test("PROP-201c (fast-check): invalid reserveThresholdUsdc always falls back to the documented default, gate never disabled", () => {
  fc.assert(
    fc.property(
      fc.constantFrom(undefined, NaN, Infinity, -Infinity),
      fc.double({ min: -10_000, max: -0.01, noNaN: true }), // any negative finite number
      fc.boolean(), // which invalid-threshold flavor to use this run
      (namedInvalid, negativeInvalid, useNamed) => {
        const badThreshold = useNamed ? namedInvalid : negativeInvalid;
        const result = filterCatalog({
          balanceUsdc: 5, // below the documented default (20) regardless of what the bad threshold claims
          allSlotNames: ["hl_trade", "report"],
          riskTagOf: (name) => (name === "hl_trade" ? "capital" : "safe"),
          alwaysAvailableOf: () => false,
          hasOpenRiskPositionOf: () => false,
          reserveThresholdUsdc: badThreshold,
        });
        assert.ok(!result.includes("hl_trade"), `bad threshold (${badThreshold}) must still fall back to a real default and filter`);
      }
    ),
    { numRuns: 1000 }
  );
  assert.equal(DEFAULT_BOOTSTRAP_RESERVE_USDC, 20);
  assert.ok(DEFAULT_BOOTSTRAP_RESERVE_USDC >= 5, "standing invariant vs COMPUTE_RESERVE_USDC's own default");
});

// ── PROP-202a ────────────────────────────────────────────────────────────────────────────────────────
// filterCatalog is a pure function of ITS OWN CALL's inputs only -- no persisted/module-level state
// leaks between successive calls. Property: calling filterCatalog(inputA), then filterCatalog(inputB)
// with completely different (randomized) inputs, then filterCatalog(inputA) again must yield IDENTICAL
// results for inputA both times, regardless of what inputB was in between.
test("PROP-202a (fast-check): filterCatalog(inputA) is unaffected by an intervening filterCatalog(inputB) call, for random inputA/inputB pairs", () => {
  fc.assert(
    fc.property(slotRecordsArb, slotRecordsArb, fc.integer({ min: 0, max: 100 }), fc.integer({ min: 0, max: 100 }), (recordsA, recordsB, balanceA, balanceB) => {
      const a = buildLookups(recordsA);
      const b = buildLookups(recordsB);
      const callA = () =>
        filterCatalog({
          balanceUsdc: balanceA,
          allSlotNames: a.slots,
          riskTagOf: a.riskTagOf,
          alwaysAvailableOf: a.alwaysAvailableOf,
          hasOpenRiskPositionOf: a.hasOpenRiskPositionOf,
          reserveThresholdUsdc: 20,
        });
      const resultA1 = [...callA()].sort();
      // intervening call with completely different inputs
      filterCatalog({
        balanceUsdc: balanceB,
        allSlotNames: b.slots,
        riskTagOf: b.riskTagOf,
        alwaysAvailableOf: b.alwaysAvailableOf,
        hasOpenRiskPositionOf: b.hasOpenRiskPositionOf,
        reserveThresholdUsdc: 20,
      });
      const resultA2 = [...callA()].sort();
      assert.deepEqual(resultA1, resultA2, "an intervening call with unrelated inputs must never change inputA's own result");
    }),
    { numRuns: 2000 }
  );
});

// ── PROP-201h ────────────────────────────────────────────────────────────────────────────────────────
// hasOpenRiskPositionOfYield(recentLedger) must equal the independent oracle
// "does some entry have a source starting with 'yield' AND a truthy tx", for ANY randomly generated
// ledger array -- not just the small number of hand-picked fixture ledgers in the Phase 2 test file.
// Also asserts the function performs zero I/O by construction: it is called here with plain in-memory
// arrays and never touches fs/network (verified structurally in purity-audit.md; this test additionally
// proves it is a total, synchronous function -- no thrown errors -- across arbitrary malformed entries).
const ledgerEntryArb = fc.record(
  {
    source: fc.option(fc.oneof(fc.constantFrom("yield", "yield_beefy", "yield-aave", "hl_trade", "economy/gig", ""), fc.string()), { nil: undefined }),
    tx: fc.option(fc.oneof(fc.constantFrom("0xabc", ""), fc.string()), { nil: undefined }),
  },
  { requiredKeys: [] }
);
const ledgerArb = fc.array(fc.oneof(ledgerEntryArb, fc.constant(null), fc.constant(undefined)), { maxLength: 20 });

test("PROP-201h (fast-check): hasOpenRiskPositionOfYield matches an independent oracle across randomized ledgers", () => {
  fc.assert(
    fc.property(ledgerArb, (ledger) => {
      const expected = ledger.some((l) => String((l && l.source) || "").startsWith("yield") && Boolean(l && l.tx));
      const actual = hasOpenRiskPositionOfYield(ledger);
      assert.equal(actual, expected);
      assert.equal(typeof actual, "boolean");
    }),
    { numRuns: 3000 }
  );

  // non-array input (malformed shape) never throws, treated as "no open position" (fail-... note: this
  // is the one fail-CLOSED direction in this gate's yield branch, unlike hl_trade's deliberate fail-open).
  for (const bad of [null, undefined, "not-an-array", 42, {}]) {
    assert.equal(hasOpenRiskPositionOfYield(bad), false, `non-array input (${JSON.stringify(bad)}) must resolve to false, never throw`);
  }
});
