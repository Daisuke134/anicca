// bridge-payout.mjs — US / global bank offramp rail for UBI distribution via Bridge.xyz.
//
// Flow (Bridge POST /v0/transfers): anicca's USDC (Base) -> Bridge converts -> fiat deposited to a
// recipient's registered external bank account. Bridge handles the on/off-ramp + settlement.
// Docs: https://apidocs.bridge.xyz/api-reference/transfers
//
// GATE (same shape as crossmint bankAccountId / kotani fiatWalletId): BRIDGE_API_KEY + a registered
// Bridge customer (on_behalf_of) and external_account are provisioned via Bridge KYB onboarding (not
// self-serve). Once set, this rail fires with no human step. Pure helpers are unit-tested; the exact
// source payment_rail token for Base-USDC and the external-account reference are marked UNVERIFIED
// until confirmed against a live Bridge account (wrong value fails closed at the API, not a money loss).

const ENV = process.env.BRIDGE_ENV === 'production' ? 'production' : 'sandbox';
export const API_BASE = ENV === 'production' ? 'https://api.bridge.xyz/v0' : 'https://api.sandbox.bridge.xyz/v0';
const TRANSFERS_PATH = '/transfers';

// Pure: USDC amount string — positive, decimal, <=6dp, and <= a sane ceiling (defense-in-depth so a
// miscomputed huge payout can't be submitted — VCSDD FIND-004). maxUsdc default 100000.
export function assertPayableAmount(amount, label = 'amount', maxUsdc = 100000) {
  const s = String(amount);
  if (!/^\d+(\.\d+)?$/.test(s)) throw new Error(`${label}: must be a decimal string`);
  if (Number(s) <= 0) throw new Error(`${label}: must be > 0`);
  if ((s.split('.')[1] || '').length > 6) throw new Error(`${label}: max 6 decimal places (USDC)`);
  if (Number(s) > maxUsdc) throw new Error(`${label}: exceeds max ${maxUsdc} per transfer`);
}

// Pure: deterministic idempotency key from referenceId — a retry of the SAME payout reuses it.
export function bridgeIdempotencyKey(referenceId) {
  if (!referenceId) throw new Error('bridge: referenceId required for idempotency');
  return `bridge-payout-${referenceId}`;
}

// Pure: map a Bridge transfer status -> our ledger vocab. failure/unknown NEVER reads as paid.
export function mapTransferStatus(bridgeStatus) {
  const s = String(bridgeStatus || '').toLowerCase();
  if (s === 'payment_processed' || s === 'completed' || s === 'paid' || s === 'funds_received') return 'paid';
  // all terminal-failure states -> needs_review (never leave a dead transfer polling forever — FIND-005)
  if (['returned', 'refunded', 'canceled', 'cancelled', 'error', 'failed', 'reversed', 'charged_back', 'declined', 'rejected', 'reclaimed', 'expired'].includes(s)) return 'needs_review';
  return 'pending'; // awaiting_funds / in_review / processing / unknown -> keep polling, never assume paid
}

// Pure: build the /transfers body. amountUsdc decimal string; recipient = registered external account.
export function buildTransferRequest({ referenceId, amountUsdc, customerId, externalAccountId, senderAddress, fiatCurrency = 'usd', destinationRail = 'ach' }) {
  if (!referenceId) throw new Error('bridge: referenceId required');
  if (!customerId) throw new Error('bridge: customerId (on_behalf_of) required');
  if (!externalAccountId) throw new Error('bridge: externalAccountId (registered bank) required');
  assertPayableAmount(amountUsdc, 'bridge: amountUsdc');
  return {
    // referenceId is the payment-unique key carried INTO the body so submitTransfer derives the
    // Idempotency-Key from it (NOT from amount) — two periods of the same fixed UBI to the same
    // recipient have DIFFERENT referenceIds, so the 2nd is NOT deduped/dropped (VCSDD FIND-001).
    referenceId,
    client_reference_id: referenceId, // Bridge's documented per-transfer reference (UNVERIFIED field name; harmless if ignored)
    on_behalf_of: customerId,
    amount: String(amountUsdc),
    // UNVERIFIED: confirm the Base-USDC source token + crypto-source shape against a live Bridge account.
    source: { currency: 'usdc', payment_rail: 'base', from_address: senderAddress },
    destination: { currency: fiatCurrency, payment_rail: destinationRail, external_account_id: externalAccountId },
  };
}

// Live: submit a transfer. Injectable fetch for tests.
export async function submitTransfer(body, { apiKey, fetchImpl = fetch } = {}) {
  if (!apiKey) throw new Error('bridge: BRIDGE_API_KEY required');
  assertPayableAmount(body?.amount, 'bridge: amount'); // defense-in-depth at the live boundary
  // Idempotency-Key derives STRICTLY from referenceId (the payment-unique id) — no amount fallback,
  // so distinct payouts never collide (FIND-001). Throws if absent.
  const idemKey = bridgeIdempotencyKey(body?.referenceId);
  const res = await fetchImpl(`${API_BASE}${TRANSFERS_PATH}`, {
    method: 'POST',
    headers: {
      // UNVERIFIED (pre-prod confirm vs live Bridge): (a) auth header name `Api-Key` vs Authorization
      // Bearer; (b) idempotency is an HTTP HEADER `Idempotency-Key` vs a body field — if Bridge expects
      // a body field, this header is ignored and retries double-pay. Confirm both before real money.
      'Api-Key': apiKey,
      'Idempotency-Key': idemKey,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`bridge transfer ${res.status}: ${text.slice(0, 300)}`);
  }
  return res.json();
}

// Live: poll a transfer's status. Returns { raw, status } mapped to our ledger vocab.
export async function getTransferStatus(transferId, { apiKey, fetchImpl = fetch } = {}) {
  if (!apiKey) throw new Error('bridge: BRIDGE_API_KEY required');
  if (!transferId) throw new Error('bridge: transferId required');
  const res = await fetchImpl(`${API_BASE}${TRANSFERS_PATH}/${transferId}`, { headers: { 'Api-Key': apiKey } });
  if (!res.ok) throw new Error(`bridge transfer status ${res.status}`);
  const data = await res.json();
  return { raw: data, status: mapTransferStatus(data?.state ?? data?.status) };
}
