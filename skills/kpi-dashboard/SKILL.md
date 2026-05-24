---
name: kpi-dashboard
description: "Daily KPI aggregation: Stripe revenue + Postiz post stats + Apify view/follower delta + Supabase subscribers. gpt-5.4-mini detects anomalies. Output: Slack post + JSON state log + optional /admin page update."
metadata:
  tags: kpi, stripe, postiz, apify, supabase, daily, anomaly-detection
  requires:
    bins: [curl, python3]
    env: [STRIPE_SECRET_KEY, APIFY_TOKEN, OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]
---

# KPI Dashboard — How to run

You are a cron-fired agent. Your only job is to run one bash command and exit.

## Trigger
- OpenClaw cron: daily 12:00 JST (use minute 13 to avoid :00 fleet collision)
- Cron message: `bash ~/.openclaw/skills/kpi-dashboard/scripts/run-detached.sh daily`

## What it does (informational)

1. Stripe: yesterday's charges, refunds, MRR (active subscriptions)
2. Postiz: post count from local `posted.jsonl`, fail rate
3. Apify: scrape each persona's TikTok profile → follower count, last post views
4. Supabase: `subscribers` count by lang/tier, daily_letter_log success rate
5. gpt-5.4-mini detects anomalies: zero-view streak / sales drop / churn spike / API failures
6. Output:
   - `~/anicca-monk-factory/state/kpi_<YYYYMMDD>.json` (machine)
   - `~/anicca-monk-factory/state/kpi_<YYYYMMDD>.md` (human)
   - Slack post if `SLACK_WEBHOOK_URL` set
   - (Phase 3) update `aniccaai.com/admin` static page

## Output schema (kpi_<date>.json)
```json
{
  "ts": "2026-05-09T12:13:00Z",
  "stripe": {"yesterday_revenue_usd": 32.97, "yesterday_count": 3, "mrr_usd": 89.97},
  "postiz": {"posted_24h": 4, "failed_24h": 0},
  "personas": [{"slug": "anicca.monk", "followers": 142, "last_view": 230}, ...],
  "supabase": {"subscribers_total": 12, "letters_sent_24h": 11, "bounce_24h": 0},
  "alerts": [{"severity": "high", "message": "@anicca.monk: 2 consecutive posts < 100 view"}]
}
```

## Failure handling
- If any data source fails (Stripe API down, Apify timeout): record `null` for that section, continue
- gpt-5.4-mini anomaly detection runs on whatever data was successfully collected
