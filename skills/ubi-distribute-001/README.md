# ubi-distribute-001 — Anicca's first on-chain UBI / charity payout

Sends 10% of Anicca's monthly revenue as USDC on Base to a verified
charity. v1 of spec 14.

## Layout

| Path | What |
|---|---|
| `SKILL.md` | frontmatter + flow doc |
| `charities.json` | 6 Endaoment-deployed Base Org entities (verified on-chain) |
| `scripts/select-charity.sh` | override OR month-of-year rotation → addr on stdout |
| `scripts/payout.sh` | `<addr> [amount]` — auto-picks cdp OR viem broadcaster |
| `scripts/payout-viem.js` | self-contained viem broadcaster (no cdp dependency) |
| `scripts/ledger-append.sh` | append-only writer + dashboard.json patch |
| `scripts/wallet-watch.sh` | hourly: promote DRY → LIVE when wallet crosses threshold |
| `scripts/register-cron.py` | idempotent insert of both crons into openclaw jobs.json |
| `cron.json` | monthly payout: `5 6 1 * *` Asia/Tokyo |
| `watcher-cron.json` | hourly trigger check: `0 * * * *` Asia/Tokyo |

## Run

```
bash scripts/select-charity.sh | xargs bash scripts/payout.sh        # default 10%
MONTH_OVERRIDE=3 bash scripts/select-charity.sh                       # simulate March
bash scripts/payout.sh 0xA296...425a2 0                              # explicit DRY
echo '{"recipient_address":"0xA296...425a2","charity_name":"MSF"}' \
  > ~/.openclaw/state/ubi-override.json                              # manual choice
```

## Threshold: when DRY flips to LIVE

The monthly cron stays in DRY mode until ALL of these hold:

| Gate | Value | Verified by |
|---|---|---|
| Base USDC balance | ≥ `$1.0` USDC | `wallet-watch.sh` (viem `balanceOf` on `0x833589…2913`) |
| Base ETH gas      | ≥ `0.0005` ETH | `wallet-watch.sh` (viem `getBalance`) |
| Live-flag file    | present       | `~/.openclaw/state/ubi-live-flag` (written by watcher) |

`wallet-watch.sh` fires every hour. On the first run that meets both balance
gates, it writes the flag once and never clobbers it again — so a one-time
manual rollback (`rm ~/.openclaw/state/ubi-live-flag`) is a deliberate
decision and not an oscillation. Override the thresholds via
`UBI_LIVE_USDC_THRESHOLD` / `UBI_LIVE_ETH_THRESHOLD` env vars.

`payout.sh` checks `UBI_LIVE` env, then the flag file, in that order. So
`UBI_LIVE=1 bash payout.sh …` always wins (testing override); a present flag
upgrades the monthly cron without touching the cron payload.

## Broadcaster selection

`payout.sh` auto-detects which signer to use, and you can override with
`UBI_BROADCASTER`:

| Broadcaster | Path | When picked |
|---|---|---|
| `cdp` | `~/.openclaw/skills/anicca-payout-wallet/scripts/payout.py` | `cdp` binary on PATH AND `CDP_API_KEY_NAME` + `CDP_API_KEY_PRIVATE` in `~/.openclaw/.env` |
| `viem` | `./scripts/payout-viem.js` (self-contained) | Default fallback — reads `~/.automaton/wallet.json` privateKey, signs via viem, broadcasts via `https://mainnet.base.org` |

The viem path verifies sender balance + ETH gas before signing and refuses
to broadcast when funds are insufficient (`action: no-funds`). `--dry-run`
uses `simulateContract` (`eth_call`) so the cron can prove the broadcast
WOULD land without spending gas.

## Notes

- Address verification: each `base_addr` checked with viem `isAddress`
  + Base RPC `eth_getCode` (EIP-1167 minimal-proxy bytecode confirmed live).
- Upstream payout-wallet entrypoint is `payout.py`; `run.sh` redirects stdout
  to its own log, so `payout.sh` invokes `payout.py` directly with the same
  env loading and parses the canonical JSON `.action` field as the row status.
- Ledger lives at `~/.openclaw/state/ubi-ledger.jsonl` (append-only).
- `state/donation-screenshot.png` + `state/donation-ledger-screenshot.png`
  are reference screenshots of the live aniccaai.com/donation page.
