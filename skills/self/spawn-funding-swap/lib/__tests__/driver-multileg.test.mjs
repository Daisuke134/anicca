// VCSDD spawn-funding-swap Phase 2a (RED). REQ-004 — multi-tx route execution with per-leg on-chain
// verification (PROP-008: simulated Leg-2 stall past timeout). Written against lib/driver.mjs's
// `runSwap(deps)` — see driver-preconditions.test.mjs for the full contract comment — which does NOT
// exist yet. Every test below MUST fail at module-load time (MODULE_NOT_FOUND) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import { runSwap } from "../driver.mjs";
import { toBaseUnits, capUsd, usdEquivalentOf } from "../pure/base-units.mjs";
import { USDC_DECIMALS_BASE, MIN_GAS_WEI, SWAP_MAX_USD } from "../pure/constants.mjs";
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

function lastWrittenLedgerState(ledgerStore) {
  const calls = ledgerStore.writeState.calls;
  assert.ok(calls.length > 0, "expected at least one ledger write");
  return calls[calls.length - 1][1];
}

test("PROP-008: Leg-1 (Base swap/bridge-out tx) confirms, Leg-2 (IBC relay to akashnet-2) stalls past its timeout -> non-zero exit; ledger shows Leg-1 confirmed, Leg-2 pending (not failed/absent)", async () => {
  const thresholdAkt = 26;
  const aktUsdPrice = 1.0;
  const requiredAmount = toBaseUnits(capUsd(usdEquivalentOf(thresholdAkt, aktUsdPrice)), USDC_DECIMALS_BASE);
  const ledgerStore = createFakeLedgerStore();

  const deps = {
    chainReader: createFakeChainReader({
      akashBalanceUakt: 0n,
      baseUsdcBalance: requiredAmount * 10n,
      baseGasBalance: MIN_GAS_WEI * 10n,
    }),
    priceOracle: createFakePriceOracle({ aktUsdPrice }),
    skipApiClient: createFakeSkipApiClient({ routeResponse: validRouteFixture({ amountOutUakt: 24_650_000n }) }),
    baseSigner: createFakeBaseSigner({ address: EXPECTED_BASE_SIGNER_ADDRESS, txHash: "0xLEG0_TX_HASH" }),
    // Leg 0 (chain 8453) confirms immediately; Leg 1 (akashnet-2 relay) is stuck 'pending' forever
    // (simulating repeated polling that exhausted its timeout budget).
    relayPoller: createFakeRelayPoller({ statusesByChain: { 8453: "confirmed", "akashnet-2": "pending" } }),
    ledgerStore,
    akashKeyName: "anicca-akash",
    expectedBaseSignerAddress: EXPECTED_BASE_SIGNER_ADDRESS,
    sourceBaseAddress: SOURCE_BASE_ADDRESS,
    destinationAkashAddress: DESTINATION,
    thresholdAkt,
    legTimeoutMs: 5_000,
  };

  const result = await runSwap(deps);
  assert.equal(result.ok, false);
  assert.equal(result.status, "leg_pending_timeout");

  const finalState = lastWrittenLedgerState(ledgerStore);
  const leg0 = finalState.legs.find((l) => l.legIndex === 0);
  const leg1 = finalState.legs.find((l) => l.legIndex === 1);
  assert.equal(leg0.status, "confirmed", "Leg-1 (index 0) must remain recorded confirmed");
  assert.equal(leg1.status, "pending", "Leg-2 (index 1) must be recorded pending, never failed or absent");

  // Leg-1 must never be re-submitted: exactly one signAndBroadcast call total.
  assert.equal(deps.baseSigner.signAndBroadcast.calls.length, 1);
});

test("PROP-008 edge case: a leg's confirmed amount differing from the route's quoted amount_out beyond tolerance fails closed at settlement, not silently accepted (REQ-007 boundary, exercised end-to-end)", async () => {
  const thresholdAkt = 26;
  const aktUsdPrice = 1.0;
  const requiredAmount = toBaseUnits(capUsd(usdEquivalentOf(thresholdAkt, aktUsdPrice)), USDC_DECIMALS_BASE);
  // Both legs report confirmed, but the final Akash balance read (fixed fake) never actually moves —
  // simulating "legs confirmed but AKT not observed at destination" (REQ-007 edge case).
  const deps = {
    chainReader: createFakeChainReader({
      akashBalanceUakt: 0n,
      baseUsdcBalance: requiredAmount * 10n,
      baseGasBalance: MIN_GAS_WEI * 10n,
    }),
    priceOracle: createFakePriceOracle({ aktUsdPrice }),
    skipApiClient: createFakeSkipApiClient({ routeResponse: validRouteFixture({ amountOutUakt: 24_650_000n }) }),
    baseSigner: createFakeBaseSigner({ address: EXPECTED_BASE_SIGNER_ADDRESS }),
    relayPoller: createFakeRelayPoller({ statusesByChain: { 8453: "confirmed", "akashnet-2": "confirmed" } }),
    ledgerStore: createFakeLedgerStore(),
    akashKeyName: "anicca-akash",
    expectedBaseSignerAddress: EXPECTED_BASE_SIGNER_ADDRESS,
    sourceBaseAddress: SOURCE_BASE_ADDRESS,
    destinationAkashAddress: DESTINATION,
    thresholdAkt,
    legTimeoutMs: 5_000,
  };
  const result = await runSwap(deps);
  assert.equal(result.ok, false);
  assert.equal(result.status, "settlement_unverified", 'distinct from a leg-level failure status');
});
