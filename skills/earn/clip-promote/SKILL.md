---
name: earn/clip-promote
description: Anicca earn slot — promote.fun USDC-Solana per-view clipping. The ONE loop calls run.sh each wake; a PURE state machine (decide.py) drives one campaign-clip item SELECT→CLIP→POST→SUBMIT→MEASURE→WITHDRAW→RECORD with zero human. DONE = a real on-chain Solana USDC inflow recorded to the canonical ledger (record-payout.mjs verifies the withdrawal signature on-chain). Use when wiring/operating promote.fun clip earning.
---

# earn/clip-promote — promote.fun USDC-Solana clip earning (no human, no Claude in the loop)

Spec (SSOT): `$LIFE_MANAGER_REPO/.vcsdd/features/promote-fun-clip-earn/specs/spec.md` (REV 4, Phase 1c PASS 5/5)
+ `$LIFE_MANAGER_REPO/docs/superpowers/specs/2026-06-28-claude-earn-skills-spec.md`.

## What it does
The automaton loop invokes `run.sh` each wake. `decide(state, now)` (PURE, `decide.py`) returns ONE bounded
transition; run.sh runs exactly that step (every browser/IO step under a portable `timeout` watchdog) and
prints ONE JSON line `{slot, did, earned_usdc, cost_usdc}`, exit 0.

| Transition | Action | earned_usdc |
|---|---|---|
| SELECT | pick an ACTIVE promote.fun campaign allowing IG, not already clipped | 0 |
| JOIN | actually join it — this is where a hidden follower-count gate surfaces (see below) | 0 |
| CLIP | produce a 15–45s 1080×1920 clip (reuse `earn-clip-rewards`) | 0 |
| POST | post to a WARMED account (`~/.cloak/clip-accounts.json` status==ready) via `poster.py` (earn/marketing-engine) | 0 |
| SUBMIT | submit the post URL to the campaign | 0 |
| MEASURE | read views + liveness; 0 views past `DEAD_ZERO_HOURS` (48h) ⇒ STALLED | 0 |
| WITHDRAW | campaign ENDED + balance>0 → claim USDC on Solana, capture signature | 0 |
| RECORD | verify the Solana sig on-chain + append the ONLY profitable line (DONE) | **>0** |

## ★ DOMAIN KNOWLEDGE: affiliate/campaign monetization requires a follower/trust base FIRST ★
(Dais 2026-07-04 verbatim, after a live investigation: "in order to do good money-making affiliate
work, you have to earn trust and followers first.") **This applies to every AI doing this kind of
affiliate/campaign monetization, not just this one skill.**

Investigation (2026-07-04, fresh evidence, not assumed): of 17 IG-eligible promote.fun campaigns,
15 were already `Ended`/budget-exhausted (some showed a "Live" badge while their budget bar read
`$0.00 left` — read the ACTUAL state from page text, never trust a status badge alone). The 2
genuinely open ones both gated on a minimum follower count (2,000 and 200) that a fresh 0-follower
account cannot clear. **A campaign's follower requirement is invisible until you actually attempt
to join it** — its Rules tab stays locked ("Join the Campaign to unlock full details") pre-join, so
there is no way to pre-filter for this in SELECT; JOIN has to actually try and read the real
error.

**The fix is NOT to hunt forever for a zero-requirement campaign.** It is architectural: run the
account's REGULAR posting loop (`earn/clip`, same IG handle) in parallel — every normal post is
what organically grows followers/trust over time. This `earn/clip-promote` loop's job, while that
count is still below any open campaign's bar, is to keep honestly reporting
`join:skipped-<slug>-follower-requirement` and freeing the slot for the next SELECT — never to
fabricate a join that didn't actually happen. Once the shared account's follower count clears a
campaign's bar, JOIN will simply start succeeding on its own; no extra logic is needed for that
transition. Two loops, one shared account, patience by design — this is a monetization-strategy
principle any campaign/affiliate-earning AI should carry, not a one-off patch to this skill.

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
node --test $LIFE_MANAGER_REPO/skills/_shared/lib/__tests__/*.test.js          # 45/45 (ledger Solana + solana-verify + guard)
node --test $LIFE_MANAGER_REPO/skills/earn/lib/__tests__/*.test.*             # 42/42 (incl record-solana round-trip)
node --test tests/test_record_payout.mjs                            # 4/4  (DONE gate: recorded/unconfirmed/zero/dup)
python3 tests/test_decide.py                                        # 8/8  (pure state machine)
bash tests/test_run.sh                                              # 4/4  (discover + watchdog + FIND-301 env -i)
```
Acceptance: a confirmed Solana withdrawal sig with inbound USDC delta>0 → one ledger line whose
`isProfitable` is true. Narration / unconfirmed / zero-delta NEVER count.

## Status (2026-07-04, fresh evidence — corrects the prior "wired + validated" overclaim)
- SELECT: ✅ live-verified, IG-only filter added (was missing a platform filter, picked a
  TikTok-only campaign once — fixed).
- JOIN: ✅ implemented (`join_campaign.py`), live-verified to correctly detect both success and
  the follower-count gate; no campaign has been successfully joined yet (see DOMAIN KNOWLEDGE above
  — currently blocked on follower count, by design, not a bug).
- CLIP: ✅ live-verified end-to-end (real YouTube URL extraction + `producer.sh`, real mp4 produced
  in `~/clips/queue-clip-promote`).
- POST: ✅ implemented, live-verified to reach the composer/caption/share step in dry-run; stays
  dry (never `--live`) until campaign-specific required tags/CTA are applied to the caption
  (deferred, a per-campaign judgment call).
- SUBMIT / WITHDRAW / RECORD: SUBMIT not yet implemented (UI not yet investigated). WITHDRAW/RECORD
  code exists and is unit-tested but has NOT been run against a real ended campaign + real
  withdrawal yet — treat as unverified until that happens.
