// VCSDD spawn-funding-swap Phase 2a (RED) — CLI test fixture (PROP-014). Loaded by
// bin/spawn-funding-swap.mjs ONLY when SPAWN_FUNDING_SWAP_FAKE_DEPS_MODULE points at this file (a
// test-only seam; production never sets that env var). Exports createDeps(), returning a full
// lib/driver.mjs `runSwap(deps)`-shaped deps object built entirely from in-memory fakes — zero real
// network/RPC/signing clients, consistent with the Test-Money Safety Rule. This fixture is engineered to
// reach REQ-007 success (exit 0).
import {
  createFakeChainReader,
  createFakePriceOracle,
  createFakeSkipApiClient,
  createFakeBaseSigner,
  createFakeRelayPoller,
  createFakeLedgerStore,
  validRouteFixture,
} from "./fake-clients.mjs";
import { toBaseUnits, capUsd, usdEquivalentOf } from "../../pure/base-units.mjs";
import { USDC_DECIMALS_BASE, MIN_GAS_WEI } from "../../pure/constants.mjs";

const EXPECTED_BASE_SIGNER_ADDRESS = "0xFAKE_EXPECTED_SIGNER";
const SOURCE_BASE_ADDRESS = "0xFAKE_SOURCE_BASE_WALLET";
const DESTINATION = "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523";

export function createDeps() {
  const thresholdAkt = 26;
  const aktUsdPrice = 1.0;
  const requiredAmount = toBaseUnits(capUsd(usdEquivalentOf(thresholdAkt, aktUsdPrice)), USDC_DECIMALS_BASE);
  return {
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
}
