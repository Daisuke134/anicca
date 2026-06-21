// kotani-payout.mjs — mobile-money (M-Pesa & other African rails) offramp for UBI distribution.
//
// Flow (Kotani Pay /api/v3/offramp): anicca sends USDC (Base) to Kotani; Kotani converts to local
// fiat and disburses to a recipient's mobile-money wallet (customerKey, created by phone number).
// Kotani auto-refunds the crypto if the fiat leg fails (5 min) — a built-in at-least-once safety.
// Docs: https://kotani-pay.readme.io/reference/offrampcontroller_createofframp
//
// GATE (like gmo's token / crossmint's bankAccountId): KOTANI_API_KEY + KOTANI_FIAT_WALLET_ID come
// from a Kotani integrator account, onboarded via https://calendly.com/workwithkotanipay (KYB, not
// self-serve). Once set, this rail fires with no human step. Pure helpers are unit-tested; the auth
// header name + a couple of body fields are marked UNVERIFIED until confirmed against a live key.

const ENV = process.env.KOTANI_ENV === "production" ? "production" : "sandbox";
export const API_BASE =
  ENV === "production" ? "https://api.kotanipay.io" : "https://sandbox-api.kotanipay.io";
const OFFRAMP_PATH = "/api/v3/offramp";

// Pure: validate a USDC amount string — positive, decimal, <=6 dp (USDC precision). Shared guard
// against zero-value "paid" ledger lines and over-precision truncation (VCSDD FIND-003).
export function assertPayableAmount(amount, label = "amount") {
  const s = String(amount);
  if (!/^\d+(\.\d+)?$/.test(s)) throw new Error(`${label}: must be a decimal string`);
  if (Number(s) <= 0) throw new Error(`${label}: must be > 0`);
  if ((s.split(".")[1] || "").length > 6) throw new Error(`${label}: max 6 decimal places (USDC)`);
}

// Pure: deterministic idempotency key from referenceId (the payment-unique id). A retry of the SAME
// payout reuses it; distinct payouts differ (VCSDD FIND-001).
export function kotaniIdempotencyKey(referenceId) {
  if (!referenceId) throw new Error("kotani: referenceId required for idempotency");
  return `kotani-offramp-${referenceId}`;
}

// Pure: build the offramp request body. cryptoAmount is a decimal string of USDC ("19.87").
export function buildOfframpRequest({ referenceId, cryptoAmount, fiatCurrency, customerKey, fiatWalletId, senderAddress }) {
  if (!referenceId) throw new Error("kotani: referenceId required (idempotency + refund tracking)");
  if (!customerKey) throw new Error("kotani: customerKey required (recipient mobile-money customer)");
  if (!fiatWalletId) throw new Error("kotani: fiatWalletId required (KOTANI_FIAT_WALLET_ID)");
  assertPayableAmount(cryptoAmount, "kotani: cryptoAmount");
  if (!fiatCurrency) throw new Error("kotani: fiatCurrency required (e.g. 'KES')");
  return {
    referenceId,
    cryptoAmount: String(cryptoAmount),
    fiatCurrency,
    customerKey,
    fiatWalletId,
    senderAddress,                 // anicca's Base wallet (the crypto sender)
    usingIntegratedWallet: false,  // we send USDC ourselves from anicca's own wallet
  };
}

// Pure: map Kotani offramp status -> our ledger status. Money-safety: a failed/uncertain fiat leg
// becomes needs_review (a human confirms) — never auto-resend. Kotani's own auto-refund handles the
// crypto return; we do NOT re-dispatch.
export function mapOfframpStatus(kotaniStatus) {
  const s = String(kotaniStatus || "").toUpperCase();
  if (s === "SUCCESSFUL" || s === "SUCCESS" || s === "COMPLETED") return "paid";
  // ALL terminal-non-success states escalate to needs_review (a human re-dispatches deliberately).
  // Includes EXPIRED/REVERSED/REFUNDED (the auto-refund leg): the recipient got NO fiat, so the
  // payout is NOT done — never leave it stuck in "pending" forever (VCSDD NEW-001).
  if (["FAILED", "CANCELLED", "CANCELED", "REJECTED", "EXPIRED", "REVERSED", "REFUNDED", "REFUND"].includes(s)) return "needs_review";
  return "pending"; // PENDING / PROCESSING / unknown -> keep polling, never assume paid
}

// Live: submit the offramp request. Injectable fetch for tests.
export async function submitOfframp(reqBody, { apiKey, fetchImpl = fetch } = {}) {
  if (!apiKey) throw new Error("kotani: KOTANI_API_KEY required");
  // defense-in-depth: validate at the live network boundary too, not only in buildOfframpRequest,
  // so a hand-built body can't POST a malformed amount (VCSDD NEW-002).
  assertPayableAmount(reqBody?.cryptoAmount, "kotani: cryptoAmount");
  const res = await fetchImpl(`${API_BASE}${OFFRAMP_PATH}`, {
    method: "POST",
    // UNVERIFIED: confirm header name (Authorization Bearer vs x-api-key) against a live Kotani key.
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json",
               // idempotency: a network-timeout retry of the same payout must not double-send (FIND-001).
               "x-idempotency-key": kotaniIdempotencyKey(reqBody?.referenceId) },
    body: JSON.stringify(reqBody),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`kotani offramp ${res.status}: ${text.slice(0, 300)}`);
  }
  return res.json();
}

// Live: poll an offramp's status by referenceId.
export async function getOfframpStatus(referenceId, { apiKey, fetchImpl = fetch } = {}) {
  if (!apiKey) throw new Error("kotani: KOTANI_API_KEY required");
  if (!referenceId) throw new Error("kotani: referenceId required");
  const res = await fetchImpl(`${API_BASE}${OFFRAMP_PATH}/status/${referenceId}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
  });
  if (!res.ok) throw new Error(`kotani offramp status ${res.status}`);
  const data = await res.json();
  return { raw: data, status: mapOfframpStatus(data?.status ?? data?.data?.status) };
}
