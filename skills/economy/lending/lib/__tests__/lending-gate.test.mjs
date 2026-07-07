// node:test — lending-gate.mjs (Phase 2a RED, anicca-agent-lending REQ-101/102/104/105/106/109/114).
// RED phase: this file is written BEFORE ../lending-gate.mjs exists, so every import below is the
// first failing assertion (module not found) — this is the intended RED-phase signal. GREEN = Phase
// 2b implements ../lending-gate.mjs to make all of this pass, per
// .vcsdd/features/anicca-agent-lending/specs/behavioral-spec.md (REQ-101 through REQ-114) and
// specs/verification-architecture.md (PROP-101a..PROP-114f).
//
// Scope note: this file covers Tier 1 (pure-function unit tests) and Tier 1/2 mocked-wiring fixtures
// ONLY. Tier 0 structural/source-read obligations (PROP-103a, PROP-104b, PROP-105h, PROP-106d/i/m's
// own structural half, PROP-107a/b's structural half, PROP-109c/e/g, PROP-110a, PROP-111a/b, PROP-112a,
// PROP-113a, PROP-114c) are NOT runtime-testable against code that doesn't exist yet — those are
// verified in Phase 3 (vcsdd-adversary) by reading the real, production source directly. Tier 3 (live
// on-chain E2E, PROP-108a) is covered separately, live, once GREEN lands.
//
// REQ-113 (dependency-freshness gate) — dated re-read confirmation, recorded here per this
// requirement's own Phase-2a-artifact acceptance criterion (PROP-113a):
//   Re-read on 2026-07-08, immediately before writing this file, of
//   .vcsdd/features/anicca-agent-spawn/specs/behavioral-spec.md and state.json:
//     - state.json: currentPhase="1b", iterations={1a:2,1b:2}; a "1c" gate entry exists with
//       verdict:"FAIL" (iteration 13, 2026-07-07T14:28:33.892Z, findings FIND-1201/FIND-1202) — that
//       spec is STILL mid-VCSDD-pipeline, exactly as this feature's own Dependencies section expects.
//     - (a) pipeline shape: filterProductiveCitizens -> readCitizenBalances -> computeColonySurplusUsd
//       is STILL the real three-step shape (behavioral-spec.md lines ~396-458) — REQ-109's own
//       composition point (below) remains correctly targeted.
//     - (b) coLocatedWithCoordinator: STILL present on every citizens.json record (seeded `true` for
//       both of today's real citizens per REQ-703's own resolution, `false` for every REQ-305-spawned
//       child) — REQ-112's own eligibility check (out of this file's scope; see lending-gate's own
//       Tier-0 REQ-112 checks in Phase 3) remains correctly targeted.
//   Nothing else material changed since this feature's own iteration-3 Dependencies-section citation.
import { test } from "node:test";
import assert from "node:assert/strict";
import { isSelfFunded } from "../../../../_shared/lib/is-self-funded.mjs";
import {
  GOJO_SENDER_ID,
  BORROWER_LOW_USD,
  FIRST_LOAN_USD,
  LOAN_INTEREST_RATE,
  LOAN_REPAYMENT_WINDOW_DAYS,
  RECENT_DEFAULT_LOSS_THRESHOLD_USD,
  RECENT_DEFAULT_LOSS_WINDOW_DAYS,
  computeLenderAvailableUsd,
  sumOutstandingPrincipalUsd,
  sumRecentGojoGiftsUsd,
  isBorrowerEligible,
  computeTotalDueUsd,
  computeLoanCapUsd,
  countSuccessfulOnTimeRepayments,
  decideLoan,
  computeColdStartRepaymentRate,
  evaluateColdStartKillSwitch,
  computeOverallDefaultRateUsd,
  computeRecentDefaultLossUsd,
  evaluateOverallDefaultKillSwitch,
  detectDefaultedLoans,
  adjustBalancesForOutstandingDebt,
  nextLoanSequenceForLender,
  resolveLoanLockAcquisitionOrder,
} from "../lending-gate.mjs";

const BASE_BORROWER = { wallet: { evm: true }, fuel: { provider: "x402" }, humanDependencies: [] };
const NOT_SELF_FUNDED_BORROWER = { wallet: { evm: true }, fuel: { provider: "anthropic-subscription" }, humanDependencies: [] };

// ===========================================================================
// Constants — REQ-101/102/104/114's own declared, independently-owned values.
// ===========================================================================
test("constants: GOJO_SENDER_ID/BORROWER_LOW_USD/FIRST_LOAN_USD/LOAN_INTEREST_RATE/LOAN_REPAYMENT_WINDOW_DAYS/RECENT_DEFAULT_LOSS_THRESHOLD_USD/RECENT_DEFAULT_LOSS_WINDOW_DAYS have the exact values this spec fixes", () => {
  assert.equal(GOJO_SENDER_ID, "anicca-a3cdd4");
  assert.equal(BORROWER_LOW_USD, 0.5);
  assert.equal(FIRST_LOAN_USD, 0.02);
  assert.equal(LOAN_INTEREST_RATE, 0.1);
  assert.equal(LOAN_REPAYMENT_WINDOW_DAYS, 14);
  assert.equal(RECENT_DEFAULT_LOSS_THRESHOLD_USD, 5.0);
  assert.equal(RECENT_DEFAULT_LOSS_WINDOW_DAYS, 14);
});

// ===========================================================================
// REQ-101 — computeLenderAvailableUsd / sumOutstandingPrincipalUsd / sumRecentGojoGiftsUsd
// ===========================================================================

test("PROP-101a: computeLenderAvailableUsd(balance=8, reserve=5, outstanding=1) === 2", () => {
  assert.equal(
    computeLenderAvailableUsd({ lenderBalanceUsd: 8, perCitizenReserveUsd: 5, outstandingPrincipalUsd: 1 }),
    2
  );
});

test("PROP-101a: perCitizenReserveUsd defaults to 5.00 and recentGojoGiftsUsd defaults to 0 when omitted", () => {
  assert.equal(computeLenderAvailableUsd({ lenderBalanceUsd: 8, outstandingPrincipalUsd: 1 }), 2);
});

test("PROP-101a: result never goes negative — clamped at 0 (max(0, ...))", () => {
  assert.equal(
    computeLenderAvailableUsd({ lenderBalanceUsd: 3, perCitizenReserveUsd: 5, outstandingPrincipalUsd: 0 }),
    0
  );
});

test("PROP-101b: a citizen failing isSelfFunded() contributes 0 available surplus regardless of raw balance magnitude", () => {
  const richButNotSelfFunded = { wallet: { evm: true }, fuel: { provider: "anthropic-subscription" }, humanDependencies: [] };
  const lenderSelfFunded = isSelfFunded(richButNotSelfFunded);
  const available = computeLenderAvailableUsd({ lenderBalanceUsd: 1000, perCitizenReserveUsd: 5, outstandingPrincipalUsd: 0 });
  const eligibleAsLender = lenderSelfFunded && available > 0;
  assert.equal(lenderSelfFunded, false);
  assert.equal(eligibleAsLender, false, "a non-self-funded lender must be excluded regardless of computed available surplus");
});

test("PROP-101c: missing/non-finite/negative lenderBalanceUsd yields 0 available surplus, never throws", () => {
  assert.doesNotThrow(() => {
    assert.equal(computeLenderAvailableUsd({ lenderBalanceUsd: NaN, perCitizenReserveUsd: 5, outstandingPrincipalUsd: 0 }), 0);
    assert.equal(computeLenderAvailableUsd({ lenderBalanceUsd: undefined, perCitizenReserveUsd: 5, outstandingPrincipalUsd: 0 }), 0);
    assert.equal(computeLenderAvailableUsd({ lenderBalanceUsd: -5, perCitizenReserveUsd: 5, outstandingPrincipalUsd: 0 }), 0);
  });
});

test("PROP-101d: sumOutstandingPrincipalUsd reduces to one effective row per loan_id (last-write-wins) and includes a defaulted row's unrecovered principal", () => {
  const rows = [
    { loan_id: "loan_L1_1", lender_id: "L1", status: "provisioning", principal_usd: 1, repaid_usd: 0 },
    { loan_id: "loan_L1_1", lender_id: "L1", status: "active", principal_usd: 1, repaid_usd: 0 },
    { loan_id: "loan_L1_1", lender_id: "L1", status: "defaulted", principal_usd: 1, repaid_usd: 0.3 },
    { loan_id: "loan_L1_2", lender_id: "L1", status: "repaid", principal_usd: 0.5, repaid_usd: 0.55 },
    { loan_id: "loan_L2_1", lender_id: "L2", status: "active", principal_usd: 2, repaid_usd: 0 },
  ];
  assert.equal(sumOutstandingPrincipalUsd(rows, "L1"), 0.7, "only the LAST row per loan_id counts (defaulted, 1-0.3=0.7); a repaid row contributes 0");
  assert.equal(sumOutstandingPrincipalUsd(rows, "L2"), 2, "L2's own row is independent of L1's");
});

test("PROP-101e: sumOutstandingPrincipalUsd is unaffected by any citizen-level isSelfFunded()/agent field — a lender's later isSelfFunded()=false never retroactively changes an already-active loan's contribution", () => {
  const rows = [{ loan_id: "loan_L1_1", lender_id: "L1", status: "active", principal_usd: 0.02, repaid_usd: 0 }];
  // sumOutstandingPrincipalUsd takes only (loanRows, lenderId) — no isSelfFunded/agent input at all, so
  // a lender's later loss of self-funded status structurally cannot retroactively alter this sum.
  assert.equal(sumOutstandingPrincipalUsd(rows, "L1"), 0.02);
});

test("PROP-101f: sumRecentGojoGiftsUsd sums only in-window, amount_usd>0 rows, and is GATED to lenderId===GOJO_SENDER_ID (resolves FIND-102)", () => {
  const nowMs = 1781450000000;
  const gojoLogRows = [
    { ts: new Date(nowMs - 3600 * 1000).toISOString(), decision: { amount_usd: 1 } }, // 1h ago, in-window
    { ts: new Date(nowMs - 30 * 3600 * 1000).toISOString(), decision: { amount_usd: 5 } }, // 30h ago, OUT of window
    { ts: new Date(nowMs - 3600 * 1000).toISOString(), decision: { amount_usd: 0 } }, // in-window but zero amount
  ];
  assert.equal(sumRecentGojoGiftsUsd(gojoLogRows, nowMs, 24, GOJO_SENDER_ID), 1);
  assert.equal(
    computeLenderAvailableUsd({ lenderBalanceUsd: 8, perCitizenReserveUsd: 5, outstandingPrincipalUsd: 0, recentGojoGiftsUsd: 1 }),
    2
  );
  assert.equal(
    sumRecentGojoGiftsUsd(gojoLogRows, nowMs, 24, "some-other-lender"),
    0,
    "any lenderId other than GOJO_SENDER_ID must get 0, regardless of gojoLogRows content (resolves FIND-102's misattribution risk)"
  );
});

test("PROP-101f: lookbackHours defaults to 24 when omitted", () => {
  const nowMs = 1781450000000;
  const gojoLogRows = [{ ts: new Date(nowMs - 3600 * 1000).toISOString(), decision: { amount_usd: 2 } }];
  assert.equal(sumRecentGojoGiftsUsd(gojoLogRows, nowMs, undefined, GOJO_SENDER_ID), 2);
});

// ===========================================================================
// REQ-102 — isBorrowerEligible
// ===========================================================================

test("PROP-102a: isBorrowerEligible returns eligible:true only when ALL of self-funded/broke/no-open-obligation/not-self-loan hold", () => {
  const result = isBorrowerEligible({
    borrowerAgent: BASE_BORROWER,
    loanRows: [],
    borrowerId: "b1",
    borrowerBalanceUsd: 0.49,
    lenderId: "L1",
  });
  assert.equal(result.eligible, true);
  assert.equal(result.reason, "ok");
});

test("PROP-102a: condition (a) failing — not self-funded — rejects regardless of balance/history", () => {
  const result = isBorrowerEligible({
    borrowerAgent: NOT_SELF_FUNDED_BORROWER,
    loanRows: [],
    borrowerId: "b1",
    borrowerBalanceUsd: 0.01,
    lenderId: "L1",
  });
  assert.equal(result.eligible, false);
  assert.equal(result.reason, "not_self_funded");
});

test("PROP-102a/PROP-102b: condition (b) failing — balance at or above BORROWER_LOW_USD, strict < boundary", () => {
  const atBoundary = isBorrowerEligible({ borrowerAgent: BASE_BORROWER, loanRows: [], borrowerId: "b1", borrowerBalanceUsd: 0.5, lenderId: "L1" });
  assert.equal(atBoundary.eligible, false, "exactly $0.50 is NOT eligible — strict less-than");
  assert.equal(atBoundary.reason, "not_broke_enough");

  const justBelow = isBorrowerEligible({ borrowerAgent: BASE_BORROWER, loanRows: [], borrowerId: "b1", borrowerBalanceUsd: 0.49, lenderId: "L1" });
  assert.equal(justBelow.eligible, true, "$0.49 (just below the boundary) IS eligible");
});

test("PROP-102a/PROP-102c: condition (c) failing — an active (not overdue) loan blocks a second loan regardless of how low the balance is", () => {
  const rows = [{ loan_id: "loan_L1_1", borrower_id: "b1", lender_id: "L1", status: "active", principal_usd: 0.02, repaid_usd: 0 }];
  const result = isBorrowerEligible({ borrowerAgent: BASE_BORROWER, loanRows: rows, borrowerId: "b1", borrowerBalanceUsd: 0.01, lenderId: "L2" });
  assert.equal(result.eligible, false);
  assert.equal(result.reason, "outstanding_loan");
});

test("PROP-102d: a brand-new citizen with ZERO rows in loans.jsonl passes condition (c) vacuously (the cold-start entry point)", () => {
  const result = isBorrowerEligible({ borrowerAgent: BASE_BORROWER, loanRows: [], borrowerId: "brand-new", borrowerBalanceUsd: 0.01, lenderId: "L1" });
  assert.equal(result.eligible, true);
  assert.equal(result.reason, "ok");
});

test("PROP-102e: a self-loan candidate (lenderId===borrowerId) is rejected FIRST — before (a)/(b)/(c) — even when every other condition would otherwise pass (resolves FIND-402)", () => {
  const result = isBorrowerEligible({
    borrowerAgent: BASE_BORROWER, // isSelfFunded() true
    loanRows: [], // zero outstanding obligations
    borrowerId: "same-citizen",
    borrowerBalanceUsd: 0.01, // below BORROWER_LOW_USD
    lenderId: "same-citizen", // === borrowerId
  });
  assert.equal(result.eligible, false);
  assert.equal(result.reason, "self_loan");
});

test("REQ-109/PROP-109d: a late-but-eventual full repayment after a defaulted row restores eligibility immediately (last-write-wins) but does NOT grow successfulOnTimeRepayments", () => {
  const rows = [
    { loan_id: "loan_L1_1", borrower_id: "b1", lender_id: "L1", status: "active", principal_usd: 0.02, total_due_usd: 0.022, repaid_usd: 0, due_ms: 1000, issued_ms: 0 },
    { loan_id: "loan_L1_1", borrower_id: "b1", lender_id: "L1", status: "defaulted", principal_usd: 0.02, total_due_usd: 0.022, repaid_usd: 0, defaulted_ms: 1500 },
    { loan_id: "loan_L1_1", borrower_id: "b1", lender_id: "L1", status: "repaid", on_time: false, principal_usd: 0.02, total_due_usd: 0.022, repaid_usd: 0.022 },
  ];
  const result = isBorrowerEligible({ borrowerAgent: BASE_BORROWER, loanRows: rows, borrowerId: "b1", borrowerBalanceUsd: 0.01, lenderId: "L2" });
  assert.equal(result.eligible, true, "the retroactive repaid row restores eligibility immediately");
  assert.equal(countSuccessfulOnTimeRepayments(rows, "b1"), 0, "a late (on_time:false) repayment never grows the reputation count");
});

test("REQ-107/PROP-107a: a Solana-only borrower (no wallet.evm) is excluded from borrower eligibility this increment — NOT because isSelfFunded() fails (it does not: solana presence alone satisfies isSelfFunded's own wallet leg)", () => {
  const solanaOnlyAgent = { wallet: { solana: true }, fuel: { provider: "x402" }, humanDependencies: [] };
  assert.equal(isSelfFunded(solanaOnlyAgent), true, "sanity: isSelfFunded() itself does NOT require evm specifically — solana alone passes");
  const result = isBorrowerEligible({ borrowerAgent: solanaOnlyAgent, loanRows: [], borrowerId: "b1", borrowerBalanceUsd: 0.01, lenderId: "L1" });
  assert.equal(result.eligible, false, "REQ-107's own chain/asset scope narrowing excludes a Solana-only citizen from borrower eligibility this increment");
});

// ===========================================================================
// REQ-104 — computeTotalDueUsd (loan terms: fixed, small, conservative, no variable market)
// ===========================================================================

test("PROP-104a: total_due_usd for FIRST_LOAN_USD (0.02) is exactly 0.022 (0.02 * 1.10, clamped)", () => {
  assert.equal(computeTotalDueUsd(FIRST_LOAN_USD), 0.022);
});

test("PROP-104a: total_due_usd for the max loan size (5.00) is exactly 5.5", () => {
  assert.equal(computeTotalDueUsd(5.0), 5.5);
});

test("PROP-104c: total_due_usd is computed once from principal only — calling it again later for the SAME principal never accrues additional interest (no penalty-interest mechanism this increment)", () => {
  const a = computeTotalDueUsd(0.02);
  const b = computeTotalDueUsd(0.02); // simulates re-deriving the SAME loan's total_due_usd after its due_ms has passed
  assert.equal(a, b);
});

// ===========================================================================
// REQ-105 — computeLoanCapUsd / countSuccessfulOnTimeRepayments / decideLoan /
//           computeColdStartRepaymentRate / evaluateColdStartKillSwitch
// ===========================================================================

test("PROP-105a: computeLoanCapUsd({successfulOnTimeRepayments:0}) === 0.02 — zero-collateral cold-start sizing", () => {
  assert.equal(computeLoanCapUsd({ successfulOnTimeRepayments: 0 }), 0.02);
});

test("PROP-105b: computeLoanCapUsd doubling ladder at n=1,7,8 produces 0.04, 2.56, 5.00 (capped, not 5.12)", () => {
  assert.equal(computeLoanCapUsd({ successfulOnTimeRepayments: 1 }), 0.04);
  assert.equal(computeLoanCapUsd({ successfulOnTimeRepayments: 7 }), 2.56);
  assert.equal(computeLoanCapUsd({ successfulOnTimeRepayments: 8 }), 5.0, "2^8 * 0.02 = 5.12, must be capped at maxLoanUsd=5.00");
});

test("PROP-105c: countSuccessfulOnTimeRepayments excludes any on_time:false or non-repaid row from its count", () => {
  const rows = [
    { loan_id: "loan_L1_1", borrower_id: "b1", status: "repaid", on_time: true },
    { loan_id: "loan_L1_2", borrower_id: "b1", status: "repaid", on_time: false },
    { loan_id: "loan_L1_3", borrower_id: "b1", status: "active" },
    { loan_id: "loan_L1_4", borrower_id: "b1", status: "defaulted" },
    { loan_id: "loan_L2_1", borrower_id: "other", status: "repaid", on_time: true },
  ];
  assert.equal(countSuccessfulOnTimeRepayments(rows, "b1"), 1);
});

test("PROP-105c: countSuccessfulOnTimeRepayments reduces to one effective row per loan_id (last-write-wins) before counting", () => {
  const rows = [
    { loan_id: "loan_L1_1", borrower_id: "b1", status: "provisioning" },
    { loan_id: "loan_L1_1", borrower_id: "b1", status: "active" },
    { loan_id: "loan_L1_1", borrower_id: "b1", status: "repaid", on_time: true },
  ];
  assert.equal(countSuccessfulOnTimeRepayments(rows, "b1"), 1, "a single loan_id must count once, using its last-appended row");
});

test("PROP-105d: decideLoan's eligibility is a plain >= comparison over already-computed numbers", () => {
  assert.equal(decideLoan({ lenderAvailableUsd: 2, loanAmountUsd: computeLoanCapUsd({ successfulOnTimeRepayments: 0 }) }).eligible, true);
  assert.equal(decideLoan({ lenderAvailableUsd: 0.01, loanAmountUsd: computeLoanCapUsd({ successfulOnTimeRepayments: 0 }) }).eligible, false);
});

test("PROP-105e: a malformed/negative/non-integer successfulOnTimeRepayments is treated as 0 (fail-closed), never a larger unearned cap, never throws", () => {
  assert.doesNotThrow(() => {
    assert.equal(computeLoanCapUsd({ successfulOnTimeRepayments: -1 }), FIRST_LOAN_USD);
    assert.equal(computeLoanCapUsd({ successfulOnTimeRepayments: NaN }), FIRST_LOAN_USD);
    assert.equal(computeLoanCapUsd({ successfulOnTimeRepayments: 1.5 }), FIRST_LOAN_USD);
  });
});

test("PROP-105f: computeColdStartRepaymentRate over 3 repaid + 1 defaulted + 1 still-active cold-start loans (5 distinct first-ever borrowers) returns {sampleSize:5, repaidCount:3, defaultedCount:1, pendingCount:1, rate:0.6}", () => {
  const rows = [
    { loan_id: "loan_L1_1", borrower_id: "b1", issued_ms: 100, status: "repaid", on_time: true },
    { loan_id: "loan_L1_2", borrower_id: "b2", issued_ms: 200, status: "repaid", on_time: true },
    { loan_id: "loan_L1_3", borrower_id: "b3", issued_ms: 300, status: "repaid", on_time: false },
    { loan_id: "loan_L1_4", borrower_id: "b4", issued_ms: 400, status: "defaulted" },
    { loan_id: "loan_L1_5", borrower_id: "b5", issued_ms: 500, status: "active" },
  ];
  const result = computeColdStartRepaymentRate({ loanRows: rows, n: 20 });
  assert.deepEqual(result, { sampleSize: 5, repaidCount: 3, defaultedCount: 1, pendingCount: 1, rate: 0.6 });
});

test("PROP-105f: zero cold-start loans -> rate:null, never a division-by-zero throw", () => {
  const result = computeColdStartRepaymentRate({ loanRows: [], n: 20 });
  assert.equal(result.sampleSize, 0);
  assert.equal(result.rate, null);
});

test("PROP-105f: a 'cold-start loan' is NOT synonymous with 'borrower's first-ever loan' — a borrower's SECOND loan (issued while successfulOnTimeRepayments is still 0, because the first was late) is ALSO counted, never deduplicated by borrower_id (resolves FIND-107)", () => {
  const rows = [
    { loan_id: "loan_L1_1", borrower_id: "b1", issued_ms: 100, status: "repaid", on_time: false },
    { loan_id: "loan_L1_2", borrower_id: "b1", issued_ms: 200, status: "active" },
  ];
  const result = computeColdStartRepaymentRate({ loanRows: rows, n: 20 });
  assert.equal(result.sampleSize, 2, "both of b1's own loans qualify as cold-start (successfulOnTimeRepayments=0 at each issuance)");
});

test("PROP-105g: evaluateColdStartKillSwitch — sampleSize>=10 AND rate<0.80 pauses", () => {
  assert.deepEqual(evaluateColdStartKillSwitch({ sampleSize: 10, rate: 0.7, defaultedCount: 3 }).paused, true);
});

test("PROP-105g: evaluateColdStartKillSwitch — sampleSize<10 AND a SINGLE default pauses, even if the raw rate is itself above 0.80", () => {
  assert.equal(evaluateColdStartKillSwitch({ sampleSize: 3, rate: 0.667, defaultedCount: 1 }).paused, true);
});

test("PROP-105g: evaluateColdStartKillSwitch — a healthy rate at a statistically-sized sample does not pause", () => {
  assert.equal(evaluateColdStartKillSwitch({ sampleSize: 15, rate: 0.87, defaultedCount: 2 }).paused, false);
});

test("PROP-105g: mocked-caller wiring — a paused cold-start kill-switch refuses a NEW cold-start request but leaves a concurrent, non-cold-start renewal for an established borrower UNAFFECTED", () => {
  function simulateColdStartGate({ successfulOnTimeRepayments, killSwitch }) {
    const isColdStart = successfulOnTimeRepayments === 0;
    if (isColdStart && killSwitch.paused) return { issued: false, reason: "cold_start_paused" };
    return { issued: true };
  }
  const killSwitch = evaluateColdStartKillSwitch({ sampleSize: 10, rate: 0.5, defaultedCount: 5 });
  assert.equal(killSwitch.paused, true);

  const coldStartAttempt = simulateColdStartGate({ successfulOnTimeRepayments: 0, killSwitch });
  assert.equal(coldStartAttempt.issued, false);
  assert.equal(coldStartAttempt.reason, "cold_start_paused");

  const establishedRenewalAttempt = simulateColdStartGate({ successfulOnTimeRepayments: 3, killSwitch });
  assert.equal(establishedRenewalAttempt.issued, true, "an established (non-cold-start) borrower's renewal must be unaffected by the cold-start-only kill-switch");
});

// ===========================================================================
// REQ-109 — detectDefaultedLoans / adjustBalancesForOutstandingDebt
// ===========================================================================

test("PROP-109a: detectDefaultedLoans flags exactly the loan_ids whose last-appended row is active, past due_ms, and repaid_usd < total_due_usd", () => {
  const nowMs = 10_000_000;
  const rows = [
    { loan_id: "loan_overdue", status: "active", due_ms: nowMs - 1000, repaid_usd: 0, total_due_usd: 0.022 },
    { loan_id: "loan_ontime_repaid", status: "repaid", on_time: true, due_ms: nowMs - 1000, repaid_usd: 0.022, total_due_usd: 0.022 },
    { loan_id: "loan_not_yet_due", status: "active", due_ms: nowMs + 100000, repaid_usd: 0, total_due_usd: 0.022 },
  ];
  assert.deepEqual(detectDefaultedLoans({ loanRows: rows, nowMs }), ["loan_overdue"]);
});

test("PROP-109b/PROP-109f: adjustBalancesForOutstandingDebt is a debt-proportional reduction, never a whole-citizen removal — SAME array length, only the defaulted borrower's own balance is reduced", () => {
  const citizens = [
    { id: "c1", balance: 50, wallet: { evm: true } },
    { id: "c2", balance: 10, wallet: { evm: true } },
  ];
  const loanRows = [{ loan_id: "loan_L1_1", borrower_id: "c1", lender_id: "L1", status: "defaulted", principal_usd: 0.022, repaid_usd: 0 }];
  const adjusted = adjustBalancesForOutstandingDebt({ citizens, loanRows });
  assert.equal(adjusted.length, 2, "no citizen is ever removed from the array");
  const c1 = adjusted.find((c) => c.id === "c1");
  const c2 = adjusted.find((c) => c.id === "c2");
  assert.equal(c1.balance, 49.978, "50 - 0.022 = 49.978, proving debt-proportional adjustment, NOT a full-balance exclusion (resolves FIND-204)");
  assert.equal(c2.balance, 10, "a citizen who is not a currently-defaulted borrower passes through with its balance UNCHANGED");
  assert.equal(c1.wallet.evm, true, "every OTHER field passes through unchanged (spread-copy, never a mutation)");
});

test("PROP-109f: when a citizen's own currently-defaulted debt EXCEEDS its current balance, the adjusted balance clamps at exactly 0, never negative", () => {
  const citizens = [{ id: "c1", balance: 0.01 }];
  const loanRows = [{ loan_id: "loan_L1_1", borrower_id: "c1", lender_id: "L1", status: "defaulted", principal_usd: 5.0, repaid_usd: 0 }];
  const adjusted = adjustBalancesForOutstandingDebt({ citizens, loanRows });
  assert.equal(adjusted[0].balance, 0);
});

test("adjustBalancesForOutstandingDebt does not mutate its own input citizens array (immutability convention)", () => {
  const citizens = [{ id: "c1", balance: 50 }];
  const loanRows = [{ loan_id: "loan_L1_1", borrower_id: "c1", lender_id: "L1", status: "defaulted", principal_usd: 0.022, repaid_usd: 0 }];
  const before = JSON.parse(JSON.stringify(citizens));
  adjustBalancesForOutstandingDebt({ citizens, loanRows });
  assert.deepEqual(citizens, before, "the input array/objects passed in must remain unchanged — a NEW array/objects are returned instead");
});

// ===========================================================================
// REQ-106 — nextLoanSequenceForLender / resolveLoanLockAcquisitionOrder
// ===========================================================================

test("PROP-106e (Tier-1 half): nextLoanSequenceForLender is namespaced per-lender — two different lenders never collide", () => {
  const rows = [
    { loan_id: "loan_lenderA_1", lender_id: "lenderA", status: "active" },
    { loan_id: "loan_lenderA_3", lender_id: "lenderA", status: "active" }, // gap-safe, mirrors child-spec.js::nextChildId
  ];
  assert.equal(nextLoanSequenceForLender(rows, "lenderA"), 4, "max existing suffix (3) + 1, gap-safe — never reuses a retired sequence number");
  assert.equal(nextLoanSequenceForLender(rows, "lenderB"), 1, "a lender with zero prior rows starts at 1, independent of lenderA's own sequence");
});

test("PROP-106e/PROP-106g/PROP-106h/PROP-106k: nextLoanSequenceForLender treats provisioning/disbursement_failed/active/disbursement_uncertain rows for the SAME loan_id as ONE already-claimed sequence number (last-write-wins) — never reuses n while unterminated", () => {
  const provisioningOnly = [{ loan_id: "loan_L1_1", lender_id: "L1", status: "provisioning" }];
  assert.equal(nextLoanSequenceForLender(provisioningOnly, "L1"), 2, "sequence 1 is already claimed by the provisioning row, even though it has no terminal follow-up yet");

  const uncertainOnly = [{ loan_id: "loan_L1_1", lender_id: "L1", status: "disbursement_uncertain" }];
  assert.equal(nextLoanSequenceForLender(uncertainOnly, "L1"), 2);
});

test("nextLoanSequenceForLender starts at 1 for a lender with zero rows at all", () => {
  assert.equal(nextLoanSequenceForLender([], "brand-new-lender"), 1);
});

test("PROP-106m: resolveLoanLockAcquisitionOrder returns the lexicographically-smaller lock key as outerKey, deterministically, for BOTH possible orderings", () => {
  const [outer1, inner1] = resolveLoanLockAcquisitionOrder("alice", "zed");
  assert.equal(outer1, "loan_alice", "'loan_alice' sorts before 'loan_borrower_zed' lexicographically");
  assert.equal(inner1, "loan_borrower_zed");

  const [outer2, inner2] = resolveLoanLockAcquisitionOrder("zed", "a");
  assert.equal(outer2, "loan_borrower_a", "'loan_borrower_a' sorts before 'loan_zed' lexicographically");
  assert.equal(inner2, "loan_zed");
});

test("resolveLoanLockAcquisitionOrder is deterministic and pure — same inputs always yield the same ordered pair", () => {
  const a = resolveLoanLockAcquisitionOrder("lenderX", "borrowerY");
  const b = resolveLoanLockAcquisitionOrder("lenderX", "borrowerY");
  assert.deepEqual(a, b);
});

// ===========================================================================
// REQ-114 — computeOverallDefaultRateUsd / computeRecentDefaultLossUsd / evaluateOverallDefaultKillSwitch
// ===========================================================================

test("PROP-114a: computeOverallDefaultRateUsd is DOLLAR-weighted — a single large default dominates the rate even though it is a small fraction by loan COUNT", () => {
  const rows = [];
  for (let i = 0; i < 8; i++) {
    rows.push({ loan_id: `loan_cold_${i}`, borrower_id: `b${i}`, status: "repaid", principal_usd: 0.02, repaid_usd: 0.022 });
  }
  rows.push({ loan_id: "loan_big_1", borrower_id: "bBig", status: "defaulted", principal_usd: 5.0, repaid_usd: 0 });
  const result = computeOverallDefaultRateUsd({ loanRows: rows });
  assert.equal(result.sampleSize, 9);
  assert.equal(result.totalIssuedUsd, 5.16);
  assert.equal(result.totalDefaultedUsd, 5.0);
  assert.ok(Math.abs(result.defaultRateUsd - 0.969) < 0.001);
});

test("PROP-114a: zero terminal loans -> {totalIssuedUsd:0, totalDefaultedUsd:0, defaultRateUsd:null, sampleSize:0}, never a throw", () => {
  assert.deepEqual(computeOverallDefaultRateUsd({ loanRows: [] }), { totalIssuedUsd: 0, totalDefaultedUsd: 0, defaultRateUsd: null, sampleSize: 0 });
});

test("PROP-114a: non-terminal rows (active/provisioning/disbursement_failed/disbursement_uncertain) are excluded from sampleSize entirely", () => {
  const rows = [{ loan_id: "loan_pending", borrower_id: "b1", status: "active", principal_usd: 1, repaid_usd: 0 }];
  const result = computeOverallDefaultRateUsd({ loanRows: rows });
  assert.equal(result.sampleSize, 0);
});

test("PROP-114b: evaluateOverallDefaultKillSwitch — the single-large-default-while-small-sample branch pauses", () => {
  assert.equal(
    evaluateOverallDefaultKillSwitch({ sampleSize: 9, totalIssuedUsd: 5.16, totalDefaultedUsd: 5.0, defaultRateUsd: 0.969, totalRecentDefaultLossUsd: 5.0 }).paused,
    true
  );
});

test("PROP-114b: evaluateOverallDefaultKillSwitch — a healthy aggregate loss rate at a statistically-sized sample does not pause", () => {
  assert.equal(
    evaluateOverallDefaultKillSwitch({ sampleSize: 20, totalIssuedUsd: 10.0, totalDefaultedUsd: 0.5, defaultRateUsd: 0.05, totalRecentDefaultLossUsd: 0.5 }).paused,
    false
  );
});

test("PROP-114b: evaluateOverallDefaultKillSwitch — a loss rate above 0.20 at a statistically-sized sample pauses", () => {
  assert.equal(
    evaluateOverallDefaultKillSwitch({ sampleSize: 20, totalIssuedUsd: 10.0, totalDefaultedUsd: 3.0, defaultRateUsd: 0.3, totalRecentDefaultLossUsd: 3.0 }).paused,
    true
  );
});

test("PROP-114b: the THIRD, absolute-loss branch pauses independently of sampleSize — a healthy ratio at a LARGE sample still pauses once totalRecentDefaultLossUsd alone crosses its own threshold (resolves FIND-602/FIND-701, >= not >)", () => {
  assert.equal(
    evaluateOverallDefaultKillSwitch({ sampleSize: 50, totalIssuedUsd: 200, totalDefaultedUsd: 4.0, defaultRateUsd: 0.02, totalRecentDefaultLossUsd: 5.01 }).paused,
    true
  );
  assert.equal(
    evaluateOverallDefaultKillSwitch({ sampleSize: 50, totalIssuedUsd: 200, totalDefaultedUsd: 4.0, defaultRateUsd: 0.02, totalRecentDefaultLossUsd: 5.0 }).paused,
    true,
    "a bust-out landing EXACTLY at RECENT_DEFAULT_LOSS_THRESHOLD_USD (5.00) must trip via >=, not strict > (resolves FIND-701)"
  );
});

test("PROP-114d: evaluateColdStartKillSwitch=false but evaluateOverallDefaultKillSwitch=true for the SAME request still refuses issuance — the two kill-switches are independent, ADDITIVE gates", () => {
  function simulateIssuanceGate({ coldStartPaused, overallPaused }) {
    if (coldStartPaused) return { issued: false, reason: "cold_start_paused" };
    if (overallPaused) return { issued: false, reason: "overall_default_paused" };
    return { issued: true };
  }
  const coldStart = evaluateColdStartKillSwitch({ sampleSize: 15, rate: 0.9, defaultedCount: 0 });
  const overall = evaluateOverallDefaultKillSwitch({ sampleSize: 9, totalIssuedUsd: 5.16, totalDefaultedUsd: 5.0, defaultRateUsd: 0.969, totalRecentDefaultLossUsd: 5.0 });
  assert.equal(coldStart.paused, false);
  assert.equal(overall.paused, true);
  const gate = simulateIssuanceGate({ coldStartPaused: coldStart.paused, overallPaused: overall.paused });
  assert.equal(gate.issued, false);
  assert.equal(gate.reason, "overall_default_paused");
});

test("PROP-114e: computeRecentDefaultLossUsd sums only in-window, still-defaulted (last-write-wins) rows' unrecovered loss — excludes out-of-window rows and rows retroactively corrected to repaid", () => {
  const nowMs = 100_000_000;
  const windowDays = 14;
  const inWindowMs = nowMs - 5 * 86400000;
  const outWindowMs = nowMs - 20 * 86400000;
  const rows = [
    { loan_id: "loan_a", status: "defaulted", principal_usd: 5.0, repaid_usd: 0, defaulted_ms: inWindowMs },
    { loan_id: "loan_b", status: "defaulted", principal_usd: 2.0, repaid_usd: 0, defaulted_ms: outWindowMs },
    { loan_id: "loan_c", status: "defaulted", principal_usd: 3.0, repaid_usd: 0, defaulted_ms: inWindowMs },
    { loan_id: "loan_c", status: "repaid", on_time: false, principal_usd: 3.0, repaid_usd: 3.3 }, // retroactive correction — last-write-wins excludes it
  ];
  const result = computeRecentDefaultLossUsd({ loanRows: rows, nowMs, windowDays });
  assert.equal(result.totalRecentDefaultLossUsd, 5.0, "only loan_a's in-window, still-defaulted row counts — loan_b is out of window, loan_c was retroactively repaid");
});

test("PROP-114e: multiple small in-window defaults correctly ACCUMULATE (never merely the single largest)", () => {
  const nowMs = 100_000_000;
  const inWindowMs = nowMs - 1 * 86400000;
  const rows = [
    { loan_id: "loan_a", status: "defaulted", principal_usd: 2.0, repaid_usd: 0, defaulted_ms: inWindowMs },
    { loan_id: "loan_b", status: "defaulted", principal_usd: 2.0, repaid_usd: 0, defaulted_ms: inWindowMs },
    { loan_id: "loan_c", status: "defaulted", principal_usd: 2.0, repaid_usd: 0, defaulted_ms: inWindowMs },
  ];
  const result = computeRecentDefaultLossUsd({ loanRows: rows, nowMs, windowDays: 14 });
  assert.equal(result.totalRecentDefaultLossUsd, 6.0);
});

test("PROP-114f: volume-dilution-defeat proof — 9 unrelated healthy repaid loans dilute the RATIO below 0.20, but the ABSOLUTE recent-loss signal still catches the single bust-out default", () => {
  const nowMs = 100_000_000;
  const inWindowMs = nowMs - 1 * 86400000;
  const rows = [];
  for (let i = 0; i < 9; i++) {
    rows.push({ loan_id: `loan_healthy_${i}`, borrower_id: `b${i}`, status: "repaid", principal_usd: 5.0, repaid_usd: 5.55 });
  }
  rows.push({ loan_id: "loan_bustout", borrower_id: "bBust", status: "defaulted", principal_usd: 5.0, repaid_usd: 0, defaulted_ms: inWindowMs });

  const ratio = computeOverallDefaultRateUsd({ loanRows: rows });
  assert.equal(ratio.defaultRateUsd, 0.1, "the ratio ALONE is below the 0.20 threshold — this is the exact dilution failure mode FIND-602 identifies");

  const recentLoss = computeRecentDefaultLossUsd({ loanRows: rows, nowMs, windowDays: 14 });
  assert.equal(recentLoss.totalRecentDefaultLossUsd, 5.0);

  const killSwitch = evaluateOverallDefaultKillSwitch({
    totalIssuedUsd: ratio.totalIssuedUsd,
    totalDefaultedUsd: ratio.totalDefaultedUsd,
    defaultRateUsd: ratio.defaultRateUsd,
    sampleSize: ratio.sampleSize,
    totalRecentDefaultLossUsd: recentLoss.totalRecentDefaultLossUsd,
  });
  assert.equal(killSwitch.paused, true, "the NEW absolute-loss signal catches what the ratio alone would miss due to volume dilution (resolves FIND-602)");
});
