// node:test + fast-check — property-based hardening for anicca-agent-lending's pure core
// (skills/economy/lending/lib/lending-gate.mjs), written during VCSDD Phase 5 (formal hardening).
//
// This file does NOT re-test what lending-gate.test.mjs's 79 fixed-fixture unit tests already prove
// (single hand-picked inputs, exact expected outputs). Instead it exercises each targeted property
// against a RANGE of generated/edge-case inputs (fast-check's fc.assert(fc.property(...))), closing the
// gap a handful of hand-picked fixtures cannot: "does this hold for every input in the domain, not just
// the ones we thought to write down." See
// .vcsdd/features/anicca-agent-lending/verification/verification-report.md's own "## Proof Obligations"
// table for which PROP-ID each block below is evidence for.
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import {
  BORROWER_LOW_USD,
  RECENT_DEFAULT_LOSS_THRESHOLD_USD,
  computeLenderAvailableUsd,
  sumOutstandingPrincipalUsd,
  isBorrowerEligible,
  computeTotalDueUsd,
  computeLoanCapUsd,
  computeOverallDefaultRateUsd,
  computeRecentDefaultLossUsd,
  evaluateOverallDefaultKillSwitch,
  resolveLoanLockAcquisitionOrder,
} from "../lending-gate.mjs";

const BASE_BORROWER = { wallet: { evm: true }, fuel: { provider: "x402" }, humanDependencies: [] };

// finite, non-adversarial money-shaped doubles (no NaN/Infinity — those are exercised by the dedicated
// fail-closed properties below, which intentionally DO include NaN/Infinity/negative-malformed inputs).
const usd = (min, max) => fc.double({ min, max, noNaN: true, noDefaultInfinity: true });

// ===========================================================================
// PROP-101a (computeLenderAvailableUsd) — never negative, exact clamp(0, balance-reserve-outstanding-gojo)
// ===========================================================================

test("PROP-101a (property): computeLenderAvailableUsd is NEVER negative and exactly matches max(0, balance-reserve-outstanding-gojo), for ANY finite combination of its four inputs", () => {
  fc.assert(
    fc.property(
      usd(-1e6, 1e6),
      usd(-1e6, 1e6),
      usd(-1e6, 1e6),
      usd(-1e6, 1e6),
      (lenderBalanceUsd, perCitizenReserveUsd, outstandingPrincipalUsd, recentGojoGiftsUsd) => {
        const result = computeLenderAvailableUsd({
          lenderBalanceUsd,
          perCitizenReserveUsd,
          outstandingPrincipalUsd,
          recentGojoGiftsUsd,
        });
        const expected = +Math.max(
          0,
          lenderBalanceUsd - perCitizenReserveUsd - outstandingPrincipalUsd - recentGojoGiftsUsd
        ).toFixed(6);
        assert.ok(result >= 0, `result ${result} must never be negative`);
        assert.equal(result, expected);
      }
    ),
    { numRuns: 500 }
  );
});

// ===========================================================================
// PROP-101c (computeLenderAvailableUsd) — fail-closed for ANY malformed lenderBalanceUsd, never throws
// ===========================================================================

test("PROP-101c (property): computeLenderAvailableUsd never throws and always returns a finite, non-negative number for ANY malformed lenderBalanceUsd (NaN/Infinity/-Infinity/undefined/negative)", () => {
  const malformed = fc.oneof(
    fc.constant(NaN),
    fc.constant(undefined),
    fc.constant(Infinity),
    fc.constant(-Infinity),
    usd(-1e9, -0.01)
  );
  fc.assert(
    fc.property(malformed, (lenderBalanceUsd) => {
      let result;
      assert.doesNotThrow(() => {
        result = computeLenderAvailableUsd({ lenderBalanceUsd });
      });
      assert.ok(Number.isFinite(result), `result must be finite, got ${result}`);
      assert.ok(result >= 0, `result must be non-negative (fail-closed), got ${result}`);
    }),
    { numRuns: 200 }
  );
});

// ===========================================================================
// PROP-101g (sumOutstandingPrincipalUsd) — per-row floor at 0, for ANY randomly generated repaid_usd
// including extreme negatives and repaid_usd far exceeding principal_usd.
// ===========================================================================

test("PROP-101g (property): sumOutstandingPrincipalUsd's per-row contribution is ALWAYS max(0, principal_usd - repaid_usd) — never negative, for ANY repaid_usd including extreme negatives or values far exceeding principal_usd", () => {
  fc.assert(
    fc.property(
      usd(0, 10000),
      usd(-1e9, 1e9),
      fc.constantFrom("active", "defaulted"),
      (principal_usd, repaid_usd, status) => {
        const rows = [{ loan_id: "loan_L1_1", lender_id: "L1", status, principal_usd, repaid_usd }];
        const result = sumOutstandingPrincipalUsd(rows, "L1");
        const expected = +Math.max(0, principal_usd - repaid_usd).toFixed(6);
        assert.ok(result >= 0, `result ${result} must never be negative regardless of repaid_usd=${repaid_usd}`);
        assert.equal(result, expected);
      }
    ),
    { numRuns: 500 }
  );
});

// ===========================================================================
// PROP-104a (computeTotalDueUsd) — exact formula for ANY non-negative principal
// ===========================================================================

test("PROP-104a (property): computeTotalDueUsd(principal) === +(principal * 1.10).toFixed(6) for ANY non-negative principal in the realistic loan range", () => {
  // The exact-formula equality below is the whole of PROP-104a's own requirement. A "result >=
  // principalUsd" sanity check was deliberately NOT added here: at sub-cent magnitudes, comparing a
  // .toFixed(6)-rounded result against an un-rounded principalUsd carriying its own floating-point
  // representation noise produces false failures unrelated to computeTotalDueUsd's actual correctness
  // (both sides round to the same 6-decimal value, but raw un-rounded principalUsd can carry a tiny
  // epsilon past it) — a test-harness artifact, not a property of the function under test.
  fc.assert(
    fc.property(usd(0, 10000), (principalUsd) => {
      const result = computeTotalDueUsd(principalUsd);
      const expected = +(principalUsd * 1.1).toFixed(6);
      assert.equal(result, expected);
    }),
    { numRuns: 500 }
  );
});

// ===========================================================================
// PROP-105e (computeLoanCapUsd) — fail-closed to firstLoanUsd for ANY malformed successfulOnTimeRepayments
// ===========================================================================

test("PROP-105e (property): computeLoanCapUsd treats ANY malformed successfulOnTimeRepayments (negative/non-integer/NaN/Infinity) as 0 — always returns exactly firstLoanUsd, never throws, never a larger unearned cap", () => {
  const malformed = fc.oneof(
    fc.integer({ min: -100000, max: -1 }),
    fc.double({ min: 0.0001, max: 99, noNaN: true }).filter((n) => !Number.isInteger(n)),
    fc.constant(NaN),
    fc.constant(Infinity),
    fc.constant(-Infinity)
  );
  fc.assert(
    fc.property(malformed, (successfulOnTimeRepayments) => {
      let result;
      assert.doesNotThrow(() => {
        result = computeLoanCapUsd({ successfulOnTimeRepayments });
      });
      assert.equal(result, 0.02, `malformed input ${successfulOnTimeRepayments} must floor to firstLoanUsd (0.02), got ${result}`);
    }),
    { numRuns: 300 }
  );
});

// ===========================================================================
// PROP-105b (computeLoanCapUsd) — monotonic, clamped doubling ladder for ANY n in a wide range
// ===========================================================================

test("PROP-105b (property): computeLoanCapUsd is monotonically non-decreasing in n, always <= maxLoanUsd, and equals firstLoanUsd*2^n exactly until the cap is reached — for ANY n from 0 to 40", () => {
  fc.assert(
    fc.property(fc.integer({ min: 0, max: 40 }), (n) => {
      const result = computeLoanCapUsd({ successfulOnTimeRepayments: n });
      const uncapped = 0.02 * 2 ** n;
      const expected = +Math.min(5.0, uncapped).toFixed(6);
      assert.equal(result, expected);
      assert.ok(result <= 5.0, "result must never exceed the max loan cap");
      if (n > 0) {
        const prev = computeLoanCapUsd({ successfulOnTimeRepayments: n - 1 });
        assert.ok(result >= prev, `cap at n=${n} (${result}) must be >= cap at n=${n - 1} (${prev}) — monotonic ladder`);
      }
    }),
    { numRuns: 41 }
  );
});

// ===========================================================================
// PROP-114b (evaluateOverallDefaultKillSwitch) — exact >= boundary at RECENT_DEFAULT_LOSS_THRESHOLD_USD,
// for ARBITRARY otherwise-healthy sampleSize/defaultRateUsd combinations (proves the absolute-loss branch
// is genuinely independent of sampleSize/ratio, across a range, not just the single fixed fixture already
// in lending-gate.test.mjs).
// ===========================================================================

test("PROP-114b (property): evaluateOverallDefaultKillSwitch's absolute-loss branch trips (paused:true) for ANY totalRecentDefaultLossUsd >= RECENT_DEFAULT_LOSS_THRESHOLD_USD, and does NOT trip for ANY value strictly below it, even when sampleSize/defaultRateUsd/totalDefaultedUsd are otherwise healthy", () => {
  const healthySampleSize = fc.integer({ min: 10, max: 100000 });
  const healthyRate = fc.double({ min: 0, max: 0.19, noNaN: true }); // strictly below the 0.20 ratio threshold
  fc.assert(
    fc.property(
      healthySampleSize,
      healthyRate,
      usd(RECENT_DEFAULT_LOSS_THRESHOLD_USD, RECENT_DEFAULT_LOSS_THRESHOLD_USD + 1e6),
      (sampleSize, defaultRateUsd, totalRecentDefaultLossUsd) => {
        const result = evaluateOverallDefaultKillSwitch({
          totalIssuedUsd: 1000,
          totalDefaultedUsd: 0,
          defaultRateUsd,
          sampleSize,
          totalRecentDefaultLossUsd,
        });
        assert.equal(result.paused, true, `totalRecentDefaultLossUsd=${totalRecentDefaultLossUsd} >= threshold must pause even with a healthy ratio/sample`);
      }
    ),
    { numRuns: 300 }
  );
  fc.assert(
    fc.property(
      healthySampleSize,
      healthyRate,
      usd(0, RECENT_DEFAULT_LOSS_THRESHOLD_USD - 0.000001),
      (sampleSize, defaultRateUsd, totalRecentDefaultLossUsd) => {
        const result = evaluateOverallDefaultKillSwitch({
          totalIssuedUsd: 1000,
          totalDefaultedUsd: 0,
          defaultRateUsd,
          sampleSize,
          totalRecentDefaultLossUsd,
        });
        assert.equal(result.paused, false, `totalRecentDefaultLossUsd=${totalRecentDefaultLossUsd} strictly below threshold, with a healthy ratio/sample and totalDefaultedUsd:0, must not pause`);
      }
    ),
    { numRuns: 300 }
  );
});

// ===========================================================================
// PROP-114g (computeOverallDefaultRateUsd / computeRecentDefaultLossUsd) — repaid_usd floor holds for
// ANY randomly generated principal_usd/repaid_usd pair on a defaulted row, generalizing the single
// FIND-C02 fixture (principal:1, repaid:-5) to the full domain.
// ===========================================================================

test("PROP-114g (property): a defaulted row's loss contribution to BOTH computeOverallDefaultRateUsd.totalDefaultedUsd and computeRecentDefaultLossUsd.totalRecentDefaultLossUsd is ALWAYS max(0, principal_usd - max(0, repaid_usd)) — for ANY repaid_usd, including extreme negatives, a negative repaid_usd is indistinguishable from repaid_usd:0 (never inflates the loss beyond principal_usd), and the contribution never exceeds principal_usd", () => {
  const nowMs = Date.now();
  fc.assert(
    fc.property(usd(0, 10000), usd(-1e9, 1e9), (principal_usd, repaid_usd) => {
      const row = {
        loan_id: "loan_L1_1",
        status: "defaulted",
        principal_usd,
        repaid_usd,
        defaulted_ms: nowMs - 1000,
      };
      const rateResult = computeOverallDefaultRateUsd({ loanRows: [row] });
      const lossResult = computeRecentDefaultLossUsd({ loanRows: [row], nowMs });
      // The implementation floors repaid_usd at 0 BEFORE subtracting (FIND-C02) — a negative repaid_usd
      // must never SUBTRACT a negative and thereby INFLATE the contribution beyond principal_usd itself.
      const expected = +Math.max(0, principal_usd - Math.max(0, repaid_usd)).toFixed(6);
      assert.equal(rateResult.totalDefaultedUsd, expected);
      assert.equal(lossResult.totalRecentDefaultLossUsd, expected);
      // tolerance matches the .toFixed(6) rounding convention itself (up to +/-0.0000005 at the boundary)
      assert.ok(rateResult.totalDefaultedUsd >= 0 && rateResult.totalDefaultedUsd <= principal_usd + 1e-6);
      assert.ok(lossResult.totalRecentDefaultLossUsd >= 0 && lossResult.totalRecentDefaultLossUsd <= principal_usd + 1e-6);
      // the FIND-C02 invariant itself, generalized: any negative repaid_usd is indistinguishable from 0
      if (repaid_usd < 0) {
        const zeroRepaidRow = { ...row, repaid_usd: 0 };
        const zeroRate = computeOverallDefaultRateUsd({ loanRows: [zeroRepaidRow] });
        const zeroLoss = computeRecentDefaultLossUsd({ loanRows: [zeroRepaidRow], nowMs });
        assert.equal(rateResult.totalDefaultedUsd, zeroRate.totalDefaultedUsd);
        assert.equal(lossResult.totalRecentDefaultLossUsd, zeroLoss.totalRecentDefaultLossUsd);
      }
    }),
    { numRuns: 500 }
  );
});

// ===========================================================================
// PROP-106m (resolveLoanLockAcquisitionOrder) — deterministic lexicographic ordering for ANY pair of
// lender/borrower id strings, generalizing the two fixed-direction fixtures already in
// lending-gate.test.mjs.
// ===========================================================================

test("PROP-106m (property): resolveLoanLockAcquisitionOrder always returns [outerKey, innerKey] with outerKey lexicographically <= innerKey, for ANY pair of lenderId/borrowerId strings, in either input order", () => {
  const idString = fc.string({ minLength: 1, maxLength: 20 }).filter((s) => s.trim().length > 0);
  fc.assert(
    fc.property(idString, idString, (lenderId, borrowerId) => {
      const [outerKey, innerKey] = resolveLoanLockAcquisitionOrder(lenderId, borrowerId);
      assert.ok(outerKey <= innerKey, `outerKey "${outerKey}" must sort <= innerKey "${innerKey}"`);
      const expectedKeys = [`loan_${lenderId}`, `loan_borrower_${borrowerId}`].sort();
      assert.deepEqual([outerKey, innerKey], expectedKeys);
      // determinism: calling again with the SAME inputs always yields the SAME pair
      const again = resolveLoanLockAcquisitionOrder(lenderId, borrowerId);
      assert.deepEqual(again, [outerKey, innerKey]);
    }),
    { numRuns: 300 }
  );
});

// ===========================================================================
// PROP-102b (isBorrowerEligible) — the strict-< BORROWER_LOW_USD boundary holds across a swept range of
// balances, not merely the two fixed points (boundary, boundary-0.01) already in lending-gate.test.mjs.
// ===========================================================================

test("PROP-102b (property): isBorrowerEligible's condition (b) is a strict < BORROWER_LOW_USD comparison — for ANY balance in [0, 2*BORROWER_LOW_USD], eligible iff balance < BORROWER_LOW_USD, holding every other condition fixed at a passing state", () => {
  fc.assert(
    fc.property(usd(0, BORROWER_LOW_USD * 2), (borrowerBalanceUsd) => {
      const result = isBorrowerEligible({
        borrowerAgent: BASE_BORROWER,
        loanRows: [],
        borrowerId: "b1",
        borrowerBalanceUsd,
        lenderId: "L1",
      });
      if (borrowerBalanceUsd < BORROWER_LOW_USD) {
        assert.equal(result.eligible, true, `balance ${borrowerBalanceUsd} < BORROWER_LOW_USD must be eligible`);
      } else {
        assert.equal(result.eligible, false);
        assert.equal(result.reason, "not_broke_enough");
      }
    }),
    { numRuns: 500 }
  );
});
