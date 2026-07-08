# Sprint-1 Contract Review — hl-realized-pnl

Reviewer: fresh-context vcsdd-adversary (strict-mode sprint contract review)
Contract: `contracts/sprint-1.md`
Compared against: `specs/behavioral-spec.md`, `specs/verification-architecture.md`, `evidence/sprint-1-red-phase.log`

## F-1 — BLOCKING — target: whole criteria set (spec_fidelity / verification_readiness) — PROP-021 (Tier-2 live E2E money-correctness capstone) is entirely absent from all 5 criteria

**What**: `verification-architecture.md` defines 28 proof obligations and is explicit that "1 Tier-2 live capstone required for Done (strict mode does not waive the Tier-2 obligation)" (line 87-88), and again: "Tier 2 (PROP-021) = the only way to actually prove the fill-based pipeline computes the CORRECT real-world number, using real settled fills instead of fixtures. Required for Done in strict mode (unlike a typical Tier-2 'nice to have'...)" (lines 99-103). PROP-021 is mapped to REQ-A2, REQ-B*, REQ-C1 — i.e. it is the only proof obligation that verifies the reconciler actually derives realized P&L from a live Hyperliquid `userFills` call end-to-end, rather than from a fixture that merely *mimics* the live shape.

None of CRIT-001 through CRIT-005's `passThreshold` fields mention PROP-021, `user_fills_by_time`, live data, or any E2E/integration run against the real Hyperliquid API. Every passThreshold in the contract is satisfied by `test_fills.py`, `test_reconcile.py` (fixture/injected-fake based), and `ledger.test.mjs` alone. A sprint that runs ONLY these fixture suites — all green — would satisfy every criterion in this contract, `overallVerdict: PASS`, while REQ-A2 (the requirement that realized P&L is "derived EXCLUSIVELY from Hyperliquid's own `userFills` fill records... via a live call to the Hyperliquid Info API") is never once exercised against the real API in this sprint.

This is precisely the class of defect the feature exists to fix: `behavioral-spec.md` section 2 documents that the OLD code was ~2 orders of magnitude wrong (-$0.0006 vs real -0.123734) despite presumably having internally-consistent logic against its own (wrong) data source. A fixture that *asserts* the live API returns numeric-string `closedPnl`/`fee` and integer `tid` (PROP-003's fixture, copied from `evidence/audit-userfills-summary.md`) proves the code handles that shape correctly IF that shape is what the live API actually returns on every call — but nothing in this contract requires that assumption to ever be checked against a live response. `NFR-1` (pagination) is also explicitly "discovered... during Phase 5 hardening's live E2E," meaning even that risk is only closed by PROP-021, which this contract never invokes.

This also reads as a direct violation of this repo's own workflow rule (`.claude/rules/dev-workflow.md`): "`vcsdd-adversary`（実装レビュー）| fresh adversary + agent 自己完結 E2E green（maestro E2E or 実ブラウザ/実行検証、fresh evidence）| blocking 0 件 + E2E green" — the implementation-review gate this contract feeds is required to include fresh E2E evidence, not fixture tests alone.

**Evidence**: `contracts/sprint-1.md` lines 12/17/22/27/32 (all 5 `passThreshold` strings, none mention PROP-021/live/E2E/`user_fills_by_time`); `specs/verification-architecture.md` lines 85-103, 116-153 (Done section = PROP-021 plan, explicitly gating strict-mode Done); `.claude/rules/dev-workflow.md` (adversary gate requires E2E green).

**Required fix**: Add a criterion (or extend an existing one, e.g. CRIT-002 or a new CRIT-006) whose `passThreshold` requires PROP-021's live E2E plan (Done section in verification-architecture.md) to run successfully against the audited wallet `0xa3cdd4...`, asserting (a) zero silent drops / zero fabricated extras, (b) the summed `net_usdc` matches the raw `(closedPnl - fee)` sum within tolerance, (c) a second call appends zero additional lines, (d) no "dry/fake/mock/simulated" language appears in the recorded output. Alternatively, if PROP-021 is deliberately deferred to a later, explicitly-planned sprint or to Phase 5 hardening as a SEPARATE gate that this sprint's Done does NOT depend on, the contract must say so explicitly (with a dated rationale) rather than silently omitting it — as written, `state.json` shows `sprintCount: 1` and the contract's own `scope` line covers the ENTIRE feature (all new/modified files in verification-architecture.md's file table), so there is no visible later sprint that would pick this up.

---

## F-2 — major — target: structural_integrity / (no criterion) — REQ-D4 (per-instance ledger/checkpoint isolation) has no proof obligation anywhere in verification-architecture.md, so no contract criterion can cover it

**What**: `behavioral-spec.md` REQ-D4 requires that a line recorded by this feature "SHALL NEVER cause a write to, or be influenced by the contents of, any OTHER instance's `earn-ledger.jsonl` or checkpoint file." Scanning the full PROP-001..022 "Covers" column in `verification-architecture.md`, no PROP-ID cites REQ-D4 (PROP-016 covers REQ-D2's identity/key-path reuse, which is adjacent but not the same claim — REQ-D2 is about not reimplementing key resolution, REQ-D4 is about path isolation). Since the contract's criteria are built by referencing PROP-IDs, and no PROP-ID exists for REQ-D4, this sprint has no verifiable pass condition proving cross-instance isolation. Given this feature explicitly touches file paths (`skills/earn/hl-trade/.last-fill-ts`, `skills/earn/state/earn-ledger.jsonl`) and the project's own memory record (`feedback_earn_identity_resolve_per_instance_gate_on_anicca_home.md`) flags exactly this class of bug (shared identity/path leakage across instances) as a recurring, real defect class in this codebase, this gap is more than cosmetic.

**Evidence**: `specs/behavioral-spec.md` lines 247-252 (REQ-D4); `specs/verification-architecture.md` lines 56-85 (PROP table, no REQ-D4 entry).

**Required fix**: Either verification-architecture.md needs a proof obligation for REQ-D4 (e.g. a static grep confirming both paths are constructed relative to a caller-supplied/`ANICCA_HOME`-scoped instance root, never a hardcoded absolute path or another instance's directory) and the contract needs a criterion citing it, or the contract must explicitly note this is covered by the existing PROP-016/identity-reuse check plus code inspection at Phase 3 and accept the residual risk explicitly.

---

## F-3 — minor — target: verification_readiness (CRIT-005) — ledger.mjs functional correctness (REQ-C2/REQ-C3) is graded under the "verification_readiness" dimension rather than spec_fidelity/implementation_correctness

**What**: CRIT-005's passThreshold is really two different claims bundled under one dimension label: (1) the *functional correctness* of `deriveLine`'s passthrough and `isProfitable`'s new disjunct (PROP-013, PROP-014a-e — this is spec_fidelity/implementation_correctness territory, since it's "does the code do what REQ-C2/C3 say"), and (2) the *process* claim that this is proven via a NEW test file rather than edits to the existing one (this IS legitimately verification_readiness — proving the verification apparatus itself wasn't weakened). Bundling both under one dimension means a reviewer scoring "verification_readiness" is implicitly also scoring ledger.mjs's core correctness, and there is no separate criterion anywhere that grades ledger.mjs's correctness under spec_fidelity or implementation_correctness. This doesn't break falsifiability (the passThreshold is still concrete and checkable) but it does mean the grading-schema's 5-dimension score for spec_fidelity/implementation_correctness is silently incomplete for the ledger.mjs slice of this feature's scope.

**Evidence**: `contracts/sprint-1.md` lines 28-32 (CRIT-005, dimension: verification_readiness, bundles both claims).

**Required fix**: Non-blocking; consider re-labeling CRIT-005 to implementation_correctness (or splitting into two criteria) in a future negotiation round if dimension-purity matters for downstream scoring aggregation. Not required to fix before Phase 2b/3.

---

## F-4 — note — target: implementation_correctness (CRIT-003) / edge_case_coverage (CRIT-002) — PROP-007 is claimed as a pass condition under two different criteria

**What**: PROP-007 (checkpoint advances to the LAST recorded fill's time, atomic write) is listed in CRIT-002's passThreshold ("...PROP-004/005/006/007/008/009/010/010b/011/022...") AND explicitly called out again in CRIT-003's passThreshold ("PROP-012... and PROP-007 (checkpoint == last recorded fill's time, not first) both pass"). This isn't contradictory (the same test can legitimately support two dimensions — checkpoint-advance-correctness is both an edge-case concern (E2/E4) and an implementation-correctness concern (composition-root ordering)), but it means the same single test result is double-counted toward two separately-weighted dimension scores. This is a minor scoring-hygiene note, not a fidelity gap.

**Evidence**: `contracts/sprint-1.md` line 17 (CRIT-002) and line 22 (CRIT-003), both citing PROP-007.

**Required fix**: None required; optional clarification in a future negotiation round on whether shared PROP-ID references across criteria are intentional design or an oversight.

---

## Summary

| ID | Severity | Target |
|---|---|---|
| F-1 | BLOCKING | spec_fidelity / verification_readiness — PROP-021 (Tier-2 live E2E) missing from all criteria |
| F-2 | major | structural_integrity — REQ-D4 has no proof obligation anywhere, so no contract coverage |
| F-3 | minor | verification_readiness (CRIT-005) — dimension bundling |
| F-4 | note | edge_case_coverage / implementation_correctness — PROP-007 cited under two criteria |

BLOCKING count: 1 -> overallVerdict: FAIL.
