---
name: donation
description: Anicca's autonomous philanthropy — Stripe Connect rail. On the 1st of each month at 09:00 JST, computes 1% of last month's Stripe revenue, splits it across recipients in recipients.json by weight, fires `stripe.transfers.create({destination: <connect_account_id>})` per recipient, generates a PDF receipt, and posts a public tweet via Postiz. Annual 1099 rollup on Jan 1. Use when user says "make donation now" or auto-fired by cron donation-monthly. Vercel Agent Browser rail for charities NOT on Stripe Connect lives in ~/.openclaw/skills/donation-v2-archive/.
metadata:
  tags: donation, stripe-connect, transfers, philanthropy, monthly, ending-suffering, 1099, receipt
  requires:
    bins: [python3, jq, curl]
    python_pkgs: [stripe, reportlab]
  requires_env: [STRIPE_API_KEY]
  optional_env:
    - STRIPE_WEBHOOK_SECRET
    - DONATION_DRY_RUN
    - POSTIZ_API_KEY
    - POSTIZ_X_INTEGRATION_ID
    - SLACK_BOT_TOKEN
---

# donation

Anicca's autonomous philanthropy on the **Stripe Connect transfers** rail.

## Two payment rails

This repo ships **two** payment rails because most US charities are not on
Stripe Connect:

| Rail | Lives at | When to use |
|------|----------|-------------|
| **A. Stripe Connect** *(this skill, default)* | `~/.openclaw/skills/donation/` | Charity onboarded as a Stripe Connected Account and `charges_enabled=true`. Direct, fee-free, idempotent, fully programmatic. |
| **B. Vercel Agent Browser** *(archive)* | `~/.openclaw/skills/donation-v2-archive/` | Charity is NOT on Stripe Connect and won't onboard. Drives the charity's existing donate page with a saved card. Slower, more brittle. |

Set `recipients.json[i].rail = "agent-{{profile.lateness.stakeholders.channel}}"` to fall through to rail B for
that one recipient. The default rail is `"stripe-connect"`.

## Invariants (do not violate)

- Rate: **`donation.percent` of last month's Stripe revenue**, default **1%**,
  floored at **$1**, no ceiling. Matches the public contract on
  `apps/landing/app/donation/page.tsx`.
- Revenue base: `stripe.charges.list` minus `stripe.refunds.list` for the
  closed prior month, in the account's currency, then converted to USD.
- Idempotency: every transfer carries `transfer_group=donation-YYYY-MM` and
  `idempotency_key=donation-YYYY-MM-<recipient_id>`. Re-runs that month are
  no-ops — Stripe rejects the duplicate key.
- Recipients: each entry must have `charges_enabled_verified=true` to receive
  funds. Unverified entries are skipped with a 🚨 to Slack.
- Weighted split: each recipient's share is `weight / sum(weights) * total`,
  rounded to nearest cent. Rounding remainder goes to the highest-weight entry.
- DRY_RUN defaults to **true** until the user flips `DONATION_DRY_RUN=false`
  in the cron payload. DRY_RUN: compute everything, write the run JSON, but
  do NOT call `transfers.create`.
- The skill never executes a `payouts.create`, never moves money out of
  Anicca's bank, and never modifies recipient bank/payout details.

## Pipeline

```
                   ┌─────────────────────────────┐
                   │ MONTHLY CRON (1st 09:00 JST) │
                   │ cron-id: donation-monthly    │
                   └─────────────┬───────────────┘
                                 ▼
   1. compute-revenue.py  ──►  charges - refunds for prior month   ──┐
                                                                     │
   2. percent-compute      ──►  amount = max(1, revenue * percent)   │
                                                                     │
   3. weighted split       ──►  per-recipient amounts (cents int)    │
                                                                     │
   4. transfer.py          ──►  stripe.transfers.create per entry    │
                                with idempotency_key + transfer_group│
                                                                     │
   5. pdf-receipt.py       ──►  workspace/donation/receipts/         │
                                YYYY-MM.pdf  (reportlab)             │
                                                                     │
   6. public-tweet.py      ──►  Postiz post on @aniccaxxx            │
                                (skip if DRY_RUN)                    │
                                                                     │
   7. write run-YYYY-MM.json   into ~/.openclaw/workspace/donation/ ◄┘

                   ┌─────────────────────────────┐
                   │ ANNUAL CRON (Jan 1 12:00 JST)│
                   │ cron-id: donation-annual-rollup│
                   └─────────────┬───────────────┘
                                 ▼
   annual-1099.py  ──►  rollup of all 12 monthly runs
                        emits one PDF per recipient suitable for 1099-MISC,
                        plus a CSV totals.csv for the LLC books.
```

## Files

| Path | Purpose |
|------|---------|
| `scripts/compute-revenue.py` | Pull `stripe.charges.list` + `stripe.refunds.list` for prior month, return USD totals. |
| `scripts/transfer.py`        | Per-recipient `stripe.transfers.create({destination, amount, currency, transfer_group, metadata})` with idempotency keys; waits for `succeeded`. |
| `scripts/pdf-receipt.py`     | reportlab → `workspace/donation/receipts/YYYY-MM.pdf` with month, total, breakdown, transaction IDs. |
| `scripts/public-tweet.py`    | Posts a single English tweet via Postiz REST. Reads `donation.tweet_account` for which integration ID. |
| `scripts/annual-1099.py`     | December rollup; one PDF per recipient + `totals.csv`. |
| `scripts/skip.sh`            | `donation skip <YYYY-MM>` — writes a `skipped-YYYY-MM.json` sentinel that the monthly cron honors as a no-op. |
| `recipients.json`            | `[{recipient_id, name, stripe_connect_account_id, weight, charges_enabled_verified, country, ein_or_npo_id, rail}]` |

## Output paths (under `~/.openclaw/workspace/donation/`)

| File | Written by | Contents |
|------|-----------|----------|
| `run-YYYY-MM.json`             | monthly cron      | `{period, dry_run, revenue_usd, total_amount_usd, transfers:[{recipient, amount, transfer_id, status}], receipt_pdf, tweet_status}` |
| `receipts/YYYY-MM.pdf`         | pdf-receipt.py    | Donor receipt PDF |
| `skipped-YYYY-MM.json`         | scripts/skip.sh   | Sentinel honored by the monthly cron |
| `1099/YYYY/<recipient>.pdf`    | annual-1099.py    | Per-recipient 12-month rollup |
| `1099/YYYY/totals.csv`         | annual-1099.py    | LLC books summary |

## Wizard config (read from `~/.openclaw/openclaw.json` → `skills.donation`)

| Key | Default | Purpose |
|-----|---------|---------|
| `donation.percent`             | `1` (interpreted as 1%) | Donation rate as a percent integer (1 = 1%). |
| `donation.recipients_path`     | `~/.openclaw/skills/donation/recipients.json` | Recipients file. |
| `donation.receipt_host`        | `https://aniccaai.com/donation` | Where receipts will be linked from publicly. |
| `donation.tweet_account`       | `@aniccaxxx` | Postiz integration to use. |
| `donation.tax_entity`          | `(set during wizard — LLC name for 1099)` | LLC name printed on receipt + 1099. |
| `donation.anonymize_amount`    | `false` | If true, public tweet shows "we donated this month" without the dollar amount. |
| `STRIPE_API_KEY`               | env | Already present in `~/.openclaw/.env`. Required. |
| `STRIPE_WEBHOOK_SECRET`        | env | For `charges_enabled` validation via webhook ingestion (out of scope of this skill, but the var is reserved). |

## Run commands

```bash
# Monthly run (DRY_RUN by default until user flips the cron env)
DONATION_DRY_RUN=true python3 ~/.openclaw/skills/donation/scripts/compute-revenue.py
DONATION_DRY_RUN=true python3 ~/.openclaw/skills/donation/scripts/transfer.py
DONATION_DRY_RUN=true python3 ~/.openclaw/skills/donation/scripts/pdf-receipt.py
DONATION_DRY_RUN=true python3 ~/.openclaw/skills/donation/scripts/public-tweet.py

# Annual rollup
python3 ~/.openclaw/skills/donation/scripts/annual-1099.py --year 2026

# Skip a month
bash ~/.openclaw/skills/donation/scripts/skip.sh 2026-05
```

## Crons

| ID | Schedule | Purpose |
|----|----------|---------|
| `donation-monthly`        | `0 9 1 * *`  JST | Monthly compute → transfer → receipt → tweet |
| `donation-annual-rollup`  | `0 12 1 1 *` JST | One-shot per year on Jan 1 |

## Surprises / open issues

- **Stripe Connect-onboarded charities are rare.** Most US 501(c)(3)s use
  Stripe Checkout, NOT Connect. Each recipient must run through the
  Connect onboarding flow (Stripe-hosted) and reach `charges_enabled=true`
  before it can receive `transfers.create`. The wizard cannot bypass this —
  the charity has to do it. Until then, route through rail B (the
  archive) for that recipient.
- **The starter `recipients.json` ships with `charges_enabled_verified=false`
  for every entry**, so the very first DRY_RUN will report "no eligible
  recipients" until the user verifies one. This is intentional — guards
  against blindly transferring on day one.
- **Postiz integration shared with build-in-public** — the same
  `POSTIZ_X_INTEGRATION_ID` (e.g. `cmm6d7m5703rwpr0yr5vtme3w` for
  `@aniccaxxx`) is reused. Open issue: does the donation skill share the
  build-in-public infra (one queue, one rate-limit budget) or duplicate it
  (separate queue, no risk of accidental DM-of-DM collision)? Spec says
  "check"; this skill reuses by default — set
  `donation.tweet_via_buildinpublic=false` to opt into a standalone post.

## Backup / archive

- Pre-rewrite v2 snapshot: `~/.openclaw/skills/_backups/donation-v2-pre-rewrite-<TS>/`
- Live archive of v2 (Vercel Agent Browser rail): `~/.openclaw/skills/donation-v2-archive/`
- Old shell scripts (`run.sh`, `install.sh`, `monthly.sh`, `lib/`) remain
  in `scripts/` as deprecation stubs because the sandboxed mount denies unlink.
  Each prints a notice and exits 1 if invoked. The v1 entrypoints are the
  Python scripts listed above.
