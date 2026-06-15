#!/usr/bin/env node
// LIVE-on-aniccaai.com E2E. Posts a REAL Stripe-test-signed event to the deployed function URL,
// so the whole flow (signature verify → DO create → Supabase owners → DO destroy) runs in production.
// Proves the merged+live state on main/aniccaai.com — exactly what the separate verifier checks.
import Stripe from "stripe";

const URL = process.env.SPAWN_FN_URL || "https://aniccaai.com/.netlify/functions/stripe-spawn-webhook";
const KEY = process.env.STRIPE_SECRET_KEY;            // sk_test_… (only used to sign here)
const WH = process.env.STRIPE_SPAWN_WEBHOOK_SECRET;   // the real registered we_… secret deployed to Netlify
const DO_TOKEN = process.env.DIGITALOCEAN_TOKEN;
const SUPA_URL = process.env.SUPABASE_URL, SUPA_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
for (const [k, v] of Object.entries({ STRIPE_SECRET_KEY: KEY, STRIPE_SPAWN_WEBHOOK_SECRET: WH, DIGITALOCEAN_TOKEN: DO_TOKEN, SUPABASE_URL: SUPA_URL, SUPABASE_SERVICE_ROLE_KEY: SUPA_KEY }))
  if (!v) { console.error(`missing env ${k}`); process.exit(2); }

const stripe = new Stripe(KEY);
const SUB_ID = `sub_live_${Date.now()}`, EMAIL = `live+${Date.now()}@aniccaai.com`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function post(obj) {
  const payload = JSON.stringify(obj);
  const sig = stripe.webhooks.generateTestHeaderString({ payload, secret: WH });
  const r = await fetch(URL, { method: "POST", headers: { "stripe-signature": sig, "content-type": "application/json" }, body: payload });
  return { status: r.status, body: await r.text() };
}
async function doDroplet(id) { const r = await fetch(`https://api.digitalocean.com/v2/droplets/${id}`, { headers: { Authorization: `Bearer ${DO_TOKEN}` } }); return r.status; }
async function owner(sub) { const r = await fetch(`${SUPA_URL}/rest/v1/owners?sub_id=eq.${sub}&select=droplet_id,status`, { headers: { apikey: SUPA_KEY, Authorization: `Bearer ${SUPA_KEY}` } }); return (await r.json())[0]; }

(async () => {
  console.log("── LIVE-on-aniccaai.com E2E ──", URL);
  const r1 = await post({ id: `evt_live_c_${Date.now()}`, type: "checkout.session.completed",
    data: { object: { id: `cs_live_${Date.now()}`, customer_email: EMAIL, subscription: SUB_ID } } });
  console.log("checkout.session.completed →", r1.status, r1.body);
  if (r1.status !== 200) process.exit(1);
  const dropletId = JSON.parse(r1.body).droplet_id;
  console.log(`✅ LIVE function created REAL droplet id=${dropletId}; DO says status ${await doDroplet(dropletId)}`);
  console.log("   Supabase owners row:", JSON.stringify(await owner(SUB_ID)));

  const r2 = await post({ id: `evt_live_d_${Date.now()}`, type: "customer.subscription.deleted", data: { object: { id: SUB_ID } } });
  console.log("customer.subscription.deleted →", r2.status, r2.body);
  if (r2.status !== 200) process.exit(1);
  let gone = false; for (let i = 0; i < 20; i++) { if ((await doDroplet(dropletId)) === 404) { gone = true; break; } await sleep(3000); }
  console.log(gone ? `✅ DO confirms droplet ${dropletId} GONE (404)` : `FAIL: droplet ${dropletId} still alive`);
  console.log("   Supabase owners row:", JSON.stringify(await owner(SUB_ID)));
  if (!gone) process.exit(1);
  console.log(`\n🎯 LIVE-ON-PROD E2E PASSED — droplet ${dropletId} created then destroyed through aniccaai.com.`);
})().catch((e) => { console.error("ERROR", e); process.exit(1); });
