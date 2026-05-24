---
name: trustmrr
description: List Anicca products on trustmrr.com (verified startup revenue marketplace, 120k+ monthly visitors, 50+ DR dofollow backlink). Auto-creates listing via "Add startup" modal with Stripe rk_live_ key, claims via {{profile.lateness.stakeholders.channel}} OTP, persists ownership to dashboard. Auto-flags listings "for sale" when MRR > $500 AND 30d growth < 5%. Use when triggered by `trustmrr-list-weekly` cron at Mon 06:00 JST, or manually as `bash scripts/list-products.sh`.
metadata:
  tags: trustmrr, marketplace, exit, revenue, startup-sale, {{profile.lateness.stakeholders.channel}}-harness
  requires:
    bins: [bash, jq, curl, {{profile.lateness.stakeholders.channel}}-harness]
    env: [STRIPE_RK_LIVE_ALL, DAIS_EMAIL]
---

# trustmrr

End-to-end TrustMRR listing skill — verified revenue → marketplace presence → optional sale.

## Why TrustMRR

| Metric | Value |
|----|----|
| Monthly visitors | 120,000+ |
| Backlink DR | 54+ dofollow |
| Sale multiple | 0.6× – 5.3× MRR (live data) |
| Verification | Stripe rk_live restricted key (auto-refresh) |

## End-to-end flow (verified working 2026-05-05)

```
1. {{profile.lateness.stakeholders.channel}}-harness Way 2 (Chrome 9223 isolated profile, persistent cookies)
2. goto_url('https://trustmrr.com/')
3. Click 'Add startup' button (top of marketplace)
4. Modal opens with 6 fields:
   - apiKey (text, name="apiKey", placeholder="rk_live_...")
   - X handle (text, placeholder="username", optional)
   - Anonymous mode (checkbox)
   - List for sale (checkbox)
5. Fill apiKey via JS setNativeValue + dispatchEvent
6. Fill X handle same way
7. Click 'Add startup' — Stripe API call validates the key (5-15 sec)
8. Page navigates to https://trustmrr.com/startup/<slug>
9. "Log in to claim" dialog appears:
   a. Fill {{profile.lateness.stakeholders.channel}} (DAIS_EMAIL)
   b. Click Continue → 4-digit OTP sent to gmail
   c. Read OTP via Gmail MCP search "from:trustmrr"
   d. Fill 4 digit inputs (or single input)
   e. Click 'Log in'
10. Dashboard opens at /dashboard?tab=my-startups
    - Click '+ Add' in My startups column
    - Re-paste apiKey
    - Click 'Add startup' (claim flow — same modal)
11. Listing now owned by DAIS_EMAIL
12. Save state to data/listings/<slug>.json
```

## Field types — handler reference

| field | type | input strategy |
|------|----|------|
| apiKey | input[name="apiKey"] | JS setNativeValue + dispatchEvent input/change/blur |
| X handle | input[placeholder="username"] | same |
| anonymous mode | checkbox | el.click() to toggle |
| list for sale | checkbox | same |
| Add startup | button (CSS-only enabled when apiKey valid) | use `click_at_xy` on getBoundingClientRect coords; in-process JS click hangs the CDP session during Stripe validation |
| OTP | 1 input (or 4 digit inputs) | setVal full code OR per-digit |

## Critical gotchas

| gotcha | fix |
|----|----|
| `fill_input(selector, text)` doubles characters (e.g. `aniccaai` → `aanniiccccaaaaii`) | use JS setVal + dispatchEvent only |
| React clears apiKey value if set before modal fully mounted | wait 2-3s after click before fill |
| Clicking "Add startup" via JS .click() can hang Runtime.evaluate while Stripe API validates | use `click_at_xy(x, y)` from getBoundingClientRect |
| Stripe rk_live key needs 6 read perms minimum | charge_read, subscription_read, plan_read, bucket_connect_read, file_read, product_read — env `TRUSTMRR_STRIPE_KEY` is purpose-built; `STRIPE_RK_LIVE_ALL` works for any service |
| OTP code is in Gmail | use Gmail MCP `search_threads` query `from:trustmrr newer_than:1h` |

## Sale Decision Cron

| key | value |
|----|---|
| name | `trustmrr-sell-decision-monthly` |
| schedule | `0 7 1 * *` JST (1st 07:00) |
| logic | for each listing in `data/listings/*.json`: if current_mrr > 500 AND 30d_growth < 5% → toggle "List for sale" + set sale_price = mrr × 24-36 |

## Listing Cron

| key | value |
|----|---|
| name | `trustmrr-list-weekly` |
| schedule | `0 6 * * 1` JST (Mon 06:00) |
| script | `bash scripts/list-products.sh` |
| action | for each `dashboard.json` product with mrr > $10: ensure listed; refresh metadata |

## Manual run

```bash
# List a single product (default: anicca)
bash ~/.openclaw/skills/trustmrr/scripts/list-products.sh

# Dry run — fill but don't submit
DRY_RUN=true bash ~/.openclaw/skills/trustmrr/scripts/list-products.sh

# Specific product
PRODUCT=letter STRIPE_KEY=$STRIPE_RK_LIVE_ALL \
  bash ~/.openclaw/skills/trustmrr/scripts/list-products.sh
```

## State

| file | purpose |
|----|----|
| `data/listings/<slug>.json` | listing state (url, key used, anonymous flag, sale flag, listed_at) |
| `~/.{{profile.lateness.stakeholders.channel}}-harness-profile/` | persistent TrustMRR + Gmail cookies |

## Live listings

| product | url | mrr_30d | listed |
|----|----|----|----|
| anicca | https://trustmrr.com/startup/anicca | $11 | 2026-05-05 |
