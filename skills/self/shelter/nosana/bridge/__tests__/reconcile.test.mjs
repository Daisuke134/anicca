// node:test — reconcile.mjs: the at-most-once / never-blind-retry core for the Base burn, plus
// polling the Solana destination balance for the credit. Every dependency below is injected and
// read-only (fake clock/sleep) — no real waiting, no real network, and structurally no way for
// these functions to send/resend anything (none of them takes a "send" dependency at all).
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  decideBaseReceiptOutcome,
  pollForBaseReceipt,
  reconcileUnknownBurnOutcome,
  pollForDestinationCredit,
} from "../reconcile.mjs";

// ---- decideBaseReceiptOutcome --------------------------------------------------------------

test("decideBaseReceiptOutcome classifies not-found/confirmed/failed/pending", () => {
  assert.deepEqual(decideBaseReceiptOutcome(null), { outcome: "not-found" });
  assert.equal(decideBaseReceiptOutcome({ status: "0x1" }).outcome, "confirmed");
  assert.equal(decideBaseReceiptOutcome({ status: 1 }).outcome, "confirmed");
  assert.equal(decideBaseReceiptOutcome({ status: "0x0" }).outcome, "failed-onchain");
  assert.equal(decideBaseReceiptOutcome({ status: 0 }).outcome, "failed-onchain");
  assert.equal(decideBaseReceiptOutcome({ status: null }).outcome, "pending");
});

// ---- pollForBaseReceipt (fake clock/sleep — no real waiting) -------------------------------

test("pollForBaseReceipt returns 'confirmed' as soon as the receipt shows status success", async () => {
  let calls = 0;
  const result = await pollForBaseReceipt({
    txHash: "0xabc",
    getReceiptImpl: async () => {
      calls += 1;
      return calls < 3 ? null : { status: "0x1" };
    },
    sleepImpl: async () => {},
    now: () => 0,
    pollIntervalMs: 1,
    timeoutMs: 100,
  });
  assert.equal(result.outcome, "confirmed");
  assert.equal(calls, 3);
});

test("pollForBaseReceipt returns 'failed-onchain' when the receipt shows status failure", async () => {
  const result = await pollForBaseReceipt({
    txHash: "0xabc",
    getReceiptImpl: async () => ({ status: "0x0" }),
    sleepImpl: async () => {},
    now: () => 0,
    pollIntervalMs: 1,
    timeoutMs: 100,
  });
  assert.equal(result.outcome, "failed-onchain");
});

test("pollForBaseReceipt returns 'timeout' when the receipt never resolves and never treats an RPC hiccup as failure", async () => {
  let t = 0;
  const result = await pollForBaseReceipt({
    txHash: "0xabc",
    getReceiptImpl: async () => {
      throw new Error("RPC hiccup");
    },
    sleepImpl: async () => {
      t += 10;
    },
    now: () => t,
    pollIntervalMs: 10,
    timeoutMs: 30,
  });
  assert.equal(result.outcome, "timeout");
});

// ---- reconcileUnknownBurnOutcome: the at-most-once / never-blind-retry core ----------------
// Every dependency here is READ-ONLY — there is no "send" or "resend" capability anywhere in this
// function's signature, so it is structurally, not just behaviorally, incapable of a duplicate burn.

test("reconcileUnknownBurnOutcome resolves via the receipt when it eventually shows confirmed", async () => {
  const outcome = await reconcileUnknownBurnOutcome({
    txHash: "0xburn1",
    getReceiptImpl: async () => ({ status: "0x1" }),
  });
  assert.equal(outcome.outcome, "confirmed");
  assert.equal(outcome.source, "eth_getTransactionReceipt");
  assert.equal(outcome.retried, false);
});

test("reconcileUnknownBurnOutcome treats an on-chain failure as terminal, not unknown", async () => {
  const outcome = await reconcileUnknownBurnOutcome({
    txHash: "0xburn2",
    getReceiptImpl: async () => ({ status: "0x0" }),
  });
  assert.equal(outcome.outcome, "failed-onchain");
  assert.equal(outcome.retried, false);
});

test("reconcileUnknownBurnOutcome reports unknown-unresolved (never retries) when the receipt never appears, and is idempotent on re-run", async () => {
  const getReceiptImpl = async () => null;
  const first = await reconcileUnknownBurnOutcome({ txHash: "0xburn3", getReceiptImpl });
  assert.equal(first.outcome, "unknown-unresolved");
  assert.equal(first.retried, false);
  assert.match(first.reason, /refusing to blind-retry/);

  const second = await reconcileUnknownBurnOutcome({ txHash: "0xburn3", getReceiptImpl });
  assert.equal(second.outcome, "unknown-unresolved");
  assert.equal(second.retried, false);
});

test("reconcileUnknownBurnOutcome treats a receipt-lookup RPC error the same as not-found — still unknown, never a crash", async () => {
  const outcome = await reconcileUnknownBurnOutcome({
    txHash: "0xburn4",
    getReceiptImpl: async () => {
      throw new Error("RPC down");
    },
  });
  assert.equal(outcome.outcome, "unknown-unresolved");
});

// ---- pollForDestinationCredit: the cross-chain "did the money actually arrive" signal -------

test("pollForDestinationCredit returns 'credited' once the Solana USDC balance increases by at least the expected amount", async () => {
  let calls = 0;
  const result = await pollForDestinationCredit({
    getSolanaUsdcBalanceImpl: async () => {
      calls += 1;
      return calls < 3 ? 5 : 15; // preBalance 5 -> 15 = +10, matches a $10 bridge
    },
    preBalance: 5,
    minExpectedDelta: 9.9,
    sleepImpl: async () => {},
    now: () => 0,
    pollIntervalMs: 1,
    timeoutMs: 100,
  });
  assert.equal(result.outcome, "credited");
  assert.ok(Math.abs(result.delta - 10) < 1e-9);
});

test("pollForDestinationCredit: THE unknown-outcome path — reconciles into 'awaiting-credit' rather than retrying any send, when the destination balance never moves within the poll window", async () => {
  // This is the literal proof required by the spec: "bridges are asynchronous and slow, so
  // 'unknown' is the normal case here... it must poll for the destination-side credit and NEVER
  // re-send." getSolanaUsdcBalanceImpl below is called repeatedly (proving it polls) but nothing
  // in this function's signature can send/resend a transaction on either chain — there is no such
  // dependency to call, so the test also proves this by construction, not just by assertion.
  let pollCount = 0;
  let t = 0;
  const result = await pollForDestinationCredit({
    getSolanaUsdcBalanceImpl: async () => {
      pollCount += 1;
      return 5; // balance never moves — the destination-side finalize never happened
    },
    preBalance: 5,
    minExpectedDelta: 9.9,
    sleepImpl: async () => {
      t += 15000;
    },
    now: () => t,
    pollIntervalMs: 15000,
    timeoutMs: 60000,
  });
  assert.equal(result.outcome, "awaiting-credit");
  assert.match(result.reason, /never re-sent/);
  assert.ok(pollCount >= 4, `expected multiple polls proving it actually polled, got ${pollCount}`);

  // Idempotence: re-running the same poll against the same still-unresolved real state returns the
  // same honest verdict both times — nothing about calling this twice changes behavior.
  let t2 = 0;
  const again = await pollForDestinationCredit({
    getSolanaUsdcBalanceImpl: async () => 5,
    preBalance: 5,
    minExpectedDelta: 9.9,
    sleepImpl: async () => {
      t2 += 15000;
    },
    now: () => t2,
    pollIntervalMs: 15000,
    timeoutMs: 60000,
  });
  assert.equal(again.outcome, "awaiting-credit");
});

test("pollForDestinationCredit tolerates transient RPC errors on the balance read without treating them as credited or as a hard failure", async () => {
  let calls = 0;
  let t = 0;
  const result = await pollForDestinationCredit({
    getSolanaUsdcBalanceImpl: async () => {
      calls += 1;
      if (calls < 3) throw new Error("RPC hiccup");
      return 20; // +15, well past the 9.9 threshold for a $10 bridge (some interest/rounding slack)
    },
    preBalance: 5,
    minExpectedDelta: 9.9,
    sleepImpl: async () => {
      t += 1000;
    },
    now: () => t,
    pollIntervalMs: 1000,
    timeoutMs: 30000,
  });
  assert.equal(result.outcome, "credited");
});

test("pollForDestinationCredit fails closed on a non-positive minExpectedDelta (a zero threshold would call 'no change' a success)", async () => {
  await assert.rejects(
    pollForDestinationCredit({
      getSolanaUsdcBalanceImpl: async () => 5,
      preBalance: 5,
      minExpectedDelta: 0,
      sleepImpl: async () => {},
      now: () => 0,
      timeoutMs: 10,
    }),
    /minExpectedDelta must be a positive finite number/,
  );
});
