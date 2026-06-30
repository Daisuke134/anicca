# gig EARN-CORE recipe — autonomous-loop verification + portable recipe (2026-06-30)

VCSDD spec. Goal: PROVE the gig loop runs autonomously 24/7 on claude-p (no main session), and
turn it into a portable recipe any Claude can use to earn daily. Built via /vcsdd: spec → RED →
GREEN → fresh-context adversary → no-mock E2E → my own runtime verify.

## Provable finish line (done = ALL true)
1. **AUTONOMOUS FIRE (the #1 proof)**: with NO main-session intervention, the in-session :27 cron
   fires a pass — provable by `~/gig/.last-pass` mtime advancing across a :27 boundary that I did
   NOT trigger, AND an independent `audit.jsonl` row written by the launchd auditor recording
   `verdict=FIRING`. (Currently UNPROVEN — prior heartbeats came from my manual --restart.)
2. **CONVERSATION SWEEP**: one pass checks ALL active talk-rooms (not just one), so a buyer reply is
   never dropped. Evidence: applied.jsonl `replied` rows keep pace with inbound Gmail notifications.
3. **EARN-CORE TEMPLATE**: the clip/gig common parts (core-cli + healthcheck + heartbeat + auditor +
   ledger) extracted as a reusable template; a new rail = clone + swap {account, runbook, payout}.
4. **CONCURRENCY/QUOTA reality**: document how many claude-p cores one subscription sustains
   (observed: this week hit 96% weekly cap from heavy dev usage; resets Jul 3). Honest limit, not a fix.

## Architecture (3 persistence layers — why it self-runs)
- **OS layer (launchd, session-independent)**: `gig-core-healthcheck` (5min) restarts the core if the
  tmux died OR is STALE (no pass >90min → in-session cron stopped). This is the 24/7 anchor.
- **AGENT layer (claude-p tmux, subscription-fueled, NO API)**: `gig-cli.sh` core registers an
  in-session recurring cron `27 * * * *` (durable) and idles; the cron fires it hourly.
- **WORK layer (one bounded pass)**: touch heartbeat → drive daily-driver CDP as mtdc per
  APPLY_RUNBOOK → INBOX(reply/deliver/評価) ELSE APPLY(scan→propose) → applied.jsonl; ¥ recorded to
  earnings.jsonl ONLY on 検収/支払 + evidence (deterministic, no fake).
- **AUDIT layer (independent, read-only)**: `auditor.sh` (launchd :45) writes audit.jsonl
  {verdict FIRING/STALE/DEAD, applied_delta, jpy} — the proof the loop self-runs without me.

## Money path
Coconala gig (human-funded): 応募→トーク往復→見積り→仮払い→納品→検収→¥ → Dais MUFG. Multi-day,
conversation-driven (unlike set-and-forget yield/trade) — hourly passes advance every live conversation.

## Recipe (any Claude earns daily)
Ingredients: (1) a Claude Code subscription (claude-p fuel, no API balance needed), (2) a logged-in
daily-driver browser with a gig-platform account, (3) the EARN-CORE template. Recipe: clone EARN-CORE,
swap {account creds, platform RUNBOOK, payout destination}, `launchctl load` the healthcheck → the OS
keeps the core alive → the core's hourly cron runs the gig conversation loop → money to the account.
human-funded → ¥/bank; self-funded → USDC/wallet. Same template, different {account/runbook/payout}.

## VCSDD tasks
1. SPEC (this file) + commit+push.
2. IMPLEMENT: install the independent auditor (auditor.sh + ai.anicca.gig-auditor.plist); strengthen
   the cron prompt to sweep ALL active talk-rooms each pass.
3. RED/GREEN: a test that auditor.sh emits a correct verdict from heartbeat+ledgers (FIRING/STALE/DEAD).
4. ADVERSARY (fresh context): no-fake-earn, no-human, the auditor cannot report FIRING when stale, the
   verdict logic is deterministic. (Quota-aware: run when weekly budget allows so it doesn't starve the
   core's own quota needed for the autonomous-fire proof.)
5. NO-MOCK E2E (the #1 proof): leave the core UNTOUCHED; observe `.last-pass` advance across a :27
   boundary I didn't trigger + an audit.jsonl `FIRING` row → autonomous loop proven.
6. Extract EARN-CORE template (clip∩gig) as the reusable recipe.

## Hands-off discipline (correcting my own error)
I over-restarted the core + over-spawned adversaries this session → burned the weekly quota to 96%.
The correct verification is HANDS-OFF: stop touching the core, let launchd+cron run it, and read
audit.jsonl/applied.jsonl to confirm it advanced on its own.
