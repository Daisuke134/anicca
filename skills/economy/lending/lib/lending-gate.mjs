// economy/lending/lib/lending-gate.mjs — pure core (zero I/O) for anicca-agent-lending REQ-101,
// REQ-102, REQ-104, REQ-105, REQ-106 (pure helpers only), REQ-109, REQ-114. Every function here is
// deterministic arithmetic/boolean logic over already-known bookkeeping facts (REQ-103: no model
// judgment, no LLM call, no heuristic scoring beyond the declared reputation ladder) — see
// .vcsdd/features/anicca-agent-lending/specs/behavioral-spec.md (REQ-101..REQ-114) and
// specs/verification-architecture.md (PROP-101a..PROP-114g).
import { isSelfFunded } from "../../../_shared/lib/is-self-funded.mjs";

// ===========================================================================
// Constants (REQ-101/102/104/114's own declared, independently-owned values)
// ===========================================================================

// Today's real, only gojo sender (economy/ubi/run.sh hardcodes this identity) — see
// sumRecentGojoGiftsUsd's own gating below (resolves FIND-102).
export const GOJO_SENDER_ID = "anicca-a3cdd4";
// Same numeral as economy/gig/decide.mjs's DEFAULT_LOW_USDC, declared independently — zero import
// coupling (REQ-110/PROP-110a).
export const BORROWER_LOW_USD = 0.5;
export const FIRST_LOAN_USD = 0.02;
export const LOAN_INTEREST_RATE = 0.1;
export const LOAN_REPAYMENT_WINDOW_DAYS = 14;
export const RECENT_DEFAULT_LOSS_THRESHOLD_USD = 5.0;
export const RECENT_DEFAULT_LOSS_WINDOW_DAYS = 14;

const DEFAULT_RESERVE_USD = 5.0;
const DEFAULT_MAX_LOAN_USD = 5.0;

// Every reduction in this document treats the LAST-appended row per loan_id as authoritative
// (last-write-wins) — the same convention anicca-agent-spawn already established for ledger.js's
// duplicate-child_id rows. Order-preserving is irrelevant here since callers only ever need the final
// per-loan_id row, never the sequence of prior transitions.
function reduceLastByLoanId(loanRows) {
  const byId = new Map();
  for (const row of loanRows || []) {
    if (row && typeof row.loan_id === "string") byId.set(row.loan_id, row);
  }
  return [...byId.values()];
}

function finiteOr(value, fallback) {
  return Number.isFinite(value) ? value : fallback;
}

// ===========================================================================
// REQ-101 — computeLenderAvailableUsd / sumOutstandingPrincipalUsd / sumRecentGojoGiftsUsd
// ===========================================================================

export function computeLenderAvailableUsd({
  lenderBalanceUsd,
  perCitizenReserveUsd = DEFAULT_RESERVE_USD,
  outstandingPrincipalUsd = 0,
  recentGojoGiftsUsd = 0,
} = {}) {
  const balance = finiteOr(lenderBalanceUsd, 0);
  const reserve = finiteOr(perCitizenReserveUsd, DEFAULT_RESERVE_USD);
  const outstanding = finiteOr(outstandingPrincipalUsd, 0);
  const gojo = finiteOr(recentGojoGiftsUsd, 0);
  return +Math.max(0, balance - reserve - outstanding - gojo).toFixed(6);
}

export function sumOutstandingPrincipalUsd(loanRows, lenderId) {
  const rows = reduceLastByLoanId(loanRows).filter(
    (r) => r.lender_id === lenderId && (r.status === "active" || r.status === "defaulted")
  );
  const sum = rows.reduce((acc, r) => acc + (finiteOr(r.principal_usd, 0) - finiteOr(r.repaid_usd, 0)), 0);
  return +sum.toFixed(6);
}

export function sumRecentGojoGiftsUsd(gojoLogRows, nowMs, lookbackHours = 24, lenderId) {
  if (lenderId !== GOJO_SENDER_ID) return 0;
  const hours = finiteOr(lookbackHours, 24);
  const windowMs = hours * 3600 * 1000;
  let sum = 0;
  for (const row of gojoLogRows || []) {
    const amount = row && row.decision ? Number(row.decision.amount_usd) : NaN;
    if (!Number.isFinite(amount) || amount <= 0) continue;
    const ts = row ? Date.parse(row.ts) : NaN;
    if (!Number.isFinite(ts)) continue;
    if (nowMs - ts < windowMs) sum += amount;
  }
  return +sum.toFixed(6);
}

// ===========================================================================
// REQ-102 — isBorrowerEligible
// ===========================================================================

// Six possible `reason` values, in check order: "self_loan" (condition (d), FIND-402) — "not_evm"
// (REQ-107's chain/asset scope narrowing; not one of REQ-102's own four named conditions (a)-(d), and
// checked separately from them, but never colliding with any of the other five values here) —
// "not_self_funded" (a) — "not_broke_enough" (b) — "outstanding_loan" (c) — "ok".
export function isBorrowerEligible({ borrowerAgent, loanRows, borrowerId, borrowerBalanceUsd, lenderId }) {
  // (d) self-loan exclusion — checked FIRST, before any other condition (resolves FIND-402).
  if (lenderId === borrowerId) return { eligible: false, reason: "self_loan" };
  // REQ-107: this increment is Base-mainnet-USDC-only — a Solana-only citizen (no wallet.evm) is out
  // of scope for borrowing, even though it may otherwise pass isSelfFunded()'s own wallet leg.
  const wallet = borrowerAgent && borrowerAgent.wallet;
  if (!wallet || wallet.evm !== true) return { eligible: false, reason: "not_evm" };
  // (a) self-funded
  if (!isSelfFunded(borrowerAgent)) return { eligible: false, reason: "not_self_funded" };
  // (b) genuinely broke — strict less-than, matching decide.mjs's own boundary convention
  const balance = finiteOr(borrowerBalanceUsd, Infinity);
  if (!(balance < BORROWER_LOW_USD)) return { eligible: false, reason: "not_broke_enough" };
  // (c) zero currently-open loan obligations
  const hasOpenLoan = reduceLastByLoanId(loanRows).some(
    (r) => r.borrower_id === borrowerId && (r.status === "active" || r.status === "defaulted")
  );
  if (hasOpenLoan) return { eligible: false, reason: "outstanding_loan" };
  return { eligible: true, reason: "ok" };
}

// ===========================================================================
// REQ-104 — computeTotalDueUsd (fixed, small, conservative loan terms)
// ===========================================================================

export function computeTotalDueUsd(principalUsd) {
  const principal = finiteOr(principalUsd, 0);
  return +(principal * (1 + LOAN_INTEREST_RATE)).toFixed(6);
}

// ===========================================================================
// REQ-105 — computeLoanCapUsd / countSuccessfulOnTimeRepayments / decideLoan /
//           computeColdStartRepaymentRate / evaluateColdStartKillSwitch
// ===========================================================================

export function computeLoanCapUsd({
  successfulOnTimeRepayments,
  firstLoanUsd = FIRST_LOAN_USD,
  maxLoanUsd = DEFAULT_MAX_LOAN_USD,
} = {}) {
  const n =
    Number.isInteger(successfulOnTimeRepayments) && successfulOnTimeRepayments >= 0
      ? successfulOnTimeRepayments
      : 0; // fail-closed: malformed/negative/non-integer input floors to the cold-start cap, never a
  // larger, unearned one (PROP-105e).
  return +Math.min(maxLoanUsd, firstLoanUsd * 2 ** n).toFixed(6);
}

export function countSuccessfulOnTimeRepayments(loanRows, borrowerId) {
  return reduceLastByLoanId(loanRows).filter(
    (r) => r.borrower_id === borrowerId && r.status === "repaid" && r.on_time === true
  ).length;
}

export function decideLoan({ lenderAvailableUsd, loanAmountUsd }) {
  const available = finiteOr(lenderAvailableUsd, 0);
  const amount = finiteOr(loanAmountUsd, Infinity);
  const eligible = available >= amount;
  return { eligible, reason: eligible ? "ok" : "insufficient_lender_surplus" };
}

export function computeColdStartRepaymentRate({ loanRows, n = 20 } = {}) {
  const sorted = reduceLastByLoanId(loanRows)
    .filter((r) => Number.isFinite(r.issued_ms))
    .sort((a, b) => a.issued_ms - b.issued_ms);

  // Walk the colony-wide history in issued_ms order, tracking each borrower's own running count of
  // on-time-repaid loans SEEN SO FAR (strictly earlier than the row currently being visited) — a loan
  // qualifies as "cold-start" exactly when that running count is still 0 at its own issuance. This is a
  // re-derivation, never a stored snapshot field, so a borrower's 2nd+ loan can recur as cold-start
  // (resolves FIND-107 — "cold-start" is NOT synonymous with "borrower's first-ever loan").
  const priorOnTimeCount = new Map();
  const coldStartCandidates = [];
  for (const row of sorted) {
    const borrowerId = row.borrower_id;
    const priorCount = priorOnTimeCount.get(borrowerId) || 0;
    if (priorCount === 0) coldStartCandidates.push(row);
    if (row.status === "repaid" && row.on_time === true) {
      priorOnTimeCount.set(borrowerId, priorCount + 1);
    }
  }

  const sample = coldStartCandidates.slice(0, n);
  const sampleSize = sample.length;
  const repaidCount = sample.filter((r) => r.status === "repaid").length;
  const defaultedCount = sample.filter((r) => r.status === "defaulted").length;
  const pendingCount = sampleSize - repaidCount - defaultedCount;
  const rate = sampleSize === 0 ? null : +(repaidCount / sampleSize).toFixed(6);
  return { sampleSize, repaidCount, defaultedCount, pendingCount, rate };
}

export function evaluateColdStartKillSwitch({ sampleSize, rate, defaultedCount }) {
  if (sampleSize >= 10 && rate < 0.8) return { paused: true, reason: "cold_start_rate_below_threshold" };
  if (sampleSize < 10 && defaultedCount >= 1) return { paused: true, reason: "cold_start_small_sample_default" };
  return { paused: false, reason: "ok" };
}

// ===========================================================================
// REQ-109 — detectDefaultedLoans / adjustBalancesForOutstandingDebt
// ===========================================================================

export function detectDefaultedLoans({ loanRows, nowMs } = {}) {
  return reduceLastByLoanId(loanRows)
    .filter(
      (r) =>
        r.status === "active" &&
        Number.isFinite(r.due_ms) &&
        nowMs >= r.due_ms &&
        finiteOr(r.repaid_usd, 0) < finiteOr(r.total_due_usd, Infinity)
    )
    .map((r) => r.loan_id);
}

export function adjustBalancesForOutstandingDebt({ citizens, loanRows } = {}) {
  const debtByBorrower = new Map();
  for (const row of reduceLastByLoanId(loanRows)) {
    if (row.status !== "defaulted") continue;
    const debt = Math.max(0, finiteOr(row.principal_usd, 0) - finiteOr(row.repaid_usd, 0));
    debtByBorrower.set(row.borrower_id, (debtByBorrower.get(row.borrower_id) || 0) + debt);
  }
  return (citizens || []).map((citizen) => {
    const debt = debtByBorrower.get(citizen.id) || 0;
    if (debt === 0) return { ...citizen };
    const balance = finiteOr(citizen.balance, 0);
    return { ...citizen, balance: +Math.max(0, balance - debt).toFixed(6) };
  });
}

// ===========================================================================
// REQ-106 — nextLoanSequenceForLender / resolveLoanLockAcquisitionOrder
// ===========================================================================

export function nextLoanSequenceForLender(loanRows, lenderId) {
  const prefix = `loan_${lenderId}_`;
  let max = 0;
  for (const row of loanRows || []) {
    if (!row || row.lender_id !== lenderId || typeof row.loan_id !== "string" || !row.loan_id.startsWith(prefix)) {
      continue;
    }
    const n = parseInt(row.loan_id.slice(prefix.length), 10);
    if (Number.isInteger(n) && n > max) max = n;
  }
  return max + 1;
}

export function resolveLoanLockAcquisitionOrder(lenderId, borrowerId) {
  return [`loan_${lenderId}`, `loan_borrower_${borrowerId}`].sort();
}

// ===========================================================================
// REQ-114 — computeOverallDefaultRateUsd / computeRecentDefaultLossUsd /
//           evaluateOverallDefaultKillSwitch
// ===========================================================================

export function computeOverallDefaultRateUsd({ loanRows } = {}) {
  const terminal = reduceLastByLoanId(loanRows).filter((r) => r.status === "repaid" || r.status === "defaulted");
  const sampleSize = terminal.length;
  let totalIssuedUsd = 0;
  let totalDefaultedUsd = 0;
  for (const row of terminal) {
    const principal = finiteOr(row.principal_usd, 0) >= 0 ? finiteOr(row.principal_usd, 0) : 0;
    totalIssuedUsd += principal;
    if (row.status === "defaulted") {
      // repaid_usd is floored the SAME way principal already is above — a malformed/negative
      // repaid_usd must never SUBTRACT a negative and thereby INFLATE the loss beyond principal
      // (resolves FIND-C02: repaid_usd:-5 on principal_usd:1 previously yielded a nonsensical 600%
      // defaultRateUsd instead of the fail-closed, worst-case-assumed 100%).
      const repaid = finiteOr(row.repaid_usd, 0) >= 0 ? finiteOr(row.repaid_usd, 0) : 0;
      totalDefaultedUsd += Math.max(0, principal - repaid);
    }
  }
  totalIssuedUsd = +totalIssuedUsd.toFixed(6);
  totalDefaultedUsd = +totalDefaultedUsd.toFixed(6);
  const defaultRateUsd = totalIssuedUsd === 0 ? null : +(totalDefaultedUsd / totalIssuedUsd).toFixed(6);
  return { totalIssuedUsd, totalDefaultedUsd, defaultRateUsd, sampleSize };
}

export function computeRecentDefaultLossUsd({ loanRows, nowMs, windowDays = RECENT_DEFAULT_LOSS_WINDOW_DAYS } = {}) {
  const windowMs = windowDays * 86400000;
  const rows = reduceLastByLoanId(loanRows).filter(
    (r) => r.status === "defaulted" && Number.isFinite(r.defaulted_ms) && nowMs - r.defaulted_ms < windowMs
  );
  let sum = 0;
  for (const row of rows) {
    // Same fail-closed floor as computeOverallDefaultRateUsd above, applied to BOTH inputs here since
    // this function (unlike the one above) had no floor on either before this fix (FIND-C02).
    const principal = finiteOr(row.principal_usd, 0) >= 0 ? finiteOr(row.principal_usd, 0) : 0;
    const repaid = finiteOr(row.repaid_usd, 0) >= 0 ? finiteOr(row.repaid_usd, 0) : 0;
    sum += Math.max(0, principal - repaid);
  }
  return { totalRecentDefaultLossUsd: +sum.toFixed(6), windowDays };
}

export function evaluateOverallDefaultKillSwitch({
  totalIssuedUsd,
  totalDefaultedUsd,
  defaultRateUsd,
  sampleSize,
  totalRecentDefaultLossUsd,
} = {}) {
  if (sampleSize >= 10 && defaultRateUsd > 0.2) return { paused: true, reason: "ratio_threshold_exceeded" };
  if (sampleSize < 10 && totalDefaultedUsd > 0) return { paused: true, reason: "small_sample_default" };
  // Absolute-loss branch: independent of sampleSize, immune to ratio-style volume dilution by
  // construction (resolves FIND-602). >= (not >), so a bust-out landing EXACTLY at the threshold still
  // trips it (resolves FIND-701).
  if (Number.isFinite(totalRecentDefaultLossUsd) && totalRecentDefaultLossUsd >= RECENT_DEFAULT_LOSS_THRESHOLD_USD) {
    return { paused: true, reason: "recent_default_loss_threshold_exceeded" };
  }
  return { paused: false, reason: "ok" };
}
