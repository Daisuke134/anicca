// VCSDD spawn-funding-swap Phase 2a (RED). REQ-005 — idempotency/resumability across crash windows
// (PROP-009 property, PROP-020 call-order). Written against lib/driver.mjs's `runSwap(deps)` — see
// driver-preconditions.test.mjs for the full contract comment — which does NOT exist yet. Every test
// below MUST fail at module-load time (MODULE_NOT_FOUND) until Phase 2b.
//
// Crash-injection model: a "crash" is simulated by an injected fault that throws SYNCHRONOUSLY inside
// one of the effectful deps at a precisely chosen point, causing runSwap()'s returned promise to REJECT
// (standing in for "the process died here"). The test then simulates "process restart, same durable
// ledger file" by constructing a FRESH ledgerStore instance (a fresh, unlocked `locked` flag — a crashed
// process no longer holds any lock) that shares the SAME underlying backingStore Map, so the ledger
// CONTENTS written before the crash survive into the resumed attempt exactly as REQ-005 requires.
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import { runSwap } from "../driver.mjs";
import { toBaseUnits, capUsd, usdEquivalentOf } from "../pure/base-units.mjs";
import { USDC_DECIMALS_BASE, MIN_GAS_WEI } from "../pure/constants.mjs";
import { createFakeChainReader, createFakePriceOracle, createFakeSkipApiClient, createFakeLedgerStore, createFakeRelayPoller, spyFn, validRouteFixture } from "./fakes/fake-clients.mjs";

const DESTINATION = "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523";
const SOURCE_BASE_ADDRESS = "0xFAKE_SOURCE_BASE_WALLET";
const EXPECTED_BASE_SIGNER_ADDRESS = "0xFAKE_EXPECTED_SIGNER";
const FIXED_NONCE = 7n;

// A crash-injectable BaseSigner double. `crashPoint` selects EXACTLY where, relative to the RPC call and
// the driver's own writeState calls, the simulated process dies. `onChainStatusAfterCrash` seeds what
// chainReader.getBaseTxStatusByNonce must report for FIXED_NONCE on the RESUMED attempt, modeling ground
// truth about whether the pre-crash broadcast actually reached the chain.
function makeCrashInjectableSigner(crashPoint, callOrderLog) {
  return {
    getAddress: spyFn(async () => EXPECTED_BASE_SIGNER_ADDRESS),
    getNextNonce: spyFn(async () => FIXED_NONCE),
    signAndBroadcast: spyFn(async (tx) => {
      callOrderLog.push("signAndBroadcast:called");
      if (crashPoint === "window2a-rpc-not-returned") {
        throw new Error("simulated crash: process died while the broadcast RPC call was in flight");
      }
      callOrderLog.push("signAndBroadcast:returned");
      return { txHash: "0xLEG0_TX_HASH" };
    }),
  };
}

function makeCrashInjectableLedgerStore(backingStore, crashPoint, callOrderLog) {
  const base = createFakeLedgerStore({ backingStore });
  const originalWriteState = base.writeState;
  let writeStateCallCount = 0;
  base.writeState = spyFn(async (destinationAddress, state) => {
    writeStateCallCount += 1;
    const isPreBroadcastWrite = writeStateCallCount === 1; // the SYNCHRONOUS pre-broadcast 'submitting' record (REQ-005/PROP-020)
    const isPostBroadcastWrite = writeStateCallCount === 2; // the write immediately after signAndBroadcast returns (txHash/confirmed)
    if (isPreBroadcastWrite) {
      callOrderLog.push("writeState:pre-broadcast");
      const result = await originalWriteState(destinationAddress, state);
      if (crashPoint === "window1") {
        throw new Error("simulated crash: process died right after the pre-broadcast submitting record was durably written, before any RPC call");
      }
      return result;
    }
    if (isPostBroadcastWrite) {
      callOrderLog.push("writeState:post-broadcast");
      if (crashPoint === "window2b-hash-write") {
        throw new Error("simulated crash: process died after the broadcast RPC call returned but before the ledger's tx-hash/confirmed write completed");
      }
      return originalWriteState(destinationAddress, state);
    }
    callOrderLog.push(`writeState:leg${state.legs?.length ?? "?"}`);
    return originalWriteState(destinationAddress, state);
  });
  return base;
}

function commonDeps({ ledgerStore, baseSigner, onChainStatusAfterCrash = "not-found" }) {
  const thresholdAkt = 26;
  const aktUsdPrice = 1.0;
  const requiredAmount = toBaseUnits(capUsd(usdEquivalentOf(thresholdAkt, aktUsdPrice)), USDC_DECIMALS_BASE);
  return {
    chainReader: createFakeChainReader({
      akashBalanceUakt: 0n,
      // Every test in this file drives the swap to a genuine ok:true completion (crash-recovery,
      // idempotency) — a faithful REQ-007 settlement re-query needs the post-swap balance to actually
      // reflect the route's quoted amount_out (validRouteFixture's amountOutUakt below), otherwise the
      // driver correctly (and separately) fails closed on settlement_unverified regardless of how
      // correctly the crash-recovery logic itself behaved. See fake-clients.mjs's
      // akashBalanceCreditUakt doc comment.
      akashBalanceCreditUakt: 24_650_000n,
      baseUsdcBalance: requiredAmount * 10n,
      baseGasBalance: MIN_GAS_WEI * 10n,
      baseTxStatusByNonce: { [`${SOURCE_BASE_ADDRESS}:${FIXED_NONCE}`]: onChainStatusAfterCrash },
    }),
    priceOracle: createFakePriceOracle({ aktUsdPrice }),
    skipApiClient: createFakeSkipApiClient({ routeResponse: validRouteFixture({ amountOutUakt: 24_650_000n }) }),
    baseSigner,
    relayPoller: createFakeRelayPoller({ statusesByChain: { 8453: "confirmed", "akashnet-2": "confirmed" } }),
    ledgerStore,
    akashKeyName: "anicca-akash",
    expectedBaseSignerAddress: EXPECTED_BASE_SIGNER_ADDRESS,
    sourceBaseAddress: SOURCE_BASE_ADDRESS,
    destinationAkashAddress: DESTINATION,
    thresholdAkt,
    legTimeoutMs: 5_000,
  };
}

// PROP-020 — the pre-broadcast 'submitting' record is written SYNCHRONOUSLY and BEFORE the broadcast RPC
// call, verified by call-order (not merely "both eventually happened").
test("PROP-020: the pre-broadcast 'submitting' ledger write (nonce+legIndex) happens BEFORE BaseSigner.signAndBroadcast is called — call-order, not just eventual presence", async () => {
  const backingStore = new Map();
  const callOrderLog = [];
  const ledgerStore = makeCrashInjectableLedgerStore(backingStore, "none", callOrderLog);
  const baseSigner = makeCrashInjectableSigner("none", callOrderLog);
  const result = await runSwap(commonDeps({ ledgerStore, baseSigner }));
  assert.equal(result.ok, true, JSON.stringify(result));

  const preBroadcastIdx = callOrderLog.indexOf("writeState:pre-broadcast");
  const broadcastCalledIdx = callOrderLog.indexOf("signAndBroadcast:called");
  assert.ok(preBroadcastIdx !== -1, "pre-broadcast submitting record must be written");
  assert.ok(broadcastCalledIdx !== -1, "signAndBroadcast must be called");
  assert.ok(preBroadcastIdx < broadcastCalledIdx, `pre-broadcast ledger write (index ${preBroadcastIdx}) must precede signAndBroadcast (index ${broadcastCalledIdx})`);

  const persisted = backingStore.get(DESTINATION);
  const leg0 = persisted.legs.find((l) => l.legIndex === 0);
  assert.equal(leg0.nonce, FIXED_NONCE, "the durable pre-broadcast record must contain the deterministic nonce");
});

// PROP-020 (crash-injection variant): even when the broadcast RPC call itself throws (never returns),
// the pre-broadcast record was ALREADY durably written before that call was made — proving it is not
// contingent on the broadcast call succeeding.
test("PROP-020: the pre-broadcast submitting record survives even when the broadcast RPC call itself throws mid-flight (Window 2, sub-case: RPC not yet returned)", async () => {
  const backingStore = new Map();
  const callOrderLog = [];
  const ledgerStore = makeCrashInjectableLedgerStore(backingStore, "none", callOrderLog);
  const baseSigner = makeCrashInjectableSigner("window2a-rpc-not-returned", callOrderLog);
  await assert.rejects(() => runSwap(commonDeps({ ledgerStore, baseSigner })));

  const persisted = backingStore.get(DESTINATION);
  assert.ok(persisted, "the ledger must have been written to before the crash");
  const leg0 = persisted.legs.find((l) => l.legIndex === 0);
  assert.equal(leg0.status, "submitting");
  assert.equal(leg0.nonce, FIXED_NONCE);
});

// PROP-009 — Window 1: crash before ANY broadcast RPC call is made -> next run treats the leg as
// not-yet-attempted and submits it fresh; still exactly one confirmed-producing broadcast overall.
test("PROP-009 (Window 1): crash before the broadcast RPC call -> resumed run submits Leg 0 fresh, exactly one broadcast call total, run completes", async () => {
  const backingStore = new Map();
  const callOrderLog1 = [];
  const attempt1Signer = makeCrashInjectableSigner("none", callOrderLog1);
  const attempt1Ledger = makeCrashInjectableLedgerStore(backingStore, "window1", callOrderLog1);
  await assert.rejects(() => runSwap(commonDeps({ ledgerStore: attempt1Ledger, baseSigner: attempt1Signer })));
  assert.equal(attempt1Signer.signAndBroadcast.calls.length, 0, "Window 1: nothing was ever sent to any chain");

  const callOrderLog2 = [];
  const attempt2Signer = makeCrashInjectableSigner("none", callOrderLog2);
  const attempt2Ledger = makeCrashInjectableLedgerStore(backingStore, "none", callOrderLog2);
  const result = await runSwap(commonDeps({ ledgerStore: attempt2Ledger, baseSigner: attempt2Signer, onChainStatusAfterCrash: "not-found" }));
  assert.equal(result.ok, true, JSON.stringify(result));
  assert.equal(attempt2Signer.signAndBroadcast.calls.length, 1, "resumed run submits Leg 0 exactly once");
});

// PROP-009 — Window 2 (RPC made, not yet returned when the crash hit): the resumed run MUST query
// on-chain status by nonce BEFORE deciding to resubmit, and — because the on-chain query reports the
// earlier broadcast actually landed — MUST NOT resubmit at all.
test("PROP-009 (Window 2, sub-case RPC not returned): resumed run queries on-chain status by nonce and does NOT resubmit when the chain shows the earlier broadcast already landed", async () => {
  const backingStore = new Map();
  const callOrderLog1 = [];
  const attempt1Signer = makeCrashInjectableSigner("window2a-rpc-not-returned", callOrderLog1);
  const attempt1Ledger = makeCrashInjectableLedgerStore(backingStore, "none", callOrderLog1);
  await assert.rejects(() => runSwap(commonDeps({ ledgerStore: attempt1Ledger, baseSigner: attempt1Signer })));
  assert.equal(attempt1Signer.signAndBroadcast.calls.length, 1, "the RPC call WAS made on attempt 1, it just never returned before the crash");

  const callOrderLog2 = [];
  const attempt2Signer = makeCrashInjectableSigner("none", callOrderLog2);
  const attempt2Ledger = makeCrashInjectableLedgerStore(backingStore, "none", callOrderLog2);
  const deps2 = commonDeps({ ledgerStore: attempt2Ledger, baseSigner: attempt2Signer, onChainStatusAfterCrash: "confirmed" });
  const result = await runSwap(deps2);

  assert.equal(deps2.chainReader.getBaseTxStatusByNonce.calls.length >= 1, true, "the resumed run must query on-chain status by nonce before deciding");
  assert.equal(attempt2Signer.signAndBroadcast.calls.length, 0, "MUST NOT blind-resubmit a leg found 'submitting' without first querying on-chain state");
  assert.equal(result.ok, true, JSON.stringify(result));
});

// PROP-009 — Window 2 (RPC returned, crash before the hash/confirmed write): same on-chain-query
// requirement; the earlier broadcast's nonce is still the sole re-derivable query key even though a
// txHash never made it into the ledger.
test("PROP-009 (Window 2, sub-case RPC returned but ledger write crashed): resumed run still resolves via the on-chain nonce query, never blind-resubmits", async () => {
  const backingStore = new Map();
  const callOrderLog1 = [];
  const attempt1Signer = makeCrashInjectableSigner("none", callOrderLog1);
  const attempt1Ledger = makeCrashInjectableLedgerStore(backingStore, "window2b-hash-write", callOrderLog1);
  await assert.rejects(() => runSwap(commonDeps({ ledgerStore: attempt1Ledger, baseSigner: attempt1Signer })));
  assert.equal(attempt1Signer.signAndBroadcast.calls.length, 1);

  const callOrderLog2 = [];
  const attempt2Signer = makeCrashInjectableSigner("none", callOrderLog2);
  const attempt2Ledger = makeCrashInjectableLedgerStore(backingStore, "none", callOrderLog2);
  const deps2 = commonDeps({ ledgerStore: attempt2Ledger, baseSigner: attempt2Signer, onChainStatusAfterCrash: "confirmed" });
  const result = await runSwap(deps2);

  assert.equal(attempt2Signer.signAndBroadcast.calls.length, 0, "the on-chain query must reveal the tx already landed — no resubmit");
  assert.equal(result.ok, true, JSON.stringify(result));
});

// PROP-009 — Window 3: crash after the confirmed write for Leg 0. The resumed run must re-evaluate
// overall route-completion state (planNextLeg) rather than re-touching Leg 0.
test("PROP-009 (Window 3): crash after Leg 0's confirmed write -> resumed run never re-broadcasts Leg 0, proceeds straight to Leg 1", async () => {
  const backingStore = new Map();
  // Seed the ledger as if Leg 0 already fully confirmed in a PRIOR (already-completed) attempt.
  backingStore.set(DESTINATION, {
    legs: [{ legIndex: 0, status: "confirmed", nonce: FIXED_NONCE, txHash: "0xLEG0_TX_HASH" }],
    completedAtMs: null,
    quoteSnapshot: { txsRequired: 2, amountOutUakt: 24_650_000n },
  });
  const callOrderLog = [];
  const ledgerStore = makeCrashInjectableLedgerStore(backingStore, "none", callOrderLog);
  const baseSigner = makeCrashInjectableSigner("none", callOrderLog);
  const result = await runSwap(commonDeps({ ledgerStore, baseSigner }));
  assert.equal(result.ok, true, JSON.stringify(result));
  assert.equal(baseSigner.signAndBroadcast.calls.length, 0, "Leg 0 already confirmed — must never be re-broadcast");
});

// PROP-009 (property tier): for an arbitrary single crash point drawn from the full named set (including
// "none" = normal completion), replaying to completion NEVER results in more than one confirmed-producing
// broadcast call for Leg 0.
test("PROP-009 (property): for any single named crash point injected at Leg 0's boundary, replay-to-completion never issues more than one broadcast call that ultimately reaches 'confirmed'", async () => {
  const crashPoints = ["none", "window1", "window2a-rpc-not-returned", "window2b-hash-write"];
  await fc.assert(
    fc.asyncProperty(fc.constantFrom(...crashPoints), async (crashPoint) => {
      const backingStore = new Map();
      const callOrderLog1 = [];
      const attempt1Signer = makeCrashInjectableSigner(crashPoint, callOrderLog1);
      const attempt1Ledger = makeCrashInjectableLedgerStore(backingStore, crashPoint, callOrderLog1);
      const deps1 = commonDeps({ ledgerStore: attempt1Ledger, baseSigner: attempt1Signer, onChainStatusAfterCrash: "confirmed" });

      let attempt1Result;
      let attempt1Crashed = false;
      try {
        attempt1Result = await runSwap(deps1);
      } catch {
        attempt1Crashed = true;
      }

      let finalResult = attempt1Result;
      let attempt2Signer = attempt1Signer;
      if (attempt1Crashed || (attempt1Result && attempt1Result.ok === false && attempt1Result.status === "leg_pending_timeout")) {
        const callOrderLog2 = [];
        attempt2Signer = makeCrashInjectableSigner("none", callOrderLog2);
        const attempt2Ledger = makeCrashInjectableLedgerStore(backingStore, "none", callOrderLog2);
        finalResult = await runSwap(commonDeps({ ledgerStore: attempt2Ledger, baseSigner: attempt2Signer, onChainStatusAfterCrash: "confirmed" }));
      }

      assert.equal(finalResult.ok, true, `crashPoint=${crashPoint}: expected eventual success, got ${JSON.stringify(finalResult)}`);
      const totalConfirmedBroadcasts = (crashPoint === "none" ? attempt1Signer.signAndBroadcast.calls.length : 0) + (attempt2Signer === attempt1Signer ? 0 : attempt2Signer.signAndBroadcast.calls.length);
      assert.ok(totalConfirmedBroadcasts <= 1, `crashPoint=${crashPoint}: at most one confirmed-producing broadcast call expected, got ${totalConfirmedBroadcasts}`);
    }),
    { numRuns: 20 }
  );
});
