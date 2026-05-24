---
name: daily-letter-sender
description: "Sends today's letter to all active subscribers via Resend Batch API. Each subscriber receives the letter at their personal day_offset (signup day → letter 1, day 2 → letter 2, etc.). Logs sends to Supabase daily_letter_log."
metadata:
  tags: newsletter, resend, supabase, daily, drip
  requires:
    bins: [curl, python3]
    env: [RESEND_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]
---

# Daily Letter Sender — How to run

You are a cron-fired agent. Your job is to run one bash command and exit.

## Trigger
- OpenClaw cron: daily 06:13 JST
- Cron message: `bash ~/.openclaw/skills/daily-letter-sender/scripts/run-detached.sh daily`

## What it does

1. Read all active subscribers from Supabase (`subscribers` table where `tier='free'` OR `tier='paid'`)
2. For each: compute `day_offset = (today - signed_up_at).days + 1`
3. Pick letter `bank_letter_<lang>.jsonl` line index `(day_offset - 1)`
4. Resend Batch API: send up to 100 letters per batch
5. Log sends to Supabase `daily_letter_log`
6. Bounce handler: mark `active=false` for hard bounces

## Tier rules (Phase 3)
- `tier='free'` → first 14 days only (then expires unless they upgrade)
- `tier='paid'` → unlimited days, cycles bank if > 365

## Output
- `~/anicca-monk-factory/state/letter_send_<YYYYMMDD>.log`
- Supabase rows in `daily_letter_log`
- Slack notification on completion if SLACK_WEBHOOK_URL set

## Failure handling
- If bank empty: abort with clear error
- If Resend rate-limited (3000/mo free tier): batch in chunks, sleep between
- Per-recipient send failure: log, continue
