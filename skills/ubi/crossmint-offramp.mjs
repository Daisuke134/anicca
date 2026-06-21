// crossmint-offramp.mjs — US (and other fiat) bank offramp rail for UBI distribution.
//
// Flow (Crossmint Stablecoin Orchestration / Treasury Wallet withdrawals):
//   anicca treasury USDC  --Crossmint Create-Order(offramp)-->  USDC debited, converted to fiat,
//   fiat (minus fees) deposited to a REGISTERED bank account (bankAccountId).
//   Docs: https://docs.crossmint.com/stablecoin-orchestration/treasury-wallet/guides/withdrawals
//
// GATE (same shape as gmo-furikomi's token): the destination bankAccountId must be registered with
// Crossmint's CSE team first (KYB onboarding) — it is NOT self-serve. Once obtained, set
// CROSSMINT_BANK_ACCOUNT_ID and this rail fires with no further human step. The order-submit +
// status-poll below are fully API-driven (x-api-key). Pure helpers are unit-tested; the live POST
// shape for the withdrawal line item is marked UNVERIFIED where the public docs were incomplete —
// confirm against a real CSE-provided bankAccountId before first production send.

const ENV = process.env.CROSSMINT_ENV === "production" ? "production" : "staging";
export const API_BASE =
  ENV === "production" ? "https://www.crossmint.com" : "https://staging.crossmint.com";
const ORDERS_PATH = "/api/2022-06-09/orders";

// Pure: validate a USDC amount string — positive, decimal, <=6 dp. Blocks zero-value "paid" lines
// and over-precision truncation (VCSDD FIND-003).
export function assertPayableAmount(amount, label = "amount") {
  const s = String(amount);
  if (!/^\d+(\.\d+)?$/.test(s)) throw new Error(`${label}: must be a decimal string`);
  if (Number(s) <= 0) throw new Error(`${label}: must be > 0`);
  if ((s.split(".")[1] || "").length > 6) throw new Error(`${label}: max 6 decimal places (USDC)`);
}

// Pure: build the offramp (withdrawal) order body. amountUsdc is a decimal string ("19.87").
// referenceId is REQUIRED so the idempotency key is always payment-unique — two distinct payouts to
// the same bank+amount must NOT collapse to one (VCSDD FIND-002).
export function buildOfframpOrder({ bankAccountId, amountUsdc, referenceId }) {
  if (!bankAccountId) throw new Error("crossmint-offramp: bankAccountId required (CSE-registered)");
  if (!referenceId) throw new Error("crossmint-offramp: referenceId required (payment-unique idempotency)");
  assertPayableAmount(amountUsdc, "crossmint-offramp: amountUsdc");
  return {
    // UNVERIFIED: exact withdrawal line-item nesting — docs confirm currencyLocator 'fiat:usd' +
    // amount + bankAccountId via the Create-Order API; verify field placement with a live CSE account.
    recipient: { bankAccountId },
    lineItems: [{ currencyLocator: "fiat:usd", amount: String(amountUsdc) }],
    metadata: referenceId ? { referenceId } : undefined,
  };
}

// Pure: deterministic idempotency key. referenceId is required so distinct payouts never collide
// (VCSDD FIND-002) — no "0" fallback.
export function offrampIdempotencyKey({ bankAccountId, amountUsdc, referenceId }) {
  if (!referenceId) throw new Error("crossmint-offramp: referenceId required for idempotency");
  return `anicca-offramp-${bankAccountId}-${amountUsdc}-${referenceId}`;
}

// Pure: map a Crossmint order status -> our ledger status. Money-safety: failure/unknown is NEVER
// reported as paid; failure -> needs_review (a human confirms, no auto-resend) (VCSDD FIND-006).
export function mapOrderStatus(orderStatus) {
  const s = String(orderStatus || "").toLowerCase();
  if (s === "completed" || s === "success" || s === "succeeded" || s === "paid") return "paid";
  if (s === "failed" || s === "cancelled" || s === "rejected" || s === "expired") return "needs_review";
  return "pending"; // awaiting-payment / in-progress / unknown -> keep polling, never assume paid
}

// Live: submit the offramp order. Injectable fetch for tests.
export async function submitOfframp(order, { apiKey, fetchImpl = fetch } = {}) {
  if (!apiKey) throw new Error("crossmint-offramp: CROSSMINT_API_KEY required");
  const res = await fetchImpl(`${API_BASE}${ORDERS_PATH}`, {
    method: "POST",
    headers: { "x-api-key": apiKey, "Content-Type": "application/json",
               "x-idempotency-key": offrampIdempotencyKey({
                 bankAccountId: order.recipient?.bankAccountId,
                 amountUsdc: order.lineItems?.[0]?.amount,
                 referenceId: order.metadata?.referenceId }) },
    body: JSON.stringify(order),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`crossmint-offramp submit ${res.status}: ${text.slice(0, 300)}`);
  }
  return res.json(); // { orderId, ... }
}

// Live: poll an offramp order's status. Returns { raw, status } where status is mapped to our
// ledger vocab (paid / needs_review / pending) — never let a caller misread a pending order as paid.
export async function getOfframpStatus(orderId, { apiKey, fetchImpl = fetch } = {}) {
  if (!orderId) throw new Error("crossmint-offramp: orderId required");
  const res = await fetchImpl(`${API_BASE}${ORDERS_PATH}/${orderId}`, {
    headers: { "x-api-key": apiKey },
  });
  if (!res.ok) throw new Error(`crossmint-offramp status ${res.status}`);
  const data = await res.json();
  return { raw: data, status: mapOrderStatus(data?.status ?? data?.phase) };
}
