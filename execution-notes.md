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

## sprint-4 (a1) post-deploy notes (2026-07-01)

- (a1) STARTUP deployed successfully; gig-cli.sh --status=ALIVE
- **task #6 hook fix**: `~/.claude/settings.json` PreToolUse:Bash hook was `rtk hook claude` (PATH-dependent). Headless tmux sessions couldn't resolve `rtk` → repeated "PreToolUse:Bash hook error". Fixed by pinning to `/opt/homebrew/bin/rtk hook claude`. Post-fix: session runs clean, no more hook errors.
- **First post-fix pass**: correctly detected concurrency (multiple restarts + healthcheck cron) and skipped browser-driving to avoid collision. Registered cron `52b154a2` for future ticks. This is the CORRECT anti-collision behavior spec'd in HARD 0.36's INV-4.
- **task-request-map.jsonl materialization**: waiting for first uncontested B2 apply pass (next hourly cron fire).
- M2 auto-close path: unchanged. First real Coconala 検収 → gig-cli.sh a1 lookup → earnings row w/ pass_id → (a2) mirror → (b) reconciler → roi_jpy_realized > 0 → M2 satisfied.

## task #2 diagnosis (2026-07-01)

- `~/clips/queue/` is empty because it's fed by `producer.sh` (creates mp4+caption)
  while the proactive-loop dispatcher enqueues `produce-clip` task descriptors to
  `~/loops/clip/tasks/` (34 descriptors queued, 5-min tick, none consumed).
- The clip LAYER C session's STARTUP (`clip-cli.sh:21`) only invokes `run.sh`
  (POSTS from queue), never `producer.sh` (FILLS queue). No consumer bridges
  `~/loops/clip/tasks/` → `producer.sh`.
- FIX (out of scope for M2 sprint-4, deferred to sprint-5): mirror the gig-cli.sh a1
  pattern in clip-cli.sh STARTUP:
    1. Read oldest `~/loops/clip/tasks/*.json`
    2. If `picked.name == "produce-clip"`, invoke `producer.sh` with the task's
       platform/params
    3. Move the consumed task descriptor to `~/loops/clip/tasks/done/`
- Impact: without this fix, `produce-clip` tasks pile up indefinitely and no
  clips are ever posted. NOT a M1/M2 blocker (gig is the M1/M2 primary slot).
- Sprint-5 candidate feature: `clip-cli.sh a1-equivalent` for task-descriptor
  consumption + producer.sh wire.

## task #5 status (山本さん #5123100 あい庵 SNS ¥40k/月) — CLOSED/lost

Full timeline from gig data (2026-06-30 → 07-01):
1. Applied w/ site-specific 3-improvement proposal — buyer replied "契約手続きを進めたい"
2. Formal 見積り sent via direct_offer/4857277 (¥40,000/月, 定期購入, 期限 7/7)
3. Two follow-ups sent (2026-06-30 23:38, 07-01 01:17)
4. **Result**: 公開募集終了 + direct_offer/4857277 → 404 (offer link dead)
   → outcome=`ignored_closed`, lesson: "高額見積りは決断を促す締切設定が必要"

M2 candidate: NO (deal closed). The gig-cli.sh a1 pipeline still stands
ready for the next buyer that reaches 検収 stage. Cron 52b154a2 next
:27 tick continues the discovery.
