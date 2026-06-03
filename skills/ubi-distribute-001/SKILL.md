---
name: ubi-distribute-001
description: |
  anicca-redistributor — sends 10% of Anicca's monthly revenue as on-chain
  USDC to a verified charity recipient on Base mainnet. First execution of
  the Anicca pitch line "10% of revenue goes to UBI / suffering-reduction".

  Charity = monthly rotation through `charities.json` (or `state/ubi-override.json`
  if present). Payout = thin wrapper around the existing `anicca-payout-wallet`
  skill, which handles signing + broadcast via the Coinbase `cdp` CLI.

  Ledger is append-only at `~/.openclaw/state/ubi-ledger.jsonl` and surfaces
  on aniccaai.com/donation via the dashboard.json publisher.

metadata:
  tags: ubi, charity, redistribute, base-usdc
  requires:
    bins: [python3, jq, bash]
    skills: [anicca-payout-wallet]
    env:
      optional: [NETLIFY_BUILD_HOOK_DONATION]
---

# ubi-distribute-001

## Trigger

Monthly cron on the 1st at 06:05 JST (see `cron.json`) — or any time
the operator runs:

```
bash scripts/select-charity.sh | xargs bash scripts/payout.sh
```

## Flow

```
select-charity.sh            payout.sh                ledger-append.sh
      │                          │                          │
      ▼                          ▼                          ▼
ubi-override.json    amount = max(0.01,        append JSONL row +
   ─OR─ rotation       mrr * 10%)               patch dashboard.json
   over charities    invoke payout-wallet      (optional Netlify hook)
                     skill (cdp wallet send)
```

Each script is independent and side-effect-minimal: `select-charity.sh`
is pure read (charities.json + optional override), `payout.sh` is the
single mutating step (calls the existing payout-wallet skill), and
`ledger-append.sh` is append-only.

## DRY mode

`bash scripts/payout.sh 0` → zero amount → emits intent JSON + ledger
row stamped `status: dry-run`, no on-chain tx.

## Why on-chain first

USDC on Base = no KYC, no recipient signup, ~$0.001 gas, public
basescan receipt for the donation ledger. The charities listed are
Endaoment-deployed Org entities — their contract `donate()` /
`reconcileBalance()` route the USDC to the org's claimed payout wallet
off-chain.

## Anti-goals

- No tip-jar inbound (Pañcasīla #2)
- No human approval gate (10% of MRR is hardcoded; no Dais click)
- No invented addresses — every entry in `charities.json` is a real
  Endaoment Base mainnet deployment, verified via the v2 search API
  + Base RPC `eth_getCode` showing live EIP-1167 minimal-proxy bytecode
