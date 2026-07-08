// node:test — economy/lending scripts/wake-gate.mjs (Phase 2a RED, anicca-agent-lending sprint-3,
// REQ-117). RED phase: this file is written BEFORE ../../scripts/wake-gate.mjs exists, so the import
// below is the first failing assertion (module not found) — mirrors sprint-2's own RED-phase precedent
// (lending-orchestrator.test.mjs, written before ../lending-orchestrator.mjs existed) and
// self/spawn/lib/__tests__/wake-gate.test.mjs's own real `runWakeGate({argv, env, deps})`
// test-injection convention (REQ-117's Test-injection seam clause, resolves FIND-1002).
//
// `deps` seam this file exercises (per REQ-117's own canonical order, behavioral-spec.md REQ-117):
//   citizensRegistryFile / ensureCitizensRegistry -- citizens.json path/bootstrap override (step 1)
//   ledgerFile                                    -- loans.jsonl path override, threaded through into
//                                                     BOTH step 2's own read AND the REAL, unmodified
//                                                     executeLoanIssuanceAttempt/executeDefaultDetectionSweep's
//                                                     own internal ledgerFile/lockStatePath (steps 6-9) --
//                                                     never a second, parallel ledger, and never the
//                                                     REAL production LOANS_LEDGER_PATH from a test.
//   gojoLogFile                                   -- gojo-log.jsonl path override (step 3)
//   fetchImpl                                     -- threaded into every usdcBalance() call (step 4 AND
//                                                     step 6's own fresh getCitizen re-fetch) -- zero
//                                                     live RPC calls anywhere in this file.
//   getCitizen                                    -- a direct override of the whole citizen-lookup
//                                                     closure wake-gate.mjs would otherwise build
//                                                     internally (used by exactly one test below, to
//                                                     prove the WIRING into executeLoanIssuanceAttempt
//                                                     is correct independently of closure construction).
//   disburse                                      -- forwarded through into executeLoanIssuanceAttempt's
//                                                     own deps (REQ-115, already converged sprint-2, DO
//                                                     NOT MODIFY) so a real {status:"active"} outcome is
//                                                     reachable with zero live network calls -- mirrors
//                                                     lending-orchestrator.test.mjs's own happyDeps()
//                                                     convention (deps.disburse stub, never a real
//                                                     payViaFacilitator/facilitator HTTP call).
//
// executeLoanIssuanceAttempt/executeDefaultDetectionSweep themselves are NEVER stubbed here -- they are
// the REAL, unmodified sprint-2 functions (lending-orchestrator.mjs), invoked by the REAL wake-gate.mjs
// via a REAL 2-argument call. This file tests wake-gate.mjs's own wiring INTO them, never their own
// internal logic (already fully tested by lending-orchestrator.test.mjs, which this file does not
// duplicate).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { runWakeGate } from "../../scripts/wake-gate.mjs";

const NOW_MS = 1_800_000_000_000;

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "anicca-lending-wake-gate-"));
}

function seedCitizens(dir, citizens) {
  const registryPath = path.join(dir, "citizens.json");
  fs.writeFileSync(registryPath, JSON.stringify(citizens, null, 2));
  return registryPath;
}

function readLedgerRows(file) {
  if (!fs.existsSync(file)) return [];
  return fs
    .readFileSync(file, "utf8")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => JSON.parse(l));
}

// A realistic, FULLY-populated citizen registry record -- id/wallet.evm/walletAddress.evm/fuel.provider/
// humanDependencies/coLocatedWithCoordinator -- mirrors the REAL shape
// self/spawn/registry/citizens.seed.json already establishes, never a hand-enumerated subset (that
// exact shortcut is FIND-1004/FIND-1006's own root cause, corrected 2026-07-08 iteration-4/5 of this
// sprint's own spec review).
function fullCitizen(id, walletAddr, overrides = {}) {
  return {
    id,
    wallet: { evm: true },
    walletAddress: { evm: walletAddr },
    fuel: { provider: "clawrouter-own-wallet" },
    humanDependencies: [],
    coLocatedWithCoordinator: true,
    ...overrides,
  };
}

// Stubs usdcBalance's own eth_call transport (_shared/lib/usdc.mjs) -- keyed by the lowercase wallet
// address encoded in the last 40 hex chars of the eth_call `data` payload (balanceOf(address) selector
// + 32-byte-padded address). Zero live RPC calls anywhere in this file (PROP-117c, resolves FIND-1002).
function fetchImplForBalances(balancesByAddress) {
  const byAddr = new Map(Object.entries(balancesByAddress).map(([k, v]) => [k.toLowerCase(), v]));
  return async (_rpcUrl, opts) => {
    const body = JSON.parse(opts.body);
    const data = body.params[0].data;
    const addr = ("0x" + data.slice(-40)).toLowerCase();
    const usd = byAddr.has(addr) ? byAddr.get(addr) : 0;
    const base = BigInt(Math.round(usd * 1e6));
    return { ok: true, json: async () => ({ result: "0x" + base.toString(16) }) };
  };
}

function baseDeps(dir, overrides = {}) {
  return {
    citizensRegistryFile: path.join(dir, "citizens.json"),
    ensureCitizensRegistry: async () => ({ created: false }), // citizens.json already seeded by the test
    ledgerFile: path.join(dir, "loans.jsonl"),
    gojoLogFile: path.join(dir, "gojo-log.jsonl"),
    fetchImpl: fetchImplForBalances({}),
    nowMs: NOW_MS,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// PROP-117c fixture 1 / Edge Case "zero self-funded, EVM-walleted, co-located citizens": the
// wallet.evm-exclusion path, isolated from the single-citizen impossibility -- TWO citizens are
// present here (both Solana-only), so scarcity of citizens is never the reason this fixture produces
// zero pairs.
// ---------------------------------------------------------------------------

test("PROP-117c fixture 1: a registry where every self-funded citizen fails wallet.evm===true produces zero candidate pairs, never invokes executeLoanIssuanceAttempt, still runs executeDefaultDetectionSweep exactly once, and is a clean no-op", async () => {
  const dir = tmpDir();
  seedCitizens(dir, [
    {
      id: "solana-only-1",
      wallet: { solana: true },
      walletAddress: { solana: "Sol1111111111111111111111111111111111111" },
      fuel: { provider: "x402" },
      humanDependencies: [],
      coLocatedWithCoordinator: true,
    },
    {
      id: "solana-only-2",
      wallet: { solana: true },
      walletAddress: { solana: "Sol2222222222222222222222222222222222222" },
      fuel: { provider: "x402" },
      humanDependencies: [],
      coLocatedWithCoordinator: true,
    },
  ]);
  const deps = baseDeps(dir);

  const result = await runWakeGate({ argv: [], env: {}, deps });

  assert.equal(result.selectedPair, null, "no wallet.evm===true citizen exists -- zero candidate pairs");
  assert.equal(result.issuance, null, "executeLoanIssuanceAttempt must never be invoked this wake");
  assert.equal(result.candidatesConsidered, 0);
  assert.deepEqual(result.sweep, { defaulted: [] }, "executeDefaultDetectionSweep must still run exactly once, unconditionally, even for a zero-candidate wake");
  assert.equal(readLedgerRows(deps.ledgerFile).length, 0, "zero loans.jsonl rows appended for a clean no-op wake");
});

// ---------------------------------------------------------------------------
// PROP-117c fixture 2 / Edge Case "today's real, currently-permanent state": the single-citizen
// lenderId!==borrowerId impossibility path, isolated from the wallet.evm-exclusion path -- this
// citizen itself genuinely passes wallet.evm===true; it is excluded ONLY because no second citizen
// exists to pair with.
// ---------------------------------------------------------------------------

test("PROP-117c fixture 2: a registry with exactly ONE self-funded, EVM-walleted, co-located citizen produces zero candidate pairs via the lenderId!==borrowerId impossibility (never the wallet.evm-exclusion path), still runs executeDefaultDetectionSweep exactly once", async () => {
  const dir = tmpDir();
  const WALLET = "0x1111111111111111111111111111111111111111";
  seedCitizens(dir, [fullCitizen("only-citizen", WALLET)]);
  const deps = baseDeps(dir, { fetchImpl: fetchImplForBalances({ [WALLET]: 100 }) });

  const result = await runWakeGate({ argv: [], env: {}, deps });

  assert.equal(result.selectedPair, null, "only one citizen exists -- lenderId!==borrowerId can never hold, regardless of this citizen's own wallet/balance shape");
  assert.equal(result.issuance, null);
  assert.deepEqual(result.sweep, { defaulted: [] });
  assert.equal(readLedgerRows(deps.ledgerFile).length, 0);
});

// ---------------------------------------------------------------------------
// PROP-117c fixture 3, resolves FIND-1003/FIND-1004/FIND-1006 (critical): a real two-citizen wake (one
// broke, one with surplus) selects the correct pair and drives the REAL, unmodified
// executeLoanIssuanceAttempt to a genuine {status:"active"} outcome -- "refused" is NOT acceptable for
// this fixture (both citizens are constructed to be otherwise fully qualifying; a "refused" result here
// IS the exact silent-failure symptom a getCitizen closure omitting balanceUsd, or a hand-enumerated
// shape omitting fuel/humanDependencies, produces). Proves wake-gate.mjs's own INTERNAL getCitizen
// closure (built from citizensRegistryFile + fetchImpl, NOT a test override) genuinely returns
// {...registryCitizen, balanceUsd}.
// ---------------------------------------------------------------------------

test('PROP-117c fixture 3 (resolves FIND-1003/1004/1006): a real two-citizen wake selects the correct pair and executeLoanIssuanceAttempt genuinely returns {status:"active"}, never "refused"', async () => {
  const dir = tmpDir();
  const LENDER_WALLET = "0x1111111111111111111111111111111111111111";
  const BORROWER_WALLET = "0x2222222222222222222222222222222222222222";
  seedCitizens(dir, [fullCitizen("citizen-lender", LENDER_WALLET), fullCitizen("citizen-borrower", BORROWER_WALLET)]);
  const deps = baseDeps(dir, {
    fetchImpl: fetchImplForBalances({ [LENDER_WALLET]: 10, [BORROWER_WALLET]: 0.1 }),
    // executeLoanIssuanceAttempt's OWN disbursement seam (REQ-115, already converged sprint-2) --
    // forwarded through wake-gate.mjs's own deps exactly as lending-orchestrator.test.mjs's own
    // happyDeps() stubs it -- never a real payViaFacilitator/facilitator HTTP call.
    disburse: async ({ loanRow }) => ({
      ok: true,
      tx: "0xwakegatefixturetx000000000000000000000000000000000000000001",
      to: loanRow.borrower_wallet,
      amountBase: Math.round(loanRow.principal_usd * 1e6),
    }),
  });

  const result = await runWakeGate({ argv: [], env: {}, deps });

  assert.deepEqual(result.selectedPair, { lenderId: "citizen-lender", borrowerId: "citizen-borrower" });
  assert.ok(result.issuance, "executeLoanIssuanceAttempt must have been invoked");
  assert.equal(
    result.issuance.status,
    "active",
    'a "refused" outcome here is the exact FIND-1004/1006 silent-refusal symptom -- both citizens are constructed to be otherwise fully qualifying'
  );
  assert.deepEqual(result.sweep, { defaulted: [] });
  const rows = readLedgerRows(deps.ledgerFile);
  assert.equal(rows.filter((r) => r.status === "active").length, 1, "exactly one active loan row landed");
});

// ---------------------------------------------------------------------------
// Direct deps.getCitizen override -- a SEPARATE concern from fixture 3 above: proves wake-gate.mjs's own
// WIRING into executeLoanIssuanceAttempt is correct independently of its own internal
// closure-construction logic. Whatever a fully-populated getCitizen override returns (the full record
// spread, plus a fresh balanceUsd merged on top) must reach a genuine, non-silently-refused outcome.
// ---------------------------------------------------------------------------

test("a fully-populated deps.getCitizen override ({...registryCitizen, balanceUsd}) is threaded through to a genuine, non-refused executeLoanIssuanceAttempt outcome", async () => {
  const dir = tmpDir();
  seedCitizens(dir, [
    fullCitizen("citizen-lender", "0x1111111111111111111111111111111111111111"),
    fullCitizen("citizen-borrower", "0x2222222222222222222222222222222222222222"),
  ]);
  const citizens = {
    "citizen-lender": { ...fullCitizen("citizen-lender", "0x1111111111111111111111111111111111111111"), balanceUsd: 10 },
    "citizen-borrower": { ...fullCitizen("citizen-borrower", "0x2222222222222222222222222222222222222222"), balanceUsd: 0.1 },
  };
  const deps = baseDeps(dir, {
    getCitizen: async (id) => citizens[id] || null,
    disburse: async ({ loanRow }) => ({
      ok: true,
      tx: "0xoverridefixturetx00000000000000000000000000000000000000001",
      to: loanRow.borrower_wallet,
      amountBase: Math.round(loanRow.principal_usd * 1e6),
    }),
  });

  const result = await runWakeGate({ argv: [], env: {}, deps });

  assert.equal(result.issuance.status, "active", "a getCitizen override wiring must reach a genuine outcome, never a silent missing-field refusal");
});

// ---------------------------------------------------------------------------
// Corrected (Phase 1c iteration-2, FIND-1003): executeLoanIssuanceAttempt's real, already-converged
// (sprint-2) signature is (params, deps={}) -- a SECOND argument -- and deps.getCitizen has NO
// production default anywhere. A naive single-argument call crashes on EVERY real wake where a
// candidate pair is found. This test asserts the real 2-argument call never throws that TypeError, and
// that the call is genuinely reached (a loans.jsonl row lands), not silently skipped.
// ---------------------------------------------------------------------------

test("REQ-117 step 6: executeLoanIssuanceAttempt is invoked with the real 2-argument ({lenderId, borrowerId, nowMs}, deps) shape -- never throws TypeError: getCitizen is not a function", async () => {
  const dir = tmpDir();
  const LENDER_WALLET = "0x3333333333333333333333333333333333333333";
  const BORROWER_WALLET = "0x4444444444444444444444444444444444444444";
  seedCitizens(dir, [fullCitizen("citizen-lender", LENDER_WALLET), fullCitizen("citizen-borrower", BORROWER_WALLET)]);
  const deps = baseDeps(dir, {
    fetchImpl: fetchImplForBalances({ [LENDER_WALLET]: 10, [BORROWER_WALLET]: 0.1 }),
    disburse: async ({ loanRow }) => ({
      ok: true,
      tx: "0xtypeerrorguardtx0000000000000000000000000000000000000001",
      to: loanRow.borrower_wallet,
      amountBase: Math.round(loanRow.principal_usd * 1e6),
    }),
  });

  await assert.doesNotReject(runWakeGate({ argv: [], env: {}, deps }));
  assert.equal(readLedgerRows(deps.ledgerFile).some((r) => r.status === "active"), true, "the real executeLoanIssuanceAttempt call was genuinely reached, not skipped");
});
