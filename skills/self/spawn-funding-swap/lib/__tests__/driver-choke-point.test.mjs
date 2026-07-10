// VCSDD spawn-funding-swap Phase 2a (RED). Driver-level money-safety choke-point tests — the single
// most important file in this suite. PROP-019 (REQ-002/REQ-006/REQ-011/REQ-012 choke point), PROP-023
// (REQ-001/REQ-012 driver-level fromBaseUnits wiring), PROP-005's driver-level requiredBaseUnits/
// minGasWei cross-call-site identity (FIND-003 + iteration-5 fix), PROP-013's driver-level toleranceBps
// identity (iteration-5 fix). Written against lib/driver.mjs's `runSwap(deps)` — see
// driver-preconditions.test.mjs for the full contract comment — which does NOT exist yet. Every test
// below MUST fail at module-load time (MODULE_NOT_FOUND) until Phase 2b.
//
// deps.pure override contract (Phase 2a-defined, binding on Phase 2b): runSwap(deps) MUST accept an
// OPTIONAL `deps.pure` object whose keys shadow its internal default pure-function imports
// (computeSwapNeed, usdEquivalentOf, capUsd, toBaseUnits, fromBaseUnits, validateRoute,
// checkSourceFunded, verifySettlement, planNextLeg, reconcileLedgerOnResume) — when a key is supplied,
// the driver MUST call that supplied function INSTEAD of its own default at every call site that would
// otherwise use it. This is how these tests observe a pure function's ACTUAL call arguments as the
// driver itself invokes them (spy-wrapping the REAL implementation, never re-implementing the logic in
// the test) without needing a mocking framework this codebase doesn't already depend on.
import { test } from "node:test";
import assert from "node:assert/strict";
import { runSwap } from "../driver.mjs";
import { computeSwapNeed, usdEquivalentOf, capUsd } from "../pure/swap-need.mjs";
import { toBaseUnits, fromBaseUnits } from "../pure/base-units.mjs";
import { validateRoute } from "../pure/route-validation.mjs";
import { checkSourceFunded } from "../pure/funding-check.mjs";
import { verifySettlement } from "../pure/settlement.mjs";
import { planNextLeg, reconcileLedgerOnResume } from "../pure/ledger-plan.mjs";
import { SWAP_MAX_USD, USDC_DECIMALS_BASE, AKT_DECIMALS, MIN_GAS_WEI, TOLERANCE_BPS } from "../pure/constants.mjs";
import {
  createFakeChainReader,
  createFakePriceOracle,
  createFakeSkipApiClient,
  createFakeBaseSigner,
  createFakeRelayPoller,
  createFakeLedgerStore,
  spyFn,
  validRouteFixture,
} from "./fakes/fake-clients.mjs";

const DESTINATION = "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523";
const SOURCE_BASE_ADDRESS = "0xFAKE_SOURCE_BASE_WALLET";
const EXPECTED_BASE_SIGNER_ADDRESS = "0xFAKE_EXPECTED_SIGNER";

// realPureWithSpies — wraps the REAL pure-function implementations with call-recording spies, so a test
// can inspect the driver's ACTUAL runtime argument to each pure function while still exercising the true
// (unmodified) pure logic underneath. Individual entries can be overridden per-test (e.g. to swap in a
// deliberately-invalid route for PROP-004-style checks) without losing the spy on the others.
function realPureWithSpies(overrides = {}) {
  return {
    computeSwapNeed: spyFn(computeSwapNeed),
    usdEquivalentOf: spyFn(usdEquivalentOf),
    capUsd: spyFn(capUsd),
    toBaseUnits: spyFn(toBaseUnits),
    fromBaseUnits: spyFn(fromBaseUnits),
    validateRoute: spyFn(validateRoute),
    checkSourceFunded: spyFn(checkSourceFunded),
    verifySettlement: spyFn(verifySettlement),
    planNextLeg: spyFn(planNextLeg),
    reconcileLedgerOnResume: spyFn(reconcileLedgerOnResume),
    ...overrides,
  };
}

function fullSuccessDeps({ akashBalanceUakt, thresholdAkt, aktUsdPrice, baseUsdcBalance, baseGasBalance, amountOutUakt, akashBalanceCreditUakt = 0n, pure }) {
  const chainReader = createFakeChainReader({
    akashBalanceUakt,
    // Opt-in: fixtures that expect a genuine ok:true success (REQ-007 settlement must observe a real
    // delta) pass akashBalanceCreditUakt explicitly; fixtures that intentionally test the
    // unchanged-balance fail-closed path (PROP-013) leave this at its 0n default. See fake-clients.mjs.
    akashBalanceCreditUakt,
    baseUsdcBalance,
    baseGasBalance,
  });
  return {
    chainReader,
    priceOracle: createFakePriceOracle({ aktUsdPrice }),
    skipApiClient: createFakeSkipApiClient({ routeResponse: validRouteFixture({ amountOutUakt }) }),
    baseSigner: createFakeBaseSigner({ address: EXPECTED_BASE_SIGNER_ADDRESS }),
    relayPoller: createFakeRelayPoller({ statusesByChain: { 8453: "confirmed", "akashnet-2": "confirmed" } }),
    ledgerStore: createFakeLedgerStore(),
    akashKeyName: "anicca-akash",
    expectedBaseSignerAddress: EXPECTED_BASE_SIGNER_ADDRESS,
    sourceBaseAddress: SOURCE_BASE_ADDRESS,
    destinationAkashAddress: DESTINATION,
    thresholdAkt,
    legTimeoutMs: 5_000,
    pure,
  };
}

// PROP-019 — CAPPED case: need's USD-equivalent exceeds SWAP_MAX_USD.
test("PROP-019 (capped): Skip amount_in AND BaseSigner tx amount are BOTH bit-identical to toBaseUnits(SWAP_MAX_USD, USDC_DECIMALS_BASE) — never a <=-equivalent float comparison", async () => {
  // Choose thresholdAkt/akashBalance/price so usdEquivalentOf(need, price) exceeds SWAP_MAX_USD by construction.
  const thresholdAkt = 100; // AKT
  const akashBalanceUakt = 0n;
  const aktUsdPrice = (SWAP_MAX_USD * 5) / thresholdAkt; // need=100 AKT * price => USD-equiv = 5x SWAP_MAX_USD, comfortably capped
  const expectedAmountIn = toBaseUnits(SWAP_MAX_USD, USDC_DECIMALS_BASE);

  const deps = fullSuccessDeps({
    akashBalanceUakt,
    thresholdAkt,
    aktUsdPrice,
    baseUsdcBalance: expectedAmountIn * 10n,
    baseGasBalance: MIN_GAS_WEI * 10n,
    amountOutUakt: 24_650_000n,
    akashBalanceCreditUakt: 24_650_000n,
    pure: realPureWithSpies(),
  });

  const result = await runSwap(deps);
  assert.equal(result.ok, true, JSON.stringify(result));
  assert.equal(deps.skipApiClient.getRoute.calls.length, 1);
  const amountInArg = deps.skipApiClient.getRoute.calls[0][0].amount_in;
  assert.equal(amountInArg, expectedAmountIn, "Skip amount_in must be the exact capped INTEGER bigint");
  assert.equal(typeof amountInArg, "bigint");

  assert.equal(deps.baseSigner.signAndBroadcast.calls.length, 1);
  const txArg = deps.baseSigner.signAndBroadcast.calls[0][0];
  assert.equal(txArg.amount, expectedAmountIn, "BaseSigner.signAndBroadcast tx amount must be the SAME exact bigint as Skip's amount_in");
  assert.equal(typeof txArg.amount, "bigint");
});

// PROP-019 — UNCAPPED companion fixture: need's USD-equivalent is well under SWAP_MAX_USD.
test("PROP-019 (uncapped companion): Skip amount_in AND BaseSigner tx amount are BOTH bit-identical to toBaseUnits(usdEquivalentOf(need, price), USDC_DECIMALS_BASE) when under the cap", async () => {
  const thresholdAkt = 26;
  const akashBalanceUakt = 0n;
  const aktUsdPrice = (SWAP_MAX_USD * 0.5) / thresholdAkt; // USD-equiv = 0.5x SWAP_MAX_USD, uncapped
  const expectedUsd = capUsd(usdEquivalentOf(thresholdAkt, aktUsdPrice));
  const expectedAmountIn = toBaseUnits(expectedUsd, USDC_DECIMALS_BASE);
  assert.ok(expectedUsd < SWAP_MAX_USD, "sanity: fixture must be genuinely uncapped");

  const deps = fullSuccessDeps({
    akashBalanceUakt,
    thresholdAkt,
    aktUsdPrice,
    baseUsdcBalance: expectedAmountIn * 10n,
    baseGasBalance: MIN_GAS_WEI * 10n,
    amountOutUakt: 24_650_000n,
    akashBalanceCreditUakt: 24_650_000n,
    pure: realPureWithSpies(),
  });

  const result = await runSwap(deps);
  assert.equal(result.ok, true, JSON.stringify(result));
  const amountInArg = deps.skipApiClient.getRoute.calls[0][0].amount_in;
  const txArg = deps.baseSigner.signAndBroadcast.calls[0][0];
  assert.equal(amountInArg, expectedAmountIn);
  assert.equal(txArg.amount, expectedAmountIn);
});

// PROP-019 — wrong-decimals falsifiability: a fixture using toBaseUnits with a WRONG decimals constant
// at a pure-override call site must FAIL the exact-equality assertion above (proving the test is
// falsifiable against a 10^6x-class unit error, not merely internally self-consistent).
test("PROP-019 falsifiability: a driver wired to a WRONG-decimals toBaseUnits override produces an amount_in that FAILS exact equality against the correctly-scaled expectation", async () => {
  const thresholdAkt = 26;
  const aktUsdPrice = (SWAP_MAX_USD * 0.5) / thresholdAkt;
  const correctlyExpectedAmountIn = toBaseUnits(capUsd(usdEquivalentOf(thresholdAkt, aktUsdPrice)), USDC_DECIMALS_BASE);
  const wrongToBaseUnits = spyFn((amountFloat, _decimals) => toBaseUnits(amountFloat, 18)); // wrong decimals injected

  const deps = fullSuccessDeps({
    akashBalanceUakt: 0n,
    thresholdAkt,
    aktUsdPrice,
    baseUsdcBalance: 10n ** 30n, // absurdly large so the (wrongly-scaled) funding check still passes
    baseGasBalance: MIN_GAS_WEI * 10n,
    amountOutUakt: 24_650_000n,
    pure: realPureWithSpies({ toBaseUnits: wrongToBaseUnits }),
  });

  await runSwap(deps);
  const amountInArg = deps.skipApiClient.getRoute.calls[0]?.[0]?.amount_in;
  assert.notEqual(amountInArg, correctlyExpectedAmountIn, "a wrong-decimals toBaseUnits must produce a value that fails the exact-equality money-safety assertion");
});

// PROP-023 — driver-level fromBaseUnits wiring for computeSwapNeed's `current` argument.
test("PROP-023 (driver-level): computeSwapNeed's `current` argument is bit-identical to fromBaseUnits(mockedBalanceUakt, AKT_DECIMALS), never the raw bigint or an un-scaled Number(balanceUakt)", async () => {
  const akashBalanceUakt = 1_850_000n; // 1.85 AKT
  const thresholdAkt = 26;
  const pure = realPureWithSpies();
  const deps = fullSuccessDeps({
    akashBalanceUakt,
    thresholdAkt,
    aktUsdPrice: 1.0,
    baseUsdcBalance: 10n ** 12n,
    baseGasBalance: MIN_GAS_WEI * 10n,
    amountOutUakt: 24_650_000n,
    pure,
  });

  await runSwap(deps);
  assert.equal(pure.computeSwapNeed.calls.length, 1);
  const currentArg = pure.computeSwapNeed.calls[0][0];
  assert.equal(currentArg, fromBaseUnits(akashBalanceUakt, AKT_DECIMALS));
  assert.equal(currentArg, 1.85);
  assert.notEqual(currentArg, akashBalanceUakt, "must never pass the raw bigint through");
  assert.notEqual(currentArg, Number(akashBalanceUakt), "must never pass an un-scaled Number(balanceUakt)");
});

// PROP-005 — driver-level requiredBaseUnits cross-call-site identity (FIND-003).
test("PROP-005 (driver-level, FIND-003): checkSourceFunded's requiredBaseUnits, Skip getRoute's amount_in, and BaseSigner.signAndBroadcast's tx amount are ALL THREE bit-identical bigints in one run", async () => {
  const thresholdAkt = 26;
  const aktUsdPrice = (SWAP_MAX_USD * 0.5) / thresholdAkt;
  const pure = realPureWithSpies();
  const expectedAmount = toBaseUnits(capUsd(usdEquivalentOf(thresholdAkt, aktUsdPrice)), USDC_DECIMALS_BASE);

  const deps = fullSuccessDeps({
    akashBalanceUakt: 0n,
    thresholdAkt,
    aktUsdPrice,
    baseUsdcBalance: expectedAmount * 10n,
    baseGasBalance: MIN_GAS_WEI * 10n,
    amountOutUakt: 24_650_000n,
    akashBalanceCreditUakt: 24_650_000n,
    pure,
  });

  const result = await runSwap(deps);
  assert.equal(result.ok, true, JSON.stringify(result));

  assert.equal(pure.checkSourceFunded.calls.length, 1);
  const requiredBaseUnitsArg = pure.checkSourceFunded.calls[0][2];
  const amountInArg = deps.skipApiClient.getRoute.calls[0][0].amount_in;
  const txAmountArg = deps.baseSigner.signAndBroadcast.calls[0][0].amount;

  assert.equal(requiredBaseUnitsArg, expectedAmount);
  assert.equal(amountInArg, expectedAmount);
  assert.equal(txAmountArg, expectedAmount);
  assert.equal(requiredBaseUnitsArg, amountInArg, "checkSourceFunded and Skip amount_in must receive the identical bigint");
  assert.equal(amountInArg, txAmountArg, "Skip amount_in and the signed tx amount must receive the identical bigint");
});

// PROP-005 — driver-level minGasWei identity (iteration-5 fix).
test("PROP-005 (driver-level, iteration-5): checkSourceFunded's minGasWei argument is bit-identical to MIN_GAS_WEI — a driver hardcoding/defaulting minGasWei differently at its own call site would fail this", async () => {
  const pure = realPureWithSpies();
  const thresholdAkt = 26;
  const aktUsdPrice = 1.0;
  const expectedAmount = toBaseUnits(capUsd(usdEquivalentOf(thresholdAkt, aktUsdPrice)), USDC_DECIMALS_BASE);
  const deps = fullSuccessDeps({
    akashBalanceUakt: 0n,
    thresholdAkt,
    aktUsdPrice,
    baseUsdcBalance: expectedAmount * 10n,
    baseGasBalance: MIN_GAS_WEI * 10n,
    amountOutUakt: 24_650_000n,
    pure,
  });
  await runSwap(deps);
  assert.equal(pure.checkSourceFunded.calls.length, 1);
  const minGasWeiArg = pure.checkSourceFunded.calls[0][3];
  assert.equal(minGasWeiArg, MIN_GAS_WEI);
  assert.equal(typeof minGasWeiArg, "bigint");
});

// PROP-013 — driver-level toleranceBps identity (iteration-5 fix).
test("PROP-013 (driver-level, iteration-5): verifySettlement's toleranceBps argument is bit-identical to TOLERANCE_BPS — a driver hardcoding a looser toleranceBps at its own call site would fail this", async () => {
  const pure = realPureWithSpies();
  const thresholdAkt = 26;
  const aktUsdPrice = 1.0;
  const expectedAmount = toBaseUnits(capUsd(usdEquivalentOf(thresholdAkt, aktUsdPrice)), USDC_DECIMALS_BASE);
  const deps = fullSuccessDeps({
    akashBalanceUakt: 0n,
    thresholdAkt,
    aktUsdPrice,
    baseUsdcBalance: expectedAmount * 10n,
    baseGasBalance: MIN_GAS_WEI * 10n,
    amountOutUakt: 24_650_000n,
    pure,
  });
  await runSwap(deps);
  assert.equal(pure.verifySettlement.calls.length, 1);
  const toleranceBpsArg = pure.verifySettlement.calls[0][3];
  assert.equal(toleranceBpsArg, TOLERANCE_BPS);
  assert.equal(typeof toleranceBpsArg, "number");
});

// PROP-013 — success path unreachable unless verifySettlement genuinely returns true for the observed pair.
test("PROP-013: success path is unreachable when the mocked final-balance query shows an UNCHANGED balance after all legs 'succeed' — non-zero exit despite green legs", async () => {
  const akashBalanceUakt = 0n; // pre AND (mocked) post balance both stay 0n -> no observed increase
  const thresholdAkt = 26;
  const deps = fullSuccessDeps({
    akashBalanceUakt,
    thresholdAkt,
    aktUsdPrice: 1.0,
    baseUsdcBalance: 10n ** 12n,
    baseGasBalance: MIN_GAS_WEI * 10n,
    amountOutUakt: 24_650_000n,
    pure: realPureWithSpies(),
  });
  // chainReader.getAkashBalance always returns the SAME fixed 0n regardless of call count (fake default),
  // so the post-legs re-query observes no increase even though every leg reports 'confirmed'.
  const result = await runSwap(deps);
  assert.equal(result.ok, false);
  assert.equal(result.status, "settlement_unverified");
});

// PROP-003 (driver wiring) — checkSourceFunded never proceeds past false to a real broadcast, driver-level.
test("REQ-003 (driver-level): checkSourceFunded returning false blocks the driver before ANY Skip route request or broadcast call", async () => {
  const thresholdAkt = 26;
  const aktUsdPrice = 1.0;
  const expectedAmount = toBaseUnits(capUsd(usdEquivalentOf(thresholdAkt, aktUsdPrice)), USDC_DECIMALS_BASE);
  const deps = fullSuccessDeps({
    akashBalanceUakt: 0n,
    thresholdAkt,
    aktUsdPrice,
    baseUsdcBalance: expectedAmount - 1n, // one base unit short
    baseGasBalance: MIN_GAS_WEI * 10n,
    amountOutUakt: 24_650_000n,
    pure: realPureWithSpies(),
  });
  const result = await runSwap(deps);
  assert.equal(result.ok, false);
  assert.equal(deps.skipApiClient.getRoute.calls.length, 0);
  assert.equal(deps.baseSigner.signAndBroadcast.calls.length, 0);
});
