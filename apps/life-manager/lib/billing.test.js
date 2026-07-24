"use strict";
// HARD-3 billing lifecycle — unit tests. Source of truth = Stripe subscription.status; ordering = event.created.
// Run: node --test lib/billing.test.js
const { test } = require("node:test");
const assert = require("node:assert");
const {
  entitlementFor, parseStripeEvent, isStale, toEpoch,
  claimEvent, unclaimEvent, applyBilling,
} = require("./billing.js");

// ── entitlementFor: the fixed Stripe status → entitlement table (REQ-38) ──────
test("entitlementFor: active/trialing/past_due → paid=true (provision + grace)", () => {
  for (const s of ["active", "trialing", "past_due", "ACTIVE", "Trialing"]) assert.strictEqual(entitlementFor(s).paid, true, s);
});
test("entitlementFor: canceled/unpaid/incomplete* → paid=false (revoke)", () => {
  for (const s of ["canceled", "unpaid", "incomplete", "incomplete_expired", "paused"]) assert.strictEqual(entitlementFor(s).paid, false, s);
});
test("entitlementFor: unknown/empty/null → paid=false (fail-safe)", () => {
  for (const s of [undefined, null, "", "weird"]) assert.strictEqual(entitlementFor(s).paid, false);
  assert.strictEqual(entitlementFor("active").plan_status, "active");
  assert.strictEqual(entitlementFor(null).plan_status, null);
});

// ── parseStripeEvent (REQ-37/38) ──────
test("parseStripeEvent: checkout → uid, customer, sub, paymentStatus, created", () => {
  const p = parseStripeEvent({ id: "e", type: "checkout.session.completed", created: 1700000000,
    data: { object: { client_reference_id: "uid-abc", customer: "cus_1", subscription: "sub_1", payment_status: "paid" } } });
  assert.deepStrictEqual([p.kind, p.uid, p.customerId, p.subscriptionId, p.paymentStatus, p.created],
    ["checkout", "uid-abc", "cus_1", "sub_1", "paid", 1700000000]);
});
test("parseStripeEvent: subscription.updated → status, currentPeriodEnd, created", () => {
  const p = parseStripeEvent({ id: "e", type: "customer.subscription.updated", created: 1700000005,
    data: { object: { id: "sub_1", customer: "cus_1", status: "past_due", current_period_end: 1750000000 } } });
  assert.deepStrictEqual([p.kind, p.customerId, p.subscriptionId, p.status, p.currentPeriodEnd, p.created],
    ["subscription", "cus_1", "sub_1", "past_due", 1750000000, 1700000005]);
});
test("parseStripeEvent: deleted → canceled; unknown → null", () => {
  assert.strictEqual(parseStripeEvent({ id: "e", type: "customer.subscription.deleted", data: { object: { status: "canceled" } } }).status, "canceled");
  assert.strictEqual(parseStripeEvent({ id: "x", type: "ping", data: { object: {} } }), null);
});

// ── isStale: out-of-order guard keyed on event.created (REQ-39, FIND-002) ──────
test("isStale: older created → stale; newer/equal → fresh", () => {
  const row = { stripe_event_at: new Date(1700000100 * 1000).toISOString() };
  assert.strictEqual(isStale(1700000050, row), true);
  assert.strictEqual(isStale(1700000200, row), false);
  assert.strictEqual(isStale(1700000100, row), false);
});
test("isStale: no stored timestamp → never stale (first event applies)", () => {
  assert.strictEqual(isStale(100, null), false);
  assert.strictEqual(isStale(100, {}), false);
});
test("FIND-002: immediate-cancel with LOWER current_period_end but LATER created still applies (not stale)", () => {
  // active applied at created=1700000100 (period_end far future); cancel arrives later created=1700000200
  // but with an earlier current_period_end. Keyed on created → cancel is NOT stale → downgrade applies.
  const row = { stripe_event_at: new Date(1700000100 * 1000).toISOString() };
  assert.strictEqual(isStale(1700000200, row), false, "cancel (later created) must apply even with lower period_end");
});
test("toEpoch parses ISO + numeric + epoch", () => {
  assert.strictEqual(toEpoch(1700000100), 1700000100);
  assert.strictEqual(toEpoch("1700000100"), 1700000100);
  assert.strictEqual(toEpoch(new Date(1700000100 * 1000).toISOString()), 1700000100);
  assert.strictEqual(toEpoch(null), 0);
});

// ── claim / unclaim idempotency ledger (REQ-36) ──────
test("claimEvent: 201 → true; 409 → false; no creds → true", async () => {
  let n = 0;
  const f = async () => ({ status: ++n === 1 ? 201 : 409 });
  assert.strictEqual(await claimEvent("e1", "t", "http://s", "k", f), true);
  assert.strictEqual(await claimEvent("e1", "t", "http://s", "k", f), false);
  assert.strictEqual(await claimEvent("e1", "t", "", "", null), true);
});
test("unclaimEvent: DELETE → true; failure → false (caller logs RECONCILE)", async () => {
  assert.strictEqual(await unclaimEvent("e1", "http://s", "k", async () => ({ status: 204 })), true);
  assert.strictEqual(await unclaimEvent("e1", "http://s", "k", async () => ({ status: 500 })), false);
});

// ── applyBilling: the orchestration core (REQ-37/38/39/40, FIND-004) ──────
// fakeSupa: routes PostgREST calls; GET lm_users?stripe_customer_id → storedRow; PATCH → records patch.
function fakeSupa(storedRow) {
  const patches = [];
  const f = async (url, opts) => {
    const method = opts && opts.method;
    if (!method && url.includes("select=")) // a GET lookup (userByCustomer or userByUid)
      return { ok: true, json: async () => (storedRow ? [storedRow] : []) };
    if (method === "PATCH" && url.includes("lm_users?uid=eq.")) {
      patches.push({ url, body: JSON.parse(opts.body) }); return { status: 204 };
    }
    return { ok: false, status: 404, json: async () => [] };
  };
  return { f, patches };
}
const deps = (supa, notify) => ({ supaUrl: "http://s", supaKey: "k", fetchImpl: supa.f, notify });

test("applyBilling checkout PAID → provision (paid=true, plan=active, linked)", async () => {
  const s = fakeSupa(null);
  const r = await applyBilling({ id: "e", type: "checkout.session.completed", created: 100,
    data: { object: { client_reference_id: "u1", customer: "cus", subscription: "sub", payment_status: "paid" } } }, deps(s));
  assert.strictEqual(r.action, "provision");
  assert.strictEqual(s.patches[0].body.paid, true);
  assert.strictEqual(s.patches[0].body.plan_status, "active");
  assert.strictEqual(s.patches[0].body.stripe_customer_id, "cus");
});
test("applyBilling checkout UNPAID → link only, paid=false (FIND-003)", async () => {
  const s = fakeSupa(null);
  const r = await applyBilling({ id: "e", type: "checkout.session.completed", created: 100,
    data: { object: { client_reference_id: "u1", customer: "cus", subscription: "sub", payment_status: "unpaid" } } }, deps(s));
  assert.strictEqual(r.action, "link-unpaid");
  assert.strictEqual(s.patches[0].body.paid, false);
});
test("FIND-007: out-of-order UNPAID checkout (older created) does NOT clobber an active payer", async () => {
  // a subscription.active was already applied at created=200 (paid=true); a LATE unpaid checkout (created=100)
  // must be stale → NO write → the active payer keeps paid=true and stripe_event_at is not regressed.
  const row = { uid: "u1", paid: true, stripe_event_at: new Date(200 * 1000).toISOString() };
  const s = fakeSupa(row);
  const r = await applyBilling({ id: "e", type: "checkout.session.completed", created: 100,
    data: { object: { client_reference_id: "u1", customer: "cus", payment_status: "unpaid" } } }, deps(s));
  assert.strictEqual(r.action, "stale-checkout");
  assert.strictEqual(s.patches.length, 0, "no write — active payer not downgraded, timestamp not regressed");
});
test("FIND-007: a FRESH checkout (no prior event) still provisions (first event never stale)", async () => {
  const s = fakeSupa(null);
  const r = await applyBilling({ id: "e", type: "checkout.session.completed", created: 100,
    data: { object: { client_reference_id: "u1", customer: "cus", subscription: "sub", payment_status: "paid" } } }, deps(s));
  assert.strictEqual(r.action, "provision");
  assert.strictEqual(s.patches[0].body.paid, true);
});
test("applyBilling subscription active → provision; canceled → deprovision", async () => {
  const row = { uid: "u1", stripe_event_at: new Date(50 * 1000).toISOString() };
  let s = fakeSupa(row);
  let r = await applyBilling({ id: "e", type: "customer.subscription.updated", created: 100,
    data: { object: { id: "sub", customer: "cus", status: "active", current_period_end: 999 } } }, deps(s));
  assert.strictEqual(r.action, "provision"); assert.strictEqual(s.patches[0].body.paid, true);
  s = fakeSupa(row);
  r = await applyBilling({ id: "e", type: "customer.subscription.deleted", created: 100,
    data: { object: { id: "sub", customer: "cus", status: "canceled", current_period_end: 999 } } }, deps(s));
  assert.strictEqual(r.action, "deprovision"); assert.strictEqual(s.patches[0].body.paid, false);
});
test("applyBilling subscription STALE (older created) → no write", async () => {
  const row = { uid: "u1", stripe_event_at: new Date(200 * 1000).toISOString() };
  const s = fakeSupa(row);
  const r = await applyBilling({ id: "e", type: "customer.subscription.updated", created: 100,
    data: { object: { id: "sub", customer: "cus", status: "active", current_period_end: 999 } } }, deps(s));
  assert.strictEqual(r.action, "stale"); assert.strictEqual(s.patches.length, 0);
});
test("applyBilling orphan customer (no row) → no-op, no throw", async () => {
  const s = fakeSupa(null);
  const r = await applyBilling({ id: "e", type: "customer.subscription.updated", created: 100,
    data: { object: { id: "sub", customer: "cus_unknown", status: "active" } } }, deps(s));
  assert.strictEqual(r.action, "orphan-subscription"); assert.strictEqual(s.patches.length, 0);
});
test("applyBilling past_due → paid=true (grace) + dunning notify fired once", async () => {
  const row = { uid: "u1", stripe_event_at: new Date(50 * 1000).toISOString() };
  const s = fakeSupa(row); let dunned = [];
  const r = await applyBilling({ id: "e", type: "customer.subscription.updated", created: 100,
    data: { object: { id: "sub", customer: "cus", status: "past_due", current_period_end: 999 } } }, deps(s, (uid) => dunned.push(uid)));
  assert.strictEqual(r.paid, true); assert.strictEqual(s.patches[0].body.plan_status, "past_due");
  assert.deepStrictEqual(dunned, ["u1"]);
});
test("applyBilling unknown event type → ignored, no write", async () => {
  const s = fakeSupa(null);
  const r = await applyBilling({ id: "e", type: "invoice.created", data: { object: {} } }, deps(s));
  assert.strictEqual(r.action, "ignored"); assert.strictEqual(s.patches.length, 0);
});
test("applyBilling patch failure → throws (handler 500s + unclaims)", async () => {
  const failSupa = { f: async (url, opts) => (opts && opts.method === "PATCH" ? { status: 500 } : { ok: true, json: async () => [{ uid: "u1" }] }) };
  await assert.rejects(applyBilling({ id: "e", type: "checkout.session.completed", created: 100,
    data: { object: { client_reference_id: "u1", customer: "cus", payment_status: "paid" } } },
    { supaUrl: "http://s", supaKey: "k", fetchImpl: failSupa.f }));
});
