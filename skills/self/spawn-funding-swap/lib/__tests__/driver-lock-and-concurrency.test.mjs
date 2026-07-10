// VCSDD spawn-funding-swap Phase 2a (RED). REQ-005, REQ-010 — PROP-010, the concurrent-invocation
// canonical destination-address-keyed lock property, exercised against the REAL lock primitive (reuses
// the already-adversary-hardened `withGigLock`, economy/gig/lib/lock.mjs, unmodified — mirrors
// colony-spawn-lock.test.mjs's own reuse pattern for a different feature's lock). Written against
// lib/ledger-store.mjs's `createLedgerStore({ stateDir })` and lib/driver.mjs's `runSwap(deps)`, which do
// NOT exist yet — every test below MUST fail at module-load time (MODULE_NOT_FOUND) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { runSwap } from "../driver.mjs";
import { createLedgerStore } from "../ledger-store.mjs";
import { toBaseUnits, capUsd, usdEquivalentOf } from "../pure/base-units.mjs";
import { USDC_DECIMALS_BASE, MIN_GAS_WEI } from "../pure/constants.mjs";
import { createFakeChainReader, createFakePriceOracle, createFakeSkipApiClient, createFakeBaseSigner, createFakeRelayPoller, spyFn, validRouteFixture } from "./fakes/fake-clients.mjs";

const DESTINATION = "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523";
const SOURCE_BASE_ADDRESS = "0xFAKE_SOURCE_BASE_WALLET";
const EXPECTED_BASE_SIGNER_ADDRESS = "0xFAKE_EXPECTED_SIGNER";

function tmpStateDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "spawn-funding-swap-lock-test-"));
}

function makeInvocationDeps({ stateDir, quoteId, releaseGate }) {
  const thresholdAkt = 26;
  const aktUsdPrice = 1.0;
  const requiredAmount = toBaseUnits(capUsd(usdEquivalentOf(thresholdAkt, aktUsdPrice)), USDC_DECIMALS_BASE);
  const skipApiClient = createFakeSkipApiClient({ routeResponse: validRouteFixture({ amountOutUakt: 24_650_000n }) });
  // Wrap getRoute so each invocation observably gets a DISTINCT quote id (PROP-010's own falsifiability
  // requirement: dedup must be keyed by destination address, never by route/quote id) while still gating
  // on releaseGate so the test can hold the FIRST invocation inside its critical section until the
  // second invocation has had a chance to contend for the same lock.
  const originalGetRoute = skipApiClient.getRoute;
  skipApiClient.getRoute = spyFn(async (params) => {
    if (releaseGate) await releaseGate;
    const route = await originalGetRoute(params);
    return { ...route, __quoteId: quoteId };
  });

  return {
    chainReader: createFakeChainReader({
      akashBalanceUakt: 0n,
      baseUsdcBalance: requiredAmount * 10n,
      baseGasBalance: MIN_GAS_WEI * 10n,
    }),
    priceOracle: createFakePriceOracle({ aktUsdPrice }),
    skipApiClient,
    baseSigner: createFakeBaseSigner({ address: EXPECTED_BASE_SIGNER_ADDRESS }),
    relayPoller: createFakeRelayPoller({ statusesByChain: { 8453: "confirmed", "akashnet-2": "confirmed" } }),
    ledgerStore: createLedgerStore({ stateDir }),
    akashKeyName: "anicca-akash",
    expectedBaseSignerAddress: EXPECTED_BASE_SIGNER_ADDRESS,
    sourceBaseAddress: SOURCE_BASE_ADDRESS,
    destinationAkashAddress: DESTINATION,
    thresholdAkt,
    legTimeoutMs: 5_000,
  };
}

test("PROP-010: two concurrent invocations, each with a DISTINCT freshly-mocked Skip quote id, contending for ONE shared canonical lock keyed by the destination Akash address -> exactly one proceeds to request a route/sign, the other resumes/no-ops at lock acquisition", async () => {
  const stateDir = tmpStateDir();
  let releaseFirst;
  const firstGate = new Promise((resolve) => {
    releaseFirst = resolve;
  });

  const deps1 = makeInvocationDeps({ stateDir, quoteId: "quote-A", releaseGate: firstGate });
  const deps2 = makeInvocationDeps({ stateDir, quoteId: "quote-B", releaseGate: null });

  // Start invocation 1; it will block INSIDE the lock (at the price/route step, gated by firstGate) —
  // proving it already holds the canonical lock before invocation 2 is even started.
  const call1 = runSwap(deps1);
  // Give invocation 1's async lock-acquire a tick to actually land on disk before firing invocation 2
  // (same deterministic-handoff concern colony-spawn-lock.test.mjs documents for withGigLock's O_EXCL
  // create being scheduled on the libuv threadpool).
  await new Promise((r) => setTimeout(r, 50));

  const call2 = runSwap(deps2);
  const result2 = await call2;

  // Invocation 2 must observe the lock held and resume/no-op BEFORE calling PriceOracle or Skip at all.
  assert.equal(result2.ok, false);
  assert.equal(deps2.priceOracle.getAktUsdPrice.calls.length, 0, "the loser must never call PriceOracle.getAktUsdPrice() while the lock is held");
  assert.equal(deps2.skipApiClient.getRoute.calls.length, 0, "the loser must never call SkipApiClient.getRoute() while the lock is held");
  assert.equal(deps2.baseSigner.signAndBroadcast.calls.length, 0);

  releaseFirst();
  const result1 = await call1;
  assert.equal(result1.ok, true, JSON.stringify(result1));
  assert.equal(deps1.baseSigner.signAndBroadcast.calls.length, 1, "exactly one successful submission for the winner");

  fs.rmSync(stateDir, { recursive: true, force: true });
});

test("REQ-010 falsifiability: dedup is keyed by DESTINATION ADDRESS, not by route/quote id — even though invocation 2's (never-requested) quote id would differ from invocation 1's, it is still rejected purely by the shared lock", async () => {
  const stateDir = tmpStateDir();
  let releaseFirst;
  const firstGate = new Promise((resolve) => {
    releaseFirst = resolve;
  });
  const deps1 = makeInvocationDeps({ stateDir, quoteId: "quote-DISTINCT-1", releaseGate: firstGate });
  const deps2 = makeInvocationDeps({ stateDir, quoteId: "quote-DISTINCT-2-totally-different", releaseGate: null });

  const call1 = runSwap(deps1);
  await new Promise((r) => setTimeout(r, 50));
  const result2 = await runSwap(deps2);
  assert.equal(result2.ok, false);
  assert.equal(deps2.skipApiClient.getRoute.calls.length, 0, "invocation 2's distinct quote id was NEVER requested — proving the reject happened at lock-acquisition, before any route request");

  releaseFirst();
  await call1;
  fs.rmSync(stateDir, { recursive: true, force: true });
});
