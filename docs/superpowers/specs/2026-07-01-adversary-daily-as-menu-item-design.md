---
id: adversary-daily-as-menu-item
status: sprint-3-partial (sprint-4 completes forced-pick)
sprint: 3
task: "#35"
created: 2026-07-01
parent_spec: 2026-07-01-proactive-loop-architecture-and-cleanup-design.md
---

# Sprint-3 #35 — Adversary-daily as Menu Item

## What sprint-3 ships (LOCKED)

1. Canonical `~/loops/gig/menu.json` includes an `adversary-daily-review`
   item under `category: "adversary"` with `min_cadence_seconds: 86400`
   (= once per 24h). Zero ROI (intentional; see §sprint-4 below).
2. Sprint-1 `adversary-daily.sh` launchd wrapper stays absent from
   `launchctl list` (parent architecture spec INV-3).
3. Sprint-2 EDGE-S7 test (`test_edge_cases_sprint2.py`) proves cadence
   exclusion + companion cadence-elapsed eligibility.
4. New regression test module
   `test_adversary_menu_item_production_regression.py` (3 tests) guards:
   - production gig menu.json has adversary item with cadence=86400
   - sprint-1 adversary-daily.sh not in launchd
   - EDGE-S7 test file / assertions still present

## What sprint-3 DOES NOT ship

The adversary item's ROI score = `roi_estimate_jpy × probability_of_landing`
= 0 × 1.0 = 0. It will therefore lose EVERY `pick_next` call against any
non-zero-ROI item. In production gig the winning pick is
`follow-up-warm-leads` (score 16000). So — despite being installed and
cadence-tracked — **the adversary item never wins pick_next in sprint-3
without external help**. That's OK: sprint-3 #35's charter was "install
the menu item + regression-guard it", not "force the pick".

## Sprint-4 completes

- Add a new field `force_pick_after_cadence: true` to the menu item; when
  the cadence has elapsed AND the item has this flag, `pick_next` returns
  it in priority position (bypasses ROI ordering) — a "must run" gate.
- OR: add a separate `must_run_cadence` return path from `pick_next` that
  yields the adversary item independently of the ROI pick.
- Wire the STEP 6 ACT to spawn `vcsdd-adversary` subagent when the picked
  item's `category == "adversary"` (currently STEP 6 just enqueues a
  tasks/*.json descriptor; sprint-4 adds the category-conditional spawn).
- Add integration tests for the forced-pick behavior with a fake clock.

## Test coverage summary

| Concern | Test | Status |
|---|---|---|
| cadence exclusion (< 24h) | test_edge_s7_adversary_daily_respects_cadence | sprint-2 GREEN |
| cadence elapsed re-eligible | test_edge_s7_adversary_daily_eligible_after_cadence | sprint-2 GREEN |
| production menu present | test_production_gig_menu_has_adversary_daily_item | sprint-3 #35 GREEN |
| sprint-1 wrapper absent | test_sprint1_adversary_daily_sh_not_in_launchd | sprint-3 #35 GREEN |
| EDGE-S7 file guard | test_edge_s7_regression_still_covers_adversary_cadence | sprint-3 #35 GREEN |
| forced-pick when cadence due | (sprint-4) | DEFERRED |
| category-conditional subagent spawn | (sprint-4) | DEFERRED |

Total: 5 GREEN tests locking sprint-3 state, 2 DEFERRED to sprint-4.

## Live production state

`~/loops/gig/menu.json` currently ships with the adversary item as row #5:
```json
{
  "name": "adversary-daily-review",
  "category": "adversary",
  "platform": "internal",
  "roi_estimate_jpy": 0,
  "probability_of_landing": 1.0,
  "expected_settlement_days": 0,
  "required_budget": "LIGHT",
  "min_cadence_seconds": 86400
}
```

`launchctl list | grep adversary` returns no rows — no sprint-1 wrapper active.
