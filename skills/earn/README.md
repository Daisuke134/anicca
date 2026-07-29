# earn — TRACK B: how Anicca funds itself (and the UBI surplus)

Anicca's thesis: **earn USDC autonomously → pay its own compute → distribute the surplus as real basic
income.** This skill is TRACK B (the earning). `../ubi` is the distribution. `../_shared/lib` is the
money-handling core both use. The honest status of each part is stated below — no part is claimed
"done" beyond what the on-chain ledger proves.

## The self-funding loop (one wake)
```
automaton wake → run.sh
  → pick a source + execute a REAL on-chain earn
  → verify the receipt (status 0x1) + USDC before/after delta
  → append ONE line to state/earn-ledger.jsonl
  → if net>0 AND status 0x1 (a PROFITABLE wake): distribute_ubi() sends a share to ../ubi
```
The launch gate (`SKILL.md`): **one profitable external wake = net>0 AND receipt 0x1.** Until that
fires, Anicca is not yet self-funding — the ledger shows `discover` wakes (earn_usdc:0), which is the
current state (wired + running, awaiting the first real external payout). This README does not pretend
otherwise.

## Sources (in run.sh / siblings)
| Source | What it is | GATE-0? |
|---|---|---|
| `0xwork` (`execute-0xwork.py`, `lib/oxwork.mjs`) | external poster escrow pays USDC to our wallet | ✅ GATE-0 (real external revenue) |
| `x402-sell/` | sell an x402-paywalled endpoint | ✅ external |
| `execute-yield.mjs` | DeFi yield on idle USDC | revenue (yield) |
| `execute-invest.mjs` | invest leg | revenue |
| `hl-trade/` | Hyperliquid trading | revenue (risk) |
| `token-launch/` | token launch | revenue |
| `execute-swap.py` (`sol-to-usdc.py`, `ensure-gas.mjs`) | ETH/SOL→USDC rotation + gas floor | ❌ **NOT** a gate — net-zero asset rotation; `lib/ledger.mjs isProfitable` rejects it. Runway only. |

A swap can keep Anicca alive (rotate its own assets to spendable USDC + a gas floor) but can NEVER
mint a GATE-0 "profit" — only genuinely external revenue counts. This is enforced in code, not honor.

## Money-safety (shared with ubi, via ../_shared/lib)
- `identity-guard.mjs` fails CLOSED if any user-PII env (gmail/gcal/google-login) leaks into the earn
  process — own-funds only. The `EARN_ALLOW` allowlist in `run.sh` is the minimal env surface.
- `verify-tx.mjs` reports the receipt status; the `0x1` requirement is enforced by `ledger.mjs isProfitable()` + `run.sh`. `usdc.mjs` confirms a real before/after balance delta.
- `ledger.mjs` never rewrites prior lines (immutable); `isProfitable()` is the single source of truth
  for "did this wake actually make money."
- `earn-guard.mjs` (P1, spec §3/§4) is the CUMULATIVE layer on top of `isProfitable()`: it sums every
  recorded `net_usdc` for a wallet/skill and HALTs fail-closed the moment the running total would go
  negative, or the moment a ledger line's numbers can't be trusted. See `SKILL.md`'s "P1 fail-closed
  CUMULATIVE guard" section for the one-line integration pattern + which skills are wired.

## Verify a wake (fresh evidence, not a claim)
```bash
cd $LIFE_MANAGER_REPO/skills/earn
tail -1 state/earn-ledger.jsonl                  # the recorded wake
# net_usdc>0 AND a tx hash -> open https://basescan.org/tx/<hash> -> Status: Success
EARN_MODE=discover bash run.sh                   # safe dry wake (no tx) -> NARRATE, exit 0 (discover is the default MODE)
```

## Relationship to ubi
`run.sh distribute_ubi()` calls `../ubi/distribute-ubi.mjs` after a profitable wake — the ONLY
earn→ubi link. earn = INFLOW; ubi = OUTFLOW; neither imports the other's domain logic. See
`../ubi/README.md` / `../ubi/SKILL.md` for the distribution rails (wallet/email live; bank/M-Pesa/US
code-ready, account-gated).

## Status (honest, 2026-06-21)
- ✅ loop wired + running (discover wakes recorded); split into earn/ubi/_shared (VCSDD-converged, 97 tests)
- ⏳ **GATE-0 not yet passed** — no profitable external wake on the ledger yet. The first net>0 / 0x1
  external payout is the real launch milestone (TRACK B's actual goal — [OTHER CC] focus).
