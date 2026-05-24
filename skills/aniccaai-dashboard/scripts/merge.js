#!/usr/bin/env node
/**
 * Merge sub-fetcher outputs into final dashboard.json.
 *
 * Usage: merge.js --stripe a.json --rc b.json --postiz c.json --followers d.json --spend e.json --config conf.json
 */

const fs = require('fs');

const args = process.argv.slice(2);
function getArg(name) {
  const idx = args.indexOf(`--${name}`);
  return idx !== -1 ? args[idx + 1] : null;
}

function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf-8')); } catch { return null; }
}

const stripe = readJson(getArg('stripe')) || { total_usd: 0, by_product: {} };
const rc = readJson(getArg('rc')) || { mrr_usd: null };
const postiz = readJson(getArg('postiz')) || { weekly_total_views: 0, posts_count: 0 };
const followers = readJson(getArg('followers')) || { total: 0, by_account: [] };
const spend = readJson(getArg('spend')) || { total_usd: 0, by_category: {} };
const config = readJson(getArg('config'));
// anicca-socials per-account snapshot (optional — written by anicca-socials skill)
const socials = readJson(process.env.HOME + '/.openclaw/skills/anicca-socials/state/socials_latest.json') || null;

if (!config) {
  console.error('config.json required');
  process.exit(1);
}

// MRR: combine Stripe per-product + RC mobile
const byProduct = { ...stripe.by_product };
if (rc.mrr_usd !== null && rc.mrr_usd !== undefined) {
  byProduct['anicca-ios-rc'] = rc.mrr_usd;
}
const mrrTotal = Math.round(Object.values(byProduct).reduce((a, b) => a + b, 0) * 100) / 100;

// Profit
const profit = Math.round((mrrTotal - spend.total_usd) * 100) / 100;

// Goals progress
const goalsTarget = config.goals.mrr_target;
const goalsProgressPct = goalsTarget > 0 ? Math.round((mrrTotal / goalsTarget) * 1000) / 10 : 0;

const out = {
  updated_at: new Date().toISOString(),
  mrr: {
    total_usd: mrrTotal,
    by_product: byProduct,
    sources: {
      stripe: stripe.total_usd,
      revenuecat_mobile: rc.mrr_usd
    }
  },
  followers: {
    total: followers.total,
    by_account: followers.by_account
  },
  views: {
    weekly_total: postiz.weekly_total_views,
    weekly_total_likes: postiz.weekly_total_likes,
    weekly_total_comments: postiz.weekly_total_comments,
    posts_count: postiz.posts_count,
    avg_views_per_post: postiz.avg_views_per_post,
    target: postiz.target,
    progress_pct: postiz.progress_pct
  },
  spend: {
    total_usd: spend.total_usd,
    by_category: spend.by_category,
    fixed_subscriptions: spend.fixed_subscriptions
  },
  profit_usd: profit,
  goals: {
    mrr_target: goalsTarget,
    mrr_deadline: config.goals.mrr_deadline,
    progress_pct: goalsProgressPct
  },
  basic_income: {
    pool_usd: Math.round(mrrTotal * 0.10 * 100) / 100,
    recipients: 0,
    per_person_usd: 0,
    next_payout: 'TBD'
  },
  socials: socials ? {
    updated_at: socials.updated_at,
    window_start: socials.window_start,
    window_end: socials.window_end,
    weekly_views: socials.totals.weekly_views,
    weekly_likes: socials.totals.weekly_likes,
    weekly_comments: socials.totals.weekly_comments,
    weekly_posts: socials.totals.weekly_posts,
    accounts_total: socials.totals.accounts,
    alive_accounts: socials.totals.alive_accounts,
    dead_accounts: socials.totals.dead_accounts,
    accounts: socials.accounts,
    dead_handles: socials.dead_handles,
    viral_handles: socials.viral_handles
  } : null,
  meta: {
    rc_status: rc.error ? 'unavailable' : 'ok',
    fetcher_versions: {
      stripe: stripe.fetched_at,
      rc: rc.fetched_at,
      postiz: postiz.fetched_at,
      followers: followers.fetched_at,
      spend: spend.fetched_at,
      socials: socials ? socials.updated_at : null
    }
  }
};

console.log(JSON.stringify(out, null, 2));
