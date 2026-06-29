---
name: earn/clip-promote
description: Anicca earn slot — promote.fun USDC-Solana per-view clipping. The ONE loop calls run.sh each wake; a PURE state machine (decide.py) drives one campaign-clip item SELECT→CLIP→POST→SUBMIT→MEASURE→WITHDRAW→RECORD with zero human. DONE = a real on-chain Solana USDC inflow recorded to the canonical ledger (record-payout.mjs verifies the withdrawal signature on-chain). Use when wiring/operating promote.fun clip earning.
---

# earn/clip-promote — promote.fun USDC-Solana clip earning (no human, no Claude in the loop)

Spec (SSOT): `~/anicca-project/.vcsdd/features/promote-fun-clip-earn/specs/spec.md` (REV 4, Phase 1c PASS 5/5)
+ `~/anicca-project/docs/superpowers/specs/2026-06-28-claude-earn-skills-spec.md`.

## What it does
The automaton loop invokes `run.sh` each wake. `decide(state, now)` (PURE, `decide.py`) returns ONE bounded
transition; run.sh runs exactly that step (every browser/IO step under a portable `timeout` watchdog) and
prints ONE JSON line `{slot, did, earned_usdc, cost_usdc}`, exit 0.

| Transition | Action | earned_usdc |
|---|---|---|
| SELECT | pick an ACTIVE promote.fun campaign allowing IG, not already clipped | 0 |
| CLIP | produce a 15–45s 1080×1920 clip (reuse `earn-clip-rewards`) | 0 |
| POST | post `--live` to a WARMED account (`~/.cloak/clip-accounts.json` status==ready) via `ig-reels-poster` | 0 |
| SUBMIT | submit the post URL to the campaign | 0 |
| MEASURE | read views + liveness; 0 views past `DEAD_ZERO_HOURS` (48h) ⇒ STALLED | 0 |
| WITHDRAW | campaign ENDED + balance>0 → claim USDC on Solana, capture signature | 0 |
| RECORD | verify the Solana sig on-chain + append the ONLY profitable line (DONE) | **>0** |

## DONE = real on-chain USDC only
`record-payout.mjs` is the only path that records `earned_usdc>0`. It verifies the withdrawal signature via
`_shared/lib/solana-verify.mjs` (`sigStatus.confirmed===true` AND `usdcDeltaForSig>0` inbound to our ATA),
checks `alreadyRecordedSig` (sig-keyed idempotency), and appends via the canonical `record.mjs` →
`isProfitable` (net>0 + external:true + Solana `sig`+`confirmed`). An unconfirmed / zero-delta / duplicate
sig is REFUSED — never a false earn (HARD 0.24). Run under `env -i` (no PII) so the malice-guard passes.

## Entrypoint
```bash
# discover (default): report the transition this wake would run; NO side effect.
EARN_MODE=discover ./run.sh
# execute: run the one transition. Wallet (Solana) = CLIP_WALLET_SOLANA (default xxKC33…).
EARN_MODE=execute ./run.sh
```
Env: `SOLANA_RPC_URL`, `CLIP_WALLET_SOLANA`, `CLIP_PROMOTE_STATE`, `EARN_LEDGER`, `CLIP_ACCOUNTS`,
`STEP_DEADLINE_S` (120), `SKILL_TIMEOUT_S` (harness-enforced wake cap).

## Verify (independent)
```bash
node --test ~/anicca/skills/_shared/lib/__tests__/*.test.js          # 45/45 (ledger Solana + solana-verify + guard)
node --test ~/anicca/skills/earn/lib/__tests__/*.test.*             # 42/42 (incl record-solana round-trip)
node --test tests/test_record_payout.mjs                            # 4/4  (DONE gate: recorded/unconfirmed/zero/dup)
python3 tests/test_decide.py                                        # 8/8  (pure state machine)
bash tests/test_run.sh                                              # 4/4  (discover + watchdog + FIND-301 env -i)
```
Acceptance: a confirmed Solana withdrawal sig with inbound USDC delta>0 → one ledger line whose
`isProfitable` is true. Narration / unconfirmed / zero-delta NEVER count.

## Status
Lib + state-machine + DONE-gate executor = built & unit-proven (Phase 2 GREEN). The live execute handlers
(SELECT/CLIP/POST/SUBMIT/WITHDRAW against real promote.fun + IG) are wired + validated in the no-mock E2E
(#14): needs a warmed account + an active campaign that ends + a real withdrawal.
