// Phase 5 (formal hardening) proof harness — anicca-agent-lending sprint-2.
//
// Closes the residual gap between sprint-2's 19 targeted deferred proof obligations
// (contracts/sprint-2.md's "Deferred-obligation disposition" section) and what
// skills/economy/lending/lib/__tests__/lending-orchestrator.test.mjs (30 tests, already GREEN)
// happens to cover. Every scenario below drives the REAL, unmodified
// executeLoanIssuanceAttempt/executeRepaymentClaim/executeDefaultDetectionSweep from
// lending-orchestrator.mjs -- never a re-implementation or mock of the orchestrator itself. Only the
// module's own already-designed `deps` seam (getCitizen/reconcile/disburse/verify) is used, exactly the
// same production/test wiring convention lending-orchestrator.test.mjs already establishes.
//
// Covers: PROP-106b, PROP-106e (Tier-2 half), PROP-106f (n+1 continuation), PROP-106g (found:false
// half), PROP-106h (disbursement_uncertain-seeded reconciliation), PROP-106k (double-fault: in-process
// exception whose OWN uncertain-append also throws), PROP-106l (retry-safety: throws once, then
// resolves exactly once on a later attempt), PROP-106n (cross-lender double-borrow race), PROP-106o
// (issued_ms/due_ms drawn from the RECLAIMING call's own later nowMs, never the stale row's own earlier
// provisioned_ms), PROP-106p (both kill-switches' lock-protected fresh-recheck TOCTOU race), PROP-108c
// (partial-then-full repayment chained through the SAME evolving ledger in one continuous run).
//
// Run: node verification/proof-harnesses/sprint2-orchestrator-residual-props.mjs
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  executeLoanIssuanceAttempt,
  executeRepaymentClaim,
} from "/Users/anicca/anicca/skills/economy/lending/lib/lending-orchestrator.mjs";

const LENDER = "anicca-a3cdd4";
const BORROWER = "Franklin";
const NOW_MS = 1_800_000_000_000;

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "anicca-lending-harness-"));
}
function ledgerFileFor(dir) {
  return path.join(dir, "loans.jsonl");
}
function lockFileFor(dir, key) {
  return path.join(dir, "locks", `${key}.lock`);
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
function seedLedger(dir, rows) {
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(ledgerFileFor(dir), rows.map((r) => JSON.stringify(r)).join("\n") + (rows.length ? "\n" : ""));
}
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
function happyDeps(dir, citizenOverrides, overrides = {}) {
  const citizens = citizenOverrides || {
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
      tx: "0xharnesstxfixture000000000000000000000000000000000000000001",
      to: loanRow.borrower_wallet,
      amountBase: Math.round(loanRow.principal_usd * 1e6),
    }),
    ...overrides,
  };
}
function baseParams(overrides = {}) {
  return { lenderId: LENDER, borrowerId: BORROWER, nowMs: NOW_MS, ...overrides };
}
function poisonColdStartRows(lenderId, count = 10, borrowerPrefix = "poisonBorrower") {
  return Array.from({ length: count }, (_, i) => ({
    loan_id: `loan_${lenderId}_poison${i}`,
    lender_id: lenderId,
    borrower_id: `${borrowerPrefix}${i}`,
    status: "defaulted",
    principal_usd: 0.02,
    repaid_usd: 0,
    total_due_usd: 0.022,
    issued_ms: NOW_MS - 30 * 86400000,
    due_ms: NOW_MS - 16 * 86400000,
  }));
}
function appendRawRow(file, row) {
  fs.appendFileSync(file, JSON.stringify(row) + "\n");
}

const results = [];
async function scenario(name, fn) {
  try {
    await fn();
    results.push({ name, ok: true });
    console.log(`PASS: ${name}`);
  } catch (e) {
    results.push({ name, ok: false, error: e.message, stack: e.stack });
    console.log(`FAIL: ${name} -- ${e.message}`);
  }
}

// ---------------------------------------------------------------------------
// PROP-106b: a crashed holder's lock (no heartbeat for >= staleMs, a real backdated .lock file) is
// reclaimable, and exactly one of two concurrent reclaimers wins.
// ---------------------------------------------------------------------------
await scenario("PROP-106b: a real backdated (stale) loan_${lenderId}.lock file is reclaimed by a genuine executeLoanIssuanceAttempt, never left permanently wedged", async () => {
  const dir = tmpDir();
  const lockFile = lockFileFor(dir, `loan_${LENDER}`);
  fs.mkdirSync(path.dirname(lockFile), { recursive: true });
  fs.writeFileSync(lockFile, "");
  const oldTime = new Date(Date.now() - 90_000); // well past withGigLock's DEFAULT_STALE_MS (60_000ms)
  fs.utimesSync(lockFile, oldTime, oldTime);
  const deps = happyDeps(dir);
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "active", "a genuinely stale (backdated) lock file must be reclaimed, not treated as permanently held");
  assert.ok(fs.existsSync(ledgerFileFor(dir)));

  // control: a FRESH (non-stale) lock file of the same shape must NOT be reclaimed -- proves the
  // success above is genuinely due to staleness, not because withGigLock ignores lock files entirely.
  const dir2 = tmpDir();
  const lockFile2 = lockFileFor(dir2, `loan_${LENDER}`);
  fs.mkdirSync(path.dirname(lockFile2), { recursive: true });
  fs.writeFileSync(lockFile2, "");
  const freshTime = new Date(); // mtime = now, not stale
  fs.utimesSync(lockFile2, freshTime, freshTime);
  const deps2 = happyDeps(dir2);
  const result2 = await executeLoanIssuanceAttempt(baseParams(), deps2);
  assert.equal(result2.status, "refused");
  assert.equal(result2.reason, "lock_held", "a FRESH lock file must NOT be reclaimed -- proves the stale case above is genuinely staleness-driven");
});

await scenario("PROP-106b: two concurrent callers racing to reclaim the SAME stale lock -- exactly one reclaims and succeeds", async () => {
  const dir = tmpDir();
  const lockFile = lockFileFor(dir, `loan_${LENDER}`);
  fs.mkdirSync(path.dirname(lockFile), { recursive: true });
  fs.writeFileSync(lockFile, "");
  const oldTime = new Date(Date.now() - 90_000);
  fs.utimesSync(lockFile, oldTime, oldTime);
  const citizens = {
    [LENDER]: baseCitizen(LENDER, { balanceUsd: 10 }),
    B1: baseCitizen("B1", { balanceUsd: 0.1 }),
    B2: baseCitizen("B2", { balanceUsd: 0.1 }),
  };
  const deps = happyDeps(dir, citizens);
  const [r1, r2] = await Promise.all([
    executeLoanIssuanceAttempt(baseParams({ borrowerId: "B1" }), deps),
    executeLoanIssuanceAttempt(baseParams({ borrowerId: "B2" }), deps),
  ]);
  const activeCount = [r1, r2].filter((r) => r.status === "active").length;
  assert.equal(activeCount, 1, "exactly one of the two concurrent reclaim attempts must win the stale lock");
  const refused = [r1, r2].find((r) => r.status !== "active");
  assert.equal(refused.reason, "lock_held", "the losing reclaim attempt must observe lock_held, never a corrupted/partial state");
});

// ---------------------------------------------------------------------------
// PROP-106e (Tier-2 half): two DIFFERENT lenders concurrently issuing to two DIFFERENT borrowers ->
// distinct loan_ids, zero collision, no shared/global lock required.
// ---------------------------------------------------------------------------
await scenario("PROP-106e Tier-2: two different lenders concurrently disbursing to two different borrowers succeed with distinct, non-colliding loan_ids", async () => {
  const dir = tmpDir();
  const citizens = {
    LenderA: baseCitizen("LenderA", { balanceUsd: 10 }),
    LenderB: baseCitizen("LenderB", { balanceUsd: 10 }),
    BorrowerX: baseCitizen("BorrowerX", { balanceUsd: 0.1 }),
    BorrowerY: baseCitizen("BorrowerY", { balanceUsd: 0.1 }),
  };
  const deps = happyDeps(dir, citizens);
  const [rA, rB] = await Promise.all([
    executeLoanIssuanceAttempt({ lenderId: "LenderA", borrowerId: "BorrowerX", nowMs: NOW_MS }, deps),
    executeLoanIssuanceAttempt({ lenderId: "LenderB", borrowerId: "BorrowerY", nowMs: NOW_MS }, deps),
  ]);
  assert.equal(rA.status, "active");
  assert.equal(rB.status, "active");
  assert.notEqual(rA.loanId, rB.loanId);
  assert.equal(rA.loanId, "loan_LenderA_1");
  assert.equal(rB.loanId, "loan_LenderB_1");
});

// ---------------------------------------------------------------------------
// PROP-106f: after a clean disbursement_failed follow-up, the SAME lender's next attempt computes n+1
// and immediately re-acquires the lock (no wedge left behind by a clean facilitator-side failure).
// ---------------------------------------------------------------------------
await scenario("PROP-106f: a disbursement_failed follow-up releases the lock normally -- the SAME lender's very next attempt computes n+1 and succeeds immediately", async () => {
  const dir = tmpDir();
  const citizens = {
    [LENDER]: baseCitizen(LENDER, { balanceUsd: 10 }),
    B1: baseCitizen("B1", { balanceUsd: 0.1 }),
    B2: baseCitizen("B2", { balanceUsd: 0.1 }),
  };
  const failDeps = happyDeps(dir, citizens, { disburse: async () => ({ ok: false, error: "insufficient facilitator liquidity" }) });
  const r1 = await executeLoanIssuanceAttempt(baseParams({ borrowerId: "B1" }), failDeps);
  assert.equal(r1.status, "disbursement_failed");
  assert.equal(r1.loanId, `loan_${LENDER}_1`);

  const okDeps = happyDeps(dir, citizens);
  const r2 = await executeLoanIssuanceAttempt(baseParams({ borrowerId: "B2" }), okDeps);
  assert.equal(r2.status, "active", "the lock must be immediately re-acquirable after a clean disbursement_failed release");
  assert.equal(r2.loanId, `loan_${LENDER}_2`, "sequence numbering must genuinely advance to n+1, treating the failed n=1 row as already-claimed");
});

// ---------------------------------------------------------------------------
// PROP-106g: reconciliation lookup finds NOTHING (found:false) -> the stale row is resolved to
// disbursement_failed (never re-disbursed), and this SAME attempt proceeds to a fresh n+1 disbursement.
// ---------------------------------------------------------------------------
await scenario("PROP-106g (found:false half): an unresolved crashed disbursement with NO matching on-chain transfer is closed out as disbursement_failed, never re-disbursed, and this attempt still proceeds at n+1", async () => {
  const dir = tmpDir();
  const staleRow = {
    loan_id: `loan_${LENDER}_1`, lender_id: LENDER, borrower_id: "priorBorrower",
    status: "provisioning", principal_usd: 0.02, total_due_usd: 0.022, provisioned_ms: NOW_MS - 60000,
  };
  seedLedger(dir, [staleRow]);
  let disburseCalls = 0;
  const deps = happyDeps(dir, undefined, {
    reconcile: async () => ({ found: false }),
    disburse: async ({ loanRow }) => { disburseCalls += 1; return { ok: true, tx: "0xn2txfixture00000000000000000000000000000000000000000001", to: loanRow.borrower_wallet, amountBase: 20000 }; },
  });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "active");
  assert.equal(result.loanId, `loan_${LENDER}_2`, "the new attempt's own sequence number must be n+1, computed AFTER the stale n=1 row is resolved");
  assert.equal(disburseCalls, 1, "payViaFacilitator must be invoked exactly once -- only for this attempt's own genuine n=2 disbursement, never for the already-crashed n=1 row");
  const rows = readLoanRows(ledgerFileFor(dir));
  const n1Rows = rows.filter((r) => r.loan_id === `loan_${LENDER}_1`);
  assert.equal(n1Rows[n1Rows.length - 1].status, "disbursement_failed");
});

// ---------------------------------------------------------------------------
// PROP-106h: a stale row seeded as "disbursement_uncertain" (not "provisioning") is reconciled by the
// NEXT attempt via the identical mechanism -- proving the unification is genuine, not provisioning-only.
// ---------------------------------------------------------------------------
await scenario("PROP-106h: a disbursement_uncertain-seeded stale row (in-process-exception path, not a crash) is reconciled before the next attempt computes n+1", async () => {
  const dir = tmpDir();
  const staleRow = {
    loan_id: `loan_${LENDER}_1`, lender_id: LENDER, borrower_id: "priorBorrower",
    status: "disbursement_uncertain", principal_usd: 0.02, total_due_usd: 0.022, provisioned_ms: NOW_MS - 60000,
    error: "RPC timeout during waitForTransactionReceipt",
  };
  seedLedger(dir, [staleRow]);
  const deps = happyDeps(dir, undefined, {
    reconcile: async ({ loanRow }) => {
      assert.equal(loanRow.loan_id, staleRow.loan_id);
      assert.equal(loanRow.status, "disbursement_uncertain");
      return { found: true, txHash: "0xreconciledUncertainFixture0000000000000000000000000000001" };
    },
  });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "active");
  const rows = readLoanRows(ledgerFileFor(dir));
  const reconciledFollowUp = rows.find((r) => r.loan_id === staleRow.loan_id && r.status === "active");
  assert.ok(reconciledFollowUp, "the disbursement_uncertain row must get its own reconciled active follow-up, identically to the provisioning case");
  const newRow = rows.find((r) => r.loan_id === `loan_${LENDER}_2`);
  assert.ok(newRow, "this attempt's own new n=2 must be computed AFTER the uncertain row is reconciled");
});

// ---------------------------------------------------------------------------
// PROP-106k: the in-process exception is caught, but the CATCH BLOCK'S OWN follow-up append (recording
// disbursement_uncertain) itself throws too -- a genuine double-fault. The ledger must be left EXACTLY
// as found (no third, unhandled terminal state), the lock released normally, and the NEXT attempt for
// this SAME lender must still invoke reconciliation for this SAME unterminated row.
// ---------------------------------------------------------------------------
await scenario("PROP-106k: settle-side exception caught, but the disbursement_uncertain follow-up append ITSELF throws -- ledger left exactly as found, lock released normally, next attempt still reconciles this row", async () => {
  const dir = tmpDir();
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(ledgerFileFor(dir), "");
  // the FIRST (double-faulting) attempt targets a DIFFERENT borrower than the SECOND (reconciling)
  // attempt below -- isolates "does this lender's own stale row get reconciled" from "is my actual
  // target borrower eligible", mirroring lending-orchestrator.test.mjs's own step-5-happy precedent
  // (staleRow.borrower_id: "priorBorrower" vs the reconciling call's own distinct BORROWER).
  const citizens = {
    [LENDER]: baseCitizen(LENDER, { balanceUsd: 10 }),
    priorBorrowerK: baseCitizen("priorBorrowerK", { balanceUsd: 0.1 }),
    [BORROWER]: baseCitizen(BORROWER, { balanceUsd: 0.1 }),
  };
  const deps = happyDeps(dir, citizens, {
    disburse: async () => {
      // the real settle-side exception path: chmod BEFORE throwing, so the catch block's own
      // appendLoanRow(status:"disbursement_uncertain") call is what fails, not the disburse() call site.
      fs.chmodSync(ledgerFileFor(dir), 0o444);
      throw new Error("RPC timeout during waitForTransactionReceipt");
    },
  });
  let threw = false;
  try {
    await executeLoanIssuanceAttempt(baseParams({ borrowerId: "priorBorrowerK" }), deps);
  } catch (e) {
    threw = true;
  } finally {
    fs.chmodSync(ledgerFileFor(dir), 0o644);
  }
  assert.equal(threw, true, "a double-fault (settle exception + its own uncertain-append also failing) must propagate as a rejected promise, never silently swallowed into a fabricated status");
  const rowsAfterFault = readLoanRows(ledgerFileFor(dir));
  assert.equal(rowsAfterFault.length, 1, "only the ORIGINAL provisional row exists -- the uncertain follow-up never landed");
  assert.equal(rowsAfterFault[0].status, "provisioning");
  assert.equal(fs.existsSync(lockFileFor(dir, `loan_${LENDER}`)), false, "the lock must be released normally (not left as a stale artifact) even when fn() itself threw");
  assert.equal(fs.existsSync(lockFileFor(dir, "loan_borrower_priorBorrowerK")), false);

  // subsequent attempt for the SAME lender (targeting the OTHER borrower): this SAME unterminated
  // "provisioning" row must still be the trigger for reconciliation, proving this is NOT a third,
  // unhandled terminal state.
  let reconcileCalledWith = null;
  const deps2 = happyDeps(dir, citizens, {
    reconcile: async ({ loanRow }) => { reconcileCalledWith = loanRow; return { found: true, txHash: "0xdoublefaultreconciledfixture000000000000000000000000001" }; },
  });
  const result2 = await executeLoanIssuanceAttempt(baseParams({ borrowerId: BORROWER }), deps2);
  assert.equal(result2.status, "active");
  assert.ok(reconcileCalledWith, "reconcile must be invoked on the next attempt");
  assert.equal(reconcileCalledWith.loan_id, `loan_${LENDER}_1`);
  assert.equal(reconcileCalledWith.status, "provisioning", "the row handed to reconcile must be the SAME unterminated row left by the double-fault, driven purely by ledger state");
  assert.equal(result2.loanId, `loan_${LENDER}_2`, "the reconciling attempt's own new loan must be n+1, computed after n=1 is resolved");
});

// ---------------------------------------------------------------------------
// PROP-106l: a reconciliation-lookup-itself-throws attempt fails cleanly and is safely retriable; a
// LATER attempt with a working lookup resolves the SAME row exactly once (never re-invoked once solved).
// ---------------------------------------------------------------------------
await scenario("PROP-106l: reconciliation-lookup-throws attempt fails cleanly (zero mutation, lock released) and is safely retried -- a later attempt resolves the SAME row exactly once", async () => {
  const dir = tmpDir();
  const staleRow = {
    loan_id: `loan_${LENDER}_1`, lender_id: LENDER, borrower_id: "priorBorrower",
    status: "provisioning", principal_usd: 0.02, total_due_usd: 0.022, provisioned_ms: NOW_MS - 60000,
  };
  seedLedger(dir, [staleRow]);

  const throwingDeps = happyDeps(dir, undefined, { reconcile: async () => { throw new Error("RPC timeout"); } });
  const result1 = await executeLoanIssuanceAttempt(baseParams(), throwingDeps);
  assert.equal(result1.status, "refused");
  const rowsAfter1 = readLoanRows(ledgerFileFor(dir));
  assert.deepEqual(rowsAfter1, [staleRow], "a reconciliation-lookup failure must leave the ledger EXACTLY as found -- zero sequence consumed, zero row appended");
  assert.equal(fs.existsSync(lockFileFor(dir, `loan_${LENDER}`)), false, "lock must be released normally after a clean reconciliation-lookup failure");

  let reconcileCallCount = 0;
  const workingDeps = happyDeps(dir, undefined, {
    reconcile: async () => { reconcileCallCount += 1; return { found: true, txHash: "0xretrysucceedsfixture00000000000000000000000000000000001" }; },
  });
  const result2 = await executeLoanIssuanceAttempt(baseParams(), workingDeps);
  assert.equal(result2.status, "active");
  assert.equal(reconcileCallCount, 1);
  assert.equal(result2.loanId, `loan_${LENDER}_2`);

  // a THIRD attempt must NOT re-invoke reconcile at all -- the n=1 row is already terminal ("active").
  let thirdReconcileCalled = false;
  const thirdDeps = happyDeps(dir, { [LENDER]: baseCitizen(LENDER, { balanceUsd: 10 }), B3: baseCitizen("B3", { balanceUsd: 0.1 }) }, {
    reconcile: async () => { thirdReconcileCalled = true; return { found: true, txHash: "0xshouldneverberead" }; },
  });
  const result3 = await executeLoanIssuanceAttempt(baseParams({ borrowerId: "B3" }), thirdDeps);
  assert.equal(result3.status, "active");
  assert.equal(thirdReconcileCalled, false, "once n=1 is resolved to a terminal state, reconcile must never be invoked for it again");
});

// ---------------------------------------------------------------------------
// PROP-106n: two DIFFERENT lenders concurrently target the SAME borrower -- exactly one succeeds; the
// other, on its own fresh lock-protected recheck, observes the borrower now has an outstanding loan.
// ---------------------------------------------------------------------------
await scenario("PROP-106n: two different lenders racing to lend to the SAME borrower -- the second is locked out WHILE the first is mid-flight, then refused outstanding_loan once it can acquire the shared borrower lock after the first completes", async () => {
  const dir = tmpDir();
  const citizens = {
    LenderC: baseCitizen("LenderC", { balanceUsd: 10 }),
    LenderD: baseCitizen("LenderD", { balanceUsd: 10 }),
    SharedBorrower: baseCitizen("SharedBorrower", { balanceUsd: 0.1 }),
  };
  // mirrors lending-orchestrator.test.mjs's own PROP-115d staggered-race technique: hold LenderC's own
  // critical section open at step 9 (disburse) via a controllable promise, so LenderD's own attempt
  // during that window is provably locked out via the SHARED loan_borrower_SharedBorrower key -- a
  // naive Promise.all race is timing-dependent and does not reliably exercise the "acquires the lock
  // AFTER the first releases it, then observes outstanding_loan on its OWN fresh recheck" path this
  // obligation specifically requires.
  let releaseDisburse;
  const disburseDelay = new Promise((resolve) => { releaseDisburse = resolve; });
  let signalDisburseReached;
  const disburseReached = new Promise((resolve) => { signalDisburseReached = resolve; });
  const depsC = happyDeps(dir, citizens, {
    disburse: async ({ loanRow }) => {
      signalDisburseReached();
      await disburseDelay;
      return { ok: true, tx: "0xprop106ntxfixture000000000000000000000000000000000000001", to: loanRow.borrower_wallet, amountBase: 20000 };
    },
  });
  const attemptC = executeLoanIssuanceAttempt({ lenderId: "LenderC", borrowerId: "SharedBorrower", nowMs: NOW_MS }, depsC);
  await disburseReached;

  const depsD = happyDeps(dir, citizens);
  const staggeredD = await executeLoanIssuanceAttempt({ lenderId: "LenderD", borrowerId: "SharedBorrower", nowMs: NOW_MS }, depsD);
  assert.equal(staggeredD.status, "refused");
  assert.equal(staggeredD.reason, "lock_held", "while LenderC still holds the shared loan_borrower_SharedBorrower lock, LenderD must be locked out immediately, never allowed to race ahead");

  releaseDisburse();
  const resultC = await attemptC;
  assert.equal(resultC.status, "active", "LenderC's own attempt must complete successfully once its critical section runs uncontended");

  const depsD2 = happyDeps(dir, citizens);
  const resultD = await executeLoanIssuanceAttempt({ lenderId: "LenderD", borrowerId: "SharedBorrower", nowMs: NOW_MS }, depsD2);
  assert.equal(resultD.status, "refused");
  assert.equal(resultD.reason, "outstanding_loan", "LenderD, now able to acquire the shared borrower lock cleanly after LenderC's own release, must be refused by its OWN fresh recheck seeing SharedBorrower's new active loan");
  assert.equal(resultD.status !== "active", true);

  // last-write-wins per loan_id (this spec's own established reduction convention throughout) --
  // a single loan's own provisional ("provisioning") row and its own later follow-up ("active") row
  // share the SAME loan_id and must collapse to ONE effective row, never be double-counted.
  const rows = readLoanRows(ledgerFileFor(dir));
  const lastByLoanId = new Map();
  for (const row of rows) lastByLoanId.set(row.loan_id, row);
  const borrowerActiveRows = [...lastByLoanId.values()].filter((r) => r.borrower_id === "SharedBorrower" && (r.status === "active" || r.status === "provisioning"));
  assert.equal(borrowerActiveRows.length, 1, "the shared borrower must never carry two simultaneously active/provisioning LOANS from two different lenders");
});

// ---------------------------------------------------------------------------
// PROP-106o: issued_ms/due_ms are drawn from the RECLAIMING (later, T2) call's own nowMs, never the
// crashed attempt's own earlier provisioned_ms (T1).
// ---------------------------------------------------------------------------
await scenario("PROP-106o: a reconciled follow-up row's issued_ms/due_ms come from the LATER reclaiming call's own nowMs (T2), never the stale row's own earlier provisioned_ms (T1)", async () => {
  const dir = tmpDir();
  const T1 = NOW_MS - 3 * 86400000; // the crashed attempt's own, much earlier, provisioning time
  const T2 = NOW_MS; // the reclaiming call's own, later, nowMs
  const staleRow = {
    loan_id: `loan_${LENDER}_1`, lender_id: LENDER, borrower_id: "priorBorrower",
    status: "provisioning", principal_usd: 0.02, total_due_usd: 0.022, provisioned_ms: T1,
  };
  seedLedger(dir, [staleRow]);
  const deps = happyDeps(dir, undefined, {
    reconcile: async () => ({ found: true, txHash: "0xT1vsT2fixture00000000000000000000000000000000000000001" }),
  });
  const result = await executeLoanIssuanceAttempt(baseParams({ nowMs: T2 }), deps);
  assert.equal(result.status, "active");
  const rows = readLoanRows(ledgerFileFor(dir));
  const reconciledFollowUp = rows.find((r) => r.loan_id === staleRow.loan_id && r.status === "active");
  assert.ok(reconciledFollowUp);
  assert.equal(reconciledFollowUp.issued_ms, T2, "issued_ms must equal the reclaiming call's own T2, never the stale row's own T1 provisioned_ms");
  assert.notEqual(reconciledFollowUp.issued_ms, T1);
  assert.equal(reconciledFollowUp.due_ms, T2 + 14 * 86400000, "due_ms must be derived from T2, never T1");
});

// ---------------------------------------------------------------------------
// PROP-106p: both kill-switches are RE-EVALUATED a second time inside the lock-protected fresh-check --
// a request that is HEALTHY at the pre-lock check but whose underlying loanRows state changes before
// the fresh, lock-protected re-check is refused AT THE FRESH RE-CHECK, not merely at the initial check.
// The mutation is injected via the SAME kind of deps-seam hook (reconcile) PROP-115c step 6's own
// eligibility-TOCTOU test already uses for the analogous REQ-102 race -- deterministic, not timing-based.
// ---------------------------------------------------------------------------
await scenario("PROP-106p (cold-start switch): healthy at the pre-lock check, poisoned before the lock-protected fresh recheck -- refused AT the fresh recheck", async () => {
  const dir = tmpDir();
  const priorStaleRow = {
    loan_id: `loan_${LENDER}_1`, lender_id: LENDER, borrower_id: "unrelatedPriorBorrower",
    status: "provisioning", principal_usd: 0.02, total_due_usd: 0.022, provisioned_ms: NOW_MS - 60000,
  };
  seedLedger(dir, [priorStaleRow]);
  const deps = happyDeps(dir, undefined, {
    // fires during step 5 (inside the lock, AFTER step 3's pre-lock read already ran healthy) --
    // poisons the ledger with 10 cold-start defaults for THIS lender before step 6's fresh read.
    reconcile: async () => {
      for (const row of poisonColdStartRows(LENDER, 10, "toctouColdStartBorrower")) appendRawRow(ledgerFileFor(dir), row);
      return { found: false };
    },
  });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "refused");
  assert.equal(result.reason, "cold_start_paused", "the SECOND, lock-protected re-check must catch the kill-switch trip the pre-lock check could not have seen");
});

await scenario("PROP-106p (overall-default switch): healthy at the pre-lock check, poisoned with one large recent default before the lock-protected fresh recheck -- refused AT the fresh recheck", async () => {
  const dir = tmpDir();
  const priorStaleRow = {
    loan_id: `loan_${LENDER}_1`, lender_id: LENDER, borrower_id: "unrelatedPriorBorrower2",
    status: "provisioning", principal_usd: 0.02, total_due_usd: 0.022, provisioned_ms: NOW_MS - 60000,
  };
  seedLedger(dir, [priorStaleRow]);
  const deps = happyDeps(dir, undefined, {
    reconcile: async () => {
      appendRawRow(ledgerFileFor(dir), {
        loan_id: `loan_${LENDER}_bustout`, lender_id: LENDER, borrower_id: "toctouBustOutBorrower",
        status: "defaulted", principal_usd: 5.0, repaid_usd: 0, total_due_usd: 5.5,
        issued_ms: NOW_MS - 5 * 86400000, due_ms: NOW_MS - 1 * 86400000, defaulted_ms: NOW_MS - 1000,
      });
      return { found: false };
    },
  });
  const result = await executeLoanIssuanceAttempt(baseParams(), deps);
  assert.equal(result.status, "refused");
  assert.equal(result.reason, "overall_default_paused", "the SECOND, lock-protected re-check must catch the absolute-loss kill-switch trip the pre-lock check could not have seen");
});

// ---------------------------------------------------------------------------
// PROP-108c: a partial-then-full repayment, chained through TWO REAL SEQUENTIAL executeRepaymentClaim
// calls against the SAME evolving ledger row (not two independently-seeded fixtures).
// ---------------------------------------------------------------------------
await scenario("PROP-108c: a partial-then-full repayment, driven through two REAL sequential executeRepaymentClaim calls against the SAME loan, transitions active -> active -> repaid exactly once", async () => {
  const dir = tmpDir();
  const activeRow = {
    loan_id: `loan_${LENDER}_1`, lender_id: LENDER, borrower_id: BORROWER,
    lender_wallet: baseCitizen(LENDER).walletAddress.evm, borrower_wallet: baseCitizen(BORROWER).walletAddress.evm,
    status: "active", principal_usd: 0.02, total_due_usd: 0.022, repaid_usd: 0,
    issued_ms: NOW_MS - 5 * 86400000, due_ms: NOW_MS + 9 * 86400000,
  };
  seedLedger(dir, [activeRow]);
  const deps1 = { ledgerFile: ledgerFileFor(dir), lockStatePath: ledgerFileFor(dir), verify: async () => ({ credited: 0.01, rejected: false }) };
  const partial = await executeRepaymentClaim({ loanId: activeRow.loan_id, txHash: "0xchainedpartialfixture0000000000000000000000000000000001", nowMs: NOW_MS }, deps1);
  assert.equal(partial.status, "active", "the loan must remain active after the FIRST, partial transaction");
  assert.equal(partial.credited, 0.01);

  const deps2 = { ledgerFile: ledgerFileFor(dir), lockStatePath: ledgerFileFor(dir), verify: async () => ({ credited: 0.012, rejected: false }) };
  const full = await executeRepaymentClaim({ loanId: activeRow.loan_id, txHash: "0xchainedfullfixture000000000000000000000000000000000001", nowMs: NOW_MS }, deps2);
  assert.equal(full.status, "repaid", "the loan must transition to repaid exactly at the SECOND transaction, which reaches total_due_usd");

  const rows = readLoanRows(ledgerFileFor(dir)).filter((r) => r.loan_id === activeRow.loan_id);
  const statusSequence = rows.map((r) => r.status);
  assert.deepEqual(statusSequence, ["active", "active", "repaid"], "the row sequence must show exactly one transition point, at the second transaction");
  assert.equal(rows[rows.length - 1].repaid_usd, 0.022);
});

// ---------------------------------------------------------------------------
const failed = results.filter((r) => !r.ok);
console.log("\n=== VERDICT ===");
console.log(JSON.stringify({ total: results.length, passed: results.length - failed.length, failed: failed.length, failedNames: failed.map((f) => f.name) }, null, 2));
if (failed.length > 0) {
  process.exitCode = 1;
}
