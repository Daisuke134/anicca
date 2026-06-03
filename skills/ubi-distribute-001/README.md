# ubi-distribute-001 — Anicca's first on-chain UBI / charity payout

Sends 10% of Anicca's monthly revenue as USDC on Base to a verified
charity. v1 of spec 14.

## Layout

| Path | What |
|---|---|
| `SKILL.md` | frontmatter + flow doc |
| `charities.json` | 6 Endaoment-deployed Base Org entities (verified on-chain) |
| `scripts/select-charity.sh` | override OR month-of-year rotation → addr on stdout |
| `scripts/payout.sh` | `<addr> [amount]` — calls `anicca-payout-wallet` |
| `scripts/ledger-append.sh` | append-only writer + dashboard.json patch |
| `cron.json` | `5 6 1 * *` Asia/Tokyo, monthly |

## Run

```
bash scripts/select-charity.sh | xargs bash scripts/payout.sh        # live, default 10%
bash scripts/payout.sh 0xA296...425a2 0                              # DRY
echo '{"recipient_address":"0xA296...425a2","charity_name":"MSF"}' \
  > ~/.openclaw/state/ubi-override.json                              # manual choice
```

## Notes

- Address verification: each `base_addr` checked with viem `isAddress`
  + Base RPC `eth_getCode` (EIP-1167 minimal-proxy bytecode confirmed live).
- Upstream payout-wallet entrypoint is `run.sh`, not `send.sh` — single
  source of truth lives in `~/.openclaw/skills/anicca-payout-wallet`.
- Ledger lives at `~/.openclaw/state/ubi-ledger.jsonl` (append-only).
