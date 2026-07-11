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
import { deriveSignerAddress, addressesEqual, normalizeTxHash } from "./lending-signer.mjs";

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
//
// impl-review iteration-4, FIND-301 (critical): this is the SINGLE storage site both routes share, so
// normalizing `tx_hash` here (via `normalizeTxHash`, `lending-signer.mjs`) covers BOTH the happy-path
// disbursement's facilitator-format `disburseResult.tx` (escrow.mjs's own `settle.json.transaction`,
// an external, third-party-serialized string) and reconciliation's own RPC-derived
// `reconcileResult.txHash` (`extractTxHash`'s `log.transactionHash`) — the two uncoordinated sources
// this fix's casing gap spans.
function activeStatusFields(txHash, nowMs) {
  return {
    status: "active",
    tx_hash: normalizeTxHash(txHash),
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
//
// impl-review iteration-2, FIND-102 (critical): a {found:false} reconcile result is only trustworthy as
// "this row genuinely never disbursed" when the row's own age is still within what the reconciliation
// window (REQ-120's bounded eth_getLogs scan) could POSSIBLY have seen. If the row's real broadcast
// happened (e.g. a network timeout during waitForTransactionReceipt, not a pre-signing crash) but is
// OLDER than the lookback window, a {found:false} here is a FALSE NEGATIVE — trusting it would append
// disbursement_failed and let the caller proceed to a FRESH disbursement for the same borrower, an
// actual double-spend of real money. Fix: before trusting {found:false}, compare the row's own age
// (nowMs - provisioned_ms) against the reconciliation window's real-time span (tied to the SAME
// LENDING_RECONCILE_LOOKBACK_BLOCKS this exact `reconcile` call would have used — see
// reconcileWindowSpanMs below). A too-old row REFUSES (reason: stale_row_beyond_reconcile_window) —
// zero rows appended, zero sequence consumed — rather than being silently marked disbursement_failed;
// recovering it requires a wider manual scan, never an automatic re-disburse.
//
// impl-review iteration-3, FIND-201 (critical): `loanRows` was already a parameter of this function
// but was never forwarded into `reconcile()` — without it, reconcileProvisionalDisbursement has no way
// to reject a matched Transfer whose tx_hash is already recorded against a DIFFERENT loan_id (the same
// cross-ledger replay hazard verifyRepayment already guards against). Now threaded through.
async function resolveStaleProvisioning(ledgerFile, loanRows, lenderId, nowMs, reconcile, deps) {
  const staleRow = findHighestSequenceRow(loanRows, lenderId);
  if (!staleRow || (staleRow.status !== "provisioning" && staleRow.status !== "disbursement_uncertain")) {
    return { ok: true };
  }
  let reconcileResult;
  try {
    reconcileResult = await reconcile({ loanRow: staleRow, loanRows });
  } catch (e) {
    return { ok: false, reason: "reconciliation_failed", error: errorMessage(e) };
  }
  if (reconcileResult && reconcileResult.found) {
    appendLoanRow(ledgerFile, { ...staleRow, ...activeStatusFields(reconcileResult.txHash, nowMs) });
    return { ok: true };
  }
  const rowAgeMs = nowMs - staleRow.provisioned_ms;
  if (!Number.isFinite(staleRow.provisioned_ms) || !Number.isFinite(rowAgeMs) || rowAgeMs > reconcileWindowSpanMs(deps)) {
    return { ok: false, reason: "stale_row_beyond_reconcile_window" };
  }
  appendLoanRow(ledgerFile, { ...staleRow, status: "disbursement_failed" });
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

// FIND-002 (critical, impl-review iteration-1): this codebase's own prior FIND-702 fix
// (skills/self/founder-loop/record-earn.mjs) already discovered -- against this EXACT RPC
// (mainnet.base.org) -- that public JSON-RPC providers reject/truncate an eth_getLogs call spanning
// too many blocks (record-earn.mjs's own comment: "commonly 2,000-10,000 blocks"). record-earn.mjs
// caps its own scan span at 9000 blocks; that SAME proven-safe value is copied here verbatim (never
// re-derived) rather than "earliest", which this fix's own deps.rpcUrl wiring makes reachable against
// a real provider for the first time -- an unbounded "earliest" scan is exactly what would have
// permanently blocked the real stuck loan_Franklin_1 row's every future wake with
// reason:"reconciliation_failed" (the failure mode REQ-118b explicitly says this fix must resolve).
// Overridable via LENDING_RECONCILE_LOOKBACK_BLOCKS for an operator whose wake cadence needs a wider
// window (still bounded by the provider's own eth_getLogs range limit -- widening this must stay
// within whatever that real limit is, never re-introduce "earliest").
const DEFAULT_RECONCILE_LOOKBACK_BLOCKS = 9000; // ~5h at Base's ~2s/block; matches record-earn.mjs's own FIND-702 MAX_SPAN for this exact RPC

// Base's own documented average block time -- the SAME ~2s/block figure DEFAULT_RECONCILE_LOOKBACK_BLOCKS's
// own comment above already derives its "~5h" claim from, now made an explicit, reusable constant
// (impl-review iteration-2, FIND-102) so resolveStaleProvisioning's own age-vs-window guard is
// genuinely TIED to the same lookback-blocks figure the reconciliation scan itself uses, never a
// separately-guessed number.
const BASE_BLOCK_TIME_SECONDS = 2;

// The SAME lookback-blocks resolution defaultReconcile already performs (deps override -> env override
// -> DEFAULT_RECONCILE_LOOKBACK_BLOCKS) -- extracted so resolveStaleProvisioning's own age guard (below)
// computes the window's real-time span against the IDENTICAL figure a real reconcile call would use,
// never a duplicated/divergent computation.
function resolveReconcileLookbackBlocks(deps) {
  return (deps && deps.reconcileLookbackBlocks) || Number(process.env.LENDING_RECONCILE_LOOKBACK_BLOCKS) || DEFAULT_RECONCILE_LOOKBACK_BLOCKS;
}

// impl-review iteration-2, FIND-102: the real-time span the reconciliation window can possibly have
// scanned, in milliseconds -- exported so tests can assert the age guard's own boundary against the
// SAME constant this module computes it from, never a hand-copied literal.
export function reconcileWindowSpanMs(deps) {
  return resolveReconcileLookbackBlocks(deps) * BASE_BLOCK_TIME_SECONDS * 1000;
}

async function fetchLatestBlockNumber(rpcUrl) {
  const res = await fetch(rpcUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_blockNumber", params: [] }),
  });
  const json = await res.json();
  if (json.error || json.result === undefined) {
    throw new Error(`eth_blockNumber: ${JSON.stringify(json.error || json)}`);
  }
  return Number(BigInt(json.result));
}

// impl-review iteration-3, FIND-201: `loanRows` is now accepted (forwarded from resolveStaleProvisioning
// via `reconcile({loanRow, loanRows})`) and passed straight through to reconcileProvisionalDisbursement
// on both branches below, so its own cross-ledger tx_hash-replay guard has the full ledger to check
// against.
async function defaultReconcile({ loanRow, loanRows }, deps) {
  // deps.reconcileFromBlock is a TEST-ONLY seam (mirrors the pre-existing convention) -- production
  // never sets it, so production always computes a genuinely bounded window below.
  if (deps.reconcileFromBlock) {
    return reconcileProvisionalDisbursement({
      loanRow,
      loanRows,
      rpcUrl: deps.rpcUrl,
      fromBlock: deps.reconcileFromBlock,
      toBlock: deps.reconcileToBlock || "latest",
    });
  }
  const lookbackBlocks = resolveReconcileLookbackBlocks(deps);
  const latest = await fetchLatestBlockNumber(deps.rpcUrl);
  const from = Math.max(0, latest - lookbackBlocks);
  return reconcileProvisionalDisbursement({
    loanRow,
    loanRows,
    rpcUrl: deps.rpcUrl,
    // toBlock pinned to the SAME snapshot as fromBlock (never "latest" alongside a numeric fromBlock)
    // -- keeps the requested range exactly bounded, never silently wider by the time the provider
    // serves the request.
    fromBlock: "0x" + from.toString(16),
    toBlock: "0x" + latest.toString(16),
  });
}

// The chain identifier a Base-mainnet-configured x402 facilitator's own `/supported` response is
// expected to advertise (CAIP-2 format, matches escrow.mjs's own `network: eip155:${chainId}` payload
// field, CHAIN_ID_BASE_MAINNET=8453) -- see services/facilitator/test-facilitator-contract.mjs's own
// `supported.kinds?.some((k) => k.network === "eip155:...")` precedent for this exact response shape.
const FACILITATOR_MAINNET_NETWORK = "eip155:8453";

// FIND-103 (high, impl-review iteration-2): asks the facilitator itself, live, whether it is genuinely
// mainnet-configured -- never assumed from our own GIG_CHAIN env var or a port-liveness check alone.
// deps.fetchImpl (mirrors this repo's own established injectable-fetch convention --
// _shared/lib/usdc.mjs, wake-gate.mjs's buildDefaultGetCitizen, sol-gate.mjs -- never a bespoke seam)
// defaults to the real global fetch; production always uses it. Throws (never returns a boolean) so
// defaultDisburse's own single try/catch (REQ-106's in-process-exception discipline, already in
// runLockedIssuance) uniformly converts an unreachable/misconfigured facilitator into the SAME
// disbursement_uncertain outcome every other pre-signing guard already produces.
async function preflightFacilitatorMainnet(facilitatorUrl, deps) {
  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  let supported;
  try {
    const res = await fetchImpl(`${facilitatorUrl}/supported`);
    supported = await res.json();
  } catch (e) {
    throw new Error(
      `facilitator_not_mainnet: could not reach ${facilitatorUrl}/supported to confirm mainnet network before signing real lending money (${errorMessage(e)})`
    );
  }
  const advertisesMainnet = Array.isArray(supported && supported.kinds) && supported.kinds.some((k) => k && k.network === FACILITATOR_MAINNET_NETWORK);
  if (!advertisesMainnet) {
    throw new Error(
      `facilitator_not_mainnet: ${facilitatorUrl}/supported does not advertise network "${FACILITATOR_MAINNET_NETWORK}" (Base mainnet) -- refusing to sign real lending money against an unverified/non-mainnet facilitator`
    );
  }
}

async function defaultDisburse({ loanRow }, deps) {
  // FIND-001 (critical, impl-review iteration-1) defensive backstop: wake-gate.mjs's own pre-lock
  // guard is the PRIMARY defense (refuses BEFORE executeLoanIssuanceAttempt is ever called) -- this is
  // a SECOND, independent check at the actual point of signing, so a mismatched deps.lenderPrivateKey
  // can never reach payViaFacilitator even if executeLoanIssuanceAttempt is ever invoked directly
  // (bypassing wake-gate.mjs -- e.g. a future direct caller or test).
  const resolvedSignerAddress = deriveSignerAddress(deps.lenderPrivateKey);
  if (!addressesEqual(resolvedSignerAddress, loanRow.lender_wallet)) {
    throw new Error(
      `lender_signer_mismatch: resolved lenderPrivateKey's derived signer address does not match loanRow.lender_wallet (loan_id=${loanRow.loan_id}) -- refusing to sign`
    );
  }

  // FIND-003 (medium, impl-review iteration-1): never settle real money against a non-mainnet/unset
  // GIG_CHAIN. deps.gigChain lets a test explicitly exercise this real function's own control flow
  // without mutating process.env (mirrors deps.reconcileFromBlock's own test-seam convention);
  // production always reads the real process.env.GIG_CHAIN. escrow.mjs's own GIG_CHAIN constant
  // defaults to testnet when unset -- that default must NEVER be silently treated as "go ahead" on
  // this path, since this feature exists specifically to gate the colony's first REAL on-chain loan.
  const gigChain = deps.gigChain !== undefined ? deps.gigChain : process.env.GIG_CHAIN;
  if (gigChain !== "base" && deps.allowNonMainnetChain !== true) {
    throw new Error(
      `lending_chain_not_mainnet: GIG_CHAIN must be "base" to disburse real lending money (got ${JSON.stringify(gigChain)}) -- refusing to settle against a non-mainnet/unset chain`
    );
  }

  const facilitatorUrl = deps.facilitatorUrl || process.env.GIG_FACILITATOR_URL || "http://127.0.0.1:8405";

  // FIND-103 (high, impl-review iteration-2): GIG_CHAIN=='base' proves OUR OWN code intends to settle
  // against mainnet -- it says nothing about which network the facilitator PROCESS actually listening at
  // `facilitatorUrl` is configured for. lsof-style "is a process bound to this port" checks (this fix's
  // own prior operator precondition, REQ-121) cannot distinguish a genuinely mainnet-configured
  // facilitator from one still silently serving testnet config on the same port (WITNESS-RUNBOOK.md's
  // own documented history: PID 94412 on port 8405 WAS the testnet facilitator on 2026-07-07). A
  // mainnet-config-only-in-our-own-process assumption must never be trusted for real money -- ask the
  // facilitator itself, every real disbursement attempt (never cached: a facilitator swapped back to
  // testnet config between wakes must be caught immediately, not trusted from a stale prior check).
  // Fail-closed: unreachable/malformed/non-mainnet /supported response -> refuse, never sign.
  await preflightFacilitatorMainnet(facilitatorUrl, deps);

  return payViaFacilitator({
    privateKey: deps.lenderPrivateKey,
    to: loanRow.borrower_wallet,
    amountBase: Math.round(loanRow.principal_usd * 1e6),
    facilitatorUrl,
  });
}

// REQ-115 steps 5-9, run entirely inside the dual per-lender/per-borrower critical section.
async function runLockedIssuance({ ledgerFile, lenderId, borrowerId, nowMs, getCitizen, gojoLogRows, deps }) {
  const reconcile = deps.reconcile || ((args) => defaultReconcile(args, deps));

  // Step 5.
  let loanRows = readLoanRows(ledgerFile);
  const staleResolution = await resolveStaleProvisioning(ledgerFile, loanRows, lenderId, nowMs, reconcile, deps);
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
    // impl-review iteration-4, FIND-301 (critical): the repayment-row tx_hash storage site — the
    // caller-supplied `txHash` (already independently verified by `verifyRepayment` above) is normalized
    // the SAME way as `activeStatusFields`'s own disbursement-side tx_hash, so a later replay-guard
    // comparison never depends on the caller's own casing choice.
    const normalizedTxHash = normalizeTxHash(txHash);
    const newRow = reachedFull
      ? { ...lastRow, repaid_usd: repaidUsd, status: "repaid", tx_hash: normalizedTxHash, on_time: nowMs <= lastRow.due_ms }
      : { ...lastRow, repaid_usd: repaidUsd, status: "active", tx_hash: normalizedTxHash };
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
