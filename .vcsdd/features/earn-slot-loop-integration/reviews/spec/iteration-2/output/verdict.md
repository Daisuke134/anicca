# VCSDD Adversary Verdict — earn-slot-loop-integration (Phase 1c SPEC GATE, iteration 2)

- feature: earn-slot-loop-integration
- reviewType: spec (Phase 1c)
- timestamp: 2026-06-29
- overallVerdict: **FAIL**
- iteration: 2
- note: No `input/manifest.json` under this review scope. Reviewed `specs/behavioral-spec.md` (iter-2) +
  `specs/verification-architecture.md` (iter-2) against the live runtime: `runtime/loop/{index,prompt,earn-detect,
  parse-tool-call,brain}.mjs`, `runtime/loop/__tests__/integration.test.mjs`, `skills/registry.json`
  (all under `/Users/operator/anicca/`).

## Dimensions

| Dimension | Verdict |
|---|---|
| 1. Spec Fidelity | **PASS** |
| 2. Edge Case Coverage | **FAIL** |
| 3. Completeness / Gaps | **FAIL** |
| 4. Structural Integrity | **PASS** |
| 5. Verification Readiness | **FAIL** |

`overallVerdict = FAIL` (any FAIL ⇒ FAIL).

---

## Iteration-1 finding resolution (FIND-001..007, + 008/009 because the brief's "anti-tautology per FIND-006" maps to the prior verdict's FIND-008)

### FIND-001 — grounded in dead code (`runSkill`/`resolveSkillPath`) — **RESOLVED**
iter-2 re-grounds on the live path: spec line 11 names `runSkillWithKillRef(...)` (verified `index.mjs:301`,
defined `:363`) and explicitly states the `runSkill` export is unused by the loop. Verified: `index.mjs:30`
imports `runSkill` but no call site exists in the loop; the live resolver is the inline `runSkillWithKillRef`
(`:369-380`) + inline `buildSkillEnv` (`:430-452`). verification-architecture line 7 targets "the if/else in
runSkillWithKillRef". The dead `run-skill.mjs` symbols are no longer load-bearing in the spec.

### FIND-002 — three hardcoded lists exclude `earn/<sub>` — **RESOLVED**
iter-2 identifies the two lists that MUST change — GAP-A classify gate (`index.mjs:318`, verified) and GAP-B
env gate (`EARN_SLOTS`, `index.mjs:439-451`, verified) — and correctly states the third list `EARN_SLOT_DIRS`
(`:373`) needs NO change for `earn/<sub>` because that slot already falls to the else branch (`:379` →
`skills/earn/<sub>/run.sh`). Cross-checked: `'earn/gig' in EARN_SLOTS` is false ⇒ today only
`{...base,ANICCA_ARGS,WAKE_ID}` (`:451`); `['earn',...].includes('earn/gig')` is false at `:318`. Both accurate.

### FIND-003 — two-ledger conflation, `EARN_LEDGER` not reaching nested slots — **RESOLVED**
Spec lines 26-27 now distinguish the WAKE ledger (`state/ledger.jsonl`) from the EARN ledger (correlated by
WAKE_ID, read by `classifyEarnResult`). REQ-3 passes `EARN_LEDGER` to every `isEarnSlot` slot (when configured),
matching `index.mjs:448`. (But see NEW-002: the spec's earn-ledger line schema names the correlation field wrong.)

### FIND-004 — `ANICCA_EARN_SKILL` override ignored for nested slots — **RESOLVED**
Scope item (4) places a real `skills/earn/_probe/run.sh`; E2E (spec line 62) asserts that exact path was spawned
in a tmp ANICCA_HOME — i.e. it no longer relies on the override pattern. Cross-checked `index.mjs:374` (override
gated by `EARN_SLOT_DIRS`, so excluded for `earn/_probe`) and `:379` (real-file resolution). verification-arch
line 22 now says "run index.mjs with stub brain", not the dead `runSkill`.

### FIND-005 — registry read from repoRoot, tmp-home E2E can't prove menu surfacing — **RESOLVED (by re-scoping)**
Verified `index.mjs:97-98` still reads registry from `repoRoot`, NOT ANICCA_HOME. iter-2 moves menu-surfacing
proof to a UNIT test against pure `prompt.mjs`/`liveSlotNames` (verification-arch line 19) and uses a FORCED
tool-call for the loop E2E (spec line 61). Cross-checked the loop does not validate `slot ∈ activeSkillSlots`
before `runSkillWithKillRef`, so a forced `earn/_probe` call runs regardless of registry status — the E2E is
sound. (The "(status:live)" parenthetical on spec line 62 is irrelevant to the forced call — cosmetic only.)

### FIND-006 (prior verdict = prompt-copy contradiction) — **PARTIALLY RESOLVED → see NEW-001**
GAP-C + REQ-5 now put prompt surfacing IN scope and REQ-5 correctly states "SHALL NOT contain copy that denies a
generic/earn slot exists." BUT the GAP-C grounding line refs are wrong/incomplete (NEW-001): the denial copy is
NOT at 69-101, and `buildUserMessage` (the every-wake user message) is omitted. The requirement text is sound;
the touch-point map a builder would follow is not.

### FIND-007 — `replace('/', path.sep)` is first-occurrence-only; single-level invariant undocumented — **STILL-OPEN (MEDIUM)**
The live resolver `index.mjs:379` (`slot.replace('/', path.sep)`) still replaces only the FIRST slash. iter-2
declares only single-level subs (`earn/gig|clip|affiliate|video|audit`) but REQ-7 lets CCs own slot naming and
the spec never pins "single-level only" as an invariant. A CC naming `earn/clip/jp` mis-resolves on Windows
(`earn\clip/jp`). Not blocking on its own, but unaddressed.

### FIND-008 (prior = tautological stub E2E) — **PARTIALLY RESOLVED → see NEW-002**
verification-arch "Anti-tautology" (lines 24-27) adds the correct discriminator: assert the spawned child
RECEIVED `EARN_LEDGER` (only true once GAP-B is fixed; verified that a non-earn slot gets no `EARN_LEDGER` at
`index.mjs:451`). The DESIGN is non-tautological. BUT the concrete assertion is undermined by NEW-002 (wrong
correlation field) and the spec never states HOW the test observes the child env (stub must emit its received
`EARN_LEDGER`/`EARN_STRATEGY` to a sentinel — the existing PROP-021 stubs don't do that).

### FIND-009 — duplicated path+env resolution; spec pointed at the dead copy — **RESOLVED (by targeting the live copy)**
iter-2 explicitly targets the inline resolver in `runSkillWithKillRef`/inline `buildSkillEnv` (verification-arch
lines 7,11) — satisfying FIND-009's "or explicitly target index.mjs's inline resolver" clause. The dead
`run-skill.mjs` duplicate persists but is pre-existing and out of this feature's scope; noted, not blocking.

---

## NEW findings

## NEW-001 (Completeness/Gaps, spec_gap, CRITICAL) — GAP-C mis-locates the "no generic earn" denial and omits the every-wake user message + tool description
The spec's GROUNDING section (presented as "the REAL execution path") states at line 22:
> GAP-C — prompt.mjs (≈:69-101,121): hardcodes the old 5 slots + the line "there is NO generic earn slot"

Cross-check against `prompt.mjs`:
- Lines 69-101 (`## Your earn tools` + `## MINDSET` + tips) hardcode the 5 slots but **do NOT contain** any
  "no generic earn slot" copy.
- The denial copy actually lives at **`prompt.mjs:132-134`** (`getToolDefinitions` description:
  "...each is its own first-class action; there is NO generic \"earn\" slot.") and **`prompt.mjs:199`**
  (`buildUserMessage`: "pick ONE slot DIRECTLY ... there is no generic \"earn\""). Both are OMITTED from GAP-C.
- `buildUserMessage` (`prompt.mjs:163-208`) is the USER message sent every wake (`brain.mjs:60`). It is FULLY
  hardcoded — `ALL = ['yield','hl_trade','x402_sell','token_launch','cook']` (`:179`) and a static slot list
  (`:200-205`) — and **never reads `ctx.activeSkillSlots`/`skillCatalog`**. So it cannot surface `earn/<sub>`
  no matter what the registry says; satisfying REQ-5 here requires restructuring `buildUserMessage` to consume
  the live slots, which the spec does not acknowledge.

Consequence: a builder editing only the cited grounding (69-101) removes nothing from `:132-138`/`:199-206`, so
the tool definition and every user message would STILL deny a generic earn slot and list only the old 5 — REQ-5
clause 2 unmet and the brain remains steered away from `earn/<sub>`. This is the same class of grounding error
(citing a location that does not contain the cited code) that failed iteration 1.
Evidence: `prompt.mjs:69-101, 132-138, 179, 199-206`; `brain.mjs:59-60`; spec line 22 (GAP-C), REQ-5 lines 47-48.

## NEW-002 (Verification Readiness / Spec Fidelity, requirement_mismatch, HIGH) — the spec's earn-ledger line schema (`wake_id`) does not match the code's correlation key (`wake`), so the headline anti-tautology assertion is not satisfiable as written
`classifyEarnResult` correlates the earn-ledger line by **`l.wake === wakeId`** (`earn-detect.mjs:40`; the
file header line 6 says "Finds the line where line.wake === WAKE_ID"). The existing integration stub writes the
field as `"wake"` (`integration.test.mjs:409`). But the iter-2 spec specifies the stub's earn-ledger line as:
- spec line 59: "writes an earn-ledger line `{wake_id, earn_usdc:0.01}`"
- verification-arch line 21: "stub ... writes earn-ledger `{wake_id,earn_usdc}` ... → classifyEarnResult finds it"

A line keyed on `wake_id` (not `wake`) will NOT match at `earn-detect.mjs:40` ⇒ `classifyEarnResult` returns
`{profitable:false, earnLine:null}` ⇒ the E2E assertion "(because the earn-ledger line exists) the earn
classification ran" / "the earn-ledger line written by the stub is what classify reads" (spec lines 63-64,
verification-arch line 26) cannot be demonstrated. The spec claims to be grounded in the real path but got the
correlation field wrong. Either fix the schema to `wake` or change the reader; as written the central
non-tautological discriminator is unprovable.
Evidence: `earn-detect.mjs:6, 40`; `integration.test.mjs:409`; spec lines 59, 63-64; verification-arch lines 21, 26.

## NEW-003 (Edge Cases, requirement_mismatch, MEDIUM) — fat `earn` slot's `EARN_STRATEGY` fallback dropped by REQ-3 as worded
`isEarnSlot('earn')` is true, so REQ-3 ("EARN_STRATEGY = the legacy map value for action slots, else `<sub>`")
would set `earnStrategyFor('earn')` = the legacy map value, which today is **null** (`EARN_SLOTS.earn = null`,
`index.mjs:439`). The live code preserves a fallback chain for the fat slot:
`EARN_STRATEGY || EARN_SLOTS[slot] || args.strategy || 'yield'` (`index.mjs:446`). REQ-3 as written drops the
`args.strategy`/`'yield'` fallback for `earn`, a behavior change for the (retired but still `isEarnSlot`) fat
slot. Low impact (registry marks `earn` `declared`/retired) but the spec should preserve the null→args.strategy→
'yield' fallback for the action path. Evidence: `index.mjs:439, 446`; spec REQ-3 lines 43-44.

## NEW-004 (positive — verified so a re-spec does not over-correct)
- Re-grounding is accurate: `runSkillWithKillRef` is the live executor (`index.mjs:301/363`), the else-branch
  resolves `earn/<sub>`→`skills/earn/<sub>/run.sh` (`:379`), `EARN_SLOTS` (`:439`) and the classify gate
  (`:318`) both exclude nested earn slots today — exactly as GAP-A/GAP-B state.
- `index.mjs` slot-name branches are fully enumerated by the spec: `:272`(sleep, non-earn), `:289`(avoidSlot,
  generic), `:318`(GAP-A), `:374`(override, correctly out for nested), `:379`(else path, unchanged),
  `:440`(GAP-B). No OTHER index.mjs slot branch is missed. The completeness gap is confined to `prompt.mjs`.
- `isEarnSlot` as a single reused predicate across classify+env (REQ-1, Scope 1) is the right structural call;
  keeping `EARN_SLOT_DIRS` literal for PATH routing (so `earn/<sub>` is NOT sent to the fat skill) is correct.
- Tool-call round-trip for a slash key holds: enum carries the slash name (`prompt.mjs:126`), `parseToolCall`
  returns `slot` via `parsed.slot ?? function.name` (`parse-tool-call.mjs:41`), loop runs it (`index.mjs:301`),
  resolves `:379`; declared-but-missing → `notFound` (`:382-383`) → `kind:'skill_missing'` (`:312-313`), no crash.

---

## convergenceSignals
- findingCount (open): 4 new (NEW-001 CRITICAL, NEW-002 HIGH, NEW-003 MEDIUM) + FIND-007 STILL-OPEN (MEDIUM).
- iter-1 resolved: FIND-001, 002, 003, 004, 005, 009. Partially resolved → superseded: FIND-006→NEW-001,
  FIND-008→NEW-002. Still-open: FIND-007.
- blocking (must fix before exit):
  1. NEW-001 `prompt.mjs:132-138, 199-206` — GAP-C must cite the ACTUAL denial sites (tool description +
     `buildUserMessage`) and acknowledge `buildUserMessage` is hardcoded (doesn't read `activeSkillSlots`).
  2. NEW-002 `earn-detect.mjs:40` — the spec's stub earn-ledger line must use the `wake` correlation field,
     not `wake_id`, or the anti-tautology assertion is unprovable.
  3. NEW-002 (cont.) — state HOW the E2E observes the child received `EARN_LEDGER` (stub emits a sentinel),
     so FIND-008's discriminator is actually checkable.

## Spec gate decision
**NOT ready to exit the spec gate.** The iter-2 re-grounding of the index.mjs path (FIND-001..005, 009) is
accurate and resolved. But the GAP-C grounding repeats iter-1's failure mode — it cites a code location
(69-101) that does not contain the "no generic earn" copy and omits the two locations that do
(`prompt.mjs:132-138`, `:199-206`), including the every-wake user message that cannot surface `earn/<sub>` at
all as written (NEW-001, CRITICAL). The headline no-mock E2E is also unprovable as specified because the stub's
earn-ledger line is keyed on `wake_id` while the loop correlates on `wake` (NEW-002, HIGH). Fix GAP-C's
touch-points and the earn-ledger correlation field, then re-review.

## ready-to-exit-gate: NO
