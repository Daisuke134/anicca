"use strict";
// lib/billing.js — HARD-3 Stripe lifecycle = billing source of truth for Life Manager (apps/life-call).
//
// The Stripe webhook is the SINGLE writer of lm_users.paid; the HARD-2 sweeper (paid=is.true) is its only
// reader. Source of truth = the subscription `status` (NOT individual events), per
// https://docs.stripe.com/billing/subscriptions/webhooks. Idempotent via the lm_stripe_events ledger
// (claim 201 / dup 409, mirroring lib/ask.js claimAsk). Out-of-order deliveries are guarded by
// current_period_end (isStale). entitlementFor is a PURE fixed status→entitlement table (Stripe's own
// state machine, not an LLM judgment → deterministic code is correct here).

// PROVISION statuses: active + trialing are in good standing; past_due keeps access during the grace
// window (Stripe keeps retrying payment) while we send a dunning notice. Everything else = no access.
const PROVISION = new Set(["active", "trialing", "past_due"]);

// entitlementFor(status) → { paid, plan_status }. PURE. Unknown/empty/null → fail-safe paid=false.
function entitlementFor(status) {
  const s = status == null ? null : String(status).trim().toLowerCase();
  return { paid: !!s && PROVISION.has(s), plan_status: s || null };
}

// parseStripeEvent(event) → normalized shape we act on, or null for event types we ignore (no-op 200).
//   checkout.session.completed → { kind:"checkout", uid, customerId, subscriptionId }
//   customer.subscription.*     → { kind:"subscription", customerId, subscriptionId, status, currentPeriodEnd }
const SUBSCRIPTION_TYPES = new Set([
  "customer.subscription.created",
  "customer.subscription.updated",
  "customer.subscription.deleted",
]);
function parseStripeEvent(event) {
  const type = event && event.type;
  const o = (event && event.data && event.data.object) || {};
  if (type === "checkout.session.completed") {
    return {
      kind: "checkout",
      uid: o.client_reference_id || null,
      customerId: o.customer || null,
      subscriptionId: o.subscription || null,
    };
  }
  if (SUBSCRIPTION_TYPES.has(type)) {
    return {
      kind: "subscription",
      customerId: o.customer || null,
      subscriptionId: o.id || null,
      status: o.status || null,
      currentPeriodEnd: o.current_period_end || 0,
    };
  }
  return null; // unknown type → caller acks 200 with no side effect
}

// isStale(incomingPeriodEnd, incomingSubId, storedRow) → true when this event is OLDER than what we already
// stored for the SAME subscription (so a late/out-of-order delivery can't downgrade fresher state). A new
// subscription id, or no stored row, is never stale.
function isStale(incomingPeriodEnd, incomingSubId, storedRow) {
  if (!storedRow || !storedRow.stripe_subscription_id) return false;
  if (storedRow.stripe_subscription_id !== incomingSubId) return false; // different sub → apply
  const stored = Number(storedRow.current_period_end || 0);
  return Number(incomingPeriodEnd || 0) < stored;
}

// ── Supabase IO (service-role). All accept an injectable fetch for testing. ──────────────────────────
function hdr(key, extra) {
  return Object.assign({ apikey: key, Authorization: `Bearer ${key}` }, extra || {});
}

// claimEvent: INSERT into lm_stripe_events. 201 = claimed (process it) | 409 = duplicate (skip).
// No supa creds (local dev) → return true so the handler still runs once.
async function claimEvent(eventId, type, supaUrl, supaKey, fetchImpl) {
  const f = fetchImpl || fetch;
  if (!supaUrl || !supaKey) return true;
  const r = await f(`${supaUrl}/rest/v1/lm_stripe_events`, {
    method: "POST",
    headers: hdr(supaKey, { "Content-Type": "application/json", Prefer: "return=minimal" }),
    body: JSON.stringify({ event_id: eventId, type }),
  }).catch(() => null);
  return !!r && r.status === 201;
}

// unclaimEvent: DELETE the claim so a Stripe redelivery re-processes (used when the write failed).
async function unclaimEvent(eventId, supaUrl, supaKey, fetchImpl) {
  const f = fetchImpl || fetch;
  if (!supaUrl || !supaKey) return;
  await f(`${supaUrl}/rest/v1/lm_stripe_events?event_id=eq.${encodeURIComponent(eventId)}`, {
    method: "DELETE",
    headers: hdr(supaKey, { Prefer: "return=minimal" }),
  }).catch(() => null);
}

// userByCustomer(customerId) → the stored lm_users row (uid + billing cols) or null (orphan event).
async function userByCustomer(customerId, supaUrl, supaKey, fetchImpl) {
  const f = fetchImpl || fetch;
  if (!supaUrl || !supaKey || !customerId) return null;
  const cols = "uid,stripe_subscription_id,current_period_end,plan_status,paid";
  const r = await f(
    `${supaUrl}/rest/v1/lm_users?stripe_customer_id=eq.${encodeURIComponent(customerId)}&select=${cols}`,
    { headers: hdr(supaKey) },
  ).catch(() => null);
  if (!r || !r.ok) return null;
  const d = await r.json().catch(() => []);
  return Array.isArray(d) && d[0] ? d[0] : null;
}

// patchUserByUid / patchUserByCustomer: write the billing patch onto lm_users.
async function patchUser(filter, patch, supaUrl, supaKey, fetchImpl) {
  const f = fetchImpl || fetch;
  if (!supaUrl || !supaKey) return true;
  const r = await f(`${supaUrl}/rest/v1/lm_users?${filter}`, {
    method: "PATCH",
    headers: hdr(supaKey, { "Content-Type": "application/json", Prefer: "return=minimal" }),
    body: JSON.stringify(patch),
  }).catch(() => null);
  return !!r && (r.status === 204 || r.status === 200);
}

// applyBilling(event, deps) — orchestrates ONE event into a lm_users write. Returns a result object
// describing what happened (for logging/tests). deps = { supaUrl, supaKey, fetchImpl, notify }.
// Throws on a write failure so the webhook handler can 500 + unclaim → Stripe redelivers.
async function applyBilling(event, deps) {
  const { supaUrl, supaKey, fetchImpl, notify } = deps || {};
  const p = parseStripeEvent(event);
  if (!p) return { action: "ignored", type: event && event.type };

  if (p.kind === "checkout") {
    if (!p.uid) return { action: "orphan-checkout" };
    // Link customer↔uid. Status is resolved by the subsequent subscription.* event; provision optimistically
    // as active here only if we have nothing else — but the safe move is to store the linkage and let the
    // subscription event set paid. We set the linkage + a provisional active (checkout implies a paid sub).
    const ok = await patchUser(
      `uid=eq.${encodeURIComponent(p.uid)}`,
      { stripe_customer_id: p.customerId, stripe_subscription_id: p.subscriptionId, paid: true, plan_status: "active" },
      supaUrl, supaKey, fetchImpl,
    );
    if (!ok) throw new Error("checkout patch failed");
    return { action: "provision", uid: p.uid, paid: true };
  }

  // subscription.*: resolve the uid via the stored customer mapping, guard staleness, then write entitlement.
  const row = await userByCustomer(p.customerId, supaUrl, supaKey, fetchImpl);
  if (!row || !row.uid) return { action: "orphan-subscription", customerId: p.customerId };
  if (isStale(p.currentPeriodEnd, p.subscriptionId, row)) return { action: "stale", customerId: p.customerId };

  const ent = entitlementFor(p.status);
  const ok = await patchUser(
    `uid=eq.${encodeURIComponent(row.uid)}`,
    {
      paid: ent.paid,
      plan_status: ent.plan_status,
      stripe_subscription_id: p.subscriptionId,
      current_period_end: p.currentPeriodEnd ? new Date(p.currentPeriodEnd * 1000).toISOString() : null,
    },
    supaUrl, supaKey, fetchImpl,
  );
  if (!ok) throw new Error("subscription patch failed");

  // Dunning: past_due keeps access but warns once. notify is injected (lib/notify.js channel) — best-effort.
  if (p.status === "past_due" && typeof notify === "function") {
    try { await notify(row.uid); } catch { /* dunning is best-effort, never block the webhook */ }
  }
  return { action: ent.paid ? "provision" : "deprovision", uid: row.uid, paid: ent.paid, status: p.status };
}

module.exports = {
  entitlementFor,
  parseStripeEvent,
  isStale,
  claimEvent,
  unclaimEvent,
  userByCustomer,
  patchUser,
  applyBilling,
};
