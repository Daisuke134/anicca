# execution-notes.md — sprint-4 M1+M2

## Active /goal
`GOAL-sprint-4-M1-M2.md` (mailed to Dais via Resend id `0493d1f1-...`).

## Sub-feature status

| # | feature | phase | notes |
|---|---|---|---|
| a2 | earnings-to-settle-mirror | ✅ COMPLETE (Phase 6) | Full pipeline PROVEN LIVE on production gig: p-1782887987 roi 0→25000 |
| a1 | LAYER C STARTUP prompt update | ✅ DEPLOYED 2026-07-01 | 3 injections in gig-cli.sh: PRE-B1 CURRENT_PASS_ID binding from oldest tasks/*.json; B2 per-apply task-request-map.jsonl append; EARNED CHECK jq exact-match historical pass_id lookup + task-request-map.errors.jsonl fallback. Restarted per REQ-L3, --status=ALIVE < 30s. M2 auto-closes on first real Coconala 検収. |
| b | earn-roi-reconciler | ✅ COMPLETE | Feature (b) sprint-4 done |
| c | dispatcher-live-dormant | ✅ COMPLETE | Phase 6 converged + live E2E on prod gig; .slot_created marker deployed |
| d | recipe-6-actions | ✅ COMPLETE | 6 real wires (kill_server/send_keys/login/npm_install/git_checkout/escalate_via_bot2bot); 503 tests GREEN; INV-P1/INV-4 preserved |

## Milestone gates
- ✅ **M1** (settle pipeline ready) — reconciler + mirror COMPLETE. Full flow PROVEN LIVE.
- ⏳ **M2** (first real ¥) — pipeline FULLY WIRED including (a1) STARTUP update. Waiting on first real Coconala 検収 in production. Loop is LIVE via launchctl `ai.anicca.gig-proactive` (5-min tick) + hourly reconciler menu item.

## Regression baseline
503/503 tests GREEN.

## Block conditions
1. No settle event in 30 days across ANY slot
2. INV regression uncloseable in 3 iters
3. crypto primitive fails
