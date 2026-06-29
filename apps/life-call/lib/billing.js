"use strict";
// lib/billing.js — HARD-3 Stripe lifecycle = billing source of truth for Life Manager (apps/life-call).
//
// The Stripe webhook is the SINGLE writer of lm_users.paid; the HARD-2 sweeper (paid=is.true) is its only
// reader. Source of truth = the subscription `status` (NOT individual events), per
// https://docs.stripe.com/billing/subscriptions/webhooks. Idempotent via the lm_stripe_events ledger
// (claim 201 / dup 409). Out-of-order deliveries are guarded by the EVENT's `created` timestamp (the
// authoritative ordering key — current_period_end is NOT monotonic: an immediate cancel can lower it, which
// would wrongly drop the downgrade). entitlementFor is a PURE fixed status→entitlement table (Stripe's own
// state machine, not an LLM judgment → deterministic code is correct here).

// PROVISION statuses: active + trialing are in good standing; past_due keeps access during the grace window
// (Stripe keeps retrying payment) while we send a dunning notice. Everything else = no access.
const PROVISION = new Set(["active", "trialing", "past_due"]);

// entitlementFor(status) → { paid, plan_status }. PURE. Unknown/empty/null → fail-safe paid=false.
function entitlementFor(status) {
  const s = status == null ? null : String(status).trim().toLowerCase();
  return { paid: !!s && PROVISION.has(s), plan_status: s || null };
}

// toEpoch: normalize a timestamp to UNIX seconds. Stripe sends ints (epoch seconds); Supabase stores
// timestamptz and PostgREST returns an ISO string — Number("2033-…")=NaN, so ISO values must be Date.parsed.
function toEpoch(v) {
  if (v == null) return 0;
  if (typeof v === "number") return v;
  const n = Number(v);
  if (!Number.isNaN(n) && String(v).trim() !== "") return n; // numeric string → epoch seconds
  const t = Date.parse(v);                                    // ISO timestamp → ms
  return Number.isNaN(t) ? 0 : Math.floor(t / 1000);
}

// parseStripeEvent(event) → normalized shape we act on, or null for event types we ignore (no-op 200).
//   checkout.session.completed → { kind:"checkout", uid, customerId, subscriptionId, paymentStatus, created }
//   customer.subscription.*     → { kind:"subscription", customerId, subscriptionId, status, currentPeriodEnd, created }
const SUBSCRIPTION_TYPES = new Set([
  "customer.subscription.created",
  "customer.subscription.updated",
  "customer.subscription.deleted",
]);
function parseStripeEvent(event) {
  const type = event && event.type;
  const o = (event && event.data && event.data.object) || {};
  const created = (event && event.created) || 0; // event-level Unix seconds — the staleness ordering key
  if (type === "checkout.session.completed") {
    return {
      kind: "checkout",
      uid: o.client_reference_id || null,
      customerId: o.customer || null,
      subscriptionId: o.subscription || null,
      paymentStatus: o.payment_status || null, // 'paid' | 'unpaid' | 'no_payment_required'
      created,
    };
  }
  if (SUBSCRIPTION_TYPES.has(type)) {
    return {
      kind: "subscription",
      customerId: o.customer || null,
      subscriptionId: o.id || null,
      status: o.status || null,
      currentPeriodEnd: o.current_period_end || 0,
      created,
    };
  }
  return null; // unknown type → caller acks 200 with no side effect
}

// isStale(incomingCreated, storedRow) → true when this event is OLDER (by event.created) than the last event
// we applied for this user. Keyed on event.created — the only monotonic ordering Stripe guarantees — so an
// immediate cancel (which may carry a current_period_end ≤ the active one) STILL applies. No stored row /
// no stored timestamp → first event → never stale.
function isStale(incomingCreated, storedRow) {
  if (!storedRow || !storedRow.stripe_event_at) return false;
  return toEpoch(incomingCreated) < toEpoch(storedRow.stripe_event_at);
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

// unclaimEvent: DELETE the claim so a Stripe redelivery re-processes (used when the write failed). Returns
// true on success — the caller logs a RECONCILE marker if this fails (the transition would otherwise stick).
async function unclaimEvent(eventId, supaUrl, supaKey, fetchImpl) {
  const f = fetchImpl || fetch;
  if (!supaUrl || !supaKey) return true;
  const r = await f(`${supaUrl}/rest/v1/lm_stripe_events?event_id=eq.${encodeURIComponent(eventId)}`, {
    method: "DELETE",
    headers: hdr(supaKey, { Prefer: "return=minimal" }),
  }).catch(() => null);
  return !!r && (r.status === 204 || r.status === 200);
}

// userByCustomer(customerId) → the stored lm_users row (uid + billing cols incl. stripe_event_at) or null.
async function userByCustomer(customerId, supaUrl, supaKey, fetchImpl) {
  const f = fetchImpl || fetch;
  if (!supaUrl || !supaKey || !customerId) return null;
  const cols = "uid,stripe_subscription_id,current_period_end,stripe_event_at,plan_status,paid";
  const r = await f(
    `${supaUrl}/rest/v1/lm_users?stripe_customer_id=eq.${encodeURIComponent(customerId)}&select=${cols}`,
    { headers: hdr(supaKey) },
  ).catch(() => null);
  if (!r || !r.ok) return null;
  const d = await r.json().catch(() => []);
  return Array.isArray(d) && d[0] ? d[0] : null;
}

// userByUid(uid) → the stored lm_users row (billing cols incl. stripe_event_at) or null. Used by the
// checkout branch (keyed by uid via client_reference_id) for the same staleness guard the subscription
// branch uses (FIND-007).
async function userByUid(uid, supaUrl, supaKey, fetchImpl) {
  const f = fetchImpl || fetch;
  if (!supaUrl || !supaKey || !uid) return null;
  const cols = "uid,stripe_subscription_id,current_period_end,stripe_event_at,plan_status,paid";
  const r = await f(
    `${supaUrl}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}&select=${cols}`,
    { headers: hdr(supaKey) },
  ).catch(() => null);
  if (!r || !r.ok) return null;
  const d = await r.json().catch(() => []);
  return Array.isArray(d) && d[0] ? d[0] : null;
}

// patchUser: write the billing patch onto lm_users by a PostgREST filter.
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

const isoOrNull = (epochSecs) => (epochSecs ? new Date(epochSecs * 1000).toISOString() : null);

// applyBilling(event, deps) — orchestrates ONE event into a lm_users write. Returns a result object for
// logging/tests. deps = { supaUrl, supaKey, fetchImpl, notify }. Throws on a write failure so the webhook
// handler can 500 + unclaim → Stripe redelivers.
async function applyBilling(event, deps) {
  const { supaUrl, supaKey, fetchImpl, notify } = deps || {};
  const p = parseStripeEvent(event);
  if (!p) return { action: "ignored", type: event && event.type };

  if (p.kind === "checkout") {
    if (!p.uid) return { action: "orphan-checkout" };
    // FIND-007: guard the checkout branch by event.created too (same as subscription) — a late/out-of-order
    // checkout must NOT clobber a fresher applied state (downgrade an active payer, or regress stripe_event_at).
    const row = await userByUid(p.uid, supaUrl, supaKey, fetchImpl);
    if (isStale(p.created, row)) return { action: "stale-checkout", uid: p.uid };
    // FIND-003: only provision when the session is actually paid. An 'unpaid' checkout links the customer
    // but must NOT grant access — the subsequent subscription.* event sets the real status.
    const paid = p.paymentStatus === "paid" || p.paymentStatus === "no_payment_required";
    const patch = {
      stripe_customer_id: p.customerId,
      stripe_subscription_id: p.subscriptionId,
      paid,
      plan_status: paid ? "active" : "incomplete",
      stripe_event_at: isoOrNull(p.created),
    };
    if (!(await patchUser(`uid=eq.${encodeURIComponent(p.uid)}`, patch, supaUrl, supaKey, fetchImpl))) {
      throw new Error("checkout patch failed");
    }
    return { action: paid ? "provision" : "link-unpaid", uid: p.uid, paid };
  }

  // subscription.*: resolve the uid via the stored customer mapping, guard staleness by event.created, write.
  const row = await userByCustomer(p.customerId, supaUrl, supaKey, fetchImpl);
  if (!row || !row.uid) return { action: "orphan-subscription", customerId: p.customerId };
  if (isStale(p.created, row)) return { action: "stale", customerId: p.customerId };

  const ent = entitlementFor(p.status);
  const patch = {
    paid: ent.paid,
    plan_status: ent.plan_status,
    stripe_subscription_id: p.subscriptionId,
    current_period_end: isoOrNull(p.currentPeriodEnd),
    stripe_event_at: isoOrNull(p.created),
  };
  if (!(await patchUser(`uid=eq.${encodeURIComponent(row.uid)}`, patch, supaUrl, supaKey, fetchImpl))) {
    throw new Error("subscription patch failed");
  }

  // Dunning: past_due keeps access but warns once. notify is injected (best-effort; never blocks the webhook).
  if (p.status === "past_due" && typeof notify === "function") {
    try { await notify(row.uid); } catch { /* dunning is best-effort */ }
  }
  return { action: ent.paid ? "provision" : "deprovision", uid: row.uid, paid: ent.paid, status: p.status };
}

module.exports = {
  entitlementFor,
  parseStripeEvent,
  isStale,
  toEpoch,
  claimEvent,
  unclaimEvent,
  userByCustomer,
  userByUid,
  patchUser,
  applyBilling,
};
