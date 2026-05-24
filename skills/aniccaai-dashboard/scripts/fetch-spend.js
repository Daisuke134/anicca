#!/usr/bin/env node
/**
 * Aggregate monthly spend.
 * Live: Apify usage, Railway estimated, Supabase subscription, fal.ai/ElevenLabs/HeyGen invoiced via Stripe (we paid them).
 * Fixed (config.json): Claude Max ($200), ChatGPT Plus ($20), Living ($200).
 *
 * Auth: APIFY_API_TOKEN, RAILWAY_TOKEN, SUPABASE_ACCESS_TOKEN env vars.
 */

const fs = require('fs');
const path = require('path');
const config = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'config.json'), 'utf-8'));

const APIFY = process.env.APIFY_API_TOKEN;
const RAILWAY = process.env.RAILWAY_TOKEN;
const SUPABASE = process.env.SUPABASE_ACCESS_TOKEN;
const RAILWAY_WS = config.railway_workspace_id;

async function apify() {
  if (!APIFY) return { value: null, error: 'APIFY_API_TOKEN missing' };
  try {
    const res = await fetch(`https://api.apify.com/v2/users/me?token=${APIFY}`);
    if (!res.ok) throw new Error(`Apify ${res.status}`);
    const d = await res.json();
    const plan = d.data?.plan || {};
    // FREE = $0/mo base + usage credits. Paid plans have monthlyBasePriceUsd.
    return { value: plan.monthlyBasePriceUsd ?? 0, plan: plan.id || plan.tier };
  } catch (err) {
    return { value: null, error: err.message };
  }
}

async function railway() {
  if (!RAILWAY) return { value: null, error: 'RAILWAY_TOKEN missing' };
  try {
    const res = await fetch('https://backboard.railway.com/graphql/v2', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${RAILWAY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: `{ estimatedUsage(measurements: [CPU_USAGE, MEMORY_USAGE_GB, NETWORK_TX_GB], workspaceId: "${RAILWAY_WS}") { measurement estimatedValue } }`
      })
    });
    const d = await res.json();
    if (d.errors) throw new Error(JSON.stringify(d.errors));
    // Pricing (Railway public docs):
    // CPU: $0.000463/min ≈ $20/vCPU/month
    // Memory: $0.000231/GB-min ≈ $10/GB/month
    // Network egress: $0.10/GB
    let usd = 0;
    for (const u of d.data.estimatedUsage) {
      const v = parseFloat(u.estimatedValue) || 0;
      if (u.measurement === 'CPU_USAGE') usd += v * 0.000463;
      else if (u.measurement === 'MEMORY_USAGE_GB') usd += v * 0.000231;
      else if (u.measurement === 'NETWORK_TX_GB') usd += v * 0.10;
    }
    return { value: Math.round(usd * 100) / 100, raw: d.data.estimatedUsage };
  } catch (err) {
    return { value: null, error: err.message };
  }
}

async function supabase() {
  if (!SUPABASE) return { value: null, error: 'SUPABASE_ACCESS_TOKEN missing' };
  try {
    const orgRes = await fetch('https://api.supabase.com/v1/organizations', {
      headers: { 'Authorization': `Bearer ${SUPABASE}` }
    });
    if (!orgRes.ok) throw new Error(`Supabase orgs ${orgRes.status}`);
    const orgs = await orgRes.json();
    let total = 0;
    const breakdown = [];
    for (const org of orgs) {
      const detail = await fetch(`https://api.supabase.com/v1/organizations/${org.id}`, {
        headers: { 'Authorization': `Bearer ${SUPABASE}` }
      });
      if (!detail.ok) continue;
      const o = await detail.json();
      const plan = (o.plan || 'free').toLowerCase();
      let monthly = 0;
      if (plan === 'pro') monthly = 25;
      else if (plan === 'team') monthly = 599;
      else if (plan === 'enterprise') monthly = 2000;
      total += monthly;
      breakdown.push({ org: org.name, plan, monthly_usd: monthly });
    }
    return { value: total, breakdown };
  } catch (err) {
    return { value: null, error: err.message };
  }
}

(async () => {
  const [apifyRes, railwayRes, supabaseRes] = await Promise.all([apify(), railway(), supabase()]);

  const fixed = config.fixed_subscriptions;

  const byCategory = {
    claude: fixed.claude.amount_usd,
    chatgpt: fixed.chatgpt.amount_usd,
    living: fixed.living.amount_usd,
    apify: apifyRes.value ?? 0,
    railway: railwayRes.value ?? 0,
    supabase: supabaseRes.value ?? 0,
    postiz: 99 // Postiz Pro plan when upgraded; will be replaced by Stripe-charged-by-postiz query later
  };

  const total = Math.round(Object.values(byCategory).reduce((a, b) => a + b, 0) * 100) / 100;

  console.log(JSON.stringify({
    total_usd: total,
    by_category: byCategory,
    fixed_subscriptions: [
      `claude: $${fixed.claude.amount_usd}/mo - ${fixed.claude.label}`,
      `chatgpt: $${fixed.chatgpt.amount_usd}/mo - ${fixed.chatgpt.label}`,
      `living: $${fixed.living.amount_usd}/mo - ${fixed.living.label}`
    ],
    sources: {
      apify: apifyRes,
      railway: railwayRes,
      supabase: supabaseRes
    },
    fetched_at: new Date().toISOString()
  }, null, 2));
})().catch(err => {
  console.error('fetch-spend error:', err.message);
  process.exit(2);
});
