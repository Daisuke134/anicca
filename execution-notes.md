# execution-notes.md — sprint-4 M1+M2

*Live resume/audit state for the /goal run. Update after every phase pass.*

## Active /goal

`GOAL-sprint-4-M1-M2.md` (3578 chars, PASS length; mailed to Dais via Resend id `0493d1f1-dd89-4701-8f01-be79fac5cac0` on 2026-07-01).

## Open sub-features (4)

| # | feature | phase | adversary iter | notes |
|---|---|---|---|---|
| a | layer-c-settle-wire | not started | — | tmux inner core dequeue + settle.jsonl append |
| b | earn-roi-reconciler | not started | — | hourly menu item: earnings ↔ roi.jsonl reconcile |
| c | dispatcher-live-dormant-mode | not started | — | live-mode flag = "any row realized>0 in 90d" |
| d | recipe-6-actions-real-wire | not started | — | kill_server / send_keys / login / npm_install / git_checkout / escalate_via_bot2bot |

## Baseline (pre-run)

- pytest: 398 GREEN
- 4 tmux slots on LAYER B: gig / clip / affiliate / bounty
- roi_jpy_realized = 0 everywhere (no settle events observed yet)
- INV-1 / INV-4 / INV-P1 / J8 all honored
- gig has 23 in-flight Coconala applications (0 settled)

## Milestone gates

- **M1** (LAYER C settle wire) — depends on feature (a) + (b) COMPLETE
- **M2** (first real ¥) — depends on M1 + real buyer 検収 event

## Block conditions (stop, do NOT thrash)

1. No settle event across ANY slot in 30 days → ROI model wrong, report + stop
2. INV regression uncloseable in 3 adversary iters → propose rollback, stop
3. openssl / crypto primitive fails → report + minimal repro, stop

## Change log

- 2026-07-01: goal drafted + mailed + execution-notes initialized.
