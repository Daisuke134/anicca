// Stripe webhook → cloud Anicca spawn/destroy (WF-A A-stripe-spawn; spec27 §2 / spec26 A8d / Q12 / Q6).
// checkout.session.completed → create a DO droplet (cloud-init) + upsert Supabase `owners`.
// customer.subscription.deleted → destroy that droplet + mark owner destroyed.
// Idempotency: event.id in `spawn_events`; side effects run BEFORE markEventSeen so a crashed
// spawn is retried by Stripe rather than silently lost.
//
// Required env (Netlify):
//   STRIPE_SECRET_KEY            — sk_live_...
//   STRIPE_SPAWN_WEBHOOK_SECRET  — whsec_... (Stripe webhook signing secret)
//   DIGITALOCEAN_TOKEN           — DO API v2 token
//   DO_SSH_KEY_FP                — ssh key fingerprint to inject (optional but recommended)
//   SUPABASE_URL                 — https://<proj>.supabase.co
//   SUPABASE_SERVICE_ROLE_KEY    — for owners + spawn_events tables

const stripe = require("stripe");
const { createDroplet, destroyDroplet } = require("./_lib/spawn-droplet");
const owners = require("./_lib/owners-store");

// deps is injectable for tests (no network). Defaults wire the real modules.
exports.handler = async (event, deps = {}) => {
  if (event.httpMethod !== "POST") return { statusCode: 405, body: "method not allowed" };

  const STRIPE_SECRET = process.env.STRIPE_SECRET_KEY;
  const WEBHOOK_SECRET = process.env.STRIPE_SPAWN_WEBHOOK_SECRET;
  const DO_TOKEN = process.env.DIGITALOCEAN_TOKEN;
  const SUPA_URL = process.env.SUPABASE_URL;
  const SUPA_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!STRIPE_SECRET || !WEBHOOK_SECRET || !DO_TOKEN || !SUPA_URL || !SUPA_KEY) {
    return { statusCode: 500, body: "missing env" };
  }

  const _create = deps.createDroplet || createDroplet;
  const _destroy = deps.destroyDroplet || destroyDroplet;
  const _owners = deps.owners || owners;
  const stripeClient = deps.stripeClient || stripe(STRIPE_SECRET);

  // 1) verify signature — never trust an unsigned body.
  let stripeEvent;
  try {
    stripeEvent = stripeClient.webhooks.constructEvent(
      event.body,
      event.headers["stripe-signature"] || event.headers["Stripe-Signature"],
      WEBHOOK_SECRET
    );
  } catch (err) {
    console.error("signature verify failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  const cfg = { url: SUPA_URL, key: SUPA_KEY };
  const doCfg = { token: DO_TOKEN, sshKeyFp: process.env.DO_SSH_KEY_FP };

  try {
    // 2) idempotency — skip anything we've already fully processed.
    if (await _owners.isEventSeen(stripeEvent.id, cfg)) {
      return { statusCode: 200, body: "duplicate" };
    }

    if (stripeEvent.type === "checkout.session.completed") {
      const session = stripeEvent.data.object || {};
      const email = session.customer_email || (session.customer_details && session.customer_details.email) || null;
      const sub_id = typeof session.subscription === "string" ? session.subscription : (session.subscription && session.subscription.id) || null;
      if (!sub_id) {
        // one-off payment / no subscription — nothing to spawn, but record so we don't reprocess.
        await _owners.markEventSeen(stripeEvent.id, cfg);
        return { statusCode: 200, body: "no subscription" };
      }
      const droplet_id = await _create({ owner_email: email, sub_id }, doCfg);
      await _owners.upsertOwner({ email, droplet_id, sub_id, status: "active" }, cfg);
      await _owners.markEventSeen(stripeEvent.id, cfg);
      console.log(`✅ spawned droplet ${droplet_id} for sub ${sub_id} (${email})`);
      return { statusCode: 200, body: JSON.stringify({ ok: true, droplet_id }) };
    }

    if (stripeEvent.type === "customer.subscription.deleted") {
      const sub_id = (stripeEvent.data.object && stripeEvent.data.object.id) || null;
      const owner = sub_id ? await _owners.getOwnerBySub(sub_id, cfg) : null;
      if (!owner || !owner.droplet_id) {
        await _owners.markEventSeen(stripeEvent.id, cfg);
        return { statusCode: 200, body: "no owner" };
      }
      // Self-funded: the instance cancelled its OWN subscription because it earns enough. Keep the
      // droplet alive — do NOT destroy. (P-auto-cancel guard.) An owner still "active" (e.g. a
      // dashboard cancel) falls through to _destroy as before.
      if (owner.status === "self_funded") {
        await _owners.markEventSeen(stripeEvent.id, cfg);
        console.log(`💚 self-funded sub ${sub_id} cancelled — droplet ${owner.droplet_id} kept alive`);
        return { statusCode: 200, body: JSON.stringify({ ok: true, kept: owner.droplet_id }) };
      }
      await _destroy(owner.droplet_id, doCfg);
      await _owners.markDestroyed(sub_id, cfg);
      await _owners.markEventSeen(stripeEvent.id, cfg);
      console.log(`🗑️ destroyed droplet ${owner.droplet_id} for cancelled sub ${sub_id}`);
      return { statusCode: 200, body: JSON.stringify({ ok: true, destroyed: owner.droplet_id }) };
    }

    // other event types — ack without side effects, record so retries are cheap.
    await _owners.markEventSeen(stripeEvent.id, cfg);
    return { statusCode: 200, body: "ignored" };
  } catch (err) {
    // side-effect failed BEFORE markEventSeen → Stripe will retry → idempotency-safe.
    console.error("spawn webhook error:", err);
    return { statusCode: 500, body: `webhook error: ${err.message}` };
  }
};
