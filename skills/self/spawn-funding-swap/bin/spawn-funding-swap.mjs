#!/usr/bin/env node
// spawn-funding-swap CLI entrypoint — REQ-008/PROP-014. Wired to be callable as TREASURY_SWAP_CMD from
// skills/self/spawn/scripts/akt-treasury.sh:52 (`bash -c "$TREASURY_SWAP_CMD"`). Exits 0 ONLY on
// confirmed REQ-007 success ("settled"); non-zero on every other outcome. Depends on nothing beyond
// akt-treasury.sh's own exported vars (AKASH_KEY_NAME, AKASH_KEYRING_BACKEND, AKASH_NODE,
// AKASH_CHAIN_ID) plus this command's own self-contained config -- no cwd/shell-state dependency
// (REQ-008 edge case).
//
// Test-only seam (Phase 2a-defined, binding, driver-preconditions/cli.test.mjs's own contract): when
// SPAWN_FUNDING_SWAP_FAKE_DEPS_MODULE is set, dynamically import that module's createDeps() export
// INSTEAD OF wiring real clients. Production NEVER sets this env var. This module is NOT itself a test
// file (PROP-021's static scan only covers files under this feature's test directories) so it MAY
// import real client implementations for its production code path.
//
// REQ-009 / FIND-002 fix (contract-review, money-path identity isolation): expectedBaseSignerAddress,
// sourceBaseAddress, and akashKeyName are IDENTITY-determining values on a shared multi-instance Mac --
// they are now resolved EXCLUSIVELY via resolve-swap-identity.mjs's ANICCA_HOME-gated mechanism
// (which itself reuses skills/earn/lib/resolve-identity.mjs's own canonical resolver). There is no
// longer any code path that reads SPAWN_FUNDING_SWAP_EXPECTED_BASE_SIGNER_ADDRESS or
// SPAWN_FUNDING_SWAP_SOURCE_BASE_ADDRESS from a generic shared env var -- see resolve-swap-identity.mjs
// for the full leak-mode rationale and lib/__tests__/resolve-swap-identity.test.mjs for the proof.
import { runSwap } from "../lib/driver.mjs";
import { resolveOwnBaseIdentity } from "../lib/resolve-swap-identity.mjs";
import { resolveSwapStateDir } from "../lib/resolve-swap-state-dir.mjs";

// DESTINATION_AKASH_ADDRESS -- REQ-009/FIND-002 decision: this is the single colony-wide "anicca-akash"
// keyring's OWN address (verified against the identical `akash keys show anicca-akash -a` fixture
// literal in skills/self/spawn/scripts/test-akt-treasury.sh and test-deploy-akash.sh). It is a
// receive-side destination, not a per-instance signer identity, but it is still money-critical (a
// redirect target) -- mirroring driver.mjs's own documented design for SWAP_MAX_USD/MIN_GAS_WEI/
// TOLERANCE_BPS ("fixed literals ... never read from process.env/CLI/genome/config"), it is now a
// single sourced constant, never overridable via env. No test (production or fixture) ever set the
// removed SPAWN_FUNDING_SWAP_DESTINATION_AKASH_ADDRESS override, so this closes a fund-redirect vector
// with zero behavior change for any existing caller.
const DESTINATION_AKASH_ADDRESS = "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523";

const THRESHOLD_AKT = Number(process.env.SPAWN_FUNDING_SWAP_THRESHOLD_AKT || "26");
const LEG_TIMEOUT_MS = Number(process.env.SPAWN_FUNDING_SWAP_LEG_TIMEOUT_MS || "600000"); // NFR-4: <=10min default
// REQ-008/FIND-002 fix (Phase-3 impl review): previously undefaulted, so an unset env var meant
// `createLedgerStore({stateDir: undefined})` threw a raw path.join(undefined,...) TypeError once identity
// resolved (see resolve-swap-state-dir.mjs for the full defect + fix rationale). Now always a concrete
// string (or an explicit, early thrown error from resolveStateDir()'s own /tmp-guard) -- never undefined.
const STATE_DIR = resolveSwapStateDir({ env: process.env });

async function buildDeps() {
  const fakeDepsModule = process.env.SPAWN_FUNDING_SWAP_FAKE_DEPS_MODULE;
  if (fakeDepsModule) {
    const mod = await import(fakeDepsModule);
    return mod.createDeps();
  }

  // REQ-009: identity/key safety -- fail closed BEFORE any lock/price/route/sign activity, and before
  // any real client module is even imported (never a partial/late-catching failure).
  const identity = resolveOwnBaseIdentity({ env: process.env });
  if (!identity.ok) {
    throw new Error(`spawn-funding-swap: identity resolution failed -- ${identity.reason}`);
  }

  // Production wiring -- real clients, only ever instantiated here (never in a test file, PROP-021).
  const { createLedgerStore } = await import("../lib/ledger-store.mjs");
  const { createRealChainReader } = await import("../lib/real-clients/chain-reader.mjs");
  const { createRealPriceOracle } = await import("../lib/real-clients/price-oracle.mjs");
  const { createRealSkipApiClient } = await import("../lib/real-clients/skip-api-client.mjs");
  const { createRealBaseSigner } = await import("../lib/real-clients/base-signer.mjs");
  const { createRealRelayPoller } = await import("../lib/real-clients/relay-poller.mjs");

  return {
    chainReader: createRealChainReader(),
    priceOracle: createRealPriceOracle(),
    skipApiClient: createRealSkipApiClient(),
    baseSigner: createRealBaseSigner(),
    relayPoller: createRealRelayPoller(),
    ledgerStore: createLedgerStore({ stateDir: STATE_DIR }),
    akashKeyName: identity.akashKeyName,
    expectedBaseSignerAddress: identity.baseAddress,
    sourceBaseAddress: identity.baseAddress,
    destinationAkashAddress: DESTINATION_AKASH_ADDRESS,
    thresholdAkt: THRESHOLD_AKT,
    legTimeoutMs: LEG_TIMEOUT_MS,
  };
}

async function main() {
  const deps = await buildDeps();
  const result = await runSwap(deps);
  if (result.ok) {
    console.log(`spawn-funding-swap: ${result.status}`);
    process.exit(0);
  }
  console.error(`spawn-funding-swap: FAILED (${result.status})${result.reason ? ` -- ${result.reason}` : ""}`);
  process.exit(1);
}

main().catch((err) => {
  console.error(`spawn-funding-swap: uncaught error -- ${err && err.stack ? err.stack : err}`);
  process.exit(1);
});
