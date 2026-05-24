#!/usr/bin/env node
/**
 * Fetch Stripe revenue this month, group by product category.
 * Output: { total: $, by_product: {category: $}, charges: int, currency_breakdown: {...} }
 *
 * Auth: STRIPE_SECRET_KEY env var.
 */

const SK = process.env.STRIPE_SECRET_KEY;
if (!SK) { console.error('ERR: STRIPE_SECRET_KEY missing'); process.exit(1); }

const fs = require('fs');
const path = require('path');
const config = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'config.json'), 'utf-8'));
const CATEGORY_MAP = config.stripe_category_map;

async function api(endpoint, params = {}) {
  const url = new URL(`https://api.stripe.com/v1${endpoint}`);
  for (const [k, v] of Object.entries(params)) {
    url.searchParams.append(k, v);
  }
  const res = await fetch(url, {
    headers: { 'Authorization': `Bearer ${SK}` }
  });
  if (!res.ok) throw new Error(`Stripe ${endpoint}: ${res.status} ${await res.text()}`);
  return res.json();
}

async function listAll(endpoint, params) {
  const items = [];
  let starting_after;
  while (true) {
    const p = { ...params, limit: '100' };
    if (starting_after) p.starting_after = starting_after;
    const data = await api(endpoint, p);
    items.push(...data.data);
    if (!data.has_more) break;
    starting_after = data.data[data.data.length - 1].id;
  }
  return items;
}

(async () => {
  // Month start in unix seconds (UTC)
  const now = new Date();
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const startTs = Math.floor(monthStart.getTime() / 1000);

  // 1. Charges this month (revenue from one-time + subs combined)
  const charges = await listAll('/charges', { 'created[gte]': startTs });
  const paid = charges.filter(c => c.paid && !c.refunded);

  // 2. Active subscriptions for MRR per category (annualized → monthly)
  const subs = await listAll('/subscriptions', { status: 'active' });

  // 3. Build per-category MRR
  const byProduct = {};
  for (const cat of new Set(Object.values(CATEGORY_MAP))) byProduct[cat] = 0;
  byProduct['_other'] = 0;

  // Charges → group by category. Sources of category:
  // 1) charge.metadata.category (donation Payment Link sets this)
  // 2) charge.metadata.product_id → CATEGORY_MAP
  // 3) Default to '_other'
  for (const c of paid) {
    let cat = '_other';
    if (c.metadata?.category) {
      cat = c.metadata.category;
      if (!(cat in byProduct)) byProduct[cat] = 0;
    } else {
      const productId = c.metadata?.product_id || null;
      cat = productId ? (CATEGORY_MAP[productId] || '_other') : '_other';
    }
    const usdAmount = c.currency === 'jpy' ? c.amount / 150 : c.amount / 100;
    byProduct[cat] += usdAmount;
  }

  // Subscriptions → MRR per item
  for (const sub of subs) {
    for (const item of sub.items.data) {
      const productId = item.price.product;
      const cat = CATEGORY_MAP[productId] || '_other';
      const interval = item.price.recurring?.interval || 'month';
      const intervalCount = item.price.recurring?.interval_count || 1;
      const unit = item.price.unit_amount || 0;
      const cur = item.price.currency;
      // Normalize to monthly USD
      let monthly = unit * (item.quantity || 1);
      if (interval === 'year') monthly = monthly / 12;
      if (interval === 'week') monthly = monthly * 4.333;
      monthly = monthly / intervalCount;
      const usd = cur === 'jpy' ? monthly / 150 : monthly / 100;
      byProduct[cat] += usd;
    }
  }

  // Round
  for (const k of Object.keys(byProduct)) byProduct[k] = Math.round(byProduct[k] * 100) / 100;

  const total = Math.round(Object.values(byProduct).reduce((a, b) => a + b, 0) * 100) / 100;

  const out = {
    total_usd: total,
    by_product: byProduct,
    charges_this_month: paid.length,
    active_subscriptions: subs.length,
    fetched_at: new Date().toISOString()
  };

  console.log(JSON.stringify(out, null, 2));
})().catch(err => {
  console.error('fetch-stripe error:', err.message);
  process.exit(2);
});
