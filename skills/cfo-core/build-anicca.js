#!/usr/bin/env node
/**
 * cfo-core/build-anicca.js
 * Assemble the PUBLIC aniccaai.com CFO payload (Anicca's own P&L + lifeline).
 *   income  = RevenueCat (MRR + 28d revenue, per-app) + Stripe web + actual bank deposits (Apple/Stripe)
 *   expense = Link active subs classified → anicca_runtime (founder_dev shown separately, personal excluded)
 *   lifeline = makes vs spends → net burn → "must earn to live"
 *
 * Runs the live fetchers/scrapes itself so it is cron-safe & self-contained.
 * Output JSON on stdout (→ dashboard.json by the pipeline).
 *
 * Env required: RC_API_KEY, STRIPE_SECRET_KEY, MUFG_DIRECT_*, LINK_EMAIL, GOG_KEYRING_PASSWORD
 */
const { execSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const SK = (p) => path.join(os.homedir(), '.openclaw/skills', p);
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'cfo-anicca-'));
const log = (...a) => console.error('[build-anicca]', ...a);

function run(cmd, outFile, timeoutMs) {
  log('run:', cmd);
  const out = execSync(cmd, { timeout: timeoutMs, maxBuffer: 1 << 24, env: process.env });
  if (outFile) fs.writeFileSync(outFile, out);
  return out.toString();
}
function tryJSON(s, fallback) { try { return JSON.parse(s); } catch { return fallback; } }

(async () => {
  // 1) revenue: RevenueCat live
  let rc = {};
  try { rc = tryJSON(run(`node ${SK('aniccaai-dashboard/scripts/fetch-rc.js')}`, null, 60000), {}); }
  catch (e) { log('rc fail', e.message); }

  // 2) revenue: Stripe web live
  let stripe = {};
  try { stripe = tryJSON(run(`node ${SK('aniccaai-dashboard/scripts/fetch-stripe.js')}`, null, 90000), {}); }
  catch (e) { log('stripe fail', e.message); }

  // 3) expense: Link subs → classify
  let cls = {};
  try {
    run(`bash ${SK('cfo-link/scripts/scrape.sh')}`, `${TMP}/link.json`, 180000);
    cls = tryJSON(run(`node ${SK('cfo-core/classify.js')} --link ${TMP}/link.json`, null, 30000), {});
  } catch (e) { log('link/classify fail', e.message); }

  // 4) actual landed deposits (Apple / Stripe) from bank (30d) + Stripe API (all-time)
  let deposits = { apple_jpy: 0, stripe_jpy: 0, stripe_all_time_jpy: 0 };
  try {
    run(`bash ${SK('cfo-bank/scripts/scrape.sh')}`, `${TMP}/bank.json`, 150000);
    const bank = tryJSON(fs.readFileSync(`${TMP}/bank.json`, 'utf-8'), { transactions: [] });
    for (const t of (bank.transactions || [])) {
      if (!t.in) continue;
      if (/APPLE|ｱｯﾌﾟﾙ|アップル/i.test(t.desc)) deposits.apple_jpy += t.in;
      if (/ストライプ|STRIPE/i.test(t.desc)) deposits.stripe_jpy += t.in;
    }
  } catch (e) { log('bank fail', e.message); }

  // 4b) Stripe API direct — all-time payouts (paid status = confirmed bank arrival)
  try {
    const out = run(`curl -sS "https://api.stripe.com/v1/payouts?limit=100&status=paid" -u "${process.env.STRIPE_SECRET_KEY}:"`, null, 30000);
    const payouts = JSON.parse(out);
    for (const p of (payouts.data || [])) {
      if (p.status !== 'paid') continue;
      if (p.currency === 'jpy') deposits.stripe_all_time_jpy += p.amount;
    }
    log(`Stripe all-time payouts JPY: ${deposits.stripe_all_time_jpy}`);
  } catch (e) { log('stripe payouts api fail', e.message); }

  // 5) compute
  const fx = cls.fx_jpy_per_usd || 155;
  const mrr = rc.mrr_usd ?? 0;
  const rev28 = rc.revenue_28d_usd ?? 0;
  const webMrr = (stripe.mrr_usd ?? stripe.total_mrr_usd ?? (stripe.by_product && stripe.by_product._other)) || 0;
  const makes_monthly = Math.round((mrr + webMrr) * 100) / 100;          // recurring
  const spends_monthly = (cls.totals_monthly_usd && cls.totals_monthly_usd.anicca_runtime) || 0;
  const net_monthly = Math.round((makes_monthly - spends_monthly) * 100) / 100;
  // Use all-time Stripe payouts (paid) as authoritative for stripe revenue
  const stripe_landed_jpy = Math.max(deposits.stripe_jpy, deposits.stripe_all_time_jpy);
  const total_landed_jpy = deposits.apple_jpy + stripe_landed_jpy;
  const landed_usd = Math.round((total_landed_jpy / fx) * 100) / 100;

  // Apple-confirmed (RevenueCat 28d revenue) — Apple 側 confirmed だが Apple→銀行 payout は 2-3ヶ月遅延
  const apple_confirmed_usd = rev28; // RevenueCat actual revenue (not MRR — actual)
  const apple_confirmed_jpy = Math.round(apple_confirmed_usd * fx);

  const payload = {
    schema: 'cfo-anicca/v1',
    updated_at: new Date().toISOString(),
    makes: {
      mrr_usd: mrr,
      revenue_28d_usd: rev28,
      web_mrr_usd: webMrr,
      by_app: rc.revenue_by_app || {},
      actually_landed_usd: landed_usd,
      actually_landed_jpy: total_landed_jpy,
      landed_breakdown_jpy: deposits,
      apple_confirmed_revenue_28d_usd: apple_confirmed_usd,
      apple_confirmed_revenue_28d_jpy: apple_confirmed_jpy,
      apple_confirmed_note: 'Apple-side confirmed (RevenueCat). 銀行口座着金は Apple 月末締め + 2-3 ヶ月遅延',
      monthly_total_usd: makes_monthly,
    },
    spends: {
      anicca_runtime_usd: spends_monthly,
      runtime_items: cls.anicca_runtime || [],
      founder_dev_usd: (cls.totals_monthly_usd && cls.totals_monthly_usd.founder_dev) || 0,
      founder_dev_note: 'Dais hands-on dev (Claude Max) — not Anicca\'s own running cost',
    },
    lifeline: {
      net_monthly_usd: net_monthly,
      status: net_monthly >= 0 ? 'THRIVE' : 'HUNGRY',
      message: net_monthly >= 0
        ? 'Anicca pays for itself.'
        : `Anicca must earn $${Math.abs(net_monthly)}/mo more to survive.`,
    },
    fx_jpy_per_usd: fx,
  };
  console.log(JSON.stringify(payload, null, 2));
  try { fs.rmSync(TMP, { recursive: true, force: true }); } catch {}
})();
