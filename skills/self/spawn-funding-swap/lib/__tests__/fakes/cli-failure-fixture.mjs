// VCSDD spawn-funding-swap Phase 2a (RED) — CLI test fixture (PROP-014), the failure sibling of
// cli-success-fixture.mjs. Engineered to fail REQ-003 (insufficient funded source — today's real-world
// blocker, PROP-006) so the CLI entrypoint exits non-zero.
import {
  createFakeChainReader,
  createFakePriceOracle,
  createFakeSkipApiClient,
  createFakeBaseSigner,
  createFakeRelayPoller,
  createFakeLedgerStore,
  validRouteFixture,
} from "./fake-clients.mjs";

const EXPECTED_BASE_SIGNER_ADDRESS = "0xFAKE_EXPECTED_SIGNER";
const SOURCE_BASE_ADDRESS = "0xFAKE_SOURCE_BASE_WALLET";
const DESTINATION = "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523";

export function createDeps() {
  return {
    chainReader: createFakeChainReader({ akashBalanceUakt: 0n, baseUsdcBalance: 0n, baseGasBalance: 0n }), // today's real state
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
  };
}
