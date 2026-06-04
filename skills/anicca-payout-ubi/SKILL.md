---
name: anicca-payout-ubi
description: Weekly UBI fan-out. Reads wallet balance from CFO, computes distributable = max(0, wallet - runtime_monthly × reserve_months) (reserve_months default 3), then sends payout_percent (default 10%) of distributable USDC on Base, split across N recipients per ~/.hermes/state/ubi-recipients.json weights. DRY-RUN BY DEFAULT — every invocation logs to ~/.hermes/state/payout.jsonl. Real broadcast requires THREE independent signals: --confirm flag, env ANICCA_PAYOUT_LIVE=1, AND every recipient row must have allow_live:true plus label != "PLACEHOLDER" (codex round-2 fail-closed guard against burn-address footgun). Calls anicca-constitution-guard before every action, including dry-run; production fails closed if the guard symlink is missing (ANICCA_PAYOUT_TEST=1 toggles test-mode OK-on-missing). Signing path = wallet_lib.load_signer() from #324 P2 (NO cdp CLI dependency). Use this skill ONLY from cron; do not call it from chat. Cron schedule: every 7d (or "0 9 * * 1").
---

# anicca-payout-ubi

## What it does
Weekly cron skill that funnels a slice of Anicca's net earnings to a configurable list of recipient wallet addresses on Base mainnet via USDC, scaffolding pitch row ⑥ "収益の一部を UBI / 募金 配布" (00-MASTER LAUNCH ACCEPTANCE MATRIX). Row ⑥ flips green only after Wave 2 (Task 9 of `2026-06-04-constitution-payout.md`) lands a real on-chain micro-payout (0.01 USDC) with a verified Basescan receipt. Recipients can be charities (公認 NPO wallets), Dais's dividend address, or other publicly-declared addresses — the skill is agnostic; the config file picks the policy.

## Inputs
- `~/.openclaw/skills/cfo-core/data/anicca-cfo.json` — wallet balance + runtime monthly burn (already maintained by `cfo-daily` launchd job).
- `~/.hermes/state/ubi-recipients.json` — operational config. Schema in `scripts/recipients-schema.json`. Recipient weights MUST sum to 100. Each recipient row MUST carry `label` (string, must not equal "PLACEHOLDER" for live broadcast) and `allow_live` (boolean, must be true for live broadcast). Example:
  ```json
  {
    "recipients": [
      {"address": "0xCharityA…", "weight": 60, "label": "Animal welfare 認定 NPO", "allow_live": true},
      {"address": "0xCharityB…", "weight": 40, "label": "Suicide prevention 公認", "allow_live": true}
    ],
    "payout_percent": 10,
    "reserve_months": 3
  }
  ```

## Math
```
reserve_usd      = runtime_monthly × reserve_months
distributable    = max(0, wallet_usd - reserve_usd)
total_payout_usd = distributable × payout_percent / 100         (rounded to cents)
per recipient    = total_payout_usd × weight / 100               (rounded to cents)
```

## Modes (defense in depth — broadcast requires THREE independent signals)
| Invocation | Behavior |
|---|---|
| `./payout-ubi.sh` (default) | Dry-run. Logs `action="dry-run"`. Exit 0. |
| `./payout-ubi.sh --dry-run` | Explicit dry-run. Same as above. |
| `./payout-ubi.sh --confirm` (no env) | Refused. Logs `action="refused-no-live-env"`. Exit 0. |
| `ANICCA_PAYOUT_LIVE=1 ./payout-ubi.sh --confirm` with any PLACEHOLDER or `allow_live:false` row | Refused. Logs `action="live-recipient-validation-failed"`. Exit non-zero. NOTHING sent. |
| `ANICCA_PAYOUT_LIVE=1 ./payout-ubi.sh --confirm` with all rows `allow_live:true` + `label != "PLACEHOLDER"` | REAL broadcast via `wallet_lib.send_usdc()` from #324 P2 per recipient on Base mainnet. Logs `action="sent"` / `"partial"` / `"send-failed"`. |

## Pre-flight guard (fail-closed in production)
On every invocation (including dry-run), this skill calls `anicca-constitution-guard --action "UBI weekly payout: …"` and aborts immediately if the guard returns non-zero. The audit trail in `~/.hermes/state/constitution-violations.jsonl` therefore proves the guard ran for every payout decision. **If the guard symlink is missing**, production exits with `action="blocked-by-guard"` + non-zero rc — codex P4-guard-bypass-ok fix. The legacy "OK + guard_not_installed" return is allowed ONLY when env `ANICCA_PAYOUT_TEST=1` (used by the RED phase of the TDD test before Task 3's symlink lands).

## Signing path (codex P4-cdp-unverified fix)
Signing imports `wallet_lib` from `anicca-oss/skills/anicca-wallet/scripts/wallet_lib.py` (shipped by #324 P2). The canonical Anicca wallet is the one `wallet_lib.EXPECTED_ADDRESS` asserts (0xa3CDd4Ec…). There is NO dependency on the `cdp` CLI; `command -v cdp` is informational only and never branched on. If `wallet_lib.send_usdc()` is absent in your tree, run #324 P2 (`docs/superpowers/plans/2026-06-04-wallet-x402.md`) before this skill — that plan adds the helper.

## HARD RULE #-1 disclosure (financial-broadcast hard-block)
Per CLAUDE.md HARD RULE #-1, the Wave 2 broadcast IS a financial broadcast. The exact path the agent will attempt: `wallet_lib.load_signer()` → `wallet_lib.send_usdc(signer, to, atomic_amount)` → internally builds EIP-3009 `transferWithAuthorization` → signs → `web3.eth.send_raw_transaction()` against Base RPC. The ONLY conditions for stopping (without human-in-loop): (a) RPC returns `insufficient funds`, (b) wallet balance < threshold, (c) recipient row fails `allow_live:true` + `label != "PLACEHOLDER"`. No Dais click, no Slack approval gate. Dais's role for the first broadcast is monitoring `payout.jsonl` + Basescan, NOT clicking through a wallet UI.

## Wave 2 verification (handled in Task 9 of the plan — NOT out-of-band)
The plan's Task 9 ("Real micro-payout proof") executes the live 0.01 USDC send + Basescan receipt check + payout.jsonl row append IN-BAND, with the cross-plan rule X2 invariant that ONLY after that task lands does #326 close and row ⑥ go green. Task 9 contains the exact commands; this SKILL.md no longer carries a separate "run it out-of-band" block.

## Why this is separate from `anicca-fuel-broker`
`anicca-fuel-broker` is a one-shot alerter that mails Dais ONCE when the wallet first crosses self-fund threshold (broker.json `first_payout_sent`). `anicca-payout-ubi` is the recurring weekly cron that distributes the ongoing slice. The two skills do NOT race because broker only ever mails (no on-chain send) and `payout-ubi` only ever sends on-chain (no mail).

## Schema of `~/.hermes/state/payout.jsonl`
```json
{"ts":"…","action":"dry-run|refused-no-live-env|below-threshold|invalid-recipients|blocked-by-guard|live-recipient-validation-failed|sent|partial|send-failed",
 "wallet_usd":100.0,"runtime_monthly":10.0,"reserve_usd":30.0,
 "would_send_usd":7.0,"recipients":[{"address":"0x…","weight":100,"amount_usd":7.0,"label":"…"}],
 "sent":[{"address":"0x…","amount_usd":7.0,"tx_hash":"0x…","basescan":"https://basescan.org/tx/…"}]}
```
