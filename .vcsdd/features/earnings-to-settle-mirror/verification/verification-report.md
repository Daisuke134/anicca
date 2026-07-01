---
feature: earnings-to-settle-mirror
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Verification Report — earnings-to-settle-mirror

## Proof Obligations

Lean; 17 required:true PROPs. All proved.

Trajectory:
- Phase 1c spec: 6 → 3 → 0 (3 iters — hit lean cap on iter-3 PASS)
- Phase 2b/2c: 432 → 455 → 460
- Phase 3 impl: 1 → 0 (2 iters; critical missing integration test file)
- Live E2E on production gig BEFORE final adversary: real gig pass_id
  p-1782887987 roi_jpy_realized 0 → 25000 via mirror + reconciler pipeline

## Summary

Sprint-4 (a2) mirror ships. (a1) LAYER C STARTUP prompt update is documented
as a separate follow-up commit. When (a1) lands, real Coconala 検収 events
will fire the full pipeline automatically. The mirror is fail-closed via
`unmatched-requestId-<X>` sentinels that reconciler routes to
`.unmatched.jsonl` — pre-(a1) rows are audible not silent.
</parameter>
