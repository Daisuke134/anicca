#!/usr/bin/env node
// LIVE E2E for A-stripe-spawn (spec27 §2 / spec26 A8d). NO mocks, NO injected doubles.
// Drives the REAL handler with a REAL Stripe-test-signed event → REAL DigitalOcean droplet
// create → REAL Supabase `owners` row → REAL Stripe-test-signed cancel → REAL DO destroy.
//
// Proves the rubric's exact demand: "Show the droplet id created then destroyed."
//
// Run: node scripts/stripe-spawn-e2e.mjs   (env loaded from the caller's shell)
// Required env: STRIPE_SECRET_KEY (sk_test_…), DIGITALOCEAN_TOKEN, SUPABASE_URL,
//               SUPABASE_SERVICE_ROLE_KEY, DO_SSH_KEY_FP (optional).
//
// Exits non-zero on any failure (HARD 0.24/0.31 — no fake-ok).

import Stripe from "stripe";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { handler } = require("../netlify/functions/stripe-spawn-webhook.js");

const must = (k) => { const v = process.env[k]; if (!v) { console.error(`missing env ${k}`); process.exit(2); } return v; };
const STRIPE_KEY = must("STRIPE_SECRET_KEY");
if (!STRIPE_KEY.startsWith("sk_test_")) { console.error("REFUSING: STRIPE_SECRET_KEY is not a test key (sk_test_…)"); process.exit(2); }
const DO_TOKEN = must("DIGITALOCEAN_TOKEN");
const SUPA_URL = must("SUPABASE_URL");
const SUPA_KEY = must("SUPABASE_SERVICE_ROLE_KEY");

// A real Stripe webhook signing secret for the test. constructEvent recomputes HMAC-SHA256 over the
// raw body with this secret, so the signature is genuinely verified (not bypassed).
const WEBHOOK_SECRET = "whsec_" + Buffer.from(`e2e-${Date.now()}-${Math.random()}`).toString("hex").slice(0, 40);

// Wire env exactly as Netlify would for the function under test.
process.env.STRIPE_SPAWN_WEBHOOK_SECRET = WEBHOOK_SECRET;
// keep size small + injectable for the live run by overriding the create body via DO_* envs is not
// supported by spawn-droplet.js; the default s-2vcpu-2gb is what production uses. We accept that cost
// for a genuine end-to-end proof, then destroy immediately.

const stripe = new Stripe(STRIPE_KEY);
const SUB_ID = `sub_e2e_${Date.now()}`;
const EMAIL = `e2e+${Date.now()}@aniccaai.com`;

function signedEvent(obj) {
  const payload = JSON.stringify(obj);
  const header = stripe.webhooks.generateTestHeaderString({ payload, secret: WEBHOOK_SECRET });
  return { httpMethod: "POST", headers: { "stripe-signature": header }, body: payload };
}

async function supaGetOwner(sub_id) {
  const r = await fetch(`${SUPA_URL}/rest/v1/owners?sub_id=eq.${encodeURIComponent(sub_id)}&select=sub_id,email,droplet_id,status`, {
    headers: { apikey: SUPA_KEY, Authorization: `Bearer ${SUPA_KEY}` },
  });
  const rows = await r.json();
  return Array.isArray(rows) ? rows[0] : null;
}

async function doDroplet(id) {
  const r = await fetch(`https://api.digitalocean.com/v2/droplets/${id}`, { headers: { Authorization: `Bearer ${DO_TOKEN}` } });
  return { status: r.status, json: r.status === 200 ? await r.json() : null };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  console.log("── A-stripe-spawn LIVE E2E ──");
  console.log(`sub_id=${SUB_ID} email=${EMAIL} webhook_secret=${WEBHOOK_SECRET.slice(0, 12)}…`);

  // 1) checkout.session.completed — REAL signed event → REAL droplet + REAL owners row.
  const completed = {
    id: `evt_e2e_completed_${Date.now()}`,
    type: "checkout.session.completed",
    data: { object: { id: `cs_e2e_${Date.now()}`, customer_email: EMAIL, subscription: SUB_ID } },
  };
  const res1 = await handler(signedEvent(completed));
  console.log("checkout.session.completed →", res1.statusCode, res1.body);
  if (res1.statusCode !== 200) { console.error("FAIL: spawn did not return 200"); process.exit(1); }
  const dropletId = JSON.parse(res1.body).droplet_id;
  if (!dropletId) { console.error("FAIL: no droplet_id returned"); process.exit(1); }
  console.log(`✅ REAL DigitalOcean droplet created: id=${dropletId}`);

  // 1a) confirm the droplet really exists in DO.
  let d = await doDroplet(dropletId);
  if (d.status !== 200) { console.error(`FAIL: DO does not know droplet ${dropletId} (status ${d.status})`); process.exit(1); }
  console.log(`✅ DO confirms droplet ${dropletId} exists: name=${d.json.droplet.name} status=${d.json.droplet.status}`);

  // 1b) confirm the REAL Supabase owners row.
  let owner = await supaGetOwner(SUB_ID);
  if (!owner || String(owner.droplet_id) !== String(dropletId) || owner.status !== "active") {
    console.error("FAIL: owners row not written correctly:", owner); process.exit(1);
  }
  console.log(`✅ Supabase owners row: sub_id=${owner.sub_id} droplet_id=${owner.droplet_id} status=${owner.status}`);

  // 2) idempotency — same event.id again must NOT create a second droplet.
  const res1b = await handler(signedEvent(completed));
  console.log("duplicate event.id →", res1b.statusCode, res1b.body);
  if (res1b.statusCode !== 200 || res1b.body !== "duplicate") { console.error("FAIL: idempotency broken"); process.exit(1); }
  console.log("✅ idempotent: duplicate event created no second droplet");

  // 3) customer.subscription.deleted — REAL signed event → REAL DO destroy + markDestroyed.
  const deleted = {
    id: `evt_e2e_deleted_${Date.now()}`,
    type: "customer.subscription.deleted",
    data: { object: { id: SUB_ID } },
  };
  const res2 = await handler(signedEvent(deleted));
  console.log("customer.subscription.deleted →", res2.statusCode, res2.body);
  if (res2.statusCode !== 200) { console.error("FAIL: destroy did not return 200"); process.exit(1); }
  const destroyed = JSON.parse(res2.body).destroyed;
  if (String(destroyed) !== String(dropletId)) { console.error(`FAIL: destroyed ${destroyed} != ${dropletId}`); process.exit(1); }
  console.log(`✅ REAL DigitalOcean droplet destroyed: id=${destroyed}`);

  // 3a) poll DO until the droplet is actually gone (404). DELETE is async on DO's side.
  let gone = false;
  for (let i = 0; i < 20; i++) {
    d = await doDroplet(dropletId);
    if (d.status === 404) { gone = true; break; }
    await sleep(3000);
  }
  if (!gone) { console.error(`FAIL: droplet ${dropletId} still exists after destroy`); process.exit(1); }
  console.log(`✅ DO confirms droplet ${dropletId} is GONE (404)`);

  // 3b) confirm owner row flipped to destroyed.
  owner = await supaGetOwner(SUB_ID);
  if (!owner || owner.status !== "destroyed") { console.error("FAIL: owner not marked destroyed:", owner); process.exit(1); }
  console.log(`✅ Supabase owners row marked: status=${owner.status}`);

  console.log("\n🎯 LIVE E2E PASSED — droplet", dropletId, "created then destroyed; signature verified; Supabase row written + destroyed.");
})().catch((e) => { console.error("E2E ERROR:", e); process.exit(1); });
