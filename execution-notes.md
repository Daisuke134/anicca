# execution-notes.md — sprint-4 M1+M2

*Live resume/audit state for the /goal run. Update after every phase pass.*

## Active /goal

`GOAL-sprint-4-M1-M2.md` (mailed to Dais via Resend id
`0493d1f1-dd89-4701-8f01-be79fac5cac0` on 2026-07-01).

## Sub-feature status

| # | feature | phase | notes |
|---|---|---|---|
| a | earnings-to-settle-mirror (reframed) | 1c adversary iter-1 running | mirror pattern, LAYER C untouched (INV-1 preserved) |
| b | earn-roi-reconciler | ✅ COMPLETE (Phase 6 PASS) | 34 tests + live E2E on real gig p-1782887606: roi 0 → 40000, ~/gig SHA unchanged |
| c | dispatcher-live-dormant | not started | |
| d | recipe-6-actions | not started | |

## Milestone gates

- ✅ **M1 half** (reconciler ready) — feature (b) COMPLETE
- ⏳ **M1 rest** (mirror pipeline ready) — feature (a) in progress
- ⏳ **M2** (first real ¥) — depends on real Coconala 検収 landing in earnings.jsonl

## Regression baseline

432/432 tests GREEN (as of feature (b) close).

## Block conditions (unchanged)

1. No settle event across ANY slot in 30 days → ROI model wrong
2. INV regression uncloseable in 3 adversary iters
3. openssl / crypto primitive fails
