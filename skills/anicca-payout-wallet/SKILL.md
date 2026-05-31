---
name: anicca-payout-wallet
description: |
  Tier 3 payout (= crypto-native): sends USDC directly to the user's
  declared wallet address on Base mainnet. KYC ZERO, settlement in
  seconds, fees ~$0.

  Triggered by anicca-fuel-broker when wallet > 3 months runtime AND
  payout_destination starts with `0x` (= an EVM address). Amount
  = wallet_usd * PAYOUT_PERCENT / 100  (default 10%).

  This is the simplest of the 3 payout tiers — no Stripe, no Wise, no
  business KYC. The user just pastes a wallet address into broker state
  once, and Anicca takes care of the rest.

metadata:
  tags: payout, usdc, wallet, base
  requires:
    bins: [python3, cdp]
    env: [WALLET_ADDR, CDP_API_KEY_NAME, CDP_API_KEY_PRIVATE]
---

# anicca-payout-wallet

## Trigger

Called by anicca-fuel-broker when:
1. wallet_usd >= runtime_monthly * 3
2. broker state.payout_destination starts with "0x"
3. broker state.first_payout_sent == False  (= first time)

OR by user reply "payout now <amount>" from the broker first-payout mail.

## What it does

```
amount_usd = wallet_usd * PAYOUT_PERCENT / 100
amount_atomic = round(amount_usd * 1_000_000)  # USDC 6 decimals

cdp wallet send \
  --to <payout_destination> \
  --token USDC \
  --network base-mainnet \
  --amount <amount_atomic>
```

After confirmation:
- record tx hash in state/sent.json
- update broker state.first_payout_sent = True
- send Gmail receipt (= "I sent you $X, basescan link <link>")

## Why Tier 3 (= crypto-native) first

- ZERO setup beyond pasting an address
- ZERO settlement delay
- ZERO fees ($0.001 gas)
- ZERO trust assumption (= on-chain verifiable)

The Stripe Connect (Tier 1) and Wise (Tier 2) variants ship later with
KYC + payout-account onboarding flow.

## Not run on a cron

Triggered on demand by fuel-broker or by replying to the first-payout
mail. No autonomous schedule — every payout requires the user-set
destination address to be present.
