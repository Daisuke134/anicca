// VCSDD spawn-funding-swap Phase 2a (RED). Driver-level precondition/zero-call tests — REQ-001 (PROP-002),
// REQ-002 (PROP-004), REQ-009 (PROP-015/PROP-016), REQ-010 (lock-held zero-call), REQ-011 (bad-price
// zero-call). Written against lib/driver.mjs's `runSwap(deps)` contract, which does NOT exist yet —
// every test below MUST fail at module-load time (MODULE_NOT_FOUND) until Phase 2b.
//
// runSwap(deps) contract (defined here, Phase 2a, as the driver's required public API):
//   deps = { chainReader, priceOracle, skipApiClient, baseSigner, relayPoller, ledgerStore,
//            akashKeyName, expectedBaseSignerAddress, sourceBaseAddress, destinationAkashAddress,
//            thresholdAkt, legTimeoutMs?, pure? (per-function override hooks for driver-level spying),
//            now? }
//   returns Promise<{ ok: boolean, status: string, ...detail }>
import { test } from "node:test";
import assert from "node:assert/strict";
import { runSwap } from "../driver.mjs";
import {
  createFakeChainReader,
  createFakePriceOracle,
  createFakeSkipApiClient,
  createFakeBaseSigner,
  createFakeRelayPoller,
  createFakeLedgerStore,
  validRouteFixture,
} from "./fakes/fake-clients.mjs";

const DESTINATION = "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523";
const SOURCE_BASE_ADDRESS = "0xFAKE_SOURCE_BASE_WALLET";
const EXPECTED_BASE_SIGNER_ADDRESS = "0xFAKE_EXPECTED_SIGNER";

function baseDeps(overrides = {}) {
  return {
    chainReader: createFakeChainReader({ akashBalanceUakt: 0n }),
    priceOracle: createFakePriceOracle({ aktUsdPrice: 1.0 }),
    skipApiClient: createFakeSkipApiClient({ routeResponse: validRouteFixture() }),
    baseSigner: createFakeBaseSigner({ address: EXPECTED_BASE_SIGNER_ADDRESS }),
    relayPoller: createFakeRelayPoller({ statusesByChain: { 8453: "confirmed", "akashnet-2": "confirmed" } }),
    ledgerStore: createFakeLedgerStore(),
    akashKeyName: "anicca-akash",
    expectedBaseSignerAddress: EXPECTED_BASE_SIGNER_ADDRESS,
    sourceBaseAddress: SOURCE_BASE_ADDRESS,
    destinationAkashAddress: DESTINATION,
    thresholdAkt: 26,
    legTimeoutMs: 5_000,
    ...overrides,
  };
}

// PROP-002
test("PROP-002: WHEN current >= threshold (need === 0) THE SYSTEM calls zero Skip/sign/broadcast functions and exits ok:true", async () => {
  const deps = baseDeps({
    chainReader: createFakeChainReader({ akashBalanceUakt: 30_000_000n }), // 30 AKT >= 26 AKT threshold
    thresholdAkt: 26,
  });
  const result = await runSwap(deps);
  assert.equal(result.ok, true);
  assert.equal(deps.skipApiClient.getRoute.calls.length, 0);
  assert.equal(deps.baseSigner.signAndBroadcast.calls.length, 0);
  assert.equal(deps.priceOracle.getAktUsdPrice.calls.length, 0, "no price lookup needed when need === 0 (REQ-011 short-circuit)");
});

test("PROP-002: need === 0 EXACTLY at the boundary (current === threshold) also calls zero Skip/sign functions", async () => {
  const deps = baseDeps({ chainReader: createFakeChainReader({ akashBalanceUakt: 26_000_000n }), thresholdAkt: 26 });
  const result = await runSwap(deps);
  assert.equal(result.ok, true);
  assert.equal(deps.skipApiClient.getRoute.calls.length, 0);
  assert.equal(deps.baseSigner.signAndBroadcast.calls.length, 0);
});

// PROP-004
test("PROP-004: no signing code path is reachable unless validateRoute returned true for the specific route object in hand — an invalid route yields zero broadcast calls", async () => {
  const invalidRoute = { dest_asset_denom: "uosmo" }; // wrong denom -> validateRoute fails
  const deps = baseDeps({
    chainReader: createFakeChainReader({ akashBalanceUakt: 0n, baseUsdcBalance: 1_000_000_000n, baseGasBalance: 10_000_000_000_000_000n }),
    skipApiClient: createFakeSkipApiClient({ routeResponse: invalidRoute }),
  });
  const result = await runSwap(deps);
  assert.equal(result.ok, false);
  assert.equal(deps.baseSigner.signAndBroadcast.calls.length, 0);
});

// PROP-015
test("PROP-015: Base signer resolving to an unexpected/unpinned address -> non-zero exit, zero broadcast calls", async () => {
  const deps = baseDeps({ baseSigner: createFakeBaseSigner({ address: "0xSOME_OTHER_ADDRESS_NOT_PINNED" }) });
  const result = await runSwap(deps);
  assert.equal(result.ok, false);
  assert.equal(deps.baseSigner.signAndBroadcast.calls.length, 0);
});

// PROP-016
test("PROP-016: AKASH_KEY_NAME unset -> non-zero exit, zero broadcast calls (mirrors akt-treasury.sh's existing bash guard)", async () => {
  const deps = baseDeps({ akashKeyName: undefined });
  const result = await runSwap(deps);
  assert.equal(result.ok, false);
  assert.equal(deps.baseSigner.signAndBroadcast.calls.length, 0);
});

test("PROP-016: AKASH_KEY_NAME set to a non-'anicca-akash' value -> non-zero exit, zero broadcast calls", async () => {
  const deps = baseDeps({ akashKeyName: "some-other-instances-key" });
  const result = await runSwap(deps);
  assert.equal(result.ok, false);
  assert.equal(deps.baseSigner.signAndBroadcast.calls.length, 0);
});

// REQ-010 — canonical lock precondition
test("REQ-010: WHEN the canonical destination-scoped lock is already held, SkipApiClient.getRoute() and PriceOracle.getAktUsdPrice() are called ZERO times", async () => {
  const lockedLedgerStore = createFakeLedgerStore();
  // Pre-occupy the lock by starting (but not finishing) a withLock call.
  let releaseFirst;
  const heldPromise = new Promise((resolve) => {
    releaseFirst = resolve;
  });
  const firstCall = lockedLedgerStore.withLock(DESTINATION, async () => {
    await heldPromise;
    return {};
  });
  const deps = baseDeps({
    chainReader: createFakeChainReader({ akashBalanceUakt: 0n }),
    ledgerStore: lockedLedgerStore,
  });
  const result = await runSwap(deps);
  assert.equal(result.ok, false);
  assert.equal(deps.skipApiClient.getRoute.calls.length, 0);
  assert.equal(deps.priceOracle.getAktUsdPrice.calls.length, 0);
  releaseFirst();
  await firstCall;
});

// REQ-011 — bad-price precondition
test("REQ-011: WHEN PriceOracle.getAktUsdPrice() rejects, THE SYSTEM calls zero Skip/sign/broadcast functions and fails closed", async () => {
  const deps = baseDeps({
    chainReader: createFakeChainReader({ akashBalanceUakt: 0n }),
    priceOracle: createFakePriceOracle({ shouldReject: true }),
  });
  const result = await runSwap(deps);
  assert.equal(result.ok, false);
  assert.equal(deps.skipApiClient.getRoute.calls.length, 0);
  assert.equal(deps.baseSigner.signAndBroadcast.calls.length, 0);
});

test("REQ-011: WHEN PriceOracle.getAktUsdPrice() returns an invalid price (0, negative, NaN, Infinity), THE SYSTEM fails closed with zero Skip/sign calls", async () => {
  for (const badPrice of [0, -1, NaN, Infinity]) {
    const deps = baseDeps({
      chainReader: createFakeChainReader({ akashBalanceUakt: 0n }),
      priceOracle: createFakePriceOracle({ aktUsdPrice: badPrice }),
    });
    const result = await runSwap(deps);
    assert.equal(result.ok, false, `expected fail-closed for price=${badPrice}`);
    assert.equal(deps.skipApiClient.getRoute.calls.length, 0, `expected zero Skip calls for price=${badPrice}`);
    assert.equal(deps.baseSigner.signAndBroadcast.calls.length, 0, `expected zero broadcast calls for price=${badPrice}`);
  }
});
