const { test } = require("node:test");
const assert = require("node:assert");
const crypto = require("crypto");

// env for the missing-env guards (values are dummies; no network in these tests).
process.env.SELF_CANCEL_MASTER_SECRET = process.env.SELF_CANCEL_MASTER_SECRET || "master-test";
process.env.STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY || "sk_test_x";
process.env.SUPABASE_URL = process.env.SUPABASE_URL || "https://x.supabase.co";
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || "svc";
process.env.STRIPE_SPAWN_WEBHOOK_SECRET = process.env.STRIPE_SPAWN_WEBHOOK_SECRET || "whsec_x";
process.env.DIGITALOCEAN_TOKEN = process.env.DIGITALOCEAN_TOKEN || "do_x";

const { handler: selfCancel, expectedToken } = require("../../self-cancel.js");
const { handler: webhook } = require("../../stripe-spawn-webhook.js");

const MASTER = process.env.SELF_CANCEL_MASTER_SECRET;
const tokFor = (sub) => crypto.createHmac("sha256", MASTER).update(sub).digest("base64url");

// ── self-cancel: per-instance token auth ──────────────────────────────────────
test("self-cancel rejects a bad token with 403", async () => {
  const r = await selfCancel(
    { httpMethod: "POST", body: JSON.stringify({ sub_id: "sub_1", token: "bad" }) },
    { owners: { markSelfFunded: async () => {} }, stripeClient: { subscriptions: { cancel: async () => {} } } },
  );
  assert.strictEqual(r.statusCode, 403);
});

test("self-cancel accepts a valid per-sub token → markSelfFunded + stripe cancel", async () => {
  let marked = null,
    cancelled = null;
  const r = await selfCancel(
    { httpMethod: "POST", body: JSON.stringify({ sub_id: "sub_1", token: tokFor("sub_1") }) },
    {
      owners: { markSelfFunded: async (s) => { marked = s; } },
      stripeClient: { subscriptions: { cancel: async (s) => { cancelled = s; } } },
    },
  );
  assert.strictEqual(r.statusCode, 200);
  assert.strictEqual(marked, "sub_1");
  assert.strictEqual(cancelled, "sub_1"); // mark BEFORE cancel (race safety)
});

test("self-cancel is idempotent on an already-cancelled sub (resource_missing → 200)", async () => {
  const r = await selfCancel(
    { httpMethod: "POST", body: JSON.stringify({ sub_id: "sub_1", token: tokFor("sub_1") }) },
    {
      owners: { markSelfFunded: async () => {} },
      stripeClient: {
        subscriptions: {
          cancel: async () => {
            const e = new Error("No such subscription");
            e.code = "resource_missing";
            throw e;
          },
        },
      },
    },
  );
  assert.strictEqual(r.statusCode, 200);
});

test("a leaked token for one sub cannot cancel a DIFFERENT sub (per-instance scope)", () => {
  assert.notStrictEqual(tokFor("sub_1"), tokFor("sub_2"));
  assert.strictEqual(expectedToken("sub_1", MASTER), tokFor("sub_1"));
});

// ── webhook guard: self_funded keeps the droplet; active still destroys ────────
function fakeStripeEvent(type, obj) {
  return { stripeClient: { webhooks: { constructEvent: () => ({ id: "evt_" + type, type, data: { object: obj } }) } } };
}

test("deleted webhook KEEPS the droplet for a self_funded owner (no destroy)", async () => {
  let destroyed = false;
  const r = await webhook(
    { httpMethod: "POST", headers: { "stripe-signature": "x" }, body: "{}" },
    {
      ...fakeStripeEvent("customer.subscription.deleted", { id: "sub_1" }),
      owners: {
        isEventSeen: async () => false,
        markEventSeen: async () => {},
        getOwnerBySub: async () => ({ sub_id: "sub_1", droplet_id: "drop1", status: "self_funded" }),
        markDestroyed: async () => {},
      },
      destroyDroplet: async () => { destroyed = true; },
    },
  );
  assert.strictEqual(r.statusCode, 200);
  assert.ok(/kept/.test(r.body), "self_funded → kept");
  assert.strictEqual(destroyed, false, "must NOT destroy a self_funded droplet");
});

test("deleted webhook STILL destroys an active owner (guard does not over-trigger)", async () => {
  let destroyed = false;
  await webhook(
    { httpMethod: "POST", headers: { "stripe-signature": "x" }, body: "{}" },
    {
      ...fakeStripeEvent("customer.subscription.deleted", { id: "sub_2" }),
      owners: {
        isEventSeen: async () => false,
        markEventSeen: async () => {},
        getOwnerBySub: async () => ({ sub_id: "sub_2", droplet_id: "drop2", status: "active" }),
        markDestroyed: async () => {},
      },
      destroyDroplet: async () => { destroyed = true; },
    },
  );
  assert.strictEqual(destroyed, true, "active owner → destroy as before");
});
