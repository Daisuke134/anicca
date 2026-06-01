---
name: anicca-fuel-broker
description: |
  Continuous monitor of Anicca's wallet, sub quota, API-key residue. Sends
  the user a precise refuel / cancel-sub / first-payout mail at exactly
  the right threshold — never one earlier, never one later.

  Three trigger states (spec §10.I.4-6):
    1. RUNWAY_LOW   wallet < 14 days runway → 4-option refuel mail
    2. SELF_FUND    wallet > 3 mo runtime  → "cancel your sub" mail
    3. FIRST_PAYOUT wallet > 3 mo runtime + payout linked → first send
metadata:
  tags: fuel, broker, runway, payout
  requires:
    bins: [python3, gog]
    env: [GOG_ACCOUNT, GOG_KEYRING_PASSWORD]
---

# anicca-fuel-broker

Single source of truth for "should I tell the user about money right now?".

## Algorithm

```
cfo = read cfo state
wallet, runtime_monthly, runway_days = derive()

state = read state/fuel_broker.json
   { last_runway_low_ts, last_self_fund_ts, last_first_payout_ts,
     payout_destination, decided }

if runway_days < 14 and last_runway_low_ts > 7 days ago:
   send mail RUNWAY_LOW (= spec §10.I.4, 4 refuel options)
   update last_runway_low_ts

elif wallet >= runtime_monthly * 3 and not decided.self_fund:
   send mail SELF_FUND_UNLOCK (= spec §10.I.5, ask cancel/keep)
   update last_self_fund_ts

elif wallet >= runtime_monthly * 3 and payout_destination and not first_payout_sent:
   send mail FIRST_PAYOUT (= spec §10.I.6, wow moment)
   update last_first_payout_ts
```

## Cron

Every hour. State idempotency prevents resending within the cooldown window.

```
schedule: 17 * * * *
message : exec で次を実行: bash ~/.openclaw/skills/anicca-fuel-broker/scripts/run.sh
```
