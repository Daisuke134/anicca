# execution-notes.md — sprint-4 M1+M2

## Active /goal
`GOAL-sprint-4-M1-M2.md` (mailed to Dais via Resend id `0493d1f1-...`).

## Sub-feature status

| # | feature | phase | notes |
|---|---|---|---|
| a2 | earnings-to-settle-mirror | ✅ COMPLETE (Phase 6) | Full pipeline PROVEN LIVE on production gig: p-1782887987 roi 0→25000 |
| a1 | LAYER C STARTUP prompt update | ⏳ separate follow-up commit | Documented in mirror spec; enables real Coconala 検収 to auto-flow |
| b | earn-roi-reconciler | ✅ COMPLETE | Feature (b) sprint-4 done |
| c | dispatcher-live-dormant | 🔄 in progress | wire is_dormant_with_horizon behind 90d realized>0 gate |
| d | recipe-6-actions | pending | |

## Milestone gates
- ✅ **M1** (settle pipeline ready) — reconciler + mirror COMPLETE. Full flow PROVEN LIVE.
- ⏳ **M2** (first real ¥) — awaiting (a1) STARTUP update OR real Coconala 検収 in existing format.

## Regression baseline
460/460 tests GREEN.

## Block conditions
1. No settle event in 30 days across ANY slot
2. INV regression uncloseable in 3 iters
3. crypto primitive fails
