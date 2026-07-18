// resale-guards.mjs — pure decision logic for the /web-search resale product (PROD-2, StableEnrich
// model: this store buys from an EXTERNAL x402 upstream with its own wallet and resells at a
// markup). No I/O in this file: resale.mjs does the fs/network calls and hands the raw results to
// these functions, so every guard is unit-testable without a network or real money
// (see __tests__/resale.test.mjs).

/** UTC calendar date as YYYY-MM-DD — the daily cap resets on UTC midnight, not local time. */
export function utcDateString(date = new Date()) {
  return date.toISOString().slice(0, 10);
}

/** Float guard: refuse to spend when our own operating balance is below the safety floor. */
export function floatGuardTripped(balanceUsd, minFloatUsd = 0.5) {
  return !(Number.isFinite(balanceUsd) && balanceUsd >= minFloatUsd);
}

/**
 * Load-and-roll the daily spend ledger. `raw` is whatever was read from state/resale-spend.json
 * (or null if the file is missing/unreadable). Returns a FRESH state object, never mutates `raw`.
 * A stale date, or malformed/missing state, rolls over to {date: today, spentUsd: 0}.
 */
export function rolloverSpendState(raw, today = utcDateString()) {
  if (raw && typeof raw === "object" && raw.date === today && Number.isFinite(raw.spentUsd)) {
    return { date: today, spentUsd: raw.spentUsd };
  }
  return { date: today, spentUsd: 0 };
}

/** Daily cap guard: refuse once today's recorded spend has reached (or passed) the cap. */
export function dailyCapTripped(state, capUsd) {
  return state.spentUsd >= capUsd;
}

/** Append a paid amount to the ledger. Pure — returns a new state, never mutates `state`. */
export function recordSpend(state, amountUsd) {
  return { date: state.date, spentUsd: Math.round((state.spentUsd + amountUsd) * 1e6) / 1e6 };
}

const USDC_DECIMALS = 6;

/**
 * Decode the v2 `PAYMENT-REQUIRED` 402 challenge header — base64 JSON, per
 * node_modules/@x402/core/dist/cjs/http/index.js:1419-1421 (encodePaymentRequiredHeader) /
 * :1422-1427 (decodePaymentRequiredHeader). Never throws: malformed input -> null, which callers
 * MUST treat as "refuse to pay" (fail closed), never as "no price ceiling".
 */
export function decodeChallengeHeader(headerValue) {
  if (!headerValue || typeof headerValue !== "string") return null;
  try {
    return JSON.parse(Buffer.from(headerValue, "base64").toString("utf8"));
  } catch {
    return null;
  }
}

/**
 * Extract the USD amount an upstream challenge is asking for on the "exact" scheme, from an
 * already-decoded challenge object. Reads v2's `amount` field (PaymentRequirementsV2Schema,
 * node_modules/@x402/core/dist/cjs/http/index.js:892-900) and falls back to v1's
 * `maxAmountRequired` (PaymentRequirementsV1Schema, same file :867-880) — both atomic USDC units
 * (6 decimals). Returns null when no matching accept entry is found or the amount is not a
 * parseable non-negative integer string; callers must fail closed on null.
 */
export function extractChallengeMaxUsd(challenge, { network = "eip155:8453", scheme = "exact" } = {}) {
  const accepts = challenge && Array.isArray(challenge.accepts) ? challenge.accepts : null;
  if (!accepts) return null;
  const match = accepts.find((a) => a && a.scheme === scheme && (a.network === network || a.network === "base"));
  if (!match) return null;
  const atomic = match.amount ?? match.maxAmountRequired;
  if (typeof atomic !== "string" || !/^\d+$/.test(atomic)) return null;
  return Number(BigInt(atomic)) / 10 ** USDC_DECIMALS;
}

/**
 * Challenge guard: refuse to pay when the upstream is asking more than our per-call ceiling, OR
 * when maxUsd could not be determined at all (fail closed — never pay a price we couldn't read).
 */
export function challengeGuardTripped(maxUsd, upstreamMaxUsd) {
  return !(Number.isFinite(maxUsd) && maxUsd <= upstreamMaxUsd);
}
