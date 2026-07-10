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
import { runSwap } from "../lib/driver.mjs";

const AKASH_KEY_NAME = process.env.AKASH_KEY_NAME;
const EXPECTED_BASE_SIGNER_ADDRESS = process.env.SPAWN_FUNDING_SWAP_EXPECTED_BASE_SIGNER_ADDRESS;
const SOURCE_BASE_ADDRESS = process.env.SPAWN_FUNDING_SWAP_SOURCE_BASE_ADDRESS;
const DESTINATION_AKASH_ADDRESS = process.env.SPAWN_FUNDING_SWAP_DESTINATION_AKASH_ADDRESS || "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523";
const THRESHOLD_AKT = Number(process.env.SPAWN_FUNDING_SWAP_THRESHOLD_AKT || "26");
const LEG_TIMEOUT_MS = Number(process.env.SPAWN_FUNDING_SWAP_LEG_TIMEOUT_MS || "600000"); // NFR-4: <=10min default
const STATE_DIR = process.env.SPAWN_FUNDING_SWAP_STATE_DIR;

async function buildDeps() {
  const fakeDepsModule = process.env.SPAWN_FUNDING_SWAP_FAKE_DEPS_MODULE;
  if (fakeDepsModule) {
    const mod = await import(fakeDepsModule);
    return mod.createDeps();
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
    akashKeyName: AKASH_KEY_NAME,
    expectedBaseSignerAddress: EXPECTED_BASE_SIGNER_ADDRESS,
    sourceBaseAddress: SOURCE_BASE_ADDRESS,
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
