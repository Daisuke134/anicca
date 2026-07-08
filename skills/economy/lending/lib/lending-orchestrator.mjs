// economy/lending/lib/lending-orchestrator.mjs — the effectful orchestrator layer (REQ-115/REQ-116,
// sprint-2). Pure sequencing and error propagation over sprint-1's already-specified pure/narrow
// modules (lending-gate.mjs, lending-verify.mjs, lending-path.mjs) plus the two already-hardened,
// reused effectful modules (lock.mjs::withGigLock, escrow.mjs::payViaFacilitator) — never a second,
// competing eligibility/sizing/default-detection decision of its own (mirrors REQ-103's own
// bookkeeping-only discipline, extended here exactly as `anicca-agent-spawn` REQ-307/PROP-307b extends
// REQ-104's identical discipline to its own orchestrator). See
// .vcsdd/features/anicca-agent-lending/specs/behavioral-spec.md (REQ-115/REQ-116) and
// specs/verification-architecture.md (PROP-115a-d/PROP-116a-e).
import fs from "node:fs";
import path from "node:path";

import {
  isBorrowerEligible,
  computeLenderAvailableUsd,
  computeTotalDueUsd,
  computeLoanCapUsd,
  countSuccessfulOnTimeRepayments,
  decideLoan,
  computeColdStartRepaymentRate,
  evaluateColdStartKillSwitch,
  computeOverallDefaultRateUsd,
  computeRecentDefaultLossUsd,
  evaluateOverallDefaultKillSwitch,
  sumOutstandingPrincipalUsd,
  sumRecentGojoGiftsUsd,
  nextLoanSequenceForLender,
  resolveLoanLockAcquisitionOrder,
  detectDefaultedLoans,
  LOAN_REPAYMENT_WINDOW_DAYS,
} from "./lending-gate.mjs";
import { verifyRepayment, reconcileProvisionalDisbursement } from "./lending-verify.mjs";
import { LOANS_LEDGER_PATH } from "./lending-path.mjs";
import { withGigLock } from "../../gig/lib/lock.mjs";
import { payViaFacilitator } from "../../gig/lib/escrow.mjs";

function errorMessage(e) {
  return (e && e.message) || String(e);
}

function readLoanRows(file) {
  let raw;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch (e) {
    if (e && e.code === "ENOENT") return [];
    throw e;
  }
  return raw
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
    .map((l) => JSON.parse(l));
}

function appendLoanRow(file, row) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.appendFileSync(file, JSON.stringify(row) + "\n");
  return row;
}

function findLastRowForLoanId(loanRows, loanId) {
  let last = null;
  for (const row of loanRows) {
    if (row && row.loan_id === loanId) last = row;
  }
  return last;
}

// The "active" row shape (REQ-106's own step-3 definition) landed via either step 9's own fresh
// disbursement or step 5's reconciliation of a stale prior attempt — identical fields either way.
function activeStatusFields(txHash, nowMs) {
  return {
    status: "active",
    tx_hash: txHash,
    issued_ms: nowMs,
    due_ms: nowMs + LOAN_REPAYMENT_WINDOW_DAYS * 86400000,
  };
}

// Finds this lender's own highest-sequence-number row (last-write-wins for that loan_id) — the SAME
// "highest matching-prefix numeric suffix" scan nextLoanSequenceForLender itself already performs, but
// returning the row itself (never just the number) so REQ-106's own ledger-state-triggered
// reconciliation trigger can inspect its status.
function findHighestSequenceRow(loanRows, lenderId) {
  const prefix = `loan_${lenderId}_`;
  let maxN = 0;
  for (const row of loanRows) {
    if (!row || row.lender_id !== lenderId || typeof row.loan_id !== "string" || !row.loan_id.startsWith(prefix)) {
      continue;
    }
    const n = parseInt(row.loan_id.slice(prefix.length), 10);
    if (Number.isInteger(n) && n > maxN) maxN = n;
  }
  if (maxN === 0) return null;
  return findLastRowForLoanId(loanRows, `${prefix}${maxN}`);
}

// REQ-106's ledger-state-triggered reconciliation (step 5): if this lender's own highest-n row is
// unterminated, resolve it via a REAL on-chain lookup BEFORE this attempt computes/uses any new
// sequence number. Returns {ok:false, reason} on a reconciliation-lookup failure (zero rows appended,
// zero sequence consumed) or {ok:true} once the ledger is clean (nothing to resolve, or resolved).
async function resolveStaleProvisioning(ledgerFile, loanRows, lenderId, nowMs, reconcile) {
  const staleRow = findHighestSequenceRow(loanRows, lenderId);
  if (!staleRow || (staleRow.status !== "provisioning" && staleRow.status !== "disbursement_uncertain")) {
    return { ok: true };
  }
  let reconcileResult;
  try {
    reconcileResult = await reconcile({ loanRow: staleRow });
  } catch (e) {
    return { ok: false, reason: "reconciliation_failed", error: errorMessage(e) };
  }
  if (reconcileResult && reconcileResult.found) {
    appendLoanRow(ledgerFile, { ...staleRow, ...activeStatusFields(reconcileResult.txHash, nowMs) });
  } else {
    appendLoanRow(ledgerFile, { ...staleRow, status: "disbursement_failed" });
  }
  return { ok: true };
}

// REQ-115 step 3 / step 6 (re-evaluated identically at both points, over whichever loanRows read is
// freshest at the call site): REQ-114 states the tie-break between its own switch and REQ-105's
// cold-start switch is implementation-defined when both would independently pause ("either reason alone
// is already sufficient grounds for refusal") — this function's own choice is to check
// evaluateOverallDefaultKillSwitch's THIRD, absolute-dollar-loss condition FIRST, in isolation (neutral
// sampleSize/totalDefaultedUsd/defaultRateUsd inputs suppress the function's OTHER two branches, which
// are checked for real below) — never a second, independently-computed threshold comparison of this
// module's own; the REAL totalRecentDefaultLossUsd is still what decides the outcome, entirely inside
// the already-exported, already-hardened function. REQ-105's cold-start switch is checked next (only for
// a genuine cold-start request), then the full, unrestricted overall switch last, so an established-tier
// request that only trips the ratio/small-sample branches is still caught.
function evaluateKillSwitches({ loanRows, borrowerId, nowMs }) {
  const recentLoss = computeRecentDefaultLossUsd({ loanRows, nowMs });
  const absoluteLossSwitch = evaluateOverallDefaultKillSwitch({
    sampleSize: 0,
    totalDefaultedUsd: 0,
    defaultRateUsd: null,
    totalRecentDefaultLossUsd: recentLoss.totalRecentDefaultLossUsd,
  });
  if (absoluteLossSwitch.paused) return { paused: true, reason: "overall_default_paused" };

  const successfulOnTimeRepayments = countSuccessfulOnTimeRepayments(loanRows, borrowerId);
  if (successfulOnTimeRepayments === 0) {
    const coldStart = computeColdStartRepaymentRate({ loanRows });
    const coldSwitch = evaluateColdStartKillSwitch(coldStart);
    if (coldSwitch.paused) return { paused: true, reason: "cold_start_paused" };
  }

  const overallStats = computeOverallDefaultRateUsd({ loanRows });
  const overallSwitch = evaluateOverallDefaultKillSwitch({
    ...overallStats,
    totalRecentDefaultLossUsd: recentLoss.totalRecentDefaultLossUsd,
  });
  if (overallSwitch.paused) return { paused: true, reason: "overall_default_paused" };

  return { paused: false, reason: null };
}

async function defaultReconcile({ loanRow }, deps) {
  return reconcileProvisionalDisbursement({
    loanRow,
    rpcUrl: deps.rpcUrl,
    fromBlock: deps.reconcileFromBlock || "earliest",
    toBlock: "latest",
  });
}

async function defaultDisburse({ loanRow }, deps) {
  return payViaFacilitator({
    privateKey: deps.lenderPrivateKey,
    to: loanRow.borrower_wallet,
    amountBase: Math.round(loanRow.principal_usd * 1e6),
    facilitatorUrl: deps.facilitatorUrl || process.env.GIG_FACILITATOR_URL || "http://127.0.0.1:8405",
  });
}

// REQ-115 steps 5-9, run entirely inside the dual per-lender/per-borrower critical section.
async function runLockedIssuance({ ledgerFile, lenderId, borrowerId, nowMs, getCitizen, gojoLogRows, deps }) {
  const reconcile = deps.reconcile || ((args) => defaultReconcile(args, deps));

  // Step 5.
  let loanRows = readLoanRows(ledgerFile);
  const staleResolution = await resolveStaleProvisioning(ledgerFile, loanRows, lenderId, nowMs, reconcile);
  if (!staleResolution.ok) {
    return { status: "refused", reason: staleResolution.reason, error: staleResolution.error };
  }

  // Step 6: fresh recheck, over a fresh read + fresh citizen records (never the pre-lock snapshot).
  loanRows = readLoanRows(ledgerFile);
  const [freshLender, freshBorrower] = await Promise.all([getCitizen(lenderId), getCitizen(borrowerId)]);
  if (!freshBorrower) return { status: "refused", reason: "not_found" };

  const eligibility = isBorrowerEligible({
    borrowerAgent: freshBorrower,
    loanRows,
    borrowerId,
    borrowerBalanceUsd: freshBorrower.balanceUsd,
    lenderId,
  });
  if (!eligibility.eligible) {
    return { status: "refused", reason: eligibility.reason };
  }

  const killSwitch = evaluateKillSwitches({ loanRows, borrowerId, nowMs });
  if (killSwitch.paused) {
    return { status: "refused", reason: killSwitch.reason };
  }

  // Step 7: sizing, against step 6's own fresh-read output.
  const successfulOnTimeRepayments = countSuccessfulOnTimeRepayments(loanRows, borrowerId);
  const loanCapUsd = computeLoanCapUsd({ successfulOnTimeRepayments });
  const lenderAvailableUsd = computeLenderAvailableUsd({
    lenderBalanceUsd: freshLender && freshLender.balanceUsd,
    outstandingPrincipalUsd: sumOutstandingPrincipalUsd(loanRows, lenderId),
    recentGojoGiftsUsd: sumRecentGojoGiftsUsd(gojoLogRows, nowMs, 24, lenderId),
  });
  const decision = decideLoan({ lenderAvailableUsd, loanAmountUsd: loanCapUsd });
  if (!decision.eligible) {
    return { status: "refused", reason: decision.reason };
  }

  // Step 8: n + provisional append.
  const n = nextLoanSequenceForLender(loanRows, lenderId);
  const loanId = `loan_${lenderId}_${n}`;
  const provisionalRow = {
    loan_id: loanId,
    lender_id: lenderId,
    borrower_id: borrowerId,
    lender_wallet: freshLender && freshLender.walletAddress && freshLender.walletAddress.evm,
    borrower_wallet: freshBorrower.walletAddress && freshBorrower.walletAddress.evm,
    status: "provisioning",
    principal_usd: loanCapUsd,
    total_due_usd: computeTotalDueUsd(loanCapUsd),
    provisioned_ms: nowMs,
  };
  appendLoanRow(ledgerFile, provisionalRow);

  // Step 9: disbursement attempt (own try/catch, per REQ-106's in-process-exception discipline) + the
  // follow-up append recording the REAL outcome.
  const disburse = deps.disburse || ((args) => defaultDisburse(args, deps));
  let disburseResult;
  try {
    disburseResult = await disburse({ loanRow: provisionalRow });
  } catch (e) {
    appendLoanRow(ledgerFile, { ...provisionalRow, status: "disbursement_uncertain", error: errorMessage(e) });
    return { status: "disbursement_uncertain", loanId, error: errorMessage(e) };
  }
  if (!disburseResult || disburseResult.ok !== true) {
    appendLoanRow(ledgerFile, {
      ...provisionalRow,
      status: "disbursement_failed",
      error: (disburseResult && disburseResult.error) || "disbursement failed",
    });
    return { status: "disbursement_failed", loanId };
  }
  appendLoanRow(ledgerFile, { ...provisionalRow, ...activeStatusFields(disburseResult.tx, nowMs) });
  return { status: "active", loanId };
}

/**
 * executeLoanIssuanceAttempt — REQ-115's single entry-point function for the ENTIRE remainder of a
 * loan-issuance attempt, once a caller has already decided (via REQ-101/102's own pure functions) that
 * an attempt is worth making.
 *
 * @returns {Promise<{status: "active"|"disbursement_failed"|"disbursement_uncertain"|"refused", loanId?: string, reason?: string, error?: string}>}
 */
export async function executeLoanIssuanceAttempt({ lenderId, borrowerId, nowMs = Date.now() } = {}, deps = {}) {
  // Step 1 (REQ-102(d)) — before any other step, before any lock.
  if (lenderId === borrowerId) {
    return { status: "refused", reason: "self_loan" };
  }

  const ledgerFile = deps.ledgerFile || LOANS_LEDGER_PATH;
  const lockStatePath = deps.lockStatePath || LOANS_LEDGER_PATH;
  const getCitizen = deps.getCitizen;
  const gojoLogRows = deps.gojoLogRows || [];

  // Step 2 (REQ-112) — still before any lock.
  const [lenderCitizen, borrowerCitizen] = await Promise.all([getCitizen(lenderId), getCitizen(borrowerId)]);
  if (!lenderCitizen || lenderCitizen.coLocatedWithCoordinator !== true) {
    return { status: "refused", reason: "not_co_located" };
  }
  if (!borrowerCitizen || borrowerCitizen.coLocatedWithCoordinator !== true) {
    return { status: "refused", reason: "not_co_located" };
  }

  // Step 3 — pre-lock kill-switch evaluation, over the freshest read available before any lock.
  const preLockLoanRows = readLoanRows(ledgerFile);
  const preLockKillSwitch = evaluateKillSwitches({ loanRows: preLockLoanRows, borrowerId, nowMs });
  if (preLockKillSwitch.paused) {
    return { status: "refused", reason: preLockKillSwitch.reason };
  }

  // Step 4: acquire both locks, nested, in resolveLoanLockAcquisitionOrder's own fixed order; steps
  // 5-9 all run inside this SAME critical section.
  const [outerKey, innerKey] = resolveLoanLockAcquisitionOrder(lenderId, borrowerId);
  const lockResult = await withGigLock(lockStatePath, outerKey, () =>
    withGigLock(lockStatePath, innerKey, () =>
      runLockedIssuance({ ledgerFile, lenderId, borrowerId, nowMs, getCitizen, gojoLogRows, deps })
    )
  );
  // withGigLock's own lock-rejection shape ({ok:false, reason}) can surface from either the outer or
  // the inner acquisition — both collapse to the SAME "lock_held" refusal (never itself a status claim).
  if (lockResult && lockResult.ok === false) {
    return { status: "refused", reason: "lock_held" };
  }
  return lockResult;
}

/**
 * executeRepaymentClaim — REQ-116's repayment-verification entry point, wrapping REQ-108's
 * verifyRepayment call and its own repayment-status-transition append inside the per-loan
 * `loan_${loanId}` lock (REQ-108's own lock, never REQ-106's per-lender/per-borrower issuance locks).
 *
 * @returns {Promise<{credited: number, status: "active"|"repaid"|"rejected", rejected?: boolean}>}
 */
export async function executeRepaymentClaim({ loanId, txHash, nowMs = Date.now() } = {}, deps = {}) {
  const ledgerFile = deps.ledgerFile || LOANS_LEDGER_PATH;
  const lockStatePath = deps.lockStatePath || LOANS_LEDGER_PATH;

  const lockResult = await withGigLock(lockStatePath, `loan_${loanId}`, async () => {
    const loanRows = readLoanRows(ledgerFile);
    const lastRow = findLastRowForLoanId(loanRows, loanId);
    if (!lastRow || lastRow.status !== "active") {
      return { credited: 0, status: "rejected", rejected: true };
    }

    const verify =
      deps.verify ||
      ((args) => verifyRepayment({ ...args, rpcUrl: deps.rpcUrl }));
    const verifyResult = await verify({
      txHash,
      expectedFrom: lastRow.borrower_wallet,
      expectedTo: lastRow.lender_wallet,
      loanRows,
    });
    if (!verifyResult || verifyResult.rejected || !(verifyResult.credited > 0)) {
      return { credited: 0, status: "rejected", rejected: true };
    }

    const repaidUsd = +(( lastRow.repaid_usd || 0) + verifyResult.credited).toFixed(6);
    const reachedFull = repaidUsd >= lastRow.total_due_usd;
    const newRow = reachedFull
      ? { ...lastRow, repaid_usd: repaidUsd, status: "repaid", tx_hash: txHash, on_time: nowMs <= lastRow.due_ms }
      : { ...lastRow, repaid_usd: repaidUsd, status: "active", tx_hash: txHash };
    appendLoanRow(ledgerFile, newRow);
    return { credited: verifyResult.credited, status: newRow.status };
  });

  if (lockResult && lockResult.ok === false) {
    return { credited: 0, status: "rejected", rejected: true };
  }
  return lockResult;
}

/**
 * executeDefaultDetectionSweep — REQ-116's default-detection entry point, wrapping REQ-109's
 * detectDefaultedLoans call and, for EACH flagged loan_id, its own per-loan-lock-protected
 * `"defaulted"`-row append (sequentially, never in parallel against the SAME shared ledger).
 *
 * @returns {Promise<{defaulted: string[]}>}
 */
export async function executeDefaultDetectionSweep({ nowMs = Date.now() } = {}, deps = {}) {
  const ledgerFile = deps.ledgerFile || LOANS_LEDGER_PATH;
  const lockStatePath = deps.lockStatePath || LOANS_LEDGER_PATH;

  const loanRows = readLoanRows(ledgerFile);
  const candidates = detectDefaultedLoans({ loanRows, nowMs });

  const defaulted = [];
  for (const loanId of candidates) {
    // Step 1's own candidate list can already be stale by the time this candidate's own lock is
    // attempted (REQ-116's own Edge Cases) — yielding here, before grabbing the lock, gives any
    // concurrently-dispatched externally-triggered call (e.g. executeRepaymentClaim) a fair chance to
    // reach its own lock attempt first, rather than this background sweep greedily racing ahead merely
    // because its own step-1 scan happened to run first.
    await Promise.resolve();
    const lockResult = await withGigLock(lockStatePath, `loan_${loanId}`, async () => {
      const freshRows = readLoanRows(ledgerFile);
      const lastRow = findLastRowForLoanId(freshRows, loanId);
      if (
        !lastRow ||
        lastRow.status !== "active" ||
        !Number.isFinite(lastRow.due_ms) ||
        nowMs < lastRow.due_ms ||
        (lastRow.repaid_usd || 0) >= lastRow.total_due_usd
      ) {
        return { defaultedNow: false };
      }
      appendLoanRow(ledgerFile, { ...lastRow, status: "defaulted", defaulted_ms: nowMs });
      return { defaultedNow: true };
    });
    if (lockResult && lockResult.ok === false) continue; // lock held -> skip this pass, re-evaluated next sweep
    if (lockResult && lockResult.defaultedNow) defaulted.push(loanId);
  }

  return { defaulted };
}
