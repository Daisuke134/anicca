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

// Pure: build the offramp (withdrawal) order body. amountUsdc is a decimal string ("19.87").
// Deterministic idempotency from (bankAccountId, amount, ref) so a retry never double-sends.
export function buildOfframpOrder({ bankAccountId, amountUsdc, referenceId }) {
  if (!bankAccountId) throw new Error("crossmint-offramp: bankAccountId required (CSE-registered)");
  if (!/^\d+(\.\d+)?$/.test(String(amountUsdc))) throw new Error("crossmint-offramp: amountUsdc must be a decimal string");
  return {
    // UNVERIFIED: exact withdrawal line-item nesting — docs confirm currencyLocator 'fiat:usd' +
    // amount + bankAccountId via the Create-Order API; verify field placement with a live CSE account.
    recipient: { bankAccountId },
    lineItems: [{ currencyLocator: "fiat:usd", amount: String(amountUsdc) }],
    metadata: referenceId ? { referenceId } : undefined,
  };
}

// Pure: deterministic idempotency key (order-independent on the inputs that define the payment).
export function offrampIdempotencyKey({ bankAccountId, amountUsdc, referenceId }) {
  return `anicca-offramp-${bankAccountId}-${amountUsdc}-${referenceId || "0"}`;
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

// Live: poll an offramp order's status. Returns the raw order object (caller maps status).
export async function getOfframpStatus(orderId, { apiKey, fetchImpl = fetch } = {}) {
  if (!orderId) throw new Error("crossmint-offramp: orderId required");
  const res = await fetchImpl(`${API_BASE}${ORDERS_PATH}/${orderId}`, {
    headers: { "x-api-key": apiKey },
  });
  if (!res.ok) throw new Error(`crossmint-offramp status ${res.status}`);
  return res.json();
}
