---
feature: earn-roi-reconciler
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Verification Report — earn-roi-reconciler

## Proof Obligations

Lean; 19 required:true PROPs. All proved.

Trajectory:
- Phase 1c spec: 6 → 2 → 0 (3 iters)
- Phase 2b/2c: 398 → 426 → 432 (+34)
- Phase 3 impl: 6 → 0 (2 iters; 2 critical + 3 high + 1 medium closed)
- Live E2E on production gig BEFORE adversary: real pass_id p-1782887606 roi 0 → 40000, ~/gig SHA unchanged, gig-cli ALIVE

## Summary

Key security/correctness wins:
- Real Coconala partial→full pattern handled: monotone-MAX picks the higher value
- Coconala re-settle (same value replay): counted as skipped_dup per spec
- Malformed roi lines PRESERVED verbatim via __raw__ sentinel (lossless)
- Crash-safety proven via monkeypatched os.replace + SHA-256 diff
- Multiple malformed settle lines per run kept distinct via __malformed__:<offset>
- pick_next lowest-priority reconciler item proved concretely (earner score 1.0 > reconciler score 0.0)
- INV-1 / INV-4 / INV-P1 / J8 all preserved
</parameter>
