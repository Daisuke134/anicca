// acquire-nos.mjs — S2 of "agent financial independence": Franklin swaps its OWN SOL for NOS on
// Solana mainnet, with ZERO human step, so it can later pay its own Nosana compute rent (S1,
// ../deploy.mjs). Reuses the SAME identity resolution and money-safety discipline as S1:
//   - identity: skills/earn/lib/resolve-identity.mjs's resolveSolanaSecret + ../keypair.mjs's
//     deriveAddressFromSecret. Deliberately NOT ../keypair.mjs's ensureNosanaKeypair — that
//     materializes a JSON-array keypair FILE for the nosana CLI to shell out to; this module signs
//     an @solana/web3.js VersionedTransaction directly in-process, so only the decoded
//     {address, secretBytes} pair is needed, never a second wallet, never a file.
//   - cap/gate style: mirrors ../spend-gate.mjs's shape (pure functions, {allowed, reason} return,
//     fail-closed on any missing/non-finite number) re-expressed for a SOL-denominated per-swap
//     spend cap instead of spend-gate.mjs's USD-denominated per-job cap — a genuinely different
//     domain (buying NOS vs. spending NOS), so this is a parallel re-expression, not an import.
//   - ledger: appends to TWO new JSONL files (nosana-funding-intents.jsonl, nosana-funding.jsonl)
//     via the EXACT SAME primitives deploy.mjs already uses — ../../spawn/lib/ledger.js's
//     appendChild + ../../spawn/lib/state-path.js's resolveStateDir. This is not a third ledger
//     convention: deploy.mjs itself already splits "pre-send intent" (nosana-deploy-intents.jsonl)
//     from "settled spend" (shelter-cost.jsonl) across two files through this same ledger.js. A
//     NOS *purchase* is not a Nosana lease cost (shelter-cost-ledger.js's schema is specifically
//     `{ts, settledLeaseCostUsd, jobAddress}` for compute rent), so it gets its own two files
//     under the same convention rather than being shoehorned into that schema.
//
// Jupiter endpoints used (verified live 2026-07-25, see this feature's PR/report for the exact
// doc lines quoted from jup-ag/docs):
//   GET  https://api.jup.ag/swap/v2/quote   — route + priceImpactPct + otherAmountThreshold
//   POST https://api.jup.ag/swap/v2/swap    — base64 unsigned VersionedTransaction from a quote
//   GET  https://api.jup.ag/price/v3        — USD price per mint
// All three are served KEYLESS (no x-api-key, no signup) at 0.5 req/s on api.jup.ag — jup-ag/docs
// portal/setup.mdx: "You can start making requests to api.jup.ag immediately - no sign-up
// required. Keyless requests are rate-limited to 0.5 RPS, which is ideal for testing,
// prototyping, or AI agent use cases." This is what makes ZERO-human-step funding possible: no
// portal account, no API key, no captcha, no email.
//
// --dry is the DEFAULT (spec hard constraint 1): every step below runs for real — identity,
// balances, a real quote, a real unsigned-transaction build, the combined spend/slippage/floor
// gate — then the function returns BEFORE signing or sending. Only live:true signs and sends.

import path from "node:path";
import bs58 from "bs58";
import { resolveSolanaSecret } from "../../../../earn/lib/resolve-identity.mjs";
import { deriveAddressFromSecret } from "../keypair.mjs";
import { NOS_MINT } from "../market.mjs";
import { DEFAULT_RPC_URL } from "../deploy.mjs";
import { appendChild } from "../../../spawn/lib/ledger.js";
import { resolveStateDir } from "../../../spawn/lib/state-path.js";

export const SOL_MINT = "So11111111111111111111111111111111111111112";
export const LAMPORTS_PER_SOL = 1_000_000_000;
// NOS mint decimals — static token metadata, not returned by /quote. Verified ground truth
// 2026-07-25 (task spec); hardcoding a known mint's decimals is standard practice.
export const NOS_DECIMALS = 6;

export const JUP_QUOTE_URL = "https://api.jup.ag/swap/v2/quote";
export const JUP_SWAP_URL = "https://api.jup.ag/swap/v2/swap";
export const JUP_PRICE_URL_BASE = "https://api.jup.ag/price/v3";

// Hard constraint 2: default max spend per swap, overridable by env, additionally hard-capped at
// 25% of the wallet's SOL balance (see resolveSpendLamports — the smaller of the two always wins).
export const DEFAULT_MAX_SPEND_SOL = 0.01;
export const DEFAULT_MAX_SPEND_FRACTION_OF_BALANCE = 0.25;
// Keep at least this much SOL after the swap (spend + estimated priority fee) for future tx fees.
export const DEFAULT_SOL_FEE_FLOOR_SOL = 0.02;
// Hard constraint 3: slippage + price-impact ceilings. priceImpactPct from Jupiter is a fraction
// (verified live: "0.00497..." for a real SOL->NOS quote == 0.497%, NOT 0.497 as an already-scaled
// percentage), so DEFAULT_MAX_PRICE_IMPACT_PCT is expressed on the same fractional scale.
export const DEFAULT_MAX_SLIPPAGE_BPS = 100;
export const DEFAULT_MAX_PRICE_IMPACT_PCT = 0.02;

// Transaction-size guard. TWO DISTINCT ceilings were found in this feature (confirmed via forced
// repros + two real --live failures — see this feature's report for both stack traces):
//
// (1) @solana/web3.js's `MessageV0.serialize()` allocates a FIXED `new Uint8Array(PACKET_DATA_SIZE)`
//     scratch buffer internally (lib/index.cjs.js: `const PACKET_DATA_SIZE = 1280 - 40 - 8;` =
//     1232, then `const serializedMessage = new Uint8Array(PACKET_DATA_SIZE);`), and
//     `VersionedTransaction.sign()` calls `this.message.serialize()` BEFORE it ever computes a
//     signature. An extremely oversized message can overflow THIS buffer and throw
//     `RangeError: encoding overruns Uint8Array` from `@solana/buffer-layout` — this hit a real
//     --live run first.
// (2) The REAL wire/RPC limit (also 1232 bytes, but this time correctly understood) applies to the
//     WHOLE TRANSACTION — `shortvec(numSignatures) + 64*numSignatures + message` — not the message
//     alone. A second real --live run got PAST `.sign()` (so ceiling (1) was fine) and then failed
//     at `sendRawTransaction`'s local simulation: `"...VersionedTransaction too large: 1660 bytes
//     (max: encoded/raw 1644/1232)."` A message the FIRST guard measured as 1180 bytes (deemed
//     "safe", under its 1180-byte message-only limit) produced a 1+64+1180=1245-byte transaction —
//     already 13 bytes over the 1232 wall. The first guard's "safe margin" was on the wrong object
//     entirely: a message limit with NO headroom carved out for the 65-byte signature+shortvec
//     wrapper is structurally wrong, not merely loose.
//
// Verified empirically (see this feature's report) across multiple real Jupiter responses:
// `Buffer.from(built.swapTransaction, "base64").length` (the decoded artifact Jupiter ALREADY
// returns, zero-signature-placeholder and all) is EXACTLY `1 + 64*numRequiredSignatures +
// message.serialize().length`, and `built.swapTransaction.length` is exactly that raw length's
// base64 encoding (`Math.ceil(rawBytes/3)*4`). So THE gate below measures the real returned
// artifact directly — no arithmetic, no assumption about numRequiredSignatures, no separate
// message measurement required to decide pass/fail. A passing artifact-level check (safely under
// 1232) also structurally guarantees the message alone is well under 1232 too (it is always
// smaller than the whole transaction by construction), so ceiling (1) can never fire once ceiling
// (2) is the actual gate — `measureUnsignedTransactionMessageBytes` below is kept only for an
// informational log line, exactly as instructed: "it must not be the gate."
export const RAW_TRANSACTION_HARD_BYTE_LIMIT = 1232; // Solana's PACKET_DATA_SIZE — the true wire wall, applies to the WHOLE signed transaction.
export const BASE64_TRANSACTION_HARD_CHAR_LIMIT = 1644; // Math.ceil(1232/3)*4 — matches the RPC's own stated "encoded" max verbatim.
export const DEFAULT_TRANSACTION_SAFE_BYTE_LIMIT = 1200; // ~32-byte margin under the 1232 raw wall, on the REAL transaction artifact.
// Kept for backward-compat/logging only — NOT the gate (see the doc block above).
export const MESSAGE_HARD_BYTE_LIMIT = 1232;
export const DEFAULT_MESSAGE_SAFE_BYTE_LIMIT = 1180;
// Verified 2026-07-25: jup-ag/docs swap/advanced/reduce-transaction-size.mdx documents
// `maxAccounts` for `/swap/v2/build`: "Set maxAccounts (1-64, default 64) to limit the number of
// accounts in the swap route. Lower values produce simpler routes with fewer accounts." That page
// is written for /build; the endpoint this module actually calls is /swap/v2/quote (the
// hidden-but-live "quote-and-swap" flow — see the module header), whose OWN documented query
// parameter table does not list maxAccounts. Empirically verified live 2026-07-25 that
// /swap/v2/quote honors it anyway, same pair/amount, nothing else changed: no maxAccounts -> 5
// hops / 20 static keys / 1157 raw tx bytes; maxAccounts=20 -> 4 hops / 19 keys / 1072 bytes. This
// is the only size-affecting lever used below — never an invented/undocumented query parameter.
// RE-TUNED after the second real failure: with maxAccounts=default, the message came in at
// 1180-1198 bytes across consecutive real runs — i.e. the FULL transaction (message+65) was over
// the 1232 wall essentially every time. `undefined` is no longer the first rung (it would just
// burn a rate-limited round trip almost every run); the ladder now starts at maxAccounts=30, which
// produced a comfortably-fitting 974-byte message (1+64+974=1039 raw) in this feature's own
// earlier measurement, with tighter rungs below it as a bounded fallback.
export const SIZE_GUARD_MAX_ACCOUNTS_LADDER = [30, 20, 12];

function log(line) {
  // Every call site below passes a static/numeric/public-address string — this module NEVER
  // logs secretBytes, the base58 secret, or anything decoded from it (constraint 6).
  process.stdout.write(`[citizen-fund] ${line}\n`);
}

// ---------------------------------------------------------------------------------------------
// Pure: spend resolution + gates. No I/O — every input is already-fetched data.
// ---------------------------------------------------------------------------------------------

/**
 * Pure: resolve how many lamports this swap will spend. The 25%-of-balance hard cap (spec hard
 * constraint 2) always wins over the configured/default max-spend if it is smaller — this is an
 * unconditional CLAMP, not a refusal; evaluateFundingGate is what refuses (e.g. when even the
 * clamped amount would breach the fee floor). Never throws on a legitimately tiny/zero result —
 * callers must check `spendLamports <= 0` themselves and refuse to proceed.
 */
export function resolveSpendLamports({
  requestedSol,
  solBalanceLamports,
  maxFraction = DEFAULT_MAX_SPEND_FRACTION_OF_BALANCE,
}) {
  if (typeof requestedSol !== "number" || !Number.isFinite(requestedSol) || requestedSol <= 0) {
    throw new Error("resolveSpendLamports: requestedSol must be a positive finite number");
  }
  if (typeof solBalanceLamports !== "number" || !Number.isFinite(solBalanceLamports) || solBalanceLamports < 0) {
    throw new Error("resolveSpendLamports: solBalanceLamports must be a non-negative finite number");
  }
  const requestedLamports = Math.floor(requestedSol * LAMPORTS_PER_SOL);
  const hardCapLamports = Math.floor(solBalanceLamports * maxFraction);
  const spendLamports = Math.max(Math.min(requestedLamports, hardCapLamports), 0);
  return {
    spendLamports,
    requestedLamports,
    hardCapLamports,
    hardCapApplied: hardCapLamports < requestedLamports,
  };
}

/**
 * Pure: structural validation of a Jupiter QuoteResponse. Returns {valid, reason} rather than
 * throwing so evaluateFundingGate can fold it into a single gate reason. A missing/malformed
 * quote is NEVER treated as acceptable (spec hard constraint 3: fail closed on any quote failure).
 */
export function validateQuoteShape(quote) {
  if (!quote || typeof quote !== "object") {
    return { valid: false, reason: "quote is missing or not an object" };
  }
  const outAmount = Number(quote.outAmount);
  const otherAmountThreshold = Number(quote.otherAmountThreshold);
  if (!Number.isFinite(outAmount) || outAmount <= 0) {
    return { valid: false, reason: "quote.outAmount is missing or non-positive" };
  }
  if (!Number.isFinite(otherAmountThreshold) || otherAmountThreshold <= 0) {
    return { valid: false, reason: "quote.otherAmountThreshold is missing or non-positive" };
  }
  if (typeof quote.priceImpactPct !== "string" && typeof quote.priceImpactPct !== "number") {
    return { valid: false, reason: "quote.priceImpactPct is missing" };
  }
  return { valid: true, reason: "quote shape OK" };
}

/**
 * Pure: parse Jupiter's priceImpactPct (a decimal-string fraction) into a Number. Throws (fails
 * closed) rather than defaulting an unparseable value to 0% impact.
 */
export function parsePriceImpactPct(quote) {
  const raw = quote && quote.priceImpactPct;
  if (typeof raw !== "string" && typeof raw !== "number") {
    throw new Error("parsePriceImpactPct: quote.priceImpactPct is missing — refusing to treat as zero impact");
  }
  const n = Number(raw);
  if (!Number.isFinite(n)) {
    throw new Error(`parsePriceImpactPct: quote.priceImpactPct "${raw}" is not a finite number`);
  }
  return n;
}

/**
 * Pure: the single combined preflight gate acquireNos consults before any spend — quote validity,
 * slippage ceiling, price-impact ceiling (spec hard constraint 3), and the post-swap SOL floor
 * (spec hard constraint 2). Fails closed on any missing/non-finite number rather than treating
 * "unknown" as "safe to spend". Mirrors ../spend-gate.mjs's evaluateSpendGate shape/spirit.
 *
 * @returns {{allowed: boolean, reason: string}}
 */
export function evaluateFundingGate({
  spendLamports,
  solBalanceLamports,
  feeLamportsEstimate,
  floorLamports = Math.floor(DEFAULT_SOL_FEE_FLOOR_SOL * LAMPORTS_PER_SOL),
  quote,
  slippageBps,
  maxSlippageBps = DEFAULT_MAX_SLIPPAGE_BPS,
  maxPriceImpactPct = DEFAULT_MAX_PRICE_IMPACT_PCT,
}) {
  if (typeof spendLamports !== "number" || !Number.isFinite(spendLamports) || spendLamports <= 0) {
    return { allowed: false, reason: "spendLamports must be a positive number (fail-closed)" };
  }

  const shape = validateQuoteShape(quote);
  if (!shape.valid) {
    return { allowed: false, reason: `refusing: ${shape.reason} (fail-closed — a missing/invalid quote is never acceptable)` };
  }

  if (typeof slippageBps !== "number" || !Number.isFinite(slippageBps) || slippageBps < 0) {
    return { allowed: false, reason: "slippageBps must be a non-negative number (fail-closed)" };
  }
  if (slippageBps > maxSlippageBps) {
    return { allowed: false, reason: `slippageBps ${slippageBps} exceeds max allowed ${maxSlippageBps}` };
  }

  let priceImpactPct;
  try {
    priceImpactPct = parsePriceImpactPct(quote);
  } catch (err) {
    return { allowed: false, reason: `refusing: ${err.message}` };
  }
  if (priceImpactPct > maxPriceImpactPct) {
    return {
      allowed: false,
      reason: `price impact ${(priceImpactPct * 100).toFixed(3)}% exceeds ceiling ${(maxPriceImpactPct * 100).toFixed(2)}% — pool too thin for this size`,
    };
  }

  if (typeof solBalanceLamports !== "number" || !Number.isFinite(solBalanceLamports)) {
    return { allowed: false, reason: "solBalanceLamports is unavailable (fail-closed)" };
  }
  if (typeof feeLamportsEstimate !== "number" || !Number.isFinite(feeLamportsEstimate) || feeLamportsEstimate < 0) {
    return { allowed: false, reason: "feeLamportsEstimate is unavailable (fail-closed)" };
  }
  const postSwapLamports = solBalanceLamports - spendLamports - feeLamportsEstimate;
  if (postSwapLamports < floorLamports) {
    return {
      allowed: false,
      reason: `post-swap SOL balance ${(postSwapLamports / LAMPORTS_PER_SOL).toFixed(6)} would fall below the fee floor ${(floorLamports / LAMPORTS_PER_SOL).toFixed(6)}`,
    };
  }

  return { allowed: true, reason: "within spend cap, slippage/price-impact ceilings, and above the fee floor" };
}

// ---------------------------------------------------------------------------------------------
// Pure: cost math.
// ---------------------------------------------------------------------------------------------

/** Pure: NOS amounts (expected + worst-case-after-slippage) from a validated quote. */
export function computeExpectedNosOut(quote) {
  const shape = validateQuoteShape(quote);
  if (!shape.valid) {
    throw new Error(`computeExpectedNosOut: ${shape.reason}`);
  }
  return {
    expectedNos: Number(quote.outAmount) / 10 ** NOS_DECIMALS,
    minNos: Number(quote.otherAmountThreshold) / 10 ** NOS_DECIMALS,
  };
}

/** Pure: USD-denominated summary for logging + the ledger record. Fails closed on bad inputs. */
export function computeSpendSummary({ spendLamports, solUsdPrice, nosUsdPrice, expectedNos }) {
  for (const [key, value] of Object.entries({ spendLamports, solUsdPrice, nosUsdPrice, expectedNos })) {
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
      throw new Error(`computeSpendSummary: ${key} must be a non-negative finite number, got ${value}`);
    }
  }
  const spendSol = spendLamports / LAMPORTS_PER_SOL;
  return {
    spendSol,
    spendUsd: spendSol * solUsdPrice,
    expectedNos,
    expectedNosUsd: expectedNos * nosUsdPrice,
  };
}

// ---------------------------------------------------------------------------------------------
// Pure: transaction-size guard. Measures whether an unsigned transaction's MESSAGE (the part
// VersionedTransaction.sign() serializes internally before ever computing a signature) fits
// inside Solana's 1232-byte packet limit — WITHOUT ever calling .sign(). See
// MESSAGE_HARD_BYTE_LIMIT's doc comment above for the exact root-caused failure this guards.
// ---------------------------------------------------------------------------------------------

/**
 * Pure(ish) — takes no I/O, but calling `.message.serialize()` can itself throw (that IS the
 * measurement): measure an unsigned VersionedTransaction's real serialized message byte length
 * WITHOUT calling `.sign()`. This deliberately reuses the exact same call
 * (`unsignedTx.message.serialize()`) that `VersionedTransaction.sign()` makes internally — the
 * only reliable way to know whether a message fits is to run the real serializer, since
 * reimplementing Solana's compact-array wire format by hand to "predict" the size risks being
 * subtly wrong. A caught error here means "does not fit"; it can never mean "signing is safe".
 *
 * @returns {{fits: boolean, byteLength: number|null, error: string|null}}
 */
export function measureUnsignedTransactionMessageBytes(unsignedTx) {
  try {
    const bytes = unsignedTx.message.serialize();
    return { fits: true, byteLength: bytes.length, error: null };
  } catch (err) {
    return { fits: false, byteLength: null, error: (err && err.message) || String(err) };
  }
}

/**
 * Pure: {allowed, reason} verdict from a measurement — refuses (never signs) when the message
 * either failed to serialize at all, or serialized but exceeds the configured safe margin under
 * the hard 1232-byte wall.
 */
export function evaluateMessageSizeGuard({ measurement, safeLimit = DEFAULT_MESSAGE_SAFE_BYTE_LIMIT }) {
  if (!measurement || measurement.fits !== true || typeof measurement.byteLength !== "number") {
    return {
      allowed: false,
      reason: `message could not be serialized (${(measurement && measurement.error) || "unknown error"}) — refusing to sign (fail-closed)`,
    };
  }
  if (measurement.byteLength > safeLimit) {
    return {
      allowed: false,
      reason: `measured message size ${measurement.byteLength} bytes exceeds the safe limit ${safeLimit} bytes (hard packet limit ${MESSAGE_HARD_BYTE_LIMIT} bytes) — refusing to sign`,
    };
  }
  return {
    allowed: true,
    reason: `measured message size ${measurement.byteLength} bytes is within the safe limit ${safeLimit} bytes`,
  };
}

/** Pure: the maxAccounts value to request on a given (0-indexed) size-guard attempt, bounded to the last rung of the ladder. */
export function pickSizeGuardMaxAccounts(attempt, ladder = SIZE_GUARD_MAX_ACCOUNTS_LADDER) {
  const index = Math.min(Math.max(attempt, 0), ladder.length - 1);
  return ladder[index];
}

/**
 * Pure: measure the REAL transaction artifact Jupiter already returned — no deserialization, no
 * arithmetic, no assumption about numRequiredSignatures. `swapTransactionBase64` is the exact
 * base64 string `/swap/v2/swap` hands back, decoded to the exact byte length `sendRawTransaction`
 * will judge. This IS the gate (see RAW_TRANSACTION_HARD_BYTE_LIMIT's doc comment for why the
 * previous message-only measurement was wrong).
 *
 * @returns {{rawBytes: number|null, base64Chars: number|null, error: string|null}}
 */
export function measureTransactionArtifact(swapTransactionBase64) {
  if (typeof swapTransactionBase64 !== "string" || swapTransactionBase64.length === 0) {
    return { rawBytes: null, base64Chars: null, error: "swapTransactionBase64 is missing or empty" };
  }
  try {
    const raw = Buffer.from(swapTransactionBase64, "base64");
    return { rawBytes: raw.length, base64Chars: swapTransactionBase64.length, error: null };
  } catch (err) {
    return { rawBytes: null, base64Chars: swapTransactionBase64.length, error: (err && err.message) || String(err) };
  }
}

/**
 * Pure: {allowed, reason} verdict on the REAL transaction artifact — THE gate
 * buildRightSizedSwapTransaction consults before ever deserializing/signing. Checks the raw byte
 * length against Solana's hard wire limit AND the base64 char length against the RPC's own stated
 * encoded limit (redundant with the raw check by construction, kept as an explicit second signal
 * because that is literally the phrasing the real RPC rejection used), then the configured safety
 * margin under the raw hard limit.
 */
export function evaluateTransactionSizeGuard({
  measurement,
  safeRawLimit = DEFAULT_TRANSACTION_SAFE_BYTE_LIMIT,
  hardRawLimit = RAW_TRANSACTION_HARD_BYTE_LIMIT,
  hardBase64Limit = BASE64_TRANSACTION_HARD_CHAR_LIMIT,
}) {
  if (!measurement || typeof measurement.rawBytes !== "number" || measurement.error) {
    return {
      allowed: false,
      reason: `transaction artifact could not be measured (${(measurement && measurement.error) || "unknown error"}) — refusing to sign (fail-closed)`,
    };
  }
  if (measurement.rawBytes > hardRawLimit) {
    return {
      allowed: false,
      reason: `raw transaction size ${measurement.rawBytes} bytes exceeds Solana's hard wire limit ${hardRawLimit} bytes — refusing to sign`,
    };
  }
  if (typeof measurement.base64Chars === "number" && measurement.base64Chars > hardBase64Limit) {
    return {
      allowed: false,
      reason: `base64-encoded transaction ${measurement.base64Chars} chars exceeds the RPC's encoded limit ${hardBase64Limit} chars — refusing to sign`,
    };
  }
  if (measurement.rawBytes > safeRawLimit) {
    return {
      allowed: false,
      reason: `raw transaction size ${measurement.rawBytes} bytes exceeds the safe margin ${safeRawLimit} bytes (hard wire limit ${hardRawLimit} bytes) — refusing to sign`,
    };
  }
  return {
    allowed: true,
    reason: `raw transaction size ${measurement.rawBytes} bytes (base64 ${measurement.base64Chars} chars) is within the safe margin ${safeRawLimit} bytes`,
  };
}

// ---------------------------------------------------------------------------------------------
// Pure: signature + settlement classification (the at-most-once / never-blind-retry core).
// ---------------------------------------------------------------------------------------------

/**
 * Pure: recover the base58 transaction signature from an already-signed VersionedTransaction.
 * Solana/ed25519 signing is deterministic given the same message + key, so this signature is
 * fixed and known BEFORE the transaction is ever broadcast — that is what makes at-most-once
 * reconciliation possible (constraint 4): we can always look this exact signature up later,
 * regardless of whether the send call itself succeeded, threw, or timed out.
 */
export function transactionSignatureBase58(signedTx) {
  if (!signedTx || !Array.isArray(signedTx.signatures) || signedTx.signatures.length === 0) {
    throw new Error("transactionSignatureBase58: signedTx has no signatures array");
  }
  const sig = signedTx.signatures[0];
  if (!sig || sig.length === 0 || [...sig].every((b) => b === 0)) {
    throw new Error("transactionSignatureBase58: transaction is not signed yet");
  }
  return bs58.encode(sig);
}

/** Pure: classify one connection.getSignatureStatuses(...) entry. */
export function decideSettlementFromStatus(statusEntry) {
  if (!statusEntry) return { outcome: "not-found" };
  if (statusEntry.err) return { outcome: "failed-onchain", err: statusEntry.err };
  const level = statusEntry.confirmationStatus;
  if (level === "confirmed" || level === "finalized") return { outcome: "confirmed" };
  return { outcome: "pending" };
}

/**
 * I/O (fully injected, no real network by default): poll getSignatureStatusesImpl until the
 * signature lands, fails on-chain, the quote's blockhash expires, or timeoutMs elapses. Every
 * dependency (status lookup, block height, sleep, clock) is injected so this is unit-testable
 * with fake timers — no real waiting in tests.
 */
export async function pollForConfirmation({
  signature,
  lastValidBlockHeight,
  getSignatureStatusesImpl,
  getBlockHeightImpl,
  sleepImpl,
  now = () => Date.now(),
  pollIntervalMs = 2000,
  timeoutMs = 60000,
}) {
  const start = now();
  // eslint-disable-next-line no-constant-condition
  while (true) {
    let statusEntry = null;
    try {
      const res = await getSignatureStatusesImpl([signature]);
      statusEntry = res && res.value && res.value[0];
    } catch {
      statusEntry = null; // RPC hiccup — keep polling, never treat as "not landed" or "landed".
    }
    const decided = decideSettlementFromStatus(statusEntry);
    if (decided.outcome === "confirmed" || decided.outcome === "failed-onchain") {
      return decided;
    }
    if (typeof lastValidBlockHeight === "number") {
      try {
        const height = await getBlockHeightImpl();
        if (typeof height === "number" && height > lastValidBlockHeight) {
          return { outcome: "expired" };
        }
      } catch {
        // ignore — fall through and keep polling until timeout
      }
    }
    if (now() - start >= timeoutMs) {
      return { outcome: "timeout" };
    }
    await sleepImpl(pollIntervalMs);
  }
}

/**
 * At-most-once reconciliation for a swap whose outcome is UNKNOWN after send (timeout, expired
 * blockhash, or an RPC error on send itself) — spec hard constraint 4. This function NEVER sends
 * anything: every injected dependency is read-only, so it is structurally incapable of retrying
 * the swap, not just policy-incapable. Checks, in order of authority:
 *   1. getSignatureStatuses for the EXACT signature (deterministic — known before send).
 *   2. getSignaturesForAddress as a fallback (covers an RPC whose status index already rolled the
 *      slot off but whose recent-signatures list still has it).
 *   3. The real on-chain NOS balance delta, as the ultimate ground truth if both signature lookups
 *      come back empty.
 * Idempotent: re-running this against the same real on-chain state returns the same verdict.
 */
export async function reconcileUnknownOutcome({
  signature,
  preNosBalance,
  getSignatureStatusesImpl,
  getSignaturesForAddressImpl,
  getNosBalanceImpl,
}) {
  let statusEntry = null;
  try {
    const res = await getSignatureStatusesImpl([signature]);
    statusEntry = res && res.value && res.value[0];
  } catch {
    statusEntry = null;
  }
  const fromStatus = decideSettlementFromStatus(statusEntry);
  if (fromStatus.outcome === "confirmed" || fromStatus.outcome === "failed-onchain") {
    return { ...fromStatus, source: "getSignatureStatuses", retried: false };
  }

  let foundInRecent = false;
  try {
    const recent = await getSignaturesForAddressImpl();
    foundInRecent = Array.isArray(recent) && recent.some((r) => r && r.signature === signature && !r.err);
  } catch {
    foundInRecent = false;
  }
  if (foundInRecent) {
    return { outcome: "confirmed", source: "getSignaturesForAddress", retried: false };
  }

  let postNosBalance = null;
  try {
    postNosBalance = await getNosBalanceImpl();
  } catch {
    postNosBalance = null;
  }
  const nosDelta =
    typeof postNosBalance === "number" && typeof preNosBalance === "number" ? postNosBalance - preNosBalance : null;
  if (typeof nosDelta === "number" && nosDelta > 0) {
    return { outcome: "confirmed", source: "nos-balance-delta", nosDelta, retried: false };
  }

  return {
    outcome: "unknown-unresolved",
    source: "none",
    nosDelta,
    retried: false,
    reason: `swap outcome for ${signature} could not be confirmed by signature status, recent signatures, or a NOS balance increase — refusing to blind-retry; reconcile manually (e.g. https://solscan.io/tx/${signature}) before any further action`,
  };
}

// ---------------------------------------------------------------------------------------------
// Pure: ledger record shaping (kept out of inline object literals so a test can assert no record
// ever contains secret material, and so the record shape is documented in one place).
// ---------------------------------------------------------------------------------------------

export function buildFundingIntentRecord({
  ts,
  intentId,
  address,
  spendLamports,
  spendSol,
  quote,
  expectedNos,
  minNos,
  signature,
  slippageBps,
  priceImpactPct,
}) {
  return {
    ts,
    intentId,
    status: "intent",
    address,
    spendLamports,
    spendSol,
    quoteOutAmount: quote.outAmount,
    quoteOtherAmountThreshold: quote.otherAmountThreshold,
    priceImpactPct,
    slippageBps,
    expectedNos,
    minNos,
    signature,
  };
}

export function buildFundingSettledRecord({
  ts,
  intentId,
  address,
  signature,
  spendLamports,
  spendSol,
  spendUsd,
  nosReceived,
  nosUsdPrice,
  solUsdPrice,
  outcome,
  source,
}) {
  return {
    ts,
    intentId,
    status: "settled",
    address,
    signature,
    spendLamports,
    spendSol,
    spendUsd,
    nosReceived,
    nosUsdPrice,
    solUsdPrice,
    outcome,
    source,
  };
}

// ---------------------------------------------------------------------------------------------
// I/O: Jupiter HTTP calls. fetchImpl is injected (default global fetch) so tests never hit the
// network. All fail closed (throw) on any HTTP/shape problem — never return a fabricated quote or
// a 0/undefined price (spec hard constraint 3).
// ---------------------------------------------------------------------------------------------

/**
 * Keyless-tier Jupiter APIs are rate-limited to 0.5 req/s (jup-ag/docs portal/plans.mdx:
 * "You can make requests without an API key at 0.5 requests per second"). A 429 here is an
 * ordinary rate-limit backoff situation for an idempotent READ (quote/price/build-tx) — this is
 * NOT the "never blind-retry the swap" prohibition, which applies only to re-sending an already
 * signed transaction. Retrying a GET/POST that mutates no on-chain state is standard practice.
 */
async function fetchWithBackoff(fetchImpl, url, options, { retries = 4, backoffMs = 2200 } = {}) {
  let lastRes = null;
  for (let attempt = 0; attempt <= retries; attempt++) {
    lastRes = await fetchImpl(url, options);
    if (lastRes && lastRes.status === 429 && attempt < retries) {
      await new Promise((resolve) => setTimeout(resolve, backoffMs));
      continue;
    }
    return lastRes;
  }
  return lastRes;
}

/**
 * @param {object} opts
 * @param {number} [opts.maxAccounts] — optional 1-64 cap on route account count (see
 *   SIZE_GUARD_MAX_ACCOUNTS_LADDER's doc comment for the doc citation + empirical verification
 *   that this documented-for-/build parameter is also honored by /swap/v2/quote). Omitted from
 *   the URL entirely when not a finite number, matching Jupiter's own documented default of 64.
 */
export async function fetchQuote({ fetchImpl = fetch, spendLamports, slippageBps, maxAccounts }) {
  let url = `${JUP_QUOTE_URL}?inputMint=${SOL_MINT}&outputMint=${NOS_MINT}&amount=${spendLamports}&slippageBps=${slippageBps}`;
  if (typeof maxAccounts === "number" && Number.isFinite(maxAccounts)) {
    url += `&maxAccounts=${Math.max(1, Math.min(64, Math.floor(maxAccounts)))}`;
  }
  const res = await fetchWithBackoff(fetchImpl, url);
  if (!res || !res.ok) {
    throw new Error(`fetchQuote: HTTP ${res && res.status} from Jupiter /swap/v2/quote (fail-closed)`);
  }
  const quote = await res.json();
  const shape = validateQuoteShape(quote);
  if (!shape.valid) {
    throw new Error(`fetchQuote: ${shape.reason} (fail-closed)`);
  }
  return quote;
}

export async function buildUnsignedSwapTransaction({ fetchImpl = fetch, quote, takerAddress }) {
  const res = await fetchWithBackoff(fetchImpl, JUP_SWAP_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quoteResponse: quote, taker: takerAddress }),
  });
  if (!res || !res.ok) {
    throw new Error(`buildUnsignedSwapTransaction: HTTP ${res && res.status} from Jupiter /swap/v2/swap (fail-closed)`);
  }
  const data = await res.json();
  if (!data || typeof data.swapTransaction !== "string" || data.swapTransaction.length === 0) {
    throw new Error("buildUnsignedSwapTransaction: no swapTransaction returned (fail-closed)");
  }
  return {
    swapTransactionBase64: data.swapTransaction,
    lastValidBlockHeight: data.lastValidBlockHeight,
    prioritizationFeeLamports: typeof data.prioritizationFeeLamports === "number" ? data.prioritizationFeeLamports : 0,
    computeUnitPrice: data.computeUnitPrice,
  };
}

/**
 * Build a right-sized unsigned swap transaction, retrying with a progressively tighter
 * `maxAccounts` constraint (SIZE_GUARD_MAX_ACCOUNTS_LADDER) whenever the built transaction's
 * message does not fit inside Solana's 1232-byte packet limit (MESSAGE_HARD_BYTE_LIMIT).
 *
 * Money-safety property: this function ONLY fetches quotes and builds unsigned transactions —
 * every attempt is a fresh, read-only HTTP round-trip. It never signs (no keypair is even passed
 * in) and never writes an intent record (no ledger dependency is passed in either) — so by
 * construction, no number of retries here can ever produce two broadcasts, two signatures, or two
 * intent records. The caller (acquireNos) only signs/records AFTER this returns successfully,
 * exactly once, for the single winning attempt.
 *
 * Throws (fail-closed) if every rung of the ladder is exhausted without a transaction that fits —
 * "refusing is correct behavior; signing something that cannot serialize is not."
 *
 * @param {(attempt: number, info: object) => void} [onAttempt] optional per-attempt log callback.
 */
export async function buildRightSizedSwapTransaction({
  fetchImpl = fetch,
  spendLamports,
  slippageBps,
  takerAddress,
  VersionedTransactionCtor,
  ladder = SIZE_GUARD_MAX_ACCOUNTS_LADDER,
  safeRawLimit = DEFAULT_TRANSACTION_SAFE_BYTE_LIMIT,
  onAttempt,
  // Keyless Jupiter APIs share one 0.5 req/s bucket across /quote AND /swap (portal/plans.mdx —
  // see the module header). Each attempt already makes 2 calls; without spacing BETWEEN attempts,
  // a fetch-level 429 (already retried internally by fetchWithBackoff) can still exhaust that
  // helper's own retry budget and surface as a same-named "attempt failed" outcome as a genuine
  // size overrun — which would misleadingly burn a ladder rung for a rate-limit problem, not a
  // size problem. Sleeping between rungs is injectable (no-op in tests) purely to avoid real waits.
  interAttemptSleepMs = 2500,
  sleepImpl = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
}) {
  let lastReason = "no attempts made";
  for (let attempt = 0; attempt < ladder.length; attempt++) {
    if (attempt > 0) {
      await sleepImpl(interAttemptSleepMs);
    }
    const maxAccounts = pickSizeGuardMaxAccounts(attempt, ladder);
    let quote;
    let built;
    try {
      quote = await fetchQuote({ fetchImpl, spendLamports, slippageBps, maxAccounts });
      built = await buildUnsignedSwapTransaction({ fetchImpl, quote, takerAddress });
    } catch (err) {
      // A fetch/HTTP failure (e.g. a 429 that outlasted fetchWithBackoff's own retries) is NOT
      // the same fact as "this route is too big" — kept as a distinct errorKind so the log line
      // never conflates "we got rate-limited" with "the transaction would not have fit".
      lastReason = `attempt ${attempt} (maxAccounts=${maxAccounts ?? "default"}) failed to fetch a quote/transaction: ${err.message}`;
      if (onAttempt) onAttempt(attempt, { maxAccounts, ok: false, errorKind: "fetch", measurement: null, reason: lastReason });
      continue;
    }
    // THE gate: measure the REAL artifact Jupiter returned — this is what sendRawTransaction's
    // local simulation actually enforces (see RAW_TRANSACTION_HARD_BYTE_LIMIT's doc comment for
    // the real RPC rejection a message-only check missed). No deserialization needed to decide
    // pass/fail here at all.
    const measurement = measureTransactionArtifact(built.swapTransactionBase64);
    const guard = evaluateTransactionSizeGuard({ measurement, safeRawLimit });
    if (!guard.allowed) {
      lastReason = guard.reason;
      if (onAttempt) onAttempt(attempt, { maxAccounts, ok: false, errorKind: "size", measurement, reason: guard.reason });
      continue;
    }
    // Only deserialize once we have a WINNING candidate — a passing artifact-level measurement
    // structurally guarantees the message alone (always smaller than the whole transaction) fits
    // too, so this deserialize+message-measure step is purely informational (logged, never gates).
    const unsignedTx = VersionedTransactionCtor.deserialize(Buffer.from(built.swapTransactionBase64, "base64"));
    const messageMeasurement = measureUnsignedTransactionMessageBytes(unsignedTx);
    if (onAttempt) onAttempt(attempt, { maxAccounts, ok: true, errorKind: null, measurement, messageMeasurement, reason: guard.reason });
    return { quote, built, unsignedTx, measurement, messageMeasurement, attempt, maxAccountsUsed: maxAccounts };
  }
  throw new Error(
    `buildRightSizedSwapTransaction: exhausted ${ladder.length} size-guard attempt(s) — no route fit within the safe limit; ` +
      `refusing to sign (fail-closed). Last reason: ${lastReason}`,
  );
}

export async function fetchMintUsdPrice({ mint, fetchImpl = fetch }) {
  const res = await fetchWithBackoff(fetchImpl, `${JUP_PRICE_URL_BASE}?ids=${mint}`);
  if (!res || !res.ok) {
    throw new Error(`fetchMintUsdPrice: HTTP ${res && res.status} fetching price (fail-closed)`);
  }
  const data = await res.json();
  const usdPrice = data && data[mint] && data[mint].usdPrice;
  if (typeof usdPrice !== "number" || !Number.isFinite(usdPrice) || usdPrice <= 0) {
    throw new Error("fetchMintUsdPrice: no valid USD price returned — refusing to treat as free/zero (fail-closed)");
  }
  return usdPrice;
}

// ---------------------------------------------------------------------------------------------
// I/O: Solana RPC reads. Mirrors ../deploy.mjs's readSolBalanceSol/readNosBalance shape (a small,
// deliberate same-file duplication rather than exporting deploy.mjs's private helpers — these are
// ~6 lines each and keep this module's I/O surface self-contained).
// ---------------------------------------------------------------------------------------------

async function readSolBalanceLamports({ connection, address, PublicKeyCtor }) {
  return connection.getBalance(new PublicKeyCtor(address));
}

async function readNosBalance({ connection, address, PublicKeyCtor }) {
  const resp = await connection.getParsedTokenAccountsByOwner(new PublicKeyCtor(address), {
    mint: new PublicKeyCtor(NOS_MINT),
  });
  if (!resp || !Array.isArray(resp.value) || resp.value.length === 0) return 0;
  const amount = resp.value[0].account.data.parsed.info.tokenAmount.uiAmount;
  return typeof amount === "number" ? amount : 0;
}

// ---------------------------------------------------------------------------------------------
// Orchestration: the full acquire flow. Every I/O dependency has a real default; tests override
// them. Never throws for a REFUSED gate or dry mode (expected, successful "decided not to spend
// yet" outcomes) — DOES throw for unresolvable identity, a quote/price fetch failure, an
// unbuildable transaction, an on-chain failure, or an unresolved-after-reconciliation outcome
// (all fail-closed per spec hard constraints 1/3/4).
// ---------------------------------------------------------------------------------------------

export async function acquireNos({
  env = process.env,
  live = false,
  requestedSol = Number(env.NOSANA_FUND_SPEND_SOL || env.NOSANA_FUND_MAX_SPEND_SOL || DEFAULT_MAX_SPEND_SOL),
  maxSlippageBps = Number(env.NOSANA_FUND_MAX_SLIPPAGE_BPS || DEFAULT_MAX_SLIPPAGE_BPS),
  maxPriceImpactPct = Number(env.NOSANA_FUND_MAX_PRICE_IMPACT_PCT || DEFAULT_MAX_PRICE_IMPACT_PCT),
  solFeeFloorSol = Number(env.NOSANA_FUND_FEE_FLOOR_SOL || DEFAULT_SOL_FEE_FLOOR_SOL),
  rpcUrl = env.NOSANA_RPC_URL || env.SOLANA_RPC_URL || DEFAULT_RPC_URL,
  fetchImpl = fetch,
  connectionFactory,
  publicKeyCtor,
  keypairCtor,
  versionedTransactionCtor,
  now = () => Date.now(),
  sleepImpl = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  pollIntervalMs = 2000,
  confirmTimeoutMs = 60000,
} = {}) {
  // Step 1: identity — Franklin's OWN Solana secret, resolved the same canonical way every other
  // earn/spend engine in this repo resolves it. Never a second/new wallet (mirrors deploy.mjs's
  // constraint 2); never logs secret material (constraint 6).
  const secret = resolveSolanaSecret({ env });
  if (!secret) {
    throw new Error(
      "acquireNos: no Solana secret resolved for this instance — ANICCA_HOME must point at Franklin's home (e.g. $HOME/.blockrun)",
    );
  }
  const { address, secretBytes } = deriveAddressFromSecret(secret);
  log(`resolved address ${address}`);

  const web3 = await import("@solana/web3.js");
  const PublicKey = publicKeyCtor || web3.PublicKey;
  const Keypair = keypairCtor || web3.Keypair;
  const VersionedTransaction = versionedTransactionCtor || web3.VersionedTransaction;
  const connection = connectionFactory ? connectionFactory(rpcUrl) : new web3.Connection(rpcUrl, "confirmed");
  const keypair = Keypair.fromSecretKey(secretBytes);

  // Step 2: real balances.
  const solBalanceLamports = await readSolBalanceLamports({ connection, address, PublicKeyCtor: PublicKey });
  const preNosBalance = await readNosBalance({ connection, address, PublicKeyCtor: PublicKey });
  log(`balances: ${(solBalanceLamports / LAMPORTS_PER_SOL).toFixed(9)} SOL, ${preNosBalance} NOS`);

  // Step 3: resolve spend — configured/default cap, hard-clamped to 25% of balance (constraint 2).
  const spend = resolveSpendLamports({ requestedSol, solBalanceLamports });
  log(
    `spend sizing: requested ${(spend.requestedLamports / LAMPORTS_PER_SOL).toFixed(9)} SOL, ` +
      `25%-of-balance hard cap ${(spend.hardCapLamports / LAMPORTS_PER_SOL).toFixed(9)} SOL -> ` +
      `using ${(spend.spendLamports / LAMPORTS_PER_SOL).toFixed(9)} SOL${spend.hardCapApplied ? " (25% cap applied)" : ""}`,
  );
  if (spend.spendLamports <= 0) {
    throw new Error("acquireNos: resolved spend is zero — wallet balance too low to safely swap (fail-closed)");
  }

  // Step 4: real quote + real unsigned transaction build, WITH a bounded transaction-size-guard
  // retry ladder (constraint 3: fail closed on any quote fetch failure; see
  // buildRightSizedSwapTransaction's doc comment for why this exists — a real --live run threw
  // "encoding overruns Uint8Array" from a route Jupiter happened to hand back too big for
  // Solana's 1232-byte packet limit). Every attempt here is read-only; nothing is signed or
  // recorded yet, so retrying here can never produce a second broadcast or a second intent record.
  const sized = await buildRightSizedSwapTransaction({
    fetchImpl,
    spendLamports: spend.spendLamports,
    slippageBps: maxSlippageBps,
    takerAddress: address,
    VersionedTransactionCtor: VersionedTransaction,
    onAttempt: (attempt, info) => {
      if (info.errorKind === "fetch") {
        // Honest distinction (constraint: visible in the log so the operator sees the REAL
        // reason): a fetch/HTTP failure (e.g. rate limiting) is never reported as "too big".
        log(`size guard attempt ${attempt} (maxAccounts=${info.maxAccounts ?? "default"}): quote/build fetch failed — ${info.reason}`);
        return;
      }
      const m = info.measurement;
      const sizeText = m && typeof m.rawBytes === "number" ? `${m.rawBytes} raw bytes / ${m.base64Chars} b64 chars` : "unmeasurable";
      log(
        `size guard attempt ${attempt} (maxAccounts=${info.maxAccounts ?? "default"}): TRANSACTION ${sizeText} ` +
          `(safe limit ${DEFAULT_TRANSACTION_SAFE_BYTE_LIMIT} raw bytes, hard wire limit ${RAW_TRANSACTION_HARD_BYTE_LIMIT} raw / ${BASE64_TRANSACTION_HARD_CHAR_LIMIT} b64) — ${info.ok ? "FITS" : "TOO BIG"}`,
      );
    },
  });
  const { quote, built, unsignedTx } = sized;
  const { expectedNos, minNos } = computeExpectedNosOut(quote);
  const priceImpactPct = parsePriceImpactPct(quote);
  log(
    `quote (size-guard attempt ${sized.attempt}, maxAccounts=${sized.maxAccountsUsed ?? "default"}): ` +
      `${(spend.spendLamports / LAMPORTS_PER_SOL).toFixed(9)} SOL -> ~${expectedNos.toFixed(6)} NOS ` +
      `(min ${minNos.toFixed(6)} NOS after ${maxSlippageBps}bps slippage), price impact ${(priceImpactPct * 100).toFixed(4)}%`,
  );
  log(
    `built swap transaction: TRANSACTION ${sized.measurement.rawBytes} raw bytes / ${sized.measurement.base64Chars} b64 chars ` +
      `(safe limit ${DEFAULT_TRANSACTION_SAFE_BYTE_LIMIT}/hard limit ${RAW_TRANSACTION_HARD_BYTE_LIMIT} raw bytes) — ` +
      `message-only (informational, NOT the gate): ${sized.messageMeasurement.byteLength} bytes — ` +
      `prioritization fee ~${built.prioritizationFeeLamports} lamports, lastValidBlockHeight ${built.lastValidBlockHeight}`,
  );

  // Step 5: real USD pricing for logging + the settled ledger record (constraint 3: fail closed).
  // Sequential (not Promise.all) to respect the keyless 0.5 req/s bucket shared with /quote.
  const solUsdPrice = await fetchMintUsdPrice({ mint: SOL_MINT, fetchImpl });
  const nosUsdPrice = await fetchMintUsdPrice({ mint: NOS_MINT, fetchImpl });
  const summary = computeSpendSummary({ spendLamports: spend.spendLamports, solUsdPrice, nosUsdPrice, expectedNos });
  log(`pricing: SOL $${solUsdPrice}, NOS $${nosUsdPrice} -> spending ~$${summary.spendUsd.toFixed(4)} for ~$${summary.expectedNosUsd.toFixed(4)} of NOS`);

  // Step 7: the combined spend gate — quote validity + slippage/impact ceilings (constraint 3) +
  // post-swap SOL floor using the REAL priority-fee estimate from the built transaction (constraint 2).
  const floorLamports = Math.floor(solFeeFloorSol * LAMPORTS_PER_SOL);
  const gate = evaluateFundingGate({
    spendLamports: spend.spendLamports,
    solBalanceLamports,
    feeLamportsEstimate: built.prioritizationFeeLamports || 0,
    floorLamports,
    quote,
    slippageBps: maxSlippageBps,
    maxSlippageBps,
    maxPriceImpactPct,
  });
  log(`spend gate: ${gate.allowed ? "ALLOWED" : "REFUSED"} — ${gate.reason}`);

  const result = {
    address,
    spend,
    quote,
    expectedNos,
    minNos,
    priceImpactPct,
    solUsdPrice,
    nosUsdPrice,
    summary,
    gate,
    prioritizationFeeLamports: built.prioritizationFeeLamports,
    lastValidBlockHeight: built.lastValidBlockHeight,
    sizeGuard: {
      attempt: sized.attempt,
      maxAccountsUsed: sized.maxAccountsUsed,
      measurement: sized.measurement,
      messageMeasurement: sized.messageMeasurement,
    },
    posted: false,
  };

  // Dry mode ALWAYS stops here, before any signing — but stays honest to the real gate verdict
  // computed above from real balances/quote (constraint 1).
  if (!live) {
    if (gate.allowed) {
      log(
        `gate ALLOWED — would swap ${(spend.spendLamports / LAMPORTS_PER_SOL).toFixed(9)} SOL for ~${expectedNos.toFixed(6)} NOS ` +
          `(~$${summary.spendUsd.toFixed(4)}). Stopping before signing/sending (dry).`,
      );
    } else {
      log(`gate REFUSED (${gate.reason}) — would NOT swap even outside dry mode. Stopping before signing/sending (dry).`);
    }
    return result;
  }

  if (!gate.allowed) {
    log("refusing to swap: spend gate denied it.");
    return result;
  }

  // ---- Everything below this line only runs with --live. ----

  unsignedTx.sign([keypair]);
  const signature = transactionSignatureBase58(unsignedTx);
  const nowTs = now() / 1000;
  const stateDir = resolveStateDir({ env });
  const intentFile = path.join(stateDir, "nosana-funding-intents.jsonl");
  const fundingLedgerFile = path.join(stateDir, "nosana-funding.jsonl");
  const intentId = `${Math.floor(nowTs)}-${signature.slice(0, 12)}`;

  // Step 8: write the intent record BEFORE sending (constraint 4, at-most-once). The signature is
  // already known (deterministic signing, see transactionSignatureBase58's doc comment) — this is
  // what lets reconciliation work even if the send call itself throws or times out.
  appendChild(
    intentFile,
    buildFundingIntentRecord({
      ts: nowTs,
      intentId,
      address,
      spendLamports: spend.spendLamports,
      spendSol: summary.spendSol,
      quote,
      expectedNos,
      minNos,
      signature,
      slippageBps: maxSlippageBps,
      priceImpactPct,
    }),
  );

  try {
    // maxRetries: 0 — we handle confirmation/reconciliation ourselves below; we do not want
    // web3.js's own internal resend loop interacting with our at-most-once bookkeeping. (An RPC
    // rebroadcasting the SAME already-signed bytes under the hood is not a new swap — it carries
    // the same signature — but we keep this explicit and deliberate rather than implicit.)
    await connection.sendRawTransaction(unsignedTx.serialize(), { skipPreflight: false, maxRetries: 0 });
  } catch (err) {
    log(`sendRawTransaction threw — outcome unknown, proceeding to reconcile (never blind-retrying): ${err && err.message}`);
  }

  const polled = await pollForConfirmation({
    signature,
    lastValidBlockHeight: built.lastValidBlockHeight,
    getSignatureStatusesImpl: (sigs) => connection.getSignatureStatuses(sigs),
    getBlockHeightImpl: () => connection.getBlockHeight(),
    sleepImpl,
    now,
    pollIntervalMs,
    timeoutMs: confirmTimeoutMs,
  });

  let settlement;
  if (polled.outcome === "confirmed") {
    settlement = { outcome: "confirmed", source: "poll" };
  } else if (polled.outcome === "failed-onchain") {
    appendChild(intentFile, { ts: now() / 1000, intentId, status: "failed-onchain", err: polled.err });
    throw new Error(`acquireNos: swap ${signature} failed on-chain — refusing to retry automatically; inspect and decide manually`);
  } else {
    // timeout or expired blockhash — outcome unknown. RECONCILE, never blind-retry (constraint 4).
    settlement = await reconcileUnknownOutcome({
      signature,
      preNosBalance,
      getSignatureStatusesImpl: (sigs) => connection.getSignatureStatuses(sigs),
      getSignaturesForAddressImpl: () => connection.getSignaturesForAddress(new PublicKey(address), { limit: 20 }),
      getNosBalanceImpl: () => readNosBalance({ connection, address, PublicKeyCtor: PublicKey }),
    });
  }

  if (settlement.outcome !== "confirmed") {
    appendChild(intentFile, { ts: now() / 1000, intentId, status: "unknown", ...settlement });
    throw new Error(
      `acquireNos: outcome of intent ${intentId} (signature ${signature}) is UNKNOWN after reconciliation ` +
        `(${settlement.reason || settlement.outcome}) — check https://solscan.io/tx/${signature} manually before any retry. Never blind-retrying.`,
    );
  }

  const postNosBalance = await readNosBalance({ connection, address, PublicKeyCtor: PublicKey });
  const nosReceived = typeof settlement.nosDelta === "number" ? settlement.nosDelta : postNosBalance - preNosBalance;

  appendChild(intentFile, { ts: now() / 1000, intentId, status: "settled", signature });
  appendChild(
    fundingLedgerFile,
    buildFundingSettledRecord({
      ts: now() / 1000,
      intentId,
      address,
      signature,
      spendLamports: spend.spendLamports,
      spendSol: summary.spendSol,
      spendUsd: summary.spendUsd,
      nosReceived,
      nosUsdPrice,
      solUsdPrice,
      outcome: settlement.outcome,
      source: settlement.source,
    }),
  );
  log(`swap settled: signature ${signature}, received ${nosReceived} NOS, recorded to ${fundingLedgerFile}`);

  result.posted = true;
  result.signature = signature;
  result.nosReceived = nosReceived;
  result.intentId = intentId;
  return result;
}
