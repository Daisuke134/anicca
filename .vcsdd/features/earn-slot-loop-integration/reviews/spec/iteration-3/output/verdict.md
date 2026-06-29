# VCSDD Adversary Verdict — earn-slot-loop-integration (Phase 1c SPEC GATE, iteration 3, lean)

- feature: earn-slot-loop-integration
- reviewType: spec (Phase 1c)
- timestamp: 2026-06-29
- overallVerdict: **PASS**
- iteration: 3
- mode: lean
- note: No `input/manifest.json` under this scope. Reviewed `specs/behavioral-spec.md` (iter-3) +
  `specs/verification-architecture.md` against the LIVE runtime under `/Users/anicca/anicca/`:
  `runtime/loop/{index,prompt,earn-detect,brain}.mjs`, `skills/registry.json`. Every line citation in
  the spec was re-derived from the real files (the builder cited wrong prompt.mjs lines in iters 1-2).

## Dimensions

| Dimension | Verdict |
|---|---|
| 1. Spec Fidelity | **PASS** |
| 2. Edge Case Coverage | **PASS** |
| 3. Completeness / Gaps | **PASS** |
| 4. Structural Integrity | **PASS** |
| 5. Verification Readiness | **PASS** |

`overallVerdict = PASS` (all 5 PASS, zero open criticals, zero new criticals).

---

## Prior-finding resolution (iter-2 verdict)

### NEW-001 (CRITICAL) — GAP-C mis-located the denial + omitted the every-wake user message — **RESOLVED**
Re-derived against `prompt.mjs`:
- The denial copy "...there is NO generic \"earn\" slot" is in the `getToolDefinitions` run_skill
  DESCRIPTION at **`prompt.mjs:133`** (description block spans `:132-138`; the function name is `:131`).
  The iter-3 spec now cites this exact spot — GROUNDING line 24 + REQ-5(a) say `prompt.mjs:131-138`. ✓ ACCURATE.
- The second denial "...there is no generic \"earn\"" is in `buildUserMessage` at **`prompt.mjs:199`**, and
  `ALL=['yield','hl_trade','x402_sell','token_launch','cook']` is at **`prompt.mjs:179`** (spec says `≈:178`,
  within an explicit `≈`). `buildUserMessage` is defined `:163-208` (spec cites `163-208`). ✓ ACCURATE.
- Verified `buildUserMessage(ctx)` reads `ctx.positionsSummary/recentSlots/avoidSlot/balanceUsdc/reserveUsdc/
  wakeId/tier` but NEVER `ctx.activeSkillSlots`/`skillCatalog` — exactly as the spec states (REQ-5 line 60-62,
  GROUNDING line 26). The spec now REQUIRES `buildUserMessage` to build its menu DYNAMICALLY from live slots in
  `ctx`. Feasibility confirmed: `ctx.activeSkillSlots` is already populated by the loop (`index.mjs:224` →
  `assembleContext`), so "pass them into ctx" is already true; only `buildUserMessage` must start reading them.
- REQ-5 now names BOTH real spots (tool description + buildUserMessage), not the bogus `69-101`. The grounding
  failure mode that sank iters 1-2 is corrected.

### NEW-002 (HIGH) — earn-ledger correlation key + unprovable anti-tautology — **RESOLVED**
- `earn-detect.mjs:40` correlates with `lines.find(l => l.wake === wakeId)` (header `:6` agrees). ✓ ACCURATE.
- The spec's stub line is now keyed `wake` (NOT `wake_id`): Scope (4) line 39 `{"wake": <WAKE_ID>, ...}`
  "(NOT wake_id)"; Acceptance line 73-74 `{"wake": <WAKE_ID>, "earn_usdc": 0.01}` with the explicit note
  "key MUST be `wake` — earn-detect.mjs:40 matches `l.wake === wakeId`". So `classifyEarnResult` will match.
- E2E "EARN_LEDGER-reached-child" observation is SOUND: `buildSkillEnv` passes `EARN_LEDGER` to the child only
  when (a) the slot is `isEarnSlot` and (b) `config.EARN_LEDGER` is set (`index.mjs:448`). The stub writes its
  line to `$EARN_LEDGER` (spec line 78-79). `classifyEarnResult` reads `defaultEarnLedgerPath(config)` which
  returns `config.EARN_LEDGER` first (`earn-detect.mjs:60`) — the SAME path. If GAP-A/B regress, `earn/_probe`
  falls to the else branch (`index.mjs:451`), the child gets NO `EARN_LEDGER`, the stub cannot write the line at
  the path the test reads, and assertion (b) fails closed. The spec replaced the prior "stub must emit a sentinel"
  gap with a cleaner, valid discriminator (the line's existence at `$EARN_LEDGER` IS the proof). Anti-tautology
  (spec line 81) holds.

### NEW-003 (MEDIUM) — fat `earn` slot's EARN_STRATEGY fallback — **RESOLVED**
`index.mjs:446` is `EARN_STRATEGY: process.env.EARN_STRATEGY || EARN_SLOTS[slot] || (a.strategy?.trim() || 'yield')`,
and `EARN_SLOTS.earn = null` (`:439`). REQ-3 (lines 49-52) now explicitly says: "MUST PRESERVE the existing
fallback (index.mjs:446): for the fat `earn` slot it stays `args.strategy || 'yield'` (NOT null/empty); for the
legacy action slots it is the map value; for `earn/<sub>` it is `<sub>`. (NEW-003: do not regress the fat-earn
fallback chain.)" Citation and behavior verified. ✓ RESOLVED.

### FIND-007 (MEDIUM) — single-level earn-slot invariant unpinned — **RESOLVED**
`index.mjs:379` is `slot.replace('/', path.sep)` (first-occurrence-only) — confirmed. REQ-4 (lines 55-57) now
pins it: "Single-level invariant (FIND-007): earn slots are ONE level (`earn/<sub>`); `replace('/',sep)` replaces
only the first slash, so a deeper `earn/a/b` would mis-resolve — the registry SHALL declare only one-level earn
slots and the spec pins this (no multi-segment earn slots)." The invariant is now an explicit spec constraint. ✓.

---

## NEW finding

### FIND-010 (Completeness/Gaps, spec_gap, MEDIUM — NON-BLOCKING) — a THIRD hardcoded earn menu (`buildSystemPrompt` 69-101) is outside REQ-5's "BOTH spots"
The spec's GROUNDING (line 22-23) asserts the brain is steered toward the legacy 5 in exactly "TWO hardcoded
spots" (tool description + `buildUserMessage`). There is a third: `buildSystemPrompt` renders a curated block
**`## Your earn tools — each is its OWN run_skill slot. Pick ONE per wake:`** listing only
yield/x402_sell/hl_trade/token_launch/cook (`prompt.mjs:69-79`), plus a `## MINDSET` (`:80-85`) and per-slot
`## Tips` (`:87-101`) that frame the agent's entire earning worldview around those 5 — none mention `earn/<sub>`.
This is the same CLASS as NEW-001 (a hardcoded slot menu that won't surface per-method earners), and REQ-5 neither
fixes nor explicitly defers it.

Why this is NON-BLOCKING (not critical/major):
- It contains NO denial ("there is no generic earn") — unlike the two spots REQ-5 does fix — so the spec's
  "TWO hardcoded [denial] spots" is defensible for the steer-AWAY claim specifically.
- It is MITIGATED in the same function: `buildSystemPrompt` also emits a DYNAMIC `## Available skill slots`
  list (`prompt.mjs:103-104`) sourced from `ctx.activeSkillSlots` (`brain.mjs:59` → `prompt.mjs:46-48`), so a
  live `earn/gig` IS surfaced to the model in the system prompt regardless of the hardcoded block.
- It does not affect the E2E (forced/stubbed brain emits `earn/_probe`) nor the prompt unit test
  (verification-arch line 19: "system prompt include a live earn/* slot; no 'no generic earn slot' string"),
  which the dynamic list + the REQ-5(a) description fix already satisfy.

Recommendation (does not block the gate): the builder should either make the `## Your earn tools` block
slot-driven too, or add one line to REQ-5 deferring `buildSystemPrompt:69-101` with the rationale above, so the
"TWO hardcoded spots" grounding claim is accurate.
Evidence: `prompt.mjs:69-101, 103-104`; `brain.mjs:59`; spec GROUNDING line 22-23, REQ-5 lines 58-62.

---

## Positive verification (so a re-spec does not over-correct)
- Every spec line citation re-derived and ACCURATE: classify gate `index.mjs:318`; `EARN_SLOTS` `:439`;
  fat-earn fallback `:446`; `EARN_SLOT_DIRS` `:373` + override `:374` + else path `:379`; `runSkillWithKillRef`
  call `:301` / def `:363`; tool-description denial `prompt.mjs:133` (block `:132-138`); `buildUserMessage`
  `:163-208` with `ALL` at `:179` and denial at `:199`; every-wake user message `brain.mjs:60`;
  `earn-detect.mjs:40` correlation; `defaultEarnLedgerPath` honoring `config.EARN_LEDGER` `:60`.
- `index.mjs` slot-name branches fully enumerated by the spec; no OTHER index.mjs branch missed (`:272` sleep,
  `:289` avoidSlot, `:318` classify/REQ-2, `:374` override, `:379` else/REQ-4, `:440` env/REQ-3).
- `isEarnSlot` as a single predicate reused across classify (REQ-2) + env (REQ-3) is the right structural call;
  keeping `EARN_SLOT_DIRS` literal for PATH routing (so `earn/<sub>` is NOT sent to the fat skill) is correct.
- registry.json currently declares NO `earn/<sub>` slots — that is Phase-3 work (REQ-6), not a spec defect.

---

## convergenceSignals
- prior findings: NEW-001 (CRITICAL) RESOLVED, NEW-002 (HIGH) RESOLVED, NEW-003 (MEDIUM) RESOLVED,
  FIND-007 (MEDIUM) RESOLVED.
- new findings: FIND-010 (MEDIUM, non-blocking).
- open criticals: 0. new criticals: 0. open/un-deferred majors: 0.

## Spec gate decision
**Ready to exit the spec gate.** All four prior findings are genuinely resolved and — critically — the
prompt.mjs grounding that failed iters 1-2 is now accurate to the real lines (denial at `:133`, every-wake
`buildUserMessage` at `:163-208`, dynamic-menu requirement added). The earn-ledger correlation key is `wake`
(matches `earn-detect.mjs:40`) and the anti-tautology E2E discriminator is sound. The single remaining gap
(FIND-010, a third hardcoded earn menu in `buildSystemPrompt`) is MEDIUM and non-blocking because it carries no
denial and is mitigated by the dynamic `## Available skill slots` list; it should be folded into REQ-5 or deferred
with rationale during Phase 3, not re-litigated at the spec gate.

## ready-to-exit-gate: YES
