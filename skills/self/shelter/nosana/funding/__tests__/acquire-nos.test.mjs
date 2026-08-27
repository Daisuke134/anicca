// node:test — acquire-nos: pure spend cap / slippage / cost-math / reconcile-on-unknown parts of
// S2's Jupiter SOL->NOS funding swap. Every I/O boundary is injected — nothing here hits the
// network or signs a real transaction.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  LAMPORTS_PER_SOL,
  NOS_DECIMALS,
  DEFAULT_MAX_SPEND_SOL,
  DEFAULT_MAX_SPEND_FRACTION_OF_BALANCE,
  DEFAULT_SOL_FEE_FLOOR_SOL,
  DEFAULT_MAX_SLIPPAGE_BPS,
  DEFAULT_MAX_PRICE_IMPACT_PCT,
  RAW_TRANSACTION_HARD_BYTE_LIMIT,
  BASE64_TRANSACTION_HARD_CHAR_LIMIT,
  DEFAULT_TRANSACTION_SAFE_BYTE_LIMIT,
  SIZE_GUARD_MAX_ACCOUNTS_LADDER,
  resolveSpendLamports,
  validateQuoteShape,
  parsePriceImpactPct,
  evaluateFundingGate,
  computeExpectedNosOut,
  computeSpendSummary,
  transactionSignatureBase58,
  decideSettlementFromStatus,
  pollForConfirmation,
  reconcileUnknownOutcome,
  buildFundingIntentRecord,
  buildFundingSettledRecord,
  measureUnsignedTransactionMessageBytes,
  measureTransactionArtifact,
  evaluateTransactionSizeGuard,
  pickSizeGuardMaxAccounts,
  buildRightSizedSwapTransaction,
} from "../acquire-nos.mjs";

function makeQuote(overrides = {}) {
  return {
    inputMint: "So11111111111111111111111111111111111111112",
    outputMint: "nosXBVoaCTtYdLvKY6Csb4AC8JCdQKKAaWYtx2ZMoo7",
    inAmount: "10000000",
    outAmount: "2904770",
    otherAmountThreshold: "2875723",
    swapMode: "ExactIn",
    slippageBps: 100,
    priceImpactPct: "0.0049693078028773556788778494",
    ...overrides,
  };
}

// ---- cap gate: resolveSpendLamports (spec hard constraint 2) ------------------------------

test("resolveSpendLamports defaults documented constants to the spec values", () => {
  assert.equal(DEFAULT_MAX_SPEND_SOL, 0.01);
  assert.equal(DEFAULT_MAX_SPEND_FRACTION_OF_BALANCE, 0.25);
  assert.equal(DEFAULT_SOL_FEE_FLOOR_SOL, 0.02);
  assert.equal(DEFAULT_MAX_SLIPPAGE_BPS, 100);
  assert.equal(DEFAULT_MAX_PRICE_IMPACT_PCT, 0.02);
  assert.equal(NOS_DECIMALS, 6);
});

test("resolveSpendLamports uses the requested amount when it is under the 25% hard cap", () => {
  const r = resolveSpendLamports({ requestedSol: 0.01, solBalanceLamports: 1 * LAMPORTS_PER_SOL });
  assert.equal(r.spendLamports, 0.01 * LAMPORTS_PER_SOL);
  assert.equal(r.hardCapApplied, false);
});

test("resolveSpendLamports clamps to 25% of balance when the requested amount exceeds it (real Franklin-wallet shape: 0.01 SOL requested against a 0.0378 SOL balance)", () => {
  const solBalanceLamports = Math.floor(0.03782572 * LAMPORTS_PER_SOL);
  const r = resolveSpendLamports({ requestedSol: 0.01, solBalanceLamports });
  const expectedHardCap = Math.floor(solBalanceLamports * 0.25);
  assert.equal(r.hardCapLamports, expectedHardCap);
  assert.equal(r.spendLamports, expectedHardCap);
  assert.equal(r.hardCapApplied, true);
  assert.ok(r.spendLamports < 0.01 * LAMPORTS_PER_SOL);
});

test("resolveSpendLamports fails closed on non-finite/negative inputs", () => {
  assert.throws(() => resolveSpendLamports({ requestedSol: 0, solBalanceLamports: 1e9 }), /positive finite number/);
  assert.throws(() => resolveSpendLamports({ requestedSol: NaN, solBalanceLamports: 1e9 }), /positive finite number/);
  assert.throws(() => resolveSpendLamports({ requestedSol: 0.01, solBalanceLamports: -1 }), /non-negative finite number/);
});

test("resolveSpendLamports never returns a negative spend even with a zero balance", () => {
  const r = resolveSpendLamports({ requestedSol: 0.01, solBalanceLamports: 0 });
  assert.equal(r.spendLamports, 0);
});

// ---- quote shape + price-impact parsing --------------------------------------------------

test("validateQuoteShape accepts a well-formed quote", () => {
  assert.deepEqual(validateQuoteShape(makeQuote()), { valid: true, reason: "quote shape OK" });
});

test("validateQuoteShape rejects a missing/non-object quote", () => {
  assert.equal(validateQuoteShape(null).valid, false);
  assert.equal(validateQuoteShape(undefined).valid, false);
  assert.match(validateQuoteShape(null).reason, /missing or not an object/);
});

test("validateQuoteShape rejects a non-positive outAmount or otherAmountThreshold", () => {
  assert.equal(validateQuoteShape(makeQuote({ outAmount: "0" })).valid, false);
  assert.equal(validateQuoteShape(makeQuote({ otherAmountThreshold: "-1" })).valid, false);
});

test("validateQuoteShape rejects a missing priceImpactPct", () => {
  const q = makeQuote();
  delete q.priceImpactPct;
  assert.equal(validateQuoteShape(q).valid, false);
});

test("parsePriceImpactPct parses Jupiter's decimal-string fraction (real live value: 0.00497 == 0.497%, not 0.497)", () => {
  const n = parsePriceImpactPct(makeQuote());
  assert.ok(n > 0.004 && n < 0.005);
});

test("parsePriceImpactPct fails closed on a missing or unparseable value rather than defaulting to 0", () => {
  const q = makeQuote();
  delete q.priceImpactPct;
  assert.throws(() => parsePriceImpactPct(q), /missing/);
  assert.throws(() => parsePriceImpactPct(makeQuote({ priceImpactPct: "not-a-number" })), /not a finite number/);
});

// ---- slippage/price-impact gate + balance floor (spec hard constraints 2 & 3) -------------

function baseGateArgs(overrides = {}) {
  return {
    spendLamports: 0.009 * LAMPORTS_PER_SOL,
    solBalanceLamports: 0.0378 * LAMPORTS_PER_SOL,
    feeLamportsEstimate: 2_000_000,
    quote: makeQuote(),
    slippageBps: 100,
    ...overrides,
  };
}

test("evaluateFundingGate allows a real-shaped swap well within cap, slippage, impact, and floor", () => {
  const gate = evaluateFundingGate(baseGateArgs());
  assert.equal(gate.allowed, true);
});

test("evaluateFundingGate refuses a missing/invalid quote (fail-closed, never treats missing as acceptable)", () => {
  const gate = evaluateFundingGate(baseGateArgs({ quote: null }));
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /missing\/invalid quote is never acceptable/);
});

test("evaluateFundingGate refuses when requested slippageBps exceeds the configured ceiling", () => {
  const gate = evaluateFundingGate(baseGateArgs({ slippageBps: 500, maxSlippageBps: 100 }));
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /exceeds max allowed/);
});

test("evaluateFundingGate refuses when quoted price impact exceeds the 2% default ceiling", () => {
  const gate = evaluateFundingGate(baseGateArgs({ quote: makeQuote({ priceImpactPct: "0.05" }) }));
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /price impact/);
});

test("evaluateFundingGate refuses when the post-swap SOL balance would fall below the fee floor", () => {
  const solBalanceLamports = 0.03 * LAMPORTS_PER_SOL;
  const spendLamports = 0.02 * LAMPORTS_PER_SOL; // leaves 0.01 SOL, below the 0.02 default floor
  const gate = evaluateFundingGate(baseGateArgs({ solBalanceLamports, spendLamports, feeLamportsEstimate: 0 }));
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /below the fee floor/);
});

test("evaluateFundingGate fails closed on a missing/NaN solBalanceLamports or feeLamportsEstimate", () => {
  const g1 = evaluateFundingGate(baseGateArgs({ solBalanceLamports: NaN }));
  assert.equal(g1.allowed, false);
  assert.match(g1.reason, /solBalanceLamports is unavailable/);
  const g2 = evaluateFundingGate(baseGateArgs({ feeLamportsEstimate: undefined }));
  assert.equal(g2.allowed, false);
  assert.match(g2.reason, /feeLamportsEstimate is unavailable/);
});

test("evaluateFundingGate refuses a non-positive spendLamports", () => {
  const gate = evaluateFundingGate(baseGateArgs({ spendLamports: 0 }));
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /spendLamports must be a positive number/);
});

// ---- cost math ------------------------------------------------------------------------------

test("computeExpectedNosOut converts smallest-unit strings using 6 decimals", () => {
  const { expectedNos, minNos } = computeExpectedNosOut(makeQuote());
  assert.ok(Math.abs(expectedNos - 2.90477) < 1e-9);
  assert.ok(Math.abs(minNos - 2.875723) < 1e-9);
});

test("computeExpectedNosOut throws on an invalid quote rather than returning NaN/0", () => {
  assert.throws(() => computeExpectedNosOut({}), /outAmount is missing/);
});

test("computeSpendSummary computes spendSol/spendUsd/expectedNosUsd correctly", () => {
  const summary = computeSpendSummary({
    spendLamports: 0.01 * LAMPORTS_PER_SOL,
    solUsdPrice: 74.08,
    nosUsdPrice: 0.25436,
    expectedNos: 2.9,
  });
  assert.ok(Math.abs(summary.spendSol - 0.01) < 1e-12);
  assert.ok(Math.abs(summary.spendUsd - 0.7408) < 1e-9);
  assert.ok(Math.abs(summary.expectedNosUsd - 2.9 * 0.25436) < 1e-9);
});

test("computeSpendSummary fails closed on a negative/non-finite input", () => {
  assert.throws(
    () => computeSpendSummary({ spendLamports: -1, solUsdPrice: 1, nosUsdPrice: 1, expectedNos: 1 }),
    /must be a non-negative finite number/,
  );
  assert.throws(
    () => computeSpendSummary({ spendLamports: 1, solUsdPrice: NaN, nosUsdPrice: 1, expectedNos: 1 }),
    /must be a non-negative finite number/,
  );
});

// ---- signature parsing ------------------------------------------------------------------------

test("transactionSignatureBase58 recovers a base58 signature from a signed-looking transaction", () => {
  const sig = new Uint8Array(64).fill(7);
  const decoded = transactionSignatureBase58({ signatures: [sig] });
  assert.equal(typeof decoded, "string");
  assert.ok(decoded.length > 0);
});

test("transactionSignatureBase58 refuses an all-zero (unsigned) signature", () => {
  const sig = new Uint8Array(64); // all zero
  assert.throws(() => transactionSignatureBase58({ signatures: [sig] }), /not signed yet/);
});

test("transactionSignatureBase58 refuses a transaction with no signatures array", () => {
  assert.throws(() => transactionSignatureBase58({}), /no signatures array/);
});

// ---- settlement classification -----------------------------------------------------------

test("decideSettlementFromStatus classifies not-found/confirmed/finalized/failed/pending", () => {
  assert.deepEqual(decideSettlementFromStatus(null), { outcome: "not-found" });
  assert.equal(decideSettlementFromStatus({ confirmationStatus: "confirmed" }).outcome, "confirmed");
  assert.equal(decideSettlementFromStatus({ confirmationStatus: "finalized" }).outcome, "confirmed");
  assert.equal(decideSettlementFromStatus({ confirmationStatus: "processed" }).outcome, "pending");
  const failed = decideSettlementFromStatus({ err: { InstructionError: [0, "Custom"] } });
  assert.equal(failed.outcome, "failed-onchain");
  assert.ok(failed.err);
});

// ---- pollForConfirmation (fake clock/sleep — no real waiting) -----------------------------

test("pollForConfirmation returns 'confirmed' as soon as the status flips", async () => {
  let calls = 0;
  const result = await pollForConfirmation({
    signature: "sig1",
    lastValidBlockHeight: 1000,
    getSignatureStatusesImpl: async () => {
      calls += 1;
      return { value: [calls < 3 ? null : { confirmationStatus: "confirmed" }] };
    },
    getBlockHeightImpl: async () => 500,
    sleepImpl: async () => {},
    now: () => 0,
    pollIntervalMs: 1,
    timeoutMs: 100,
  });
  assert.equal(result.outcome, "confirmed");
  assert.equal(calls, 3);
});

test("pollForConfirmation returns 'expired' once the block height passes lastValidBlockHeight without a status", async () => {
  const result = await pollForConfirmation({
    signature: "sig1",
    lastValidBlockHeight: 100,
    getSignatureStatusesImpl: async () => ({ value: [null] }),
    getBlockHeightImpl: async () => 200, // already past lastValidBlockHeight
    sleepImpl: async () => {},
    now: () => 0,
    pollIntervalMs: 1,
    timeoutMs: 100,
  });
  assert.equal(result.outcome, "expired");
});

test("pollForConfirmation returns 'timeout' when neither a status nor expiry ever resolves", async () => {
  let t = 0;
  const result = await pollForConfirmation({
    signature: "sig1",
    lastValidBlockHeight: undefined,
    getSignatureStatusesImpl: async () => ({ value: [null] }),
    getBlockHeightImpl: async () => 0,
    sleepImpl: async () => {
      t += 10;
    },
    now: () => t,
    pollIntervalMs: 10,
    timeoutMs: 30,
  });
  assert.equal(result.outcome, "timeout");
});

// ---- reconcileUnknownOutcome: the at-most-once / never-blind-retry core --------------------
// Every dependency passed in is READ-ONLY (status lookup, recent-signatures lookup, balance
// read) — there is no "send" or "resend" capability anywhere in this function's signature, so it
// is structurally, not just behaviorally, incapable of retrying the swap.

test("reconcileUnknownOutcome resolves via getSignatureStatuses when the status eventually shows confirmed", async () => {
  const outcome = await reconcileUnknownOutcome({
    signature: "sigA",
    preNosBalance: 1,
    getSignatureStatusesImpl: async () => ({ value: [{ confirmationStatus: "finalized" }] }),
    getSignaturesForAddressImpl: async () => {
      throw new Error("should not be called — status lookup already resolved it");
    },
    getNosBalanceImpl: async () => {
      throw new Error("should not be called — status lookup already resolved it");
    },
  });
  assert.equal(outcome.outcome, "confirmed");
  assert.equal(outcome.source, "getSignatureStatuses");
  assert.equal(outcome.retried, false);
});

test("reconcileUnknownOutcome falls back to getSignaturesForAddress when getSignatureStatuses errors", async () => {
  const outcome = await reconcileUnknownOutcome({
    signature: "sigB",
    preNosBalance: 1,
    getSignatureStatusesImpl: async () => {
      throw new Error("RPC down");
    },
    getSignaturesForAddressImpl: async () => [{ signature: "sigB", err: null }],
    getNosBalanceImpl: async () => {
      throw new Error("should not be reached");
    },
  });
  assert.equal(outcome.outcome, "confirmed");
  assert.equal(outcome.source, "getSignaturesForAddress");
  assert.equal(outcome.retried, false);
});

test("reconcileUnknownOutcome falls back to a real NOS balance increase as the ultimate ground truth", async () => {
  const outcome = await reconcileUnknownOutcome({
    signature: "sigC",
    preNosBalance: 1.0,
    getSignatureStatusesImpl: async () => ({ value: [null] }),
    getSignaturesForAddressImpl: async () => [],
    getNosBalanceImpl: async () => 3.9, // balance went up — swap landed even though we lost track
  });
  assert.equal(outcome.outcome, "confirmed");
  assert.equal(outcome.source, "nos-balance-delta");
  assert.ok(Math.abs(outcome.nosDelta - 2.9) < 1e-9);
  assert.equal(outcome.retried, false);
});

test("reconcileUnknownOutcome reports unknown-unresolved (never retries) when nothing confirms landing anywhere", async () => {
  const outcome = await reconcileUnknownOutcome({
    signature: "sigD",
    preNosBalance: 1.0,
    getSignatureStatusesImpl: async () => ({ value: [null] }),
    getSignaturesForAddressImpl: async () => [],
    getNosBalanceImpl: async () => 1.0, // unchanged — swap never landed
  });
  assert.equal(outcome.outcome, "unknown-unresolved");
  assert.equal(outcome.retried, false);
  assert.match(outcome.reason, /refusing to blind-retry/);

  // Idempotence: re-running against the same (still-unresolved) real on-chain state returns the
  // same verdict both times — nothing about calling this twice changes behavior or compounds.
  const again = await reconcileUnknownOutcome({
    signature: "sigD",
    preNosBalance: 1.0,
    getSignatureStatusesImpl: async () => ({ value: [null] }),
    getSignaturesForAddressImpl: async () => [],
    getNosBalanceImpl: async () => 1.0,
  });
  assert.equal(again.outcome, "unknown-unresolved");
  assert.equal(again.retried, false);
});

test("reconcileUnknownOutcome treats an on-chain failure surfaced via getSignatureStatuses as terminal, not unknown", async () => {
  const outcome = await reconcileUnknownOutcome({
    signature: "sigE",
    preNosBalance: 1,
    getSignatureStatusesImpl: async () => ({ value: [{ err: { InstructionError: [1, "Slippage"] } }] }),
    getSignaturesForAddressImpl: async () => {
      throw new Error("should not be called");
    },
    getNosBalanceImpl: async () => {
      throw new Error("should not be called");
    },
  });
  assert.equal(outcome.outcome, "failed-onchain");
  assert.equal(outcome.retried, false);
});

// ---- ledger record shaping — no secret material ever included ------------------------------

test("buildFundingIntentRecord and buildFundingSettledRecord never embed anything secret-shaped", () => {
  const intent = buildFundingIntentRecord({
    ts: 1000,
    intentId: "id1",
    address: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T",
    spendLamports: 9_000_000,
    spendSol: 0.009,
    quote: makeQuote(),
    expectedNos: 2.9,
    minNos: 2.87,
    signature: "sigX",
    slippageBps: 100,
    priceImpactPct: 0.005,
  });
  const settled = buildFundingSettledRecord({
    ts: 1001,
    intentId: "id1",
    address: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T",
    signature: "sigX",
    spendLamports: 9_000_000,
    spendSol: 0.009,
    spendUsd: 0.66,
    nosReceived: 2.9,
    nosUsdPrice: 0.25,
    solUsdPrice: 74,
    outcome: "confirmed",
    source: "poll",
  });
  const serialized = JSON.stringify({ intent, settled });
  // A real base58 secret key is 87-88 chars with no separators; sanity-check no such run exists.
  assert.ok(!/[1-9A-HJ-NP-Za-km-z]{80,}/.test(serialized));
  assert.equal(intent.status, "intent");
  assert.equal(settled.status, "settled");
});

// ---- transaction-size guard --------------------------------------------------------------
// TWO real --live failures drove this section (see this feature's incident reports):
//   (1) VersionedTransaction.sign() -> MessageV0.serialize() threw "encoding overruns Uint8Array"
//       (an internal 1232-byte scratch-buffer overrun on the MESSAGE alone).
//   (2) AFTER fixing (1), a second --live run got past .sign() and failed at sendRawTransaction's
//       local simulation: "...too large: 1660 bytes (max: encoded/raw 1644/1232)." A message the
//       first guard measured as 1180 bytes (deemed "safe") produced a 1+64+1180=1245-byte
//       TRANSACTION — 13 bytes over the wall. The bug: gating on the message when the real limit
//       applies to the whole transaction (message + 65 bytes of signature/shortvec overhead).
// These tests prove: the gate now measures the REAL returned artifact (no arithmetic, no
// deserialization needed to decide pass/fail), the exact regression numbers from failure (2) are
// refused, and the retry ladder still produces exactly one winning attempt, never touching sign().

test("documented size-guard constants match the real Solana wire limit, its base64 encoding, and the re-tuned ladder", () => {
  assert.equal(RAW_TRANSACTION_HARD_BYTE_LIMIT, 1232); // Solana's PACKET_DATA_SIZE — applies to the WHOLE transaction
  assert.equal(BASE64_TRANSACTION_HARD_CHAR_LIMIT, 1644); // Math.ceil(1232/3)*4 — matches the real RPC error text verbatim
  assert.ok(DEFAULT_TRANSACTION_SAFE_BYTE_LIMIT < RAW_TRANSACTION_HARD_BYTE_LIMIT);
  // Re-tuned after the second failure: undefined/default is no longer the first rung (it reliably
  // produced an over-the-wall transaction in consecutive real runs); starts at maxAccounts=30.
  assert.deepEqual(SIZE_GUARD_MAX_ACCOUNTS_LADDER, [30, 20, 12]);
});

test("measureTransactionArtifact decodes the real returned base64 artifact directly — no arithmetic, no deserialization", () => {
  const raw = Buffer.alloc(935); // matches a real measurement taken in this feature's verification
  const m = measureTransactionArtifact(raw.toString("base64"));
  assert.equal(m.rawBytes, 935);
  assert.equal(m.base64Chars, raw.toString("base64").length);
  assert.equal(m.error, null);
});

test("measureTransactionArtifact fails closed on a missing/empty artifact", () => {
  assert.equal(measureTransactionArtifact(undefined).rawBytes, null);
  assert.equal(measureTransactionArtifact("").rawBytes, null);
  assert.match(measureTransactionArtifact("").error, /missing or empty/);
});

test("REGRESSION (exact numbers from the second real --live failure): a 1180-byte message with one required signature must be REFUSED, because 1 + 64 + 1180 = 1245 > 1232", () => {
  // The real returned artifact already includes the 1-byte signature-count shortvec plus one
  // 64-byte zeroed signature placeholder — exactly what Jupiter's /swap actually handed back.
  const rawTransactionBytes = 1 + 64 * 1 + 1180; // = 1245
  assert.equal(rawTransactionBytes, 1245);
  const fakeArtifactBase64 = Buffer.alloc(rawTransactionBytes).toString("base64");
  assert.equal(fakeArtifactBase64.length, 1660); // matches the real RPC error's reported b64 length exactly
  const measurement = measureTransactionArtifact(fakeArtifactBase64);
  const guard = evaluateTransactionSizeGuard({ measurement });
  assert.equal(guard.allowed, false);
  assert.match(guard.reason, /exceeds Solana's hard wire limit/);
});

test("evaluateTransactionSizeGuard allows a real-shaped small transaction (935 raw bytes, matching this feature's own successful dry run) well within every limit", () => {
  const measurement = measureTransactionArtifact(Buffer.alloc(935).toString("base64"));
  const guard = evaluateTransactionSizeGuard({ measurement });
  assert.equal(guard.allowed, true);
});

test("evaluateTransactionSizeGuard refuses a transaction that fits the hard wall but exceeds the configured safe margin", () => {
  const measurement = measureTransactionArtifact(Buffer.alloc(1210).toString("base64")); // < 1232 hard, > 1200 safe
  const guard = evaluateTransactionSizeGuard({ measurement, safeRawLimit: 1200 });
  assert.equal(guard.allowed, false);
  assert.match(guard.reason, /exceeds the safe margin/);
});

test("evaluateTransactionSizeGuard refuses an unmeasurable artifact (fail-closed)", () => {
  const guard = evaluateTransactionSizeGuard({ measurement: { rawBytes: null, base64Chars: null, error: "boom" } });
  assert.equal(guard.allowed, false);
  assert.match(guard.reason, /could not be measured/);
});

test("pickSizeGuardMaxAccounts walks the re-tuned ladder (30, 20, 12) and clamps at the last rung beyond its length", () => {
  assert.equal(pickSizeGuardMaxAccounts(0), 30);
  assert.equal(pickSizeGuardMaxAccounts(1), 20);
  assert.equal(pickSizeGuardMaxAccounts(2), 12);
  assert.equal(pickSizeGuardMaxAccounts(10), 12); // clamped, never reads past the ladder
});

// ---- buildRightSizedSwapTransaction: the full retry orchestration, fully faked I/O ---------
// The fake VersionedTransactionCtor's .sign() always throws — if buildRightSizedSwapTransaction
// ever called it, every test below would fail with that error message instead of the expected
// one, which is how these tests prove signing never happens during the guard's retry loop. Note
// deserialize() is only ever invoked by production code on a WINNING (already-passed-the-gate)
// candidate, so these fakes never need to parse real Solana wire bytes.

function makeFakeVersionedTransactionCtor() {
  return {
    deserialize(buf) {
      return {
        message: { serialize: () => new Uint8Array(Math.max(buf.length - 65, 0)) },
        sign() {
          throw new Error("buildRightSizedSwapTransaction must never call .sign() — that is the caller's job, after this returns");
        },
      };
    },
  };
}

// rawBytesByMaxAccountsKey maps the maxAccounts query value (or "default" when omitted) actually
// sent to /swap/v2/quote to a fake RAW transaction byte length — the fake swapTransaction is a
// zero-filled buffer of exactly that length, so measureTransactionArtifact's decode is real (just
// applied to synthetic bytes), letting each test script exactly which rung "wins" without needing
// a real oversized Solana transaction fixture.
function makeFakeFetchImpl(rawBytesByMaxAccountsKey) {
  return async (url, options) => {
    if (typeof url === "string" && url.includes("/swap/v2/quote")) {
      const key = new URL(url).searchParams.get("maxAccounts") || "default";
      return {
        ok: true,
        status: 200,
        json: async () => ({
          outAmount: "1000000",
          otherAmountThreshold: "990000",
          priceImpactPct: "0.001",
          _k: key,
        }),
      };
    }
    // POST /swap/v2/swap
    const body = JSON.parse(options.body);
    const rawBytes = rawBytesByMaxAccountsKey[body.quoteResponse._k];
    const swapTransaction = Buffer.alloc(rawBytes).toString("base64");
    return {
      ok: true,
      status: 200,
      json: async () => ({ swapTransaction, lastValidBlockHeight: 123456, prioritizationFeeLamports: 1000 }),
    };
  };
}

test("buildRightSizedSwapTransaction returns immediately on attempt 0 when the first route already fits — never touches sign()", async () => {
  const result = await buildRightSizedSwapTransaction({
    fetchImpl: makeFakeFetchImpl({ 30: 935 }),
    spendLamports: 9000000,
    slippageBps: 100,
    takerAddress: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T",
    VersionedTransactionCtor: makeFakeVersionedTransactionCtor(),
    ladder: [30],
    sleepImpl: async () => {},
  });
  assert.equal(result.attempt, 0);
  assert.equal(result.maxAccountsUsed, 30);
  assert.equal(result.measurement.fits === undefined, true); // artifact measurement has no `fits` field, unlike the old message-only one
  assert.equal(result.measurement.rawBytes, 935);
});

test("buildRightSizedSwapTransaction retries with a tighter maxAccounts and picks the FIRST attempt whose REAL transaction fits, never signing along the way", async () => {
  const attempts = [];
  const result = await buildRightSizedSwapTransaction({
    // Regression shape: rung 0 (maxAccounts=30) still comes back oversized (1245 raw, the exact
    // failure numbers), rung 1 (maxAccounts=20) fits comfortably.
    fetchImpl: makeFakeFetchImpl({ 30: 1245, 20: 935 }),
    spendLamports: 9000000,
    slippageBps: 100,
    takerAddress: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T",
    VersionedTransactionCtor: makeFakeVersionedTransactionCtor(),
    ladder: [30, 20],
    onAttempt: (attempt, info) => attempts.push({ attempt, maxAccounts: info.maxAccounts, ok: info.ok, rawBytes: info.measurement && info.measurement.rawBytes }),
    sleepImpl: async () => {},
  });
  assert.equal(result.attempt, 1);
  assert.equal(result.maxAccountsUsed, 20);
  assert.equal(result.measurement.rawBytes, 935);
  assert.deepEqual(attempts, [
    { attempt: 0, maxAccounts: 30, ok: false, rawBytes: 1245 },
    { attempt: 1, maxAccounts: 20, ok: true, rawBytes: 935 },
  ]);
});

test("buildRightSizedSwapTransaction's retry loop produces exactly ONE winning attempt per call — the caller only ever gets one transaction to sign/record, so a size-guard retry can never itself cause two intent records", async () => {
  const attempts = [];
  await buildRightSizedSwapTransaction({
    fetchImpl: makeFakeFetchImpl({ 30: 1245, 20: 935 }),
    spendLamports: 9000000,
    slippageBps: 100,
    takerAddress: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T",
    VersionedTransactionCtor: makeFakeVersionedTransactionCtor(),
    ladder: [30, 20],
    onAttempt: (attempt, info) => attempts.push(info.ok),
    sleepImpl: async () => {},
  });
  assert.equal(attempts.filter(Boolean).length, 1); // exactly one "fits" verdict, never more
  // buildRightSizedSwapTransaction itself has no ledger/appendChild dependency in its signature at
  // all (see acquire-nos.mjs) — it is structurally incapable of writing an intent record, whether
  // called once or retried internally many times. Only acquireNos writes intents, and only once,
  // strictly after this function returns its single winning result.
});

test("buildRightSizedSwapTransaction throws (fail-closed) when every rung of the ladder is oversized — refuses to sign rather than signing an oversized transaction", async () => {
  await assert.rejects(
    buildRightSizedSwapTransaction({
      fetchImpl: makeFakeFetchImpl({ 30: 1245, 20: 1240, 12: 1233 }),
      spendLamports: 9000000,
      slippageBps: 100,
      takerAddress: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T",
      VersionedTransactionCtor: makeFakeVersionedTransactionCtor(),
      ladder: SIZE_GUARD_MAX_ACCOUNTS_LADDER,
      sleepImpl: async () => {},
    }),
    /exhausted 3 size-guard attempt\(s\)/,
  );
  // The rejection message itself (not "must never call .sign()") is the proof sign() was never
  // reached on any of the 3 oversized attempts — the fake .sign() would have thrown a different,
  // distinguishable error had it been invoked.
});

test("buildRightSizedSwapTransaction distinguishes a fetch/rate-limit failure from a size-overrun failure in the per-attempt info (errorKind), so the operator is never told 'too big' when the real cause was a 429", async () => {
  const attempts = [];
  const fetchImpl = async (url) => {
    if (typeof url === "string" && url.includes("/swap/v2/quote")) {
      const key = new URL(url).searchParams.get("maxAccounts") || "default";
      if (key === "30") {
        // 500, not 429: fetchWithBackoff only internally retries-with-real-delay on 429, so a 500
        // here keeps this test fast while still exercising the same "fetch failed" errorKind path.
        return { ok: false, status: 500, text: async () => "server error" };
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ outAmount: "1000000", otherAmountThreshold: "990000", priceImpactPct: "0.001", _k: key }),
      };
    }
    const swapTransaction = Buffer.alloc(935).toString("base64");
    return { ok: true, status: 200, json: async () => ({ swapTransaction, lastValidBlockHeight: 1, prioritizationFeeLamports: 0 }) };
  };
  await buildRightSizedSwapTransaction({
    fetchImpl,
    spendLamports: 9000000,
    slippageBps: 100,
    takerAddress: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T",
    VersionedTransactionCtor: makeFakeVersionedTransactionCtor(),
    ladder: [30, 20],
    sleepImpl: async () => {},
    onAttempt: (attempt, info) => attempts.push({ attempt, errorKind: info.errorKind, ok: info.ok }),
  });
  assert.deepEqual(attempts, [
    { attempt: 0, errorKind: "fetch", ok: false },
    { attempt: 1, errorKind: null, ok: true },
  ]);
});

test("buildRightSizedSwapTransaction includes an informational message-only measurement on the winning attempt, but it never determines pass/fail (an oversized message with a small enough total transaction would still be gated only by the transaction check)", async () => {
  const result = await buildRightSizedSwapTransaction({
    fetchImpl: makeFakeFetchImpl({ 30: 935 }),
    spendLamports: 9000000,
    slippageBps: 100,
    takerAddress: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T",
    VersionedTransactionCtor: makeFakeVersionedTransactionCtor(),
    ladder: [30],
    sleepImpl: async () => {},
  });
  assert.equal(result.messageMeasurement.fits, true);
  assert.equal(result.messageMeasurement.byteLength, 935 - 65);
});
