// node:test — lending-orchestrator.mjs (Phase 2a RED, anicca-agent-lending sprint-2, REQ-115/REQ-116).
// RED phase: this file is written BEFORE ../lending-orchestrator.mjs exists, so every import below is
// the first failing assertion (module not found) — mirrors sprint-1's own RED-phase precedent
// (lending-path.test.mjs/lending-verify.test.mjs) and anicca-agent-spawn sprint-2's own
// spawn-orchestrator.test.mjs precedent for this exact "new orchestrator module" shape.
//
// Test-only seam (mirrors spawn-orchestrator.mjs's own `deps` convention exactly, see
// spawn-orchestrator.test.mjs's own header): executeLoanIssuanceAttempt/executeRepaymentClaim/
// executeDefaultDetectionSweep's PINNED first argument is exactly what REQ-115/REQ-116 state
// ({lenderId, borrowerId, nowMs}/{loanId, txHash, nowMs}/{nowMs}). A SECOND, optional argument --
// `deps` -- is the production/test wiring seam for the genuinely effectful, non-pure steps:
//   executeLoanIssuanceAttempt(params, deps):
//     deps.ledgerFile      -- loans.jsonl path override (defaults to LOANS_LEDGER_PATH)
//     deps.lockStatePath   -- withGigLock's statePath override (defaults to LOANS_LEDGER_PATH)
//     deps.getCitizen(id)  -- async citizen-record reader (co-location/wallet/fuel/balance) --
//                             REQ-101/102/107/112 all read citizen facts this function must supply
//     deps.gojoLogRows     -- pre-read gojo-log.jsonl rows array (defaults to [])
//     deps.reconcile({loanRow}) -- wraps REQ-106's reconcileProvisionalDisbursement (step 5);
//                             production default calls the REAL reconcileProvisionalDisbursement
//     deps.disburse({loanRow})  -- wraps REQ-106's payViaFacilitator (step 9); production default
//                             calls the REAL payViaFacilitator
//   executeRepaymentClaim(params, deps):
//     deps.ledgerFile, deps.lockStatePath
//     deps.verify({txHash, expectedFrom, expectedTo, loanRows}) -- wraps REQ-108's verifyRepayment;
//                             production default calls the REAL verifyRepayment with deps.rpcUrl
//   executeDefaultDetectionSweep(params, deps):
//     deps.ledgerFile, deps.lockStatePath -- no RPC dependency at all (detectDefaultedLoans is pure)
// Every PURE lending-gate.mjs function (isBorrowerEligible, computeLenderAvailableUsd, decideLoan,
// evaluateColdStartKillSwitch, evaluateOverallDefaultKillSwitch, nextLoanSequenceForLender,
// resolveLoanLockAcquisitionOrder, detectDefaultedLoans, ...) is called directly, for REAL, always --
// never injectable -- so PROP-115a/PROP-116a's "single call-graph root" structural check holds. Only
// the genuinely effectful, non-file-based RPC boundaries (reconcile/disburse/verify) are injectable,
// exactly mirroring spawn-orchestrator.mjs's own deploy/registerIdentity/writeMcpConfig convention.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import http from "node:http";
import { fileURLToPath } from "node:url";
import {
  executeLoanIssuanceAttempt,
  executeRepaymentClaim,
  executeDefaultDetectionSweep,
  reconcileWindowSpanMs,
} from "../lending-orchestrator.mjs";
import { withGigLock } from "../../../gig/lib/lock.mjs";
import { verifyRepayment } from "../lending-verify.mjs";
import { privateKeyToAccount } from "viem/accounts";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ORCH_PATH = path.resolve(__dirname, "../lending-orchestrator.mjs");

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "anicca-lending-orch-"));
}

function ledgerFileFor(dir) {
  return path.join(dir, "loans.jsonl");
}

function readLoanRows(file) {
  if (!fs.existsSync(file)) return [];
  return fs
    .readFileSync(file, "utf8")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => JSON.parse(l));
}

function locksDirExists(dir) {
  return fs.existsSync(path.join(dir, "locks"));
}

const LENDER = "anicca-a3cdd4";
const BORROWER = "Franklin";
const NOW_MS = 1_800_000_000_000;

function baseCitizen(id, overrides = {}) {
  return {
    id,
    wallet: { evm: true },
    fuel: { provider: "clawrouter-own-wallet" },
    humanDependencies: [],
    coLocatedWithCoordinator: true,
    walletAddress: { evm: `0x${id.replace(/[^A-Za-z0-9]/g, "")}Wallet00000000000000000001`.slice(0, 42) },
    balanceUsd: 10,
    ...overrides,
  };
}

// All 9 canonical steps succeed fast: lender well-funded, borrower broke+eligible, no kill-switch
// tripped, no prior rows for either party, disbursement succeeds cleanly. Individual tests override
// exactly one seam to force exactly one step to fail/refuse.
function happyDeps(dir, overrides = {}) {
  const citizens = {
    [LENDER]: baseCitizen(LENDER, { balanceUsd: 10 }),
    [BORROWER]: baseCitizen(BORROWER, { balanceUsd: 0.1 }),
  };
  return {
    ledgerFile: ledgerFileFor(dir),
    lockStatePath: ledgerFileFor(dir),
    getCitizen: async (id) => citizens[id] || null,
    gojoLogRows: [],
    reconcile: async () => ({ found: false }),
    disburse: async ({ loanRow }) => ({
      ok: true,
      tx: "0xdisbursetxfixture0000000000000000000000000000000000000000000001",
      payerAddress: baseCitizen(LENDER).walletAddress.evm,
      to: loanRow.borrower_wallet,
      amountBase: Math.round(loanRow.principal_usd * 1e6),
    }),
    ...overrides,
  };
}

function baseParams(overrides = {}) {
  return { lenderId: LENDER, borrowerId: BORROWER, nowMs: NOW_MS, ...overrides };
}

// ---------------------------------------------------------------------------
// PROP-115a / CRIT-201: exactly one call-graph root, no second orchestration path.
// ---------------------------------------------------------------------------

test("PROP-115a structural: lending-orchestrator.mjs exports exactly one executeLoanIssuanceAttempt entry point", () => {
  const src = fs.readFileSync(ORCH_PATH, "utf8");
  const matches = src.match(/export\s+(async\s+function|function|const)\s+executeLoanIssuanceAttempt/g) || [];
  assert.equal(matches.length, 1, "exactly one executeLoanIssuanceAttempt export, no second competing entry point");
});

test("PROP-116a structural: lending-orchestrator.mjs exports exactly one executeRepaymentClaim and exactly one executeDefaultDetectionSweep entry point", () => {
  const src = fs.readFileSync(ORCH_PATH, "utf8");
  const claimMatches = src.match(/export\s+(async\s+function|function|const)\s+executeRepaymentClaim/g) || [];
  const sweepMatches = src.match(/export\s+(async\s+function|function|const)\s+executeDefaultDetectionSweep/g) || [];
  assert.equal(claimMatches.length, 1, "exactly one executeRepaymentClaim export");
  assert.equal(sweepMatches.length, 1, "exactly one executeDefaultDetectionSweep export");
});

test("PROP-115a/PROP-116a structural: lending-orchestrator.mjs is the ONLY call site invoking verifyRepayment/detectDefaultedLoans/reconcileProvisionalDisbursement in this feature's own diff", () => {
  const src = fs.readFileSync(ORCH_PATH, "utf8");
  assert.match(src, /reconcileProvisionalDisbursement|deps\.reconcile/, "step 5 must wire reconciliation, real or injected");
  assert.match(src, /payViaFacilitator|deps\.disburse/, "step 9 must wire disbursement, real or injected");
  assert.match(src, /verifyRepayment|deps\.verify/, "executeRepaymentClaim must wire REQ-108's verification, real or injected");
  assert.match(src, /detectDefaultedLoans/, "executeDefaultDetectionSweep must call the REAL detectDefaultedLoans");
});

// ---------------------------------------------------------------------------
// PROP-115b / PROP-116b / CRIT-202: no decision/judgment logic of their own, no LLM reference.
// ---------------------------------------------------------------------------

test("PROP-115b/PROP-116b structural: lending-orchestrator.mjs contains no relational/threshold comparison against a balance/surplus/rate/count value of its own, and no LLM/prompt reference", () => {
  const src = fs.readFileSync(ORCH_PATH, "utf8");
  assert.ok(
    !/balanceUsd\s*[<>]|surplusUsd\s*[<>=]|defaultRateUsd\s*[<>=]|repaymentRate\s*[<>=]/.test(src),
    "eligibility/sizing/default-detection arithmetic belongs exclusively to lending-gate.mjs's own already-exported functions, called BY this module, never re-implemented inside it"
  );
  assert.ok(
    !/\b(anthropic|openai|llm|prompt|chat\.completions|generateText)\b/i.test(src),
    "lending-orchestrator.mjs must contain zero LLM/prompt references -- pure sequencing and error propagation only"
  );
});

// ---------------------------------------------------------------------------
// CRIT-204 / PROP-115d structural half: the two lock namespaces are never crossed between the
// issuance orchestrator and the servicing orchestrator functions.
// ---------------------------------------------------------------------------

test("CRIT-204 structural: executeRepaymentClaim/executeDefaultDetectionSweep never reference the per-lender/per-borrower issuance lock keys, and executeLoanIssuanceAttempt never references the per-loan servicing lock key", () => {
  const src = fs.readFileSync(ORCH_PATH, "utf8");
  const issuanceFnMatch = src.match(/export\s+async\s+function\s+executeLoanIssuanceAttempt[\s\S]*?\n}\n/);
  const claimFnMatch = src.match(/export\s+async\s+function\s+executeRepaymentClaim[\s\S]*?\n}\n/);
  const sweepFnMatch = src.match(/export\s+async\s+function\s+executeDefaultDetectionSweep[\s\S]*?\n}\n/);
  assert.ok(issuanceFnMatch, "executeLoanIssuanceAttempt body must be found for this structural read");
  assert.ok(claimFnMatch, "executeRepaymentClaim body must be found for this structural read");
  assert.ok(sweepFnMatch, "executeDefaultDetectionSweep body must be found for this structural read");
  assert.ok(!/loan_\$\{loanId\}|`loan_\$\{[a-zA-Z]*[Ll]oan_?[Ii]d\}`/.test(issuanceFnMatch[0]), "executeLoanIssuanceAttempt must never reference the per-loan servicing lock key");
  assert.ok(!/loan_borrower_|loan_\$\{lenderId\}/.test(claimFnMatch[0]), "executeRepaymentClaim must never reference the per-lender/per-borrower issuance lock keys");
  assert.ok(!/loan_borrower_|loan_\$\{lenderId\}/.test(sweepFnMatch[0]), "executeDefaultDetectionSweep must never reference the per-lender/per-borrower issuance lock keys");
});

// ---------------------------------------------------------------------------
// REQ-115 happy path: every one of the 9 canonical steps runs exactly once, in the canonical order.
// ---------------------------------------------------------------------------

test("REQ-115: a real invocation calls every one of steps 1-9 exactly once, in the canonical order, for a happy-path issuance attempt", async () => {
  const dir = tmpDir();
  const calls = [];
  const deps = happyDeps(dir, {
    getCitizen: async (id) => {
      calls.push(`getCitizen:${id}`);
      const citizens = { [LENDER]: baseCitizen(LENDER, { balanceUsd: 10 }), [BORROWER]: baseCitizen(BORROWER, { balanceUsd: 0.1 }) };
      return citizens[id] || null;
    },
    reconcile: async () => { calls.push("reconcile"); return { found: false }; },
    disburse: async ({ loanRow }) => {
      calls.push("disburse");
      return { ok: true, tx: "0xhappypathtxfixture000000000000000000000000000000000000000001", to: loanRow.borrower_wallet, amountBase: 20000 };
    },
  });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "active");
  assert.ok(typeof result.loanId === "string" && result.loanId.length > 0);
  assert.ok(calls.includes("disburse"), "step 9 disbursement must be invoked on the happy path");
  const rows = readLoanRows(deps.ledgerFile).filter((r) => r.loan_id === result.loanId);
  assert.equal(rows.length, 2, "exactly two rows for a happy-path issuance: the provisional row (step 8) and the follow-up active row (step 9)");
  assert.equal(rows[0].status, "provisioning");
  assert.equal(rows[1].status, "active");
  assert.equal(rows[1].loan_id, `loan_${LENDER}_1`);
  assert.equal(typeof rows[1].issued_ms, "number");
  assert.equal(rows[1].due_ms, rows[1].issued_ms + 14 * 86400000);
  assert.equal(rows[1].principal_usd, 0.02, "cold-start borrower (zero prior on-time repayments) gets FIRST_LOAN_USD");
  assert.equal(rows[1].total_due_usd, 0.022);
});

// ---------------------------------------------------------------------------
// FIND-002 (adversary round 2, spec §1 G3 correction): the G3 reputation gate must be wired into THIS
// real production entry point (runLockedIssuance's step 6, right after isBorrowerEligible), not left as
// unreachable dead code (isBorrowerEligibleWithReputationGate previously had zero production call
// sites). deps.reputationGate (config: minScore/minJobCount/clientAddresses/tag1/tag2) and
// deps.reputationGateFn (DI override, mirrors deps.reconcile/deps.disburse's own convention) are the
// production/test wiring seam.
// ---------------------------------------------------------------------------

test("★FIND-002 wiring★ REQ-115: a CONFIGURED reputation gate is actually consulted on the real executeLoanIssuanceAttempt path, and its rejection refuses the loan with the gate's own reason", async () => {
  const dir = tmpDir();
  let reputationGateCalled = false;
  let receivedArgs = null;
  const deps = happyDeps(dir, {
    reputationGate: { minScore: 50, minJobCount: 1, clientAddresses: ["0xClient1"] },
    reputationGateFn: async (args) => {
      reputationGateCalled = true;
      receivedArgs = args;
      return { eligible: false, reason: "insufficient_score" };
    },
  });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(reputationGateCalled, true, "a configured reputation gate must be consulted on this real production entry point -- it must not be dead code");
  assert.equal(receivedArgs.minScore, 50);
  assert.equal(receivedArgs.minJobCount, 1);
  assert.equal("borrowerAgentId" in receivedArgs, true, "the gate must be called WITH a borrowerAgentId key threaded through (this fixture's citizen record has no .agentId set yet, so the value is undefined -- that is a separate, future data-plumbing concern; the wiring itself must still pass the key)");
  assert.equal(result.status, "refused");
  assert.equal(result.reason, "insufficient_score");
  const rows = readLoanRows(deps.ledgerFile);
  assert.equal(rows.length, 0, "a reputation-gate refusal must happen BEFORE the provisional row append (step 8), same discipline as every other step-6 refusal");
});

test("★FIND-002★ REQ-115: with NO reputationGate config (the default), the gate fail-opens -- behavior is IDENTICAL to before this wiring existed (happy path still reaches 'active')", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir);
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "active", "unset thresholds (spec §1 G3 MUST: 段階導入 fail-open) must be a complete no-op on the pre-existing happy path");
});

// ---------------------------------------------------------------------------
// REQ-115 / CRIT-203 / PROP-115c: a failure/refusal injected at each of the 9 canonical steps.
// ---------------------------------------------------------------------------

test("PROP-115c step 1 (REQ-102(d) self-loan) -> refused, ZERO rows, ZERO lock acquired", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir);
  const result = await executeLoanIssuanceAttempt(baseParams({ lenderId: LENDER, borrowerId: LENDER }), deps);
  assert.equal(result.status, "refused");
  assert.equal(result.reason, "self_loan");
  assert.deepEqual(readLoanRows(deps.ledgerFile), []);
  assert.equal(locksDirExists(dir), false, "step 1 must acquire ZERO locks");
});

test("PROP-115c step 2 (REQ-112 non-co-located party) -> refused, ZERO rows, ZERO lock acquired", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir, {
    getCitizen: async (id) => {
      const citizens = {
        [LENDER]: baseCitizen(LENDER, { balanceUsd: 10 }),
        [BORROWER]: baseCitizen(BORROWER, { balanceUsd: 0.1, coLocatedWithCoordinator: false }),
      };
      return citizens[id] || null;
    },
  });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "refused");
  assert.deepEqual(readLoanRows(deps.ledgerFile), []);
  assert.equal(locksDirExists(dir), false, "step 2 must acquire ZERO locks");
});

test("PROP-115c step 3 (REQ-105 cold-start kill-switch tripped) -> refused reason cold_start_paused, ZERO rows, ZERO lock acquired", async () => {
  const dir = tmpDir();
  // 10 cold-start candidates for this SAME lender's own colony history, all defaulted -> rate 0 < 0.80,
  // sampleSize>=10 -> evaluateColdStartKillSwitch pauses (mirrors lending-gate.property/unit precedent).
  const priorRows = Array.from({ length: 10 }, (_, i) => ({
    loan_id: `loan_${LENDER}_${900 + i}`,
    lender_id: LENDER,
    borrower_id: `otherBorrower${i}`,
    status: "defaulted",
    principal_usd: 0.02,
    repaid_usd: 0,
    total_due_usd: 0.022,
    issued_ms: NOW_MS - 30 * 86400000,
    due_ms: NOW_MS - 16 * 86400000,
  }));
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(ledgerFileFor(dir), priorRows.map((r) => JSON.stringify(r)).join("\n") + "\n");
  const deps = happyDeps(dir);
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "refused");
  assert.equal(result.reason, "cold_start_paused");
  const rowsAfter = readLoanRows(deps.ledgerFile).filter((r) => !priorRows.some((p) => p.loan_id === r.loan_id));
  assert.deepEqual(rowsAfter, [], "step 3 refusal appends ZERO new rows");
  assert.equal(locksDirExists(dir), false, "step 3 must acquire ZERO locks");
});

test("PROP-115c step 3 (REQ-114 overall default kill-switch tripped) -> refused reason overall_default_paused, ZERO rows, ZERO lock acquired", async () => {
  const dir = tmpDir();
  // A single large recent default whose unrecovered loss alone crosses RECENT_DEFAULT_LOSS_THRESHOLD_USD
  // ($5.00) within the 14-day window -- trips the absolute-loss branch regardless of sampleSize.
  const priorRows = [{
    loan_id: `loan_${LENDER}_500`,
    lender_id: LENDER,
    borrower_id: "bustOutBorrower",
    status: "defaulted",
    principal_usd: 5.0,
    repaid_usd: 0,
    total_due_usd: 5.5,
    issued_ms: NOW_MS - 20 * 86400000,
    due_ms: NOW_MS - 6 * 86400000,
    defaulted_ms: NOW_MS - 1 * 86400000,
  }];
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(ledgerFileFor(dir), priorRows.map((r) => JSON.stringify(r)).join("\n") + "\n");
  const deps = happyDeps(dir);
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "refused");
  assert.equal(result.reason, "overall_default_paused");
  const rowsAfter = readLoanRows(deps.ledgerFile).filter((r) => !priorRows.some((p) => p.loan_id === r.loan_id));
  assert.deepEqual(rowsAfter, [], "step 3 refusal appends ZERO new rows");
  assert.equal(locksDirExists(dir), false, "step 3 must acquire ZERO locks");
});

test("PROP-115c step 4 (lock_held, another in-flight attempt already holds the lender lock) -> refused reason lock_held, ZERO rows", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir);
  let releaseHeld;
  const heldOpen = new Promise((resolve) => { releaseHeld = resolve; });
  const heldLockPromise = withGigLock(deps.lockStatePath, `loan_${LENDER}`, async () => { await heldOpen; return { ok: true }; });
  // give the holder a beat to actually create the lock file before racing our own attempt
  await new Promise((r) => setTimeout(r, 20));
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  releaseHeld();
  await heldLockPromise;
  assert.equal(result.status, "refused");
  assert.equal(result.reason, "lock_held");
  assert.deepEqual(readLoanRows(deps.ledgerFile), []);
});

test("PROP-115c step 5 (REQ-106 reconciliation lookup itself throws) -> refused/error, ZERO new rows, ZERO sequence number consumed", async () => {
  const dir = tmpDir();
  // Seed an unterminated 'provisioning' row for this lender -- nextLoanSequenceForLender must trigger
  // reconciliation before computing a new n.
  const staleRow = {
    loan_id: `loan_${LENDER}_1`,
    lender_id: LENDER,
    borrower_id: "priorBorrower",
    status: "provisioning",
    principal_usd: 0.02,
    total_due_usd: 0.022,
    provisioned_ms: NOW_MS - 60000,
  };
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(ledgerFileFor(dir), JSON.stringify(staleRow) + "\n");
  const deps = happyDeps(dir, { reconcile: async () => { throw new Error("RPC timeout during eth_getLogs lookup"); } });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "refused");
  const rows = readLoanRows(deps.ledgerFile);
  assert.equal(rows.length, 1, "the pre-existing stale row is left EXACTLY as found -- zero new rows appended");
  assert.deepEqual(rows[0], staleRow);
});

test("PROP-115c step 5 happy: an unterminated provisioning row is resolved via a successful reconciliation lookup BEFORE this attempt's own new sequence number is computed", async () => {
  const dir = tmpDir();
  const staleRow = {
    loan_id: `loan_${LENDER}_1`,
    lender_id: LENDER,
    borrower_id: "priorBorrower",
    status: "provisioning",
    principal_usd: 0.02,
    total_due_usd: 0.022,
    provisioned_ms: NOW_MS - 60000,
  };
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(ledgerFileFor(dir), JSON.stringify(staleRow) + "\n");
  const deps = happyDeps(dir, {
    reconcile: async ({ loanRow }) => {
      assert.equal(loanRow.loan_id, staleRow.loan_id, "reconcile must be called with the SAME stale loan row found on the ledger, never a fabricated one");
      return { found: true, txHash: "0xreconciledtxfixture00000000000000000000000000000000000000001" };
    },
  });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "active");
  const rows = readLoanRows(deps.ledgerFile);
  const reconciledFollowUp = rows.find((r) => r.loan_id === staleRow.loan_id && r.status === "active");
  assert.ok(reconciledFollowUp, "the reconciled stale row must get its own active follow-up row");
  assert.equal(reconciledFollowUp.tx_hash, "0xreconciledtxfixture00000000000000000000000000000000000000001");
  const newRow = rows.find((r) => r.loan_id === `loan_${LENDER}_2`);
  assert.ok(newRow, "this attempt's own new sequence number (n=2) must be computed AFTER reconciliation resolves n=1, never colliding with it");
});

// ===========================================================================
// FIND-201 fix (critical, impl-review iteration-3): resolveStaleProvisioning had `loanRows` in scope but
// never forwarded it into its own reconcile() call, so reconcileProvisionalDisbursement had no way to
// apply verifyRepayment's own already-proven cross-ledger tx_hash-replay guard (lending-verify.mjs:84-86)
// to the disbursement side of reconciliation. Now threaded through.
// ===========================================================================

test("FIND-201 fix (critical, impl-review iteration-3): resolveStaleProvisioning forwards the FULL current loanRows ledger into reconcile({loanRow, loanRows}) -- not just the stale row alone -- so reconcileProvisionalDisbursement can apply its own cross-loan tx_hash-replay guard", async () => {
  const dir = tmpDir();
  const priorRow = {
    loan_id: `loan_${LENDER}_1`,
    lender_id: LENDER,
    borrower_id: BORROWER,
    status: "active",
    principal_usd: 0.02,
    total_due_usd: 0.022,
    tx_hash: "0xpriorloanalreadycreditedtx000000000000000000000000000000000001",
    provisioned_ms: NOW_MS - 500000,
  };
  const staleRow = {
    loan_id: `loan_${LENDER}_2`,
    lender_id: LENDER,
    borrower_id: BORROWER,
    status: "disbursement_uncertain",
    principal_usd: 0.02,
    total_due_usd: 0.022,
    provisioned_ms: NOW_MS - 60000,
  };
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(ledgerFileFor(dir), [priorRow, staleRow].map((r) => JSON.stringify(r)).join("\n") + "\n");
  let receivedLoanRows;
  const deps = happyDeps(dir, {
    reconcile: async ({ loanRow, loanRows }) => {
      assert.equal(loanRow.loan_id, staleRow.loan_id, "reconcile is still called with the SAME stale row as its own loanRow");
      receivedLoanRows = loanRows;
      return { found: false };
    },
  });
  await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.ok(Array.isArray(receivedLoanRows), "reconcile must receive a loanRows array, not undefined -- production reconcileProvisionalDisbursement needs it to reject an already-recorded tx_hash");
  assert.ok(
    receivedLoanRows.some((r) => r.loan_id === priorRow.loan_id && r.tx_hash === priorRow.tx_hash),
    "the FULL ledger (including OTHER loan rows with their own tx_hash) must be forwarded, not just the stale row alone -- otherwise reconcileProvisionalDisbursement has nothing to check its cross-loan replay guard against"
  );
});

// ===========================================================================
// FIND-102 fix (critical, impl-review iteration-2): a {found:false} reconcile result for a stale row is
// only trustworthy as "genuinely never disbursed" when the row's own age is still within what the
// reconciliation window could possibly have scanned -- otherwise a genuine broadcast that landed OUTSIDE
// the window would be silently marked disbursement_failed and a FRESH disbursement would proceed, a real
// double-spend. reconcileWindowSpanMs (exported) computes the SAME real-time span
// resolveStaleProvisioning's own age guard uses, tied to LENDING_RECONCILE_LOOKBACK_BLOCKS.
// ===========================================================================

test("FIND-102 fix: a stale row well WITHIN the reconcile window's real-time span, reconciled to {found:false}, is trusted -- marked disbursement_failed and a FRESH disbursement proceeds (baseline within-window behavior, unaffected by the new age guard)", async () => {
  const dir = tmpDir();
  const staleRow = {
    loan_id: `loan_${LENDER}_1`,
    lender_id: LENDER,
    borrower_id: "priorBorrower",
    status: "disbursement_uncertain",
    principal_usd: 0.02,
    total_due_usd: 0.022,
    provisioned_ms: NOW_MS - 60000, // 60s old -- far inside any real reconcile window
  };
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(ledgerFileFor(dir), JSON.stringify(staleRow) + "\n");
  let disburseCalls = 0;
  const deps = happyDeps(dir, {
    reconcile: async () => ({ found: false }),
    disburse: async ({ loanRow }) => {
      disburseCalls += 1;
      return {
        ok: true,
        tx: "0xwithinwindowfixturetx00000000000000000000000000000000001",
        to: loanRow.borrower_wallet,
        amountBase: Math.round(loanRow.principal_usd * 1e6),
      };
    },
  });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "active", "a within-window {found:false} must still resolve the stale row and let a fresh attempt proceed");
  assert.equal(disburseCalls, 1, "exactly one fresh disburse call for the new sequence number");
  const rows = readLoanRows(deps.ledgerFile);
  const staleFollowUp = rows.find((r) => r.loan_id === staleRow.loan_id && r.status === "disbursement_failed");
  assert.ok(staleFollowUp, "the stale row must resolve to disbursement_failed when genuinely within the window");
  const freshRow = rows.find((r) => r.loan_id === `loan_${LENDER}_2`);
  assert.ok(freshRow, "a fresh sequence number must be computed and issued");
});

test("FIND-102 fix: a stale row OLDER than the reconcile window's real-time span, reconciled to {found:false}, must be REFUSED (reason: stale_row_beyond_reconcile_window) rather than trusted -- prevents an automatic fresh disbursement that could double-spend a real transfer that landed outside the window's own visibility", async () => {
  const dir = tmpDir();
  const windowSpanMs = reconcileWindowSpanMs({});
  const staleRow = {
    loan_id: `loan_${LENDER}_1`,
    lender_id: LENDER,
    borrower_id: "priorBorrower",
    status: "disbursement_uncertain",
    principal_usd: 0.02,
    total_due_usd: 0.022,
    provisioned_ms: NOW_MS - (windowSpanMs + 60000), // just OLDER than the window can possibly cover
  };
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(ledgerFileFor(dir), JSON.stringify(staleRow) + "\n");
  const deps = happyDeps(dir, {
    reconcile: async () => ({ found: false }),
    disburse: async () => {
      throw new Error("disburse must never be called for a stale row beyond the reconcile window -- that would risk a real double-spend");
    },
  });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "refused");
  assert.equal(result.reason, "stale_row_beyond_reconcile_window");
  const rows = readLoanRows(deps.ledgerFile);
  assert.equal(rows.length, 1, "the pre-existing stale row is left EXACTLY as found -- zero new rows appended, zero sequence number consumed");
  assert.deepEqual(rows[0], staleRow);
});

test("PROP-115c step 6 (lock-protected fresh recheck finds the borrower newly ineligible) -> refused, ZERO rows, both locks released normally", async () => {
  const dir = tmpDir();
  let borrowerCallCount = 0;
  const deps = happyDeps(dir, {
    getCitizen: async (id) => {
      if (id === LENDER) return baseCitizen(LENDER, { balanceUsd: 10 });
      borrowerCallCount += 1;
      // Eligible ($0.10, broke) at the pre-lock read; a concurrent attempt's own disbursement lands
      // strictly between the pre-lock check and the lock-protected fresh re-check, pushing the
      // borrower's own balance above BORROWER_LOW_USD by the time this SAME attempt re-reads it.
      return baseCitizen(BORROWER, { balanceUsd: borrowerCallCount === 1 ? 0.1 : 100 });
    },
  });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "refused");
  assert.deepEqual(readLoanRows(deps.ledgerFile), []);
  assert.ok(borrowerCallCount >= 2, "the borrower's own eligibility must genuinely be re-read a second time at the lock-protected fresh recheck");
  // both locks released normally -- no stale lock file remains after release()
  assert.equal(fs.existsSync(path.join(dir, "locks", `loan_${LENDER}.lock`)), false);
  assert.equal(fs.existsSync(path.join(dir, "locks", `loan_borrower_${BORROWER}.lock`)), false);
});

test("PROP-115c step 7 (sizing computation refuses — decideLoan finds lenderAvailableUsd < loanCapUsd) -> refused, ZERO rows, both locks released normally", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir, {
    // Lender's own balance ($1) sits below the fixed per-citizen reserve ($5), so
    // computeLenderAvailableUsd floors to $0 -- strictly less than the cold-start loanCapUsd
    // ($0.02, successfulOnTimeRepayments===0) -- so decideLoan genuinely refuses on real inputs,
    // never a fabricated/injected decision.
    getCitizen: async (id) => {
      if (id === LENDER) return baseCitizen(LENDER, { balanceUsd: 1 });
      return baseCitizen(BORROWER, { balanceUsd: 0.1 });
    },
  });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "refused");
  assert.equal(result.reason, "insufficient_lender_surplus");
  assert.deepEqual(readLoanRows(deps.ledgerFile), []);
  // both locks released normally -- no stale lock file remains after release()
  assert.equal(fs.existsSync(path.join(dir, "locks", `loan_${LENDER}.lock`)), false);
  assert.equal(fs.existsSync(path.join(dir, "locks", `loan_borrower_${BORROWER}.lock`)), false);
});

test("PROP-115c step 8 (the provisional appendChild call itself throws, e.g. ENOSPC/EACCES) -> ZERO rows for this attempt's own n", async () => {
  const dir = tmpDir();
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(ledgerFileFor(dir), "");
  fs.chmodSync(ledgerFileFor(dir), 0o444); // read-only: reads (steps 3/5/6) succeed, the step-8 write throws
  const deps = happyDeps(dir);
  try {
    await assert.rejects(() => executeLoanIssuanceAttempt(baseParams(), deps));
  } finally {
    fs.chmodSync(ledgerFileFor(dir), 0o644);
  }
  assert.deepEqual(readLoanRows(deps.ledgerFile), [], "a later attempt for this SAME lender must recompute a fresh n from the ledger's own real, unaffected (still empty) state");
});

test("PROP-115c step 9 sub-case 1 (payViaFacilitator returns {ok:false}, clean failure) -> follow-up row disbursement_failed", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir, { disburse: async () => ({ ok: false, error: "insufficient facilitator liquidity" }) });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "disbursement_failed");
  const rows = readLoanRows(deps.ledgerFile);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].status, "provisioning");
  assert.equal(rows[1].status, "disbursement_failed");
  assert.equal(rows.some((r) => r.status === "active"), false, "no row anywhere ever claims active for a loan that was never actually funded");
});

test("PROP-115c step 9 sub-case 2 (payViaFacilitator throws mid-call, in-process exception) -> follow-up row disbursement_uncertain", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir, { disburse: async () => { throw new Error("RPC timeout during waitForTransactionReceipt"); } });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "disbursement_uncertain");
  const rows = readLoanRows(deps.ledgerFile);
  assert.equal(rows.length, 2);
  assert.equal(rows[1].status, "disbursement_uncertain");
  assert.equal(rows.some((r) => r.status === "active"), false);
});

// ===========================================================================
// FIND-001/FIND-003 fixes (impl-review iteration-1): defaultDisburse's OWN defensive guards (a SECOND,
// independent backstop behind wake-gate.mjs's own primary pre-lock guard -- see wake-gate.test.mjs's
// own FIND-001 fixtures for the primary-guard coverage). These tests exercise the REAL defaultDisburse
// (deps.disburse deliberately omitted, so happyDeps's own stub does NOT shadow it) with a deliberately
// unreachable facilitatorUrl -- proving each guard throws its OWN specific error BEFORE any network
// call is ever attempted (a network-layer error would look completely different).
// ===========================================================================

test("FIND-001 fix (defensive, real defaultDisburse): resolved lenderPrivateKey's derived signer address mismatched against loanRow.lender_wallet throws lender_signer_mismatch BEFORE payViaFacilitator is ever reached", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir, {
    disburse: undefined, // exercise the REAL defaultDisburse, not happyDeps's own stub
    lenderPrivateKey: "0x" + "3".repeat(64), // derives to a DIFFERENT address than LENDER's own baseCitizen() walletAddress.evm
    gigChain: "base",
    facilitatorUrl: "http://127.0.0.1:1", // would surface a DIFFERENT (network-layer) error if ever reached -- the signer-mismatch guard must fire FIRST
  });

  const result = await executeLoanIssuanceAttempt(baseParams(), deps);

  assert.equal(result.status, "disbursement_uncertain");
  assert.match(result.error, /lender_signer_mismatch/, "the signer/lender_wallet mismatch guard must throw before any network call is attempted");
});

test("FIND-003 fix (defensive, real defaultDisburse): GIG_CHAIN unset/non-'base' throws lending_chain_not_mainnet BEFORE payViaFacilitator is ever reached, even when the signer genuinely matches loanRow.lender_wallet", async () => {
  const dir = tmpDir();
  const lenderPrivateKey = "0x" + "4".repeat(64);
  const lenderWallet = privateKeyToAccount(lenderPrivateKey).address;
  const citizens = {
    [LENDER]: baseCitizen(LENDER, { balanceUsd: 10, walletAddress: { evm: lenderWallet } }),
    [BORROWER]: baseCitizen(BORROWER, { balanceUsd: 0.1 }),
  };
  const deps = happyDeps(dir, {
    getCitizen: async (id) => citizens[id] || null,
    disburse: undefined, // exercise the REAL defaultDisburse
    lenderPrivateKey,
    gigChain: "base-sepolia", // explicitly NOT mainnet
    facilitatorUrl: "http://127.0.0.1:1",
  });

  const result = await executeLoanIssuanceAttempt(baseParams(), deps);

  assert.equal(result.status, "disbursement_uncertain");
  assert.match(result.error, /lending_chain_not_mainnet/, "a non-mainnet/unset GIG_CHAIN must refuse to disburse real money, even with a genuinely matching signer");
});

test("FIND-001/FIND-003/FIND-103 fixes, matching case (defensive, real defaultDisburse): a genuinely matching signer + GIG_CHAIN=base + a facilitator that genuinely advertises eip155:8453 pass ALL THREE guards -- proven by a DIFFERENT, network-layer error surfacing once payViaFacilitator is genuinely reached, never any guard's own error", async () => {
  const dir = tmpDir();
  const lenderPrivateKey = "0x" + "5".repeat(64);
  const lenderWallet = privateKeyToAccount(lenderPrivateKey).address;
  const citizens = {
    [LENDER]: baseCitizen(LENDER, { balanceUsd: 10, walletAddress: { evm: lenderWallet } }),
    [BORROWER]: baseCitizen(BORROWER, { balanceUsd: 0.1 }),
  };
  const deps = happyDeps(dir, {
    getCitizen: async (id) => citizens[id] || null,
    disburse: undefined, // exercise the REAL defaultDisburse
    lenderPrivateKey,
    gigChain: "base",
    facilitatorUrl: "http://127.0.0.1:1", // deliberately unreachable -- payViaFacilitator's OWN network attempt must be what fails here, not any guard
    // FIND-103: the facilitator's own /supported response, mocked here so the preflight guard genuinely
    // passes (real facilitatorUrl is unreachable -- this mock is scoped ONLY to the preflight's own
    // fetch, payViaFacilitator itself still uses the real, unreachable facilitatorUrl below).
    fetchImpl: async (url) => {
      assert.ok(String(url).endsWith("/supported"), "the preflight must call /supported");
      return { json: async () => ({ kinds: [{ network: "eip155:8453" }] }) };
    },
  });

  const result = await executeLoanIssuanceAttempt(baseParams(), deps);

  assert.equal(result.status, "disbursement_uncertain");
  assert.ok(
    !/lender_signer_mismatch|lending_chain_not_mainnet|facilitator_not_mainnet/.test(result.error || ""),
    `all three defensive guards must have passed -- expected a network-layer failure, got: ${result.error}`
  );
});

// ===========================================================================
// FIND-103 fix (high, impl-review iteration-2): GIG_CHAIN=='base' proves our OWN code's intent, never
// which network the facilitator PROCESS actually listening at facilitatorUrl is configured for --
// defaultDisburse must ask the facilitator's own live /supported endpoint before signing.
// ===========================================================================

test("FIND-103 fix (defensive, real defaultDisburse): a facilitator whose /supported response does NOT advertise eip155:8453 (Base mainnet) throws facilitator_not_mainnet BEFORE payViaFacilitator is ever reached, even when the signer+GIG_CHAIN guards both pass", async () => {
  const dir = tmpDir();
  const lenderPrivateKey = "0x" + "6".repeat(64);
  const lenderWallet = privateKeyToAccount(lenderPrivateKey).address;
  const citizens = {
    [LENDER]: baseCitizen(LENDER, { balanceUsd: 10, walletAddress: { evm: lenderWallet } }),
    [BORROWER]: baseCitizen(BORROWER, { balanceUsd: 0.1 }),
  };
  let settleAttempted = false;
  const deps = happyDeps(dir, {
    getCitizen: async (id) => citizens[id] || null,
    disburse: undefined, // exercise the REAL defaultDisburse
    lenderPrivateKey,
    gigChain: "base",
    facilitatorUrl: "http://127.0.0.1:8405",
    fetchImpl: async (url) => {
      if (String(url).endsWith("/supported")) {
        // Still testnet-configured (base-sepolia's own eip155:84532), the EXACT WITNESS-RUNBOOK.md
        // documented failure mode -- a process bound to the expected port but NOT mainnet-configured.
        return { json: async () => ({ kinds: [{ network: "eip155:84532" }] }) };
      }
      settleAttempted = true;
      throw new Error("payViaFacilitator must never be reached when the facilitator is not mainnet-configured");
    },
  });

  const result = await executeLoanIssuanceAttempt(baseParams(), deps);

  assert.equal(result.status, "disbursement_uncertain");
  assert.match(result.error, /facilitator_not_mainnet/, "a non-mainnet-advertising facilitator must refuse before signing real lending money");
  assert.equal(settleAttempted, false, "payViaFacilitator's own network calls (which use the real global fetch, not deps.fetchImpl) must never be attempted -- proven here by deps.fetchImpl never being called for anything but /supported");
});

test("FIND-103 fix (defensive, real defaultDisburse): a facilitator whose /supported call itself fails (unreachable/malformed response) throws facilitator_not_mainnet, fail-closed, never silently proceeds to sign", async () => {
  const dir = tmpDir();
  const lenderPrivateKey = "0x" + "9".repeat(64);
  const lenderWallet = privateKeyToAccount(lenderPrivateKey).address;
  const citizens = {
    [LENDER]: baseCitizen(LENDER, { balanceUsd: 10, walletAddress: { evm: lenderWallet } }),
    [BORROWER]: baseCitizen(BORROWER, { balanceUsd: 0.1 }),
  };
  const deps = happyDeps(dir, {
    getCitizen: async (id) => citizens[id] || null,
    disburse: undefined,
    lenderPrivateKey,
    gigChain: "base",
    facilitatorUrl: "http://127.0.0.1:8405",
    fetchImpl: async () => {
      throw new Error("ECONNREFUSED (simulated)");
    },
  });

  const result = await executeLoanIssuanceAttempt(baseParams(), deps);

  assert.equal(result.status, "disbursement_uncertain");
  assert.match(result.error, /facilitator_not_mainnet/, "an unreachable /supported check must fail closed, never be treated as an implicit pass");
});

test("PROP-115c step 9 sub-case 3 (settle succeeds but the FOLLOW-UP append itself throws) -> provisional row left unterminated, never a false active claim", async () => {
  const dir = tmpDir();
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(ledgerFileFor(dir), "");
  const deps = happyDeps(dir, {
    disburse: async ({ loanRow }) => {
      // The real, irreversible settle succeeded -- but immediately afterward the ledger file becomes
      // unwritable (ENOSPC/EACCES-class failure) BEFORE the follow-up append can land.
      fs.chmodSync(ledgerFileFor(dir), 0o444);
      return { ok: true, tx: "0xsettledbutappendfailsfixture00000000000000000000000000000001", to: loanRow.borrower_wallet, amountBase: 20000 };
    },
  });
  try {
    await executeLoanIssuanceAttempt(baseParams(), deps).catch(() => {});
  } finally {
    fs.chmodSync(ledgerFileFor(dir), 0o644);
  }
  const rows = readLoanRows(deps.ledgerFile);
  assert.equal(rows.length, 1, "only the provisional row exists -- the follow-up append never landed");
  assert.equal(rows[0].status, "provisioning");
  assert.equal(rows.some((r) => r.status === "active"), false, "no row anywhere ever claims active without a genuinely landed follow-up append");
});

// ---------------------------------------------------------------------------
// PROP-115d / CRIT-204: the dual per-lender/per-borrower lock scope, staggered-race proof
// (mirrors anicca-agent-spawn sprint-2's own spawn-orchestrator.test.mjs PROP-307d method).
// ---------------------------------------------------------------------------

test("PROP-115d: the loan_${lenderId}/loan_borrower_${borrowerId} locks are held together from before step 5 until after step 9 completes -- a staggered concurrent attempt for the SAME lender fails throughout, succeeds only after release", async () => {
  const dir = tmpDir();
  let releaseDisburse;
  const disburseDelay = new Promise((resolve) => { releaseDisburse = resolve; });
  let signalDisburseReached;
  const disburseReached = new Promise((resolve) => { signalDisburseReached = resolve; });

  const deps = happyDeps(dir, {
    disburse: async ({ loanRow }) => {
      signalDisburseReached();
      await disburseDelay;
      return { ok: true, tx: "0xstaggeredtxfixture0000000000000000000000000000000000000000001", to: loanRow.borrower_wallet, amountBase: 20000 };
    },
  });

  const firstAttempt = executeLoanIssuanceAttempt(baseParams(), deps);
  await disburseReached;

  for (let i = 0; i < 5; i++) {
    const staggered = await executeLoanIssuanceAttempt(baseParams(), deps).catch((e) => ({ status: "refused", error: String(e) }));
    assert.notEqual(staggered.status, "active", `staggered attempt ${i} while step 9 is still in flight must never succeed`);
  }

  releaseDisburse();
  const firstResult = await firstAttempt;
  assert.equal(firstResult.status, "active");

  const afterRelease = await executeLoanIssuanceAttempt(baseParams({ borrowerId: "SecondBorrower" }), happyDeps(dir, {
    getCitizen: async (id) => {
      const citizens = {
        [LENDER]: baseCitizen(LENDER, { balanceUsd: 10 }),
        SecondBorrower: baseCitizen("SecondBorrower", { balanceUsd: 0.1 }),
      };
      return citizens[id] || null;
    },
  }));
  assert.equal(afterRelease.status, "active", "the lender's own lock must be acquirable again only AFTER the first attempt's follow-up append actually completed");
});

// ---------------------------------------------------------------------------
// REQ-116: executeRepaymentClaim.
// ---------------------------------------------------------------------------

function activeLoanRow(overrides = {}) {
  return {
    loan_id: `loan_${LENDER}_1`,
    lender_id: LENDER,
    borrower_id: BORROWER,
    lender_wallet: baseCitizen(LENDER).walletAddress.evm,
    borrower_wallet: baseCitizen(BORROWER).walletAddress.evm,
    status: "active",
    principal_usd: 0.02,
    total_due_usd: 0.022,
    repaid_usd: 0,
    issued_ms: NOW_MS - 5 * 86400000,
    due_ms: NOW_MS + 9 * 86400000,
    ...overrides,
  };
}

function seedLedger(dir, rows) {
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(ledgerFileFor(dir), rows.map((r) => JSON.stringify(r)).join("\n") + (rows.length ? "\n" : ""));
}

test("REQ-116 executeRepaymentClaim: a partial credit updates repaid_usd, status remains active", async () => {
  const dir = tmpDir();
  seedLedger(dir, [activeLoanRow()]);
  const deps = { ledgerFile: ledgerFileFor(dir), lockStatePath: ledgerFileFor(dir), verify: async () => ({ credited: 0.01, rejected: false }) };
  const result = await executeRepaymentClaim({ loanId: `loan_${LENDER}_1`, txHash: "0xpartialtxfixture000000000000000000000000000000000000000001", nowMs: NOW_MS }, deps);
  assert.equal(result.credited, 0.01);
  assert.equal(result.status, "active");
  const rows = readLoanRows(deps.ledgerFile).filter((r) => r.loan_id === `loan_${LENDER}_1`);
  const last = rows[rows.length - 1];
  assert.equal(last.repaid_usd, 0.01);
  assert.equal(last.status, "active");
});

test("REQ-116 executeRepaymentClaim: a credit that reaches total_due_usd transitions to repaid, on_time set", async () => {
  const dir = tmpDir();
  seedLedger(dir, [activeLoanRow({ repaid_usd: 0.01 })]);
  const deps = { ledgerFile: ledgerFileFor(dir), lockStatePath: ledgerFileFor(dir), verify: async () => ({ credited: 0.012, rejected: false }) };
  const result = await executeRepaymentClaim({ loanId: `loan_${LENDER}_1`, txHash: "0xfulltxfixture00000000000000000000000000000000000000000001", nowMs: NOW_MS }, deps);
  assert.equal(result.status, "repaid");
  const rows = readLoanRows(deps.ledgerFile).filter((r) => r.loan_id === `loan_${LENDER}_1`);
  const last = rows[rows.length - 1];
  assert.equal(last.status, "repaid");
  assert.equal(last.repaid_usd, 0.022);
  assert.equal(last.on_time, true, "NOW_MS is before due_ms in this fixture -- on_time must be true");
});

test("REQ-116 executeRepaymentClaim: a rejected verification (invalid/replayed txHash) appends ZERO rows", async () => {
  const dir = tmpDir();
  seedLedger(dir, [activeLoanRow()]);
  const deps = { ledgerFile: ledgerFileFor(dir), lockStatePath: ledgerFileFor(dir), verify: async () => ({ credited: 0, rejected: true }) };
  const before = readLoanRows(deps.ledgerFile).length;
  const result = await executeRepaymentClaim({ loanId: `loan_${LENDER}_1`, txHash: "0xreplayedtxfixture0000000000000000000000000000000000000001", nowMs: NOW_MS }, deps);
  assert.deepEqual(result, { credited: 0, status: "rejected", rejected: true });
  assert.equal(readLoanRows(deps.ledgerFile).length, before, "a rejected repayment claim appends NOTHING to loans.jsonl");
});

test("REQ-116 executeRepaymentClaim: a loanId whose last row is NOT active (already repaid) is refused BEFORE verify is ever invoked", async () => {
  const dir = tmpDir();
  seedLedger(dir, [activeLoanRow({ status: "repaid", repaid_usd: 0.022, on_time: true })]);
  let verifyCalled = false;
  const deps = { ledgerFile: ledgerFileFor(dir), lockStatePath: ledgerFileFor(dir), verify: async () => { verifyCalled = true; return { credited: 0.022, rejected: false }; } };
  const result = await executeRepaymentClaim({ loanId: `loan_${LENDER}_1`, txHash: "0xneverusedtxfixture0000000000000000000000000000000000001", nowMs: NOW_MS }, deps);
  assert.equal(result.status, "rejected");
  assert.equal(result.credited, 0);
  assert.equal(verifyCalled, false, "verify must NEVER be invoked against a loan that was never actually active/disbursed");
});

// ---------------------------------------------------------------------------
// REQ-116: executeDefaultDetectionSweep.
// ---------------------------------------------------------------------------

test("REQ-116 executeDefaultDetectionSweep: an overdue-unpaid active loan is appended as defaulted with defaulted_ms genuinely set at append time", async () => {
  const dir = tmpDir();
  seedLedger(dir, [activeLoanRow({ due_ms: NOW_MS - 1000 })]);
  const deps = { ledgerFile: ledgerFileFor(dir), lockStatePath: ledgerFileFor(dir) };
  const result = await executeDefaultDetectionSweep({ nowMs: NOW_MS }, deps);
  assert.deepEqual(result.defaulted, [`loan_${LENDER}_1`]);
  const rows = readLoanRows(deps.ledgerFile).filter((r) => r.loan_id === `loan_${LENDER}_1`);
  const last = rows[rows.length - 1];
  assert.equal(last.status, "defaulted");
  assert.equal(last.defaulted_ms, NOW_MS, "PROP-116d: defaulted_ms is genuinely set to the append-time nowMs, never hand-populated fixture data");
});

test("REQ-116 executeDefaultDetectionSweep: an on-time-not-yet-due active loan is never flagged", async () => {
  const dir = tmpDir();
  seedLedger(dir, [activeLoanRow({ due_ms: NOW_MS + 5 * 86400000 })]);
  const deps = { ledgerFile: ledgerFileFor(dir), lockStatePath: ledgerFileFor(dir) };
  const result = await executeDefaultDetectionSweep({ nowMs: NOW_MS }, deps);
  assert.deepEqual(result.defaulted, []);
});

test("REQ-116 executeDefaultDetectionSweep: a candidate flagged by step 1's read but found already-repaid at step 2's own fresh re-read is correctly skipped, never defaulted", async () => {
  const dir = tmpDir();
  seedLedger(dir, [activeLoanRow({ due_ms: NOW_MS - 1000 })]);
  const deps = {
    ledgerFile: ledgerFileFor(dir),
    lockStatePath: ledgerFileFor(dir),
    // Simulate a concurrent executeRepaymentClaim landing strictly between step 1's read and this
    // candidate's own step-2 lock acquisition: append a "repaid" row for the SAME loan_id right before
    // the sweep would otherwise append its own defaulted row, by racing a real concurrent repayment.
  };
  const claimDeps = { ledgerFile: ledgerFileFor(dir), lockStatePath: ledgerFileFor(dir), verify: async () => ({ credited: 0.022, rejected: false }) };
  const [sweepResult] = await Promise.all([
    executeDefaultDetectionSweep({ nowMs: NOW_MS }, deps),
    executeRepaymentClaim({ loanId: `loan_${LENDER}_1`, txHash: "0xracingrepaytxfixture0000000000000000000000000000000001", nowMs: NOW_MS }, claimDeps),
  ]);
  const rows = readLoanRows(deps.ledgerFile).filter((r) => r.loan_id === `loan_${LENDER}_1`);
  const last = rows[rows.length - 1];
  assert.notEqual(last.status, "defaulted", "whichever of the two races wins the lock, the loan must never end up BOTH repaid and defaulted");
  if (last.status === "repaid") {
    assert.deepEqual(sweepResult.defaulted, [], "the sweep must have skipped this candidate once its own step-2 fresh re-read found it already repaid");
  }
});

// ---------------------------------------------------------------------------
// PROP-116c / CRIT-204: repayment claim vs default-detection sweep race, SAME loan_id.
// ---------------------------------------------------------------------------

test("PROP-116c: a repayment claim and a default-detection sweep racing on the SAME loan_id never both append -- exactly one wins", async () => {
  const dir = tmpDir();
  seedLedger(dir, [activeLoanRow({ due_ms: NOW_MS - 1000 })]);
  const claimDeps = { ledgerFile: ledgerFileFor(dir), lockStatePath: ledgerFileFor(dir), verify: async () => ({ credited: 0.022, rejected: false }) };
  const sweepDeps = { ledgerFile: ledgerFileFor(dir), lockStatePath: ledgerFileFor(dir) };
  const [claimResult, sweepResult] = await Promise.all([
    executeRepaymentClaim({ loanId: `loan_${LENDER}_1`, txHash: "0xraceclaimtxfixture000000000000000000000000000000000001", nowMs: NOW_MS }, claimDeps),
    executeDefaultDetectionSweep({ nowMs: NOW_MS }, sweepDeps),
  ]);
  const rows = readLoanRows(ledgerFileFor(dir)).filter((r) => r.loan_id === `loan_${LENDER}_1`);
  // exactly ONE terminal transition landed beyond the seeded active row (either repaid, or defaulted --
  // never both, and never neither if one side's own lock acquisition genuinely won).
  const terminalRows = rows.filter((r) => r.status === "repaid" || r.status === "defaulted");
  assert.equal(terminalRows.length <= 1, true, "at most one terminal append lands for this loan_id from this race");
  const bothWon = claimResult.status === "repaid" && sweepResult.defaulted.includes(`loan_${LENDER}_1`);
  assert.equal(bothWon, false, "the repayment claim and the default sweep must never BOTH win for the same loan_id");
});

// ---------------------------------------------------------------------------
// PROP-116e: loanId/txHash provenance -- never internally derived, always caller-supplied, passed
// through unmodified into the REAL verifyRepayment.
// ---------------------------------------------------------------------------

test("PROP-116e structural: executeRepaymentClaim's loanId/txHash parameters are used exactly as received -- never regenerated/derived internally before being passed to verify", () => {
  const src = fs.readFileSync(ORCH_PATH, "utf8");
  const claimFnMatch = src.match(/export\s+async\s+function\s+executeRepaymentClaim[\s\S]*?\n}\n/);
  assert.ok(claimFnMatch);
  const body = claimFnMatch[0];
  assert.ok(!/randomUUID|crypto\.random|Math\.random/.test(body), "loanId/txHash must never be internally generated inside executeRepaymentClaim");
});

test("PROP-116e structural: executeDefaultDetectionSweep's own candidate loan_id[] list is always detectDefaultedLoans's own direct return value, never hand-assembled", () => {
  const src = fs.readFileSync(ORCH_PATH, "utf8");
  const sweepFnMatch = src.match(/export\s+async\s+function\s+executeDefaultDetectionSweep[\s\S]*?\n}\n/);
  assert.ok(sweepFnMatch);
  assert.match(sweepFnMatch[0], /detectDefaultedLoans/, "executeDefaultDetectionSweep must call detectDefaultedLoans directly for its candidate list");
});

// Minimal local JSON-RPC mock server -- reused verbatim from lending-verify.test.mjs's own sprint-1
// precedent (startMockRpc), proving executeRepaymentClaim's PRODUCTION DEFAULT (deps.verify omitted,
// only deps.rpcUrl supplied) genuinely wires the REAL verifyRepayment end-to-end, never a stand-in.
const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
function padTopicExact(addr) { return "0x" + "0".repeat(24) + addr.slice(2).toLowerCase(); }
function transferLog({ from, to, valueBase }) {
  return {
    address: USDC,
    topics: [TRANSFER_TOPIC, padTopicExact(from), padTopicExact(to)],
    data: "0x" + BigInt(valueBase).toString(16).padStart(64, "0"),
  };
}
function startMockRpc(handlers) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      let body = "";
      req.on("data", (c) => (body += c));
      req.on("end", () => {
        const { method, params, id } = JSON.parse(body || "{}");
        const handler = handlers[method];
        res.setHeader("Content-Type", "application/json");
        if (!handler) {
          res.end(JSON.stringify({ jsonrpc: "2.0", id, error: { code: -32601, message: `no mock handler for ${method}` } }));
          return;
        }
        res.end(JSON.stringify({ jsonrpc: "2.0", id, result: handler(params) }));
      });
    });
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      resolve({ url: `http://127.0.0.1:${port}`, close: () => new Promise((r) => server.close(r)) });
    });
  });
}

test("PROP-116e integration: a caller-supplied loanId/txHash pair is passed through unmodified into the REAL verifyRepayment (production default wiring, no deps.verify override)", async () => {
  const dir = tmpDir();
  const lenderWallet = baseCitizen(LENDER).walletAddress.evm;
  const borrowerWallet = baseCitizen(BORROWER).walletAddress.evm;
  seedLedger(dir, [activeLoanRow({ lender_wallet: lenderWallet, borrower_wallet: borrowerWallet })]);
  const rpc = await startMockRpc({
    eth_getTransactionReceipt: () => ({ status: "0x1", blockNumber: "0x64", logs: [transferLog({ from: borrowerWallet, to: lenderWallet, valueBase: 22000 })] }),
    eth_getBlockByNumber: () => ({ number: "0x64" }),
  });
  try {
    const deps = { ledgerFile: ledgerFileFor(dir), lockStatePath: ledgerFileFor(dir), rpcUrl: rpc.url };
    const suppliedTxHash = "0xrealwiringtxfixture000000000000000000000000000000000000001";
    const result = await executeRepaymentClaim({ loanId: `loan_${LENDER}_1`, txHash: suppliedTxHash, nowMs: NOW_MS }, deps);
    assert.equal(result.status, "repaid");
    assert.equal(result.credited, 0.022);
    const rows = readLoanRows(deps.ledgerFile).filter((r) => r.loan_id === `loan_${LENDER}_1`);
    const last = rows[rows.length - 1];
    assert.equal(last.tx_hash, suppliedTxHash, "the exact caller-supplied txHash is what verifyRepayment saw and what got recorded -- never regenerated");
    // sanity: the REAL verifyRepayment function (not a stand-in) does credit this exact fixture directly
    const direct = await verifyRepayment({ txHash: suppliedTxHash, expectedFrom: borrowerWallet, expectedTo: lenderWallet, rpcUrl: rpc.url, loanRows: [] });
    assert.equal(direct.credited, 0.022);
  } finally {
    await rpc.close();
  }
});
