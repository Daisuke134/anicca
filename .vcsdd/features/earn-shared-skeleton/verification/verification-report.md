---
feature: earn-shared-skeleton
phase: 5
mode: lean
sprint: 1
generated_at: 2026-07-01T05:10:00+09:00
---

# Verification Report — earn-shared-skeleton sprint-1

## Proof Obligations

Lean-mode Phase 5: REQUIRED proof obligations = **0**. The skeleton's 13 required:true PROPs
are Tier 0 (unit tests) and Tier 1 (property-tests / integration tests) — they are
mechanically verified by the test harness, not by formal proof (Tier 2/3).

| PROP | Tier | Mechanism | Status |
|------|------|-----------|--------|
| PROP-A-classify | 1 | property-test (10k cases via test fixtures) | proved (42/42 tests pass) |
| PROP-A-oauth | 0 | unit-test (8 phishing fixtures + happy path) | proved |
| PROP-A-hook-allowlist | 0 | unit-test (7 RCE attack fixtures + happy path) | proved |
| PROP-B2-cost-formula | 1 | property-test + golden ¥2700 | proved |
| PROP-B4-killswitch | 1 | property-test (grace + multiplier boundary) | proved |
| PROP-C1-evidence | 0 | unit-test (paraphrase rejection corpus) | proved |
| PROP-C3-mutation-gate | 1 | integration-test (sandbox + fixture verdict) | proved |
| PROP-F2-dedup | 1 | property-test (rotating-id collapse) | proved |
| PROP-G2-static | 1 | static-analysis (AST walker) | proved |
| PROP-G2-runtime | 1 | integration-test (3-check pattern + ROUND-2-001 attack) | proved |
| PROP-E5-spawn-pin | 1 | integration-test (12 fixture cases f-i..f-xii) | proved |
| PROP-I1-proposal-loop | 1 | integration-test (round-1/2/3 fixtures) | proved |
| PROP-I2-deliverable-loop | 1 | integration-test (round-1/2/3 + scope-clarify msg) | proved |

All 13 required:true PROPs reach `proved` status via the test harness. Test invocation
evidence in `evidence/sprint-1-green-phase.log` (142/142 pass, 0.07s).

Optional / required:false PROPs: 15 additional PROPs in the spec; some have tests, some
are scope-deferred to sprint-2 (see Sprint-1/Sprint-2 Scope Cut table in behavioral-spec.md
section "Sprint-1 / Sprint-2 Scope Cut").

## Summary

Sprint-1 ships:
- **Verification layer** — 13 lib modules (12 Python + 1 dispatch.py companion) totaling
  ~2200 LOC, 142 passing tests across 14 test modules, 0.07s suite.
- **Runtime glue** — 8 shell scripts + 4 Python dispatchers in
  `~/anicca/skills/_shared/*.sh` and `*-dispatch.py` (ENV VAR pattern; no heredoc injection
  surface).
- **Trust anchors** — 4 seed/anchor files (anicca-bot.pub ed25519 fixture pubkey,
  hook-modules-allowlist.txt, trusted-authors.json, payout-endpoint-allowlist.json with
  5 MVP platforms).

Verification gates passed:
- Phase 1c spec gate: 6-iteration trajectory (15 → 2 → 3 → 0 (apparent) → architect-reversal
  to remove human-touch → 3 → 0). Converged at iter-6.
- Phase 2a Red: 14 test modules, all fail at import (canonical RED).
- Phase 2b Green: 142/142 pass in 0.07s.
- Phase 2c Refactor: 142/142 still pass after extracting `_common` helpers.
- Phase 3 sprint-1: 3-iteration trajectory (18 → 5 → 0). Converged at iter-3 (lean cap).

Phase 5 deliverables (this report + security-report.md + purity-audit.md + at least one
captured artifact under `security-results/`) generated 2026-07-01.

No required proof obligations are `skipped`. Phase 6 (convergence) gate prerequisites met.
