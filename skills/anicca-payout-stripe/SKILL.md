---
name: anicca-payout-stripe
description: |
  Tier 1 payout (= 95% of users): Stripe Connect Express. The user
  completes a 5-min KYC and provides a bank account; Anicca sends USD/JPY
  payouts through Stripe's marketplace flow. Settles in 3-5 business days,
  fees ~1%.

  This is the recommended default for non-crypto users. Stripe Connect
  Express handles all the recipient KYC + the platform doesn't need to
  hold funds.
metadata:
  tags: payout, stripe, jpy, bank, tier1
  requires:
    bins: [python3]
    env:
      [STRIPE_SECRET_KEY, STRIPE_CONNECT_PLATFORM_ID, GOG_ACCOUNT,
       GOG_KEYRING_PASSWORD]
  status: PARTIAL — needs Stripe Connect platform onboarding
---

# anicca-payout-stripe (Tier 1, default for 95% of users)

## Status

**SHIPPED AS STUB** — the SKILL.md and architecture are locked, but the
runtime requires the maintainer (= Dais) to complete Stripe Connect
platform registration first. That's a 1-day onboarding step at
dashboard.stripe.com/connect, then this skill goes live.

## Trigger

Called by anicca-fuel-broker when:
1. wallet_usd >= runtime_monthly * 3
2. broker.payout_destination == "stripe_connect"
3. broker.first_payout_sent == False  (= first time)

OR by user reply "payout now" from the broker first-payout mail.

## What it will do (= once Stripe Connect is live)

```
1. Verify the user's Stripe Connect Express account is active
   (= GET /v1/accounts/<acct_id>, details_submitted == True)
2. Convert wallet_usd_to_send → USDC off-ramp via Wise treasury
   (= same wallet we hold for x402 fuel)
3. Call POST /v1/transfers
       destination = user's connected account
       amount = round(amount_usd * 100)  # cents
       currency = "usd" or "jpy" per user preference
4. Webhook listener (= already wired in Anicca's webhook handler) reports
   `transfer.created` and later `payout.paid`
5. Send Gmail receipt with the Stripe payout ID
6. Record in state/sent.json
```

## Why Tier 1

Per Round 2 research (= 8 OSS Python agent codebase audit + payment-rails
competitive scan, 2026-05-31):

- Lowest user KYC (= Stripe Express handles it proactively, ~5 min)
- No business registration required for the recipient
- JPY bank payout supported (= Mizuho / SBI / Rakuten / MUFG all work)
- 1% fee + standard transfer fee
- Excellent API maturity, well-documented
- T+3-5 business days settlement (acceptable for non-urgent payouts)

For speed-critical users we have Tier 2 (Wise, same-day) and crypto-native
users get Tier 3 (anicca-payout-wallet, instant USDC).

## Maintainer todo (= unblock this skill)

1. Sign up at dashboard.stripe.com/connect as a platform
2. Complete platform KYC (= 1 day)
3. Get STRIPE_CONNECT_PLATFORM_ID, add to ~/.openclaw/.env
4. Implement scripts/payout.py mirroring the wallet variant:
   - read broker state
   - convert wallet to fiat (= cdp wallet swap or Wise treasury)
   - create transfer via stripe SDK
   - mail receipt
5. Wire cron (= same trigger conditions as wallet variant, dispatched
   on broker.payout_destination)
