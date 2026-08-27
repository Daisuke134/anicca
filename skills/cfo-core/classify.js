#!/usr/bin/env node
/**
 * cfo-core classifier.
 * Tags Link subscriptions + bank transactions into:
 *   anicca_runtime | founder_dev | personal
 * Normalizes to monthly USD. Separates Anicca's true operating cost from
 * Dais's hands-on dev cost (Claude Max) and personal spend.
 *
 * Usage:
 *   node classify.js --link /tmp/cfo-link.json [--fx 155]
 * Output JSON on stdout.
 */
const fs = require('fs');

function arg(name, def) {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : def;
}
const FX = parseFloat(arg('--fx', '155')); // JPY per USD (rough; refresh daily later)

// vendor (substring, case-insensitive) -> { cat, label }
const VENDOR_MAP = [
  // founder dev: Dais wants to build by hand — NOT Anicca's own survival cost
  [/anthropic|claude/i, 'founder_dev', 'Claude (Dais hands-on dev)'],
  // anicca runtime: what Anicca needs to run / produce / post itself
  [/openai|gpt|codex/i, 'anicca_runtime', 'GPT/Codex (model Anicca runs on)'],
  [/reelfarm|reel\.far/i, 'anicca_runtime', 'ReelFarm (video)'],
  [/postiz/i, 'anicca_runtime', 'Postiz (posting)'],
  [/grok|xai/i, 'anicca_runtime', 'Grok xAI (read X)'],
  [/heygen/i, 'anicca_runtime', 'HeyGen (video)'],
  [/eleven ?labs/i, 'anicca_runtime', 'ElevenLabs (voice)'],
  [/\bfal\b|fal\.ai|fal feat/i, 'anicca_runtime', 'fal.ai (image/video gen)'],
  [/supabase/i, 'anicca_runtime', 'Supabase (DB)'],
  [/hetzner/i, 'anicca_runtime', 'Hetzner (VPS)'],
  [/apiframe/i, 'anicca_runtime', 'APIFrame (MJ API)'],
  [/distrokid/i, 'anicca_runtime', 'DistroKid (music distribution)'],
  [/printful/i, 'anicca_runtime', 'Printful (merch)'],
  // personal: Dais's own, never on aniccaai.com
  [/aqua/i, 'personal', 'Aqua Voice (Dais personal)'],
];

// subs known to bill annually (Link shows next-date, not cadence)
const ANNUAL = [/aqua/i, /mobbin/i, /firecrawl/i, /openart/i, /sleek/i, /higgsfield/i, /distrokid/i];

function classifyVendor(name) {
  for (const [rx, cat, label] of VENDOR_MAP) if (rx.test(name)) return { cat, label };
  return { cat: 'unknown', label: name };
}
function isAnnual(name) { return ANNUAL.some(rx => rx.test(name)); }

function toMonthlyUSD(amount, currency, name) {
  if (amount == null) return 0;
  let usd = currency === 'JPY' ? amount / FX : amount;
  if (isAnnual(name)) usd = usd / 12;
  return Math.round(usd * 100) / 100;
}

const linkPath = arg('--link');
if (!linkPath) { console.error('FATAL: --link <cfo-link.json> required'); process.exit(1); }
const link = JSON.parse(fs.readFileSync(linkPath, 'utf-8'));

const overridesPath = `${__dirname}/data/cancelled-overrides.json`;
let cancelledRules = [];
try {
  const o = JSON.parse(fs.readFileSync(overridesPath, 'utf-8'));
  cancelledRules = (o.cancelled_vendors || []).map(v => ({ rx: new RegExp(v.match, 'i'), reason: v.reason, at: v.cancelled_at }));
} catch (e) { /* file optional */ }

function isCancelled(name) {
  for (const r of cancelledRules) if (r.rx.test(name)) return r;
  return null;
}

const items = [];
const cancelled = [];
for (const s of (link.active_subscriptions || [])) {
  const cx = isCancelled(s.name);
  if (cx) { cancelled.push({ vendor: s.name, price_raw: s.price_raw, cancelled_at: cx.at, reason: cx.reason }); continue; }
  const { cat, label } = classifyVendor(s.name);
  items.push({
    vendor: s.name, label, category: cat,
    price_raw: s.price_raw,
    monthly_usd: toMonthlyUSD(s.amount, s.currency, s.name),
    cadence: isAnnual(s.name) ? 'annual' : 'monthly',
  });
}

const sum = (cat) => Math.round(items.filter(i => i.category === cat).reduce((a, b) => a + b.monthly_usd, 0) * 100) / 100;

const out = {
  source: 'cfo-core/classify',
  fx_jpy_per_usd: FX,
  anicca_runtime: items.filter(i => i.category === 'anicca_runtime'),
  founder_dev: items.filter(i => i.category === 'founder_dev'),
  personal: items.filter(i => i.category === 'personal'),
  unknown: items.filter(i => i.category === 'unknown'),
  totals_monthly_usd: {
    anicca_runtime: sum('anicca_runtime'),
    founder_dev: sum('founder_dev'),
    personal: sum('personal'),
    unknown: sum('unknown'),
  },
  generated_at: new Date().toISOString(),
};
console.log(JSON.stringify(out, null, 2));
