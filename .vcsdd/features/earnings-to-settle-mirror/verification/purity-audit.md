---
feature: earnings-to-settle-mirror
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Purity Boundary Audit — earnings-to-settle-mirror

## Declared Boundaries

| Layer | Symbol | Side effects |
|---|---|---|
| PURE | parse_earnings_line, is_settled_row, extract_pass_id_or_sentinel, build_settle_row, settle_row_dedup_key | none |
| I/O SINK | mirror_earnings_to_settle | reads earnings.jsonl + settle.jsonl tail; writes settle.jsonl append + state markers |
| ORCHESTRATOR | proactive-loop-dispatch.py STEP 6 elif branch | 1 conditional, ~8 lines |

## Observed Boundaries

- All 5 PURE symbols verified side-effect-free via 23 unit tests.
- mirror_earnings_to_settle write ordering (append → last-run → offset LAST)
  documented and tested.
- Dispatcher branch integration tested via 5 additional tests including
  full-pipeline (mirror→reconciler→roi) round-trip.

## Summary

Purity clean. Dispatcher patch scope is exactly 1 elif branch + 1
next_candidate conditional (< 15 lines) as spec declares. Live production
pipeline demonstrated end-to-end on real gig pass_id.
</parameter>
