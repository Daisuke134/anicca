"use strict";
// HARD-3 billing lifecycle — unit tests (RED first). Source of truth = Stripe subscription.status.
// Run: node --test lib/billing.test.js
const { test } = require("node:test");
const assert = require("node:assert");
const {
  entitlementFor,
  parseStripeEvent,
  isStale,
  claimEvent,
  unclaimEvent,
} = require("./billing.js");

// ── entitlementFor: the fixed Stripe status → entitlement table (REQ-38) ──────
test("entitlementFor: active/trialing/past_due → paid=true (provision + grace)", () => {
  for (const s of ["active", "trialing", "past_due", "ACTIVE", "Trialing"]) {
    assert.strictEqual(entitlementFor(s).paid, true, `${s} should provision`);
  }
});
test("entitlementFor: canceled/unpaid/incomplete* → paid=false (revoke)", () => {
  for (const s of ["canceled", "unpaid", "incomplete", "incomplete_expired", "paused"]) {
    assert.strictEqual(entitlementFor(s).paid, false, `${s} should revoke`);
  }
});
test("entitlementFor: unknown/empty/null → paid=false (fail-safe)", () => {
  for (const s of [undefined, null, "", "weird_status"]) {
    assert.strictEqual(entitlementFor(s).paid, false);
  }
  assert.strictEqual(entitlementFor("active").plan_status, "active");
  assert.strictEqual(entitlementFor(null).plan_status, null);
});

// ── parseStripeEvent: pull the fields we patch from the event (REQ-37/38) ──────
test("parseStripeEvent: checkout.session.completed → uid + customer + sub", () => {
  const ev = {
    id: "evt_1", type: "checkout.session.completed",
    data: { object: { client_reference_id: "uid-abc", customer: "cus_1", subscription: "sub_1" } },
  };
  const p = parseStripeEvent(ev);
  assert.strictEqual(p.kind, "checkout");
  assert.strictEqual(p.uid, "uid-abc");
  assert.strictEqual(p.customerId, "cus_1");
  assert.strictEqual(p.subscriptionId, "sub_1");
});
test("parseStripeEvent: customer.subscription.updated → status + period end + customer", () => {
  const ev = {
    id: "evt_2", type: "customer.subscription.updated",
    data: { object: { id: "sub_1", customer: "cus_1", status: "past_due", current_period_end: 1750000000 } },
  };
  const p = parseStripeEvent(ev);
  assert.strictEqual(p.kind, "subscription");
  assert.strictEqual(p.customerId, "cus_1");
  assert.strictEqual(p.subscriptionId, "sub_1");
  assert.strictEqual(p.status, "past_due");
  assert.strictEqual(p.currentPeriodEnd, 1750000000);
});
test("parseStripeEvent: customer.subscription.deleted → status canceled", () => {
  const ev = {
    id: "evt_3", type: "customer.subscription.deleted",
    data: { object: { id: "sub_1", customer: "cus_1", status: "canceled", current_period_end: 1750000000 } },
  };
  assert.strictEqual(parseStripeEvent(ev).status, "canceled");
});
test("parseStripeEvent: unknown type → null (no-op)", () => {
  assert.strictEqual(parseStripeEvent({ id: "x", type: "ping", data: { object: {} } }), null);
});

// ── isStale: out-of-order guard (REQ-39) ──────────────────────────────────────
test("isStale: older period_end on SAME sub → stale (ignore late delivery)", () => {
  assert.strictEqual(isStale(100, "sub_1", { current_period_end: 200, stripe_subscription_id: "sub_1" }), true);
});
test("isStale: newer/equal period_end on same sub → not stale", () => {
  assert.strictEqual(isStale(300, "sub_1", { current_period_end: 200, stripe_subscription_id: "sub_1" }), false);
  assert.strictEqual(isStale(200, "sub_1", { current_period_end: 200, stripe_subscription_id: "sub_1" }), false);
});
test("isStale: different subscription id → not stale (new sub always applies)", () => {
  assert.strictEqual(isStale(50, "sub_2", { current_period_end: 999, stripe_subscription_id: "sub_1" }), false);
});
test("isStale: no stored row → not stale (first event applies)", () => {
  assert.strictEqual(isStale(100, "sub_1", null), false);
  assert.strictEqual(isStale(100, "sub_1", {}), false);
});
test("isStale: stored current_period_end as ISO string (live DB shape) is parsed, not NaN", () => {
  // Supabase returns timestamptz as ISO; Number(ISO)=NaN would break the guard. epoch 2000000200 = 2033-05-18.
  const storedIso = new Date(2000000200 * 1000).toISOString();
  const row = { stripe_subscription_id: "sub_1", current_period_end: storedIso };
  assert.strictEqual(isStale(2000000050, "sub_1", row), true,  "older incoming vs ISO stored → stale");
  assert.strictEqual(isStale(2000000300, "sub_1", row), false, "newer incoming vs ISO stored → fresh");
});

// ── claimEvent / unclaimEvent: idempotency ledger 201/409 (REQ-36) ────────────
test("claimEvent: 201 → claimed(true); 409 → already(false)", async () => {
  const calls = [];
  const fakeFetch = async (url, opts) => { calls.push({ url, opts }); return { status: calls.length === 1 ? 201 : 409 }; };
  assert.strictEqual(await claimEvent("evt_1", "t", "http://s", "k", fakeFetch), true);
  assert.strictEqual(await claimEvent("evt_1", "t", "http://s", "k", fakeFetch), false);
  assert.match(calls[0].url, /lm_stripe_events/);
  assert.strictEqual(calls[0].opts.method, "POST");
});
test("claimEvent: no supa creds → true (local no-op, never blocks dev)", async () => {
  assert.strictEqual(await claimEvent("evt_1", "t", "", "", null), true);
});
test("unclaimEvent: DELETEs the claimed row (re-process on failure)", async () => {
  let del = null;
  const fakeFetch = async (url, opts) => { del = { url, method: opts.method }; return { status: 204 }; };
  await unclaimEvent("evt_1", "http://s", "k", fakeFetch);
  assert.match(del.url, /lm_stripe_events.*event_id=eq\.evt_1/);
  assert.strictEqual(del.method, "DELETE");
});
