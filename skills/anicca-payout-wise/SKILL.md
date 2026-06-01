---
name: anicca-payout-wise
description: |
  Tier 2 payout: Wise Platform API for same-day Japan bank settlement
  via the Zengin system. ~0.5-1.5% fee, instant credit, lower friction
  than Stripe Connect because Wise individual accounts have lighter KYC
  than Stripe's Express recipient flow.

  Recommended for speed-critical Japan users.
metadata:
  tags: payout, wise, jpy, zengin, tier2
  requires:
    bins: [python3]
    env:
      [WISE_API_TOKEN, WISE_PLATFORM_ID, GOG_ACCOUNT, GOG_KEYRING_PASSWORD]
  status: PARTIAL — needs Wise Platform business onboarding
---

# anicca-payout-wise (Tier 2, speed)

## Status

**SHIPPED AS STUB** — architecture locked, runtime requires the
maintainer to apply for Wise Platform Business at wise.com/platform.
Then this skill goes live.

## Why Tier 2

Per Round 2 research:

- Wise is the first non-bank with direct API access to Japan's Zengin
  system (= Bank of Japan settlement)
- Same-day JPY domestic transfers (= up to 150M JPY per transfer)
- ~0.5-1.5% spread on USD→JPY conversion
- Lower fee than Stripe for cross-border JPY
- Individual recipient KYC = ID + address (lighter than Stripe Express
  business proof requirements)

The trade-off vs Tier 1: Wise Platform requires a one-time business
onboarding step that takes longer than Stripe Connect (= ~2 weeks vs
~1 day). Once approved, both crosses the same boundary.

## What it will do (= once Wise Platform is live)

```
1. Verify the user's Wise individual account is linked (= we hold a
   recipient ID for them after first onboarding)
2. Off-ramp USDC → USD via cdp + Coinbase / Wise treasury swap
3. POST /v3/profiles/<our_profile_id>/transfers
       targetAccount = user's Wise recipient
       sourceCurrency = USD
       targetCurrency = JPY
       targetAmount = amount_jpy
4. Wise hands off to Zengin same day
5. Webhook arrives with `transfers#state-change` → record + mail receipt
```

## Maintainer todo

1. Apply at wise.com/platform → Business → KYC docs
2. Get WISE_API_TOKEN + WISE_PLATFORM_ID after approval
3. Implement scripts/payout.py
4. Wire cron same way as Stripe variant
