---
name: aniccaai-dashboard
description: Refresh aniccaai.com dashboard.json with live MRR (Stripe + RevenueCat), followers (Apify scraper), views (Postiz analytics), and spend (Railway/Supabase/Apify live + Claude/ChatGPT/Living fixed subscriptions). Commit + push to anicca-products repo for Netlify auto-build. Use when triggered by aniccaai-dashboard-refresh cron 4x/day, or told to "refresh dashboard", "update aniccaai.com numbers".
metadata:
  tags: dashboard, revenue, mrr, followers, spend, stripe, revenuecat, postiz, apify, railway
  requires:
    bins: [bash, python3, jq, curl, git]
    env: [STRIPE_SECRET_KEY, POSTIZ_API_KEY, APIFY_API_TOKEN, SUPABASE_ACCESS_TOKEN, RAILWAY_TOKEN, RC_API_KEY]
---

# aniccaai-dashboard

Live empire dashboard for aniccaai.com. **Zero hardcoded data.** All numbers from APIs except explicit subscription-plan fixed values declared in `data/config.json`.

## Pipeline

```
fetch-stripe.js   → Stripe charges + products + per-category MRR
fetch-rc.js       → RevenueCat overview (mobile MRR, active subs, churn)
fetch-postiz.js   → posts in window + per-post analytics → views totals
fetch-followers.js→ Apify scrape per handle (TT/IG/YT) + Twitter API
fetch-spend.js    → Live: Postiz/Supabase/Railway/Apify usage
                  → Fixed (config.json): Claude $200, ChatGPT $20, Living $200
merge.js          → combine into dashboard.json
deploy.sh         → git commit + push to anicca-products (Netlify auto-build)
```

## Config (`data/config.json`)

| Key | Value | Source |
|-----|------|------|
| goals.mrr_target | 10000 | constant (5月目標) |
| goals.mrr_deadline | "2026-05-31" | constant |
| goals.weekly_views_target | 1000000 | constant |
| fixed_subscriptions.claude.amount | 200 | Claude Max plan flat fee |
| fixed_subscriptions.chatgpt.amount | 20 | ChatGPT Plus flat fee |
| fixed_subscriptions.living.amount | 200 | Dais monthly burn (manual) |

## Stripe `metadata.category`

For per-product MRR breakdown, every Stripe product MUST have `metadata.category` set:

| category | products |
|---------|---------|
| `anicca-ios` | `prod_T5DuZfF5Cj2xcJ` (Anicca Pro) |
| `letter` | `prod_URieLh8XQX9v9s` (EN), `prod_URieWG8X0gUcG1` (JP) |
| `iglowup` | `prod_UR5WZuPI0imjnm` (Yearly), `prod_UR4eWC3NUo7btr` (Monthly) |
| `clearpdf` | `prod_UQw0YKIRiasv5y` |
| `anicca-app` | `prod_UQ2LrpVy4b1bAY` (JP), `prod_UQ2LTH66Rwict4` (EN) |
| `coldcraft` | `prod_U4YiuOW1XJP6HU` |
| `signaturecraft` | `prod_U4Sgi7Fu1Bkz4A` |
| `deepworkfm` | `prod_U4KicmEZfpkr9x` |

## Cron schedule

| cron | times | action |
|------|------|------|
| aniccaai-dashboard-refresh | 04:00 / 10:00 / 16:00 / 22:00 JST | refresh.sh → Netlify |

## Output: `dashboard.json` schema

```json
{
  "updated_at": "ISO 8601",
  "mrr": { "total": int, "by_product": {...} },
  "followers": { "total": int, "by_account": [...] },
  "views": { "weekly_total": int, "weekly_avg_per_post": int, "target": 1000000, "progress_pct": float },
  "spend": { "total": int, "by_category": {...}, "fixed_subscriptions": [...] },
  "profit": int,
  "goals": { "mrr_target": 10000, "mrr_deadline": "2026-05-31", "progress_pct": float },
  "basic_income": { "pool": int, "recipients": int, "per_person": int }
}
```

## Workflow

```bash
cd ~/.openclaw/skills/aniccaai-dashboard
bash scripts/refresh.sh
# Output: ~/anicca-products/apps/landing/public/dashboard.json
