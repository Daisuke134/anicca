---
name: basic-income-monthly
description: Monthly transfers loop for Anicca Basic Income. Runs on the 1st of each month at 09:00 JST. Calculates 10% of last month's MRR, divides by active recipient count, calls stripe.transfers.create() for each, logs to Supabase payouts table, sends Resend {{profile.lateness.stakeholders.channel}} + Slack report. Use when triggered by basic-income-monthly cron, or manually as `bash scripts/run.sh` for testing.
metadata:
  tags: stripe, basic-income, transfers, supabase, monthly
  requires:
    bins: [bash, node, jq, curl]
    env: [STRIPE_SECRET_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, RESEND_API_KEY]
---

# basic-income-monthly

## Pipeline

```
1. Fetch dashboard.json → mrr.total_usd (last 28d MRR from Stripe + RC)
2. Pool = MRR × 0.10 (in USD cents)
3. SELECT * FROM recipients WHERE status='active' AND kyc_complete=true
4. perPerson = pool / count (rounded down)
5. for each recipient:
   - stripe.transfers.create({amount, destination: stripe_account_id, currency: 'usd', description})
   - INSERT INTO payouts (recipient_id, stripe_transfer_id, amount, month, status='succeeded')
   - Resend {{profile.lateness.stakeholders.channel}} to recipient
6. Slack #metrics report
```

## Cron

| 項目 | 値 |
|------|---|
| name | `basic-income-monthly` |
| schedule | cron `0 9 1 * *` JST (月初 09:00) |
| script | `bash ~/.openclaw/skills/basic-income-monthly/scripts/run.sh` |

## Manual test (dry-run)

```bash
DRY_RUN=true bash ~/.openclaw/skills/basic-income-monthly/scripts/run.sh
```

Dry-run computes the payout but skips Stripe transfers and DB inserts.

## Test recipient ($0.01 transfer)

To validate the flow without real money: insert a test recipient with `monthly_amount_usd = 0.01` override and run with `TEST_RECIPIENT_ID=<uuid>`.

## Failure modes

| 失敗 | 対処 |
|----|----|
| Stripe transfer 失敗 (insufficient balance) | payout status='failed' + Slack alert + skip remaining |
| Recipient transfers capability not active | status='inactive' に flip + 通知 |
| Resend 失敗 | 払出は成功扱い、メールのみ retry queue |
