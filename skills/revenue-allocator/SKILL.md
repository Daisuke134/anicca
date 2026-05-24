---
name: revenue-allocator
description: "Monthly revenue → spend → profit → re-investment allocator. Reads live dashboard.json (Stripe + RevenueCat MRR, full spend breakdown, profit), pulls live Apify monthly usage, computes re-investment budget (60% of profit when positive), distributes per-persona budgets across active personas in personas.json, and posts a comprehensive Slack monthly report. Runs monthly 1st 09:00 JST."
metadata:
  tags: revenue, mrr, spend, allocation, monthly, treasury, stripe, revenuecat
  requires:
    bins: [python3, jq, curl]
    env: [APIFY_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID]
  data_source:
    - ~/anicca-products/apps/landing/public/dashboard.json
    - ~/anicca-monk-factory/personas.json
---

# revenue-allocator

Monthly treasury orchestrator. Single source of truth for "where the money is, where it's going, what's our headroom."

## What it does

1. Read `~/anicca-products/apps/landing/public/dashboard.json` (already populated by `aniccaai-dashboard` skill: Stripe + RC + Postiz + spend)
2. Pull live Apify monthly usage from `https://api.apify.com/v2/users/me/usage/monthly` (current cycle spend)
3. Compute:
   - MRR total (live)
   - Spend total (live, dashboard.json)
   - Profit = MRR - Spend
   - Reinvestment budget = max(0, profit) × 0.6 (60% reinvest, 40% reserve)
   - Basic income pool = MRR × 0.10 (existing rule)
   - Per-persona budget = reinvestment_budget / active_persona_count
4. Update `~/anicca-monk-factory/personas.json` with each persona's `monthly_budget_usd`
5. Snapshot to `state/allocation_<YYYYMM>.json`
6. Post Slack message:
   - MRR / Spend / Profit / Reinvest / Per-persona budget
   - Apify monthly usage with cycle window
   - Top spending categories
   - Health alerts (e.g. "spend exceeds MRR by $X — runway negative")

## When triggered

| Mode | Schedule | What |
|---|---|---|
| Auto | monthly 1st 09:00 JST (`0 9 1 * *`) | Full monthly cycle: snapshot + persona budget update + Slack |
| On-demand | `bash ~/.openclaw/skills/revenue-allocator/scripts/run.sh` | Same logic, ad-hoc check |

## Output schema

`state/allocation_<YYYYMM>.json`:

```json
{
  "month": "2026-05",
  "computed_at": "2026-05-08T11:00:00Z",
  "mrr": { "total_usd": 67.99, "stripe": 10.99, "revenuecat_mobile": 57.0 },
  "spend": { "total_usd": 519.0, "by_category": { "claude": 200, "chatgpt": 20, "living": 200, "postiz": 99, "apify": 0, "railway": 0, "supabase": 0 } },
  "profit_usd": -451.01,
  "reinvest_budget_usd": 0,
  "basic_income_pool_usd": 6.8,
  "active_personas": 3,
  "per_persona_budget_usd": 0,
  "apify_usage": { "cycle_start": "2026-04-27", "cycle_end": "2026-05-26", "consumed_usd": 0.04, "alert": false },
  "alerts": [
    { "severity": "high", "message": "Spend exceeds MRR by $451 — runway negative" }
  ]
}
```

## Slack message format

```
*💰 Monthly Revenue Allocator — 2026-05*

*MRR*: $67.99  (Stripe $10.99 · RC mobile $57.00)
*Spend*: $519.00  (Claude $200 · ChatGPT $20 · Living $200 · Postiz $99)
*Profit*: -$451.01  ⚠️ runway negative

*Reinvestment*: $0 (no profit to allocate)
*Basic income pool*: $6.80 (10% of MRR)
*Per-persona budget*: $0 / 3 active personas

*Apify cycle 2026-04-27 → 2026-05-26*: $0.04 consumed (FREE plan)

*Health alerts:*
🔴 Spend exceeds MRR by $451 — runway negative. Cut: Claude $200 (review usage) / ChatGPT $20 (already minimal)
```

## Why this exists

- $10K MRR target by YYYY-MM-DD. Without monthly visibility into MRR vs spend, we don't know if we're 30% there or 100% there or upside-down.
- Per-persona budget cap prevents runaway API spend on a single persona.
- Triggers cascade decisions: when reinvest_budget > 0, factory expansion is unlocked. When negative, cron disables of expensive factories.

## Failure modes

| Symptom | Cause | Recovery |
|---|---|---|
| dashboard.json missing | aniccaai-dashboard cron failed | run `bash ~/.openclaw/skills/aniccaai-dashboard/scripts/refresh.sh` |
| Slack post fails | SLACK_BOT_TOKEN expired | refresh in `~/.openclaw/.env` |
| Apify 401 | APIFY_TOKEN expired | refresh in `~/anicca-monk-factory/.env` |

## Non-goals (deferred to Phase 5)

- **Auto top-up via Stripe Issuing**: requires Stripe Issuing setup + virtual cards. Out of scope until $1K MRR.
- **HeyGen / fal / ElevenLabs balance probes**: those APIs require separate keys we don't store. Manual top-up notifications via Slack are sufficient until volumes warrant automation.
