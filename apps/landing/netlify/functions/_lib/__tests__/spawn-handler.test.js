const { test, beforeEach } = require("node:test");
const assert = require("node:assert");
const { handler } = require("../../stripe-spawn-webhook");

// --- test doubles ---
function fakeStripe(eventToReturn, { throwOnVerify = false } = {}) {
  return {
    webhooks: {
      constructEvent(body, sig, secret) {
        if (throwOnVerify) throw new Error("No signatures found matching the expected signature");
        return eventToReturn;
      },
    },
  };
}

function makeOwners(overrides = {}) {
  const calls = { isEventSeen: 0, markEventSeen: 0, upsertOwner: 0, getOwnerBySub: 0, markDestroyed: 0 };
  const o = {
    seen: false,
    owner: null,
    async isEventSeen() { calls.isEventSeen++; return o.seen; },
    async markEventSeen() { calls.markEventSeen++; },
    async upsertOwner(r) { calls.upsertOwner++; o.lastUpsert = r; },
    async getOwnerBySub() { calls.getOwnerBySub++; return o.owner; },
    async markDestroyed() { calls.markDestroyed++; },
    ...overrides,
  };
  return { o, calls };
}

function ev() { return { httpMethod: "POST", body: "{}", headers: { "stripe-signature": "t=1,v1=abc" } }; }

beforeEach(() => {
  process.env.STRIPE_SECRET_KEY = "sk_test";
  process.env.STRIPE_SPAWN_WEBHOOK_SECRET = "whsec_test";
  process.env.DIGITALOCEAN_TOKEN = "do_tok";
  process.env.SUPABASE_URL = "https://x.supabase.co";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "svc";
});

test("405 on non-POST", async () => {
  const res = await handler({ httpMethod: "GET", headers: {} });
  assert.strictEqual(res.statusCode, 405);
});

test("500 when required env is missing", async () => {
  delete process.env.DIGITALOCEAN_TOKEN;
  const res = await handler(ev());
  assert.strictEqual(res.statusCode, 500);
  assert.strictEqual(res.body, "missing env");
});

test("400 on bad signature", async () => {
  const res = await handler(ev(), { stripeClient: fakeStripe(null, { throwOnVerify: true }) });
  assert.strictEqual(res.statusCode, 400);
  assert.ok(res.body.includes("Webhook Error"));
});

test("checkout.session.completed → create droplet + upsert owner + 200, markEventSeen AFTER", async () => {
  const { o, calls } = makeOwners();
  let created = 0, createArgs;
  const stripeEvent = { id: "evt_co", type: "checkout.session.completed",
    data: { object: { customer_email: "b@x.io", subscription: "sub_42" } } };
  const res = await handler(ev(), {
    stripeClient: fakeStripe(stripeEvent),
    owners: o,
    createDroplet: async (args) => { created++; createArgs = args; return 12345; },
  });
  assert.strictEqual(res.statusCode, 200);
  assert.deepStrictEqual(JSON.parse(res.body), { ok: true, droplet_id: 12345 });
  assert.strictEqual(created, 1);
  assert.strictEqual(createArgs.sub_id, "sub_42");
  assert.strictEqual(createArgs.owner_email, "b@x.io");
  assert.strictEqual(calls.upsertOwner, 1);
  assert.strictEqual(o.lastUpsert.droplet_id, 12345);
  assert.strictEqual(o.lastUpsert.status, "active");
  assert.strictEqual(calls.markEventSeen, 1);
});

test("duplicate event.id → 200 duplicate, NO droplet created (idempotent)", async () => {
  const { o, calls } = makeOwners({ seen: true });
  let created = 0;
  const stripeEvent = { id: "evt_dup", type: "checkout.session.completed",
    data: { object: { customer_email: "b@x.io", subscription: "sub_1" } } };
  const res = await handler(ev(), {
    stripeClient: fakeStripe(stripeEvent), owners: o,
    createDroplet: async () => { created++; return 1; },
  });
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body, "duplicate");
  assert.strictEqual(created, 0);
  assert.strictEqual(calls.markEventSeen, 0);
});

test("customer.subscription.deleted → destroy droplet + markDestroyed + 200", async () => {
  const { o, calls } = makeOwners();
  o.owner = { sub_id: "sub_42", droplet_id: 12345 };
  let destroyed;
  const stripeEvent = { id: "evt_del", type: "customer.subscription.deleted", data: { object: { id: "sub_42" } } };
  const res = await handler(ev(), {
    stripeClient: fakeStripe(stripeEvent), owners: o,
    destroyDroplet: async (id) => { destroyed = id; return true; },
  });
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(destroyed, 12345);
  assert.strictEqual(calls.markDestroyed, 1);
  assert.strictEqual(calls.markEventSeen, 1);
});

test("customer.subscription.deleted with no owner → 200 no owner, destroy NOT called", async () => {
  const { o, calls } = makeOwners();
  o.owner = null;
  let destroyed = 0;
  const stripeEvent = { id: "evt_del2", type: "customer.subscription.deleted", data: { object: { id: "sub_x" } } };
  const res = await handler(ev(), {
    stripeClient: fakeStripe(stripeEvent), owners: o,
    destroyDroplet: async () => { destroyed++; return true; },
  });
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body, "no owner");
  assert.strictEqual(destroyed, 0);
  assert.strictEqual(calls.markDestroyed, 0);
});

test("other event type → 200 ignored", async () => {
  const { o } = makeOwners();
  const stripeEvent = { id: "evt_other", type: "invoice.paid", data: { object: {} } };
  const res = await handler(ev(), { stripeClient: fakeStripe(stripeEvent), owners: o });
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body, "ignored");
});

test("markEventSeen NOT called when spawn throws (Stripe retry stays safe) → 500", async () => {
  const { o, calls } = makeOwners();
  const stripeEvent = { id: "evt_fail", type: "checkout.session.completed",
    data: { object: { customer_email: "b@x.io", subscription: "sub_z" } } };
  const res = await handler(ev(), {
    stripeClient: fakeStripe(stripeEvent), owners: o,
    createDroplet: async () => { throw new Error("DO create 503"); },
  });
  assert.strictEqual(res.statusCode, 500);
  assert.strictEqual(calls.markEventSeen, 0);
  assert.strictEqual(calls.upsertOwner, 0);
});

test("checkout.session.completed with no subscription → 200 no subscription, no droplet", async () => {
  const { o, calls } = makeOwners();
  let created = 0;
  const stripeEvent = { id: "evt_oneoff", type: "checkout.session.completed",
    data: { object: { customer_email: "b@x.io" } } };
  const res = await handler(ev(), {
    stripeClient: fakeStripe(stripeEvent), owners: o, createDroplet: async () => { created++; return 1; },
  });
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body, "no subscription");
  assert.strictEqual(created, 0);
  assert.strictEqual(calls.markEventSeen, 1);
});
