# VCSDD Adversary Verdict — earn-slot-loop-integration (PHASE 3 IMPLEMENTATION REVIEW, iteration 1, lean)

- feature: earn-slot-loop-integration
- reviewType: implementation (Phase 3)
- timestamp: 2026-06-29
- iteration: 1
- mode: lean
- context: ZERO builder context. Disk-only. No `input/manifest.json` exists at this scope; reviewed the
  files named in the task against `specs/behavioral-spec.md` (iter-3, gate PASSED) under
  `/Users/operator/anicca-human-funded/`. NOTE: I have NO Bash tool — I did not execute the suite; the
  builder's "7/7 unit pass / E2E pass / PROP-013+021 pre-existing-flaky" claims are judged by reading the
  test + impl source, NOT by re-running. Where a claim is unverifiable from disk I say so explicitly.

## overallVerdict: **FAIL**

| Dimension | Verdict |
|---|---|
| 1. Spec Fidelity | **FAIL** |
| 2. Edge Case Coverage | **FAIL** |
| 3. Implementation Correctness | **PASS** |
| 4. Structural Integrity | **PASS** |
| 5. Verification Readiness | **FAIL** |

`overallVerdict = FAIL` (≥1 dimension FAIL).
**Converges (4-D)? NO** — spec ✓(core wiring) but a fake-earn slot leaks to the prod SSOT; test ✗ (REQ-4/REQ-5/REQ-6 acceptance tests missing); impl ✓(in-scope logic); verification ✗ (the E2E does NOT exercise the central GAP-A/REQ-2 and would pass even if it regressed).

---

## Top must-fix (in priority order)

1. **FIND-IMPL-001 (MAJOR)** — `skills/registry.json:117-120` ships `earn/_probe` as `status:"live"`. Set it to `declared` or remove it from the committed SSOT.
2. **FIND-IMPL-002 (MAJOR)** — `runtime/loop/__tests__/earn-slot-e2e.test.mjs:61-71` does not assert anything that fails if GAP-A/REQ-2 (`index.mjs:319`) regresses. Add an assertion on the wake line's classification.
3. **FIND-IMPL-003/004/005 (MEDIUM)** — the spec's own Acceptance list (REQ-4 path resolution, REQ-5 prompt, REQ-6 skill_missing) has no test.

---

## Dimension 1 — Spec Fidelity: **FAIL**

Core wiring of REQ-1..REQ-7 is present and correct:
- REQ-1 `isEarnSlot` = legacy `{earn,yield,hl_trade,x402_sell,token_launch}` ∪ `startsWith('earn/')` — `earn-slot.mjs:9-12`. ✓
- REQ-2 classify gate uses it — `index.mjs:319` (`else if (isEarnSlot(slot))` → `classifyEarnResult`). ✓
- REQ-3 env: `buildSkillEnv` gates on `isEarnSlot` (`index.mjs:445`) and `EARN_STRATEGY` PRESERVES the fat-earn fallback — `index.mjs:450` (`process.env.EARN_STRATEGY || earnStrategyFor(slot) || (a.strategy.trim() || 'yield')`); `earnStrategyFor('earn')===null` (`earn-slot.mjs:21`) so fat `earn` keeps `args.strategy||'yield'`. ✓ EARN_LEDGER passed only when configured (`index.mjs:452`). ✓
- REQ-4 path: `EARN_SLOT_DIRS` literal excludes `earn/<sub>` → else branch → `skills/earn/<sub>/run.sh` (`index.mjs:375-382`); legacy slots → `skills/earn/run.sh`. ✓
- REQ-5 prompt BOTH spots fixed: tool description no longer denies a generic/earn slot and names `earn/<sub>` (`prompt.mjs:132-138`); `buildUserMessage` builds `earnSubs` dynamically from `ctx.activeSkillSlots` and the denial copy is gone (`prompt.mjs:181-182, 209`). ✓
- REQ-6 registry declares the 5 earners (`registry.json:97-116`). ✓

### FIND-IMPL-001 (spec_fidelity / security_surface, MAJOR — BLOCKING)
`skills/registry.json:117-120` commits `earn/_probe` with `"status": "live"` and a real `skills/earn/_probe/run.sh` (`run.sh:1-9`) that writes a fabricated earn line `{"earn_usdc":0.01,...}` to the live `$EARN_LEDGER`. The registry is the SSOT that `install.sh` syncs into EVERY production body (registry.json `description`), so this exposes a **fake-earn slot to the production loop**: it appears in `activeSkillSlots` → the system-prompt "Available skill slots" (`prompt.mjs:103-104`), the `run_skill` enum (`brain.mjs:62`), and the `buildUserMessage` per-method-earner bullet (`prompt.mjs:209`). The real model can pick it, run a no-op, burn a wake, and pollute the real earn-ledger with junk 0.01 lines. This is exactly the "no fake/dry run in production" prohibition (project HARD RULE 0.24). The spec (Scope item 4) calls `_probe` a **stub used to E2E-prove** — it does NOT authorize a live production slot, and REQ-6 enumerates only the 5 real earners. Critically, **the E2E does not even need it live**: `index.mjs:252-302` runs whatever slot the (mock) brain returns with NO allowlist check against `activeSkillSlots`, so flipping `_probe` to `declared` keeps the E2E green while removing the production hazard.
Evidence: `skills/registry.json:117-120`; `skills/earn/_probe/run.sh:7`; `runtime/loop/index.mjs:252-302`; spec Scope(4) + REQ-6.

---

## Dimension 2 — Edge Case Coverage: **FAIL**

Handled in code: `earnSubs` is null-safe when `ctx.activeSkillSlots` is absent (`prompt.mjs:181` `(ctx.activeSkillSlots || [])`); legacy slots keep their map strategy (`earn-slot.mjs:21`); non-earn (`cook`) → false (unit-tested `earn-slot.test.mjs:7`).

### FIND-IMPL-005 (test_coverage, MEDIUM — BLOCKING)
REQ-6 states a declared `earn/<sub>` with no `run.sh`, if forced, ⇒ `skill_missing` (not crash). The code path exists (`index.mjs:384-385` `access` throws → `notFound:true` → `index.mjs:313-314` `kind='skill_missing'`), but there is **no test anywhere** for the `notFound`/`skill_missing` outcome — not in `earn-slot-e2e.test.mjs`, not in `integration.test.mjs` (which covers `skill_error`/timeout but never a missing entrypoint). An enumerated spec edge with zero coverage.
Evidence: `runtime/loop/index.mjs:313-314, 384-385`; spec REQ-6; absence across `runtime/loop/__tests__/*`.

---

## Dimension 3 — Implementation Correctness: **PASS**

I found no logic defect in the in-scope new/changed code:
- `earn-slot.mjs` predicates are correct, including the trailing-slash edge (`earn/` → `isEarnSlot` true, `earnStrategyFor` → `'' || null` = null, `earn-slot.mjs:22`) — harmless, not in registry.
- The brain→prompt data flow that REQ-5 depends on is real: `brain.mjs:60` calls `buildUserMessage(ctx)`; `ctx.activeSkillSlots` is populated by `assembleContext` (`context.mjs:47`) from `index.mjs:225` ← `liveSlotNames(registry)` (`index.mjs:102`). So `earnSubs` actually receives live earn slots. Verified end-to-end by reading, not assumed.
- The E2E (`earn-slot-e2e.test.mjs`) is NOT fabricated and is non-tautological **for GAP-B/REQ-3**: the earn-ledger line at `$EARN_LEDGER` only exists if `buildSkillEnv` passed `EARN_LEDGER`+`EARN_STRATEGY=_probe` to the child; `el.strategy==='_probe'` (`:69`) and `el.wake===wakeLine.wake_id` (`:70`) genuinely prove env+WAKE_ID reached the child.

(The weaknesses of the E2E concern what it FAILS to prove — see Dimension 5 — not a correctness bug in the shipped logic.)
Evidence reviewed: `earn-slot.mjs:9-24`; `index.mjs:319,445-453,375-382`; `brain.mjs:59-62`; `context.mjs:47`; `earn-slot-e2e.test.mjs:43-76`.

---

## Dimension 4 — Structural Integrity: **PASS**

- `earn-slot.mjs` is genuinely PURE: only two string functions + a const; no `fs`, no `child_process`, no `process`, no time/random (`earn-slot.mjs:1-26`). ✓
- ONE predicate (`isEarnSlot`) reused in both the classify gate and the env builder; `earnStrategyFor` reused for the strategy — single source of truth, exactly as REQ-1 intends (`index.mjs:319` + `:445/:450`). ✓
- Small, well-named, no duplication, no dead code in the new module.
Evidence: `runtime/loop/earn-slot.mjs:1-26`; reuse at `index.mjs:319, 450`.

---

## Dimension 5 — Verification Readiness: **FAIL**

### FIND-IMPL-002 (test_quality / verification, MAJOR — BLOCKING)
The E2E does NOT exercise the feature's central requirement, **GAP-A / REQ-2 (the classify gate at `index.mjs:319`)**. Trace: if line 319 were reverted to the old `['earn','yield','hl_trade','x402_sell','token_launch'].includes(slot)` (i.e. GAP-A regresses, `earn/<sub>` excluded), then `buildSkillEnv` STILL gives the child `EARN_LEDGER` (GAP-B is an independent `isEarnSlot` call at `:445`), the stub STILL writes the earn-ledger line, and the wake line STILL has `slot='earn/_probe'`. Every assertion in `earn-slot-e2e.test.mjs:61-71` still passes — the test never inspects `kind`/`profitable`. So the spec's anti-tautology claim (spec line 81: "fails closed if GAP-A/B regress") is true ONLY for GAP-B. REQ-2 has zero anti-tautological coverage. Fix: assert the wake line is `kind:'wake'` with `profitable` reflecting the ledger (e.g. seed a profitable `_probe` line and assert `profitable===true`).
Evidence: `runtime/loop/index.mjs:319` vs `:445`; `runtime/loop/__tests__/earn-slot-e2e.test.mjs:61-71`; spec line 81.

### FIND-IMPL-006 (verification_tool_mismatch, MEDIUM)
Even if FIND-IMPL-002 is fixed, the E2E cannot meaningfully classify profit: `index.mjs:79-91` loads `isProfitable` only from `…/skills/earn/lib/ledger.mjs`, but the real export lives in `skills/_shared/lib/ledger.mjs` (`skills/earn/lib/record.mjs:8` imports `../../_shared/lib/ledger.mjs`). No `skills/earn/lib/ledger.mjs` exists in this tree → `isProfitable` falls back to `() => false` (`index.mjs:88-89`) in both the repo and the E2E's tmp home. So `classifyEarnResult` returns `profitable:false` unconditionally in the test — REQ-2's "profit only from the ledger" is not actually proven. (Pre-existing path bug, out of declared scope to FIX, but it nullifies the E2E's ability to verify REQ-2.)
Evidence: `runtime/loop/index.mjs:79-91`; `skills/earn/lib/record.mjs:8`; no `skills/earn/lib/ledger.mjs`.

### FIND-IMPL-003 (test_coverage, MEDIUM — BLOCKING)
Spec Acceptance line 71-72 explicitly requires a **unit** test for path resolution (`earn/gig→skills/earn/gig/run.sh`; `yield→skills/earn/run.sh`, REQ-4 "Regression-tested" line 54). The path logic is inline in `runSkillWithKillRef` (`index.mjs:375-382`) — not extracted, not exported, not unit-tested. `earn-slot.test.mjs:5-11` covers only `isEarnSlot`/`earnStrategyFor`. The E2E covers exactly ONE path (`earn/_probe`); the legacy `yield→skills/earn/run.sh` regression and the `earn/gig` resolution are untested.
Evidence: `runtime/loop/__tests__/earn-slot.test.mjs:5-11`; `index.mjs:375-382`; spec line 71-72.

### FIND-IMPL-004 (test_coverage, MEDIUM — BLOCKING)
REQ-5 has no regression guard. `prompt.test.mjs` contains NO assertion that the "no generic earn slot" denial is absent, nor that a live `earn/<sub>` is surfaced by `buildUserMessage` / `buildSystemPrompt`. A future edit could re-introduce the denial (the exact iter-1/2 failure mode) and the suite would stay green. The verification-architecture's stated prompt check ("system prompt include a live earn/* slot; no 'no generic earn slot' string") is unimplemented.
Evidence: `runtime/loop/__tests__/prompt.test.mjs:1-99` (no `earn/` and no denial-absence assertion); `prompt.mjs:132-138, 181-182, 209`.

### FIND-IMPL-008 (verification, LOW/MEDIUM)
The "PROP-013 / PROP-021 are pre-existing flaky and also fail on `origin/main` without this change" claim is NOT verifiable from disk: no baseline test log is committed under any `evidence/` directory, and I cannot run git/tests. Both are timing/process-race tests (`integration.test.mjs:199` SIGTERM-ordering, `:390` profitability after async classify) so flakiness is plausible, but "not a regression" is taken on faith. A committed baseline run log is required before treating 2 failing tests as acceptable.
Evidence: `runtime/loop/__tests__/integration.test.mjs:199, 390`; no baseline log on disk.

---

## FIND-010 carry-over (spec_gap, MEDIUM — NON-BLOCKING)

### FIND-IMPL-007
The spec's prior MEDIUM (FIND-010) is **still open**: the third hardcoded earn menu in `buildSystemPrompt` (`prompt.mjs:69-101`, "## Your earn tools …" + MINDSET + per-slot Tips) was neither made slot-driven nor explicitly deferred in REQ-5. It frames the agent's worldview around the legacy 5 and never mentions `earn/<sub>`. NON-BLOCKING (consistent with the spec gate): it carries no denial string, and the DYNAMIC "## Available skill slots" list (`prompt.mjs:103-104`, fed by `ctx.activeSkillSlots`) still surfaces a live `earn/<sub>` to the model, so it does NOT hard-block the brain from picking `earn/<sub>`. Recommend making the block slot-driven or recording the deferral.
Evidence: `prompt.mjs:69-101, 103-104`; spec REQ-5 (no mention of `:69-101`).

---

## convergenceSignals
- findingCount: 8 (FIND-IMPL-001..008)
- blocking: FIND-IMPL-001 (MAJOR), FIND-IMPL-002 (MAJOR), FIND-IMPL-003/004/005 (MEDIUM)
- non-blocking: FIND-IMPL-006 (pre-existing path bug, out of scope), FIND-IMPL-007 (FIND-010 carry), FIND-IMPL-008 (unverifiable claim)
- 4-D convergence: **NO** (verification dimension fails: the central REQ-2/GAP-A is not exercised, and 3 spec-mandated acceptance tests are absent)

## decision: **FAIL — route to Phase 2b (fix tests + remove the live probe), then re-review.**
