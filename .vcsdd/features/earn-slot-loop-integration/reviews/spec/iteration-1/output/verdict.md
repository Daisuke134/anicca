# VCSDD Adversary Verdict — earn-slot-loop-integration (Phase 1c SPEC GATE, iteration 1)

- feature: earn-slot-loop-integration
- reviewType: spec (Phase 1c)
- timestamp: 2026-06-29
- overallVerdict: **FAIL**
- iteration: 1
- note: No `input/manifest.json` exists under this review scope (only `state.json` + `specs/`). Reviewed
  the spec + verification-architecture against the five real runtime files named in the task brief.

## Dimensions

| Dimension | Verdict |
|---|---|
| 1. Spec Fidelity | **FAIL** |
| 2. Edge Case Coverage | **FAIL** |
| 3. Completeness / Gaps | **FAIL** |
| 4. Structural Integrity | **FAIL** |
| 5. Verification Readiness | **FAIL** |

`overallVerdict = FAIL` (any FAIL ⇒ FAIL).

---

## FIND-001 (Spec Fidelity, requirement_mismatch, CRITICAL) — the loop does NOT call `runSkill`/`resolveSkillPath`; the spec is grounded in dead code
The spec's central grounding is `run-skill.mjs resolveSkillPath` (spec line 9) and "index.mjs ... →
runSkill → ledger" (spec line 13). REQ-2 makes `resolveSkillPath('earn/<sub>')` the load-bearing,
unit-tested invariant.

But the loop does NOT use either symbol:
- `index.mjs:30` imports `runSkill` from `run-skill.mjs` — and never calls it. It is dead in the loop path.
- `index.mjs:301` calls the LOCAL `runSkillWithKillRef(...)` (defined `index.mjs:363`).
- That local function resolves the path INLINE at `index.mjs:379`
  (`path.join(ANICCA_HOME,'skills',slot.replace('/',path.sep),'run.sh')`) and builds env via a SEPARATE
  local `buildSkillEnv` (`index.mjs:430`) — NOT `run-skill.mjs:79`/`:109`.

So the cited `resolveSkillPath` (`run-skill.mjs:109-115`) and `runSkill` (`run-skill.mjs:22`) are not on
the execution path. A unit test that proves `resolveSkillPath('earn/gig')` (REQ-2) gives FALSE confidence:
it validates a function the running loop ignores. Evidence: `index.mjs:30, 301, 363, 379, 430`; spec
lines 9, 13, 30-33 (REQ-2/REQ-3 grounding).

## FIND-002 (Completeness/Gaps, spec_gap, CRITICAL) — "the 4 new methods follow the SAME pattern" is false: 3 hardcoded slot lists exclude nested earn slots
Spec line 15 + REQ-5 assert the new earn methods follow the same pattern as the live yield/hl_trade/
x402_sell/token_launch slots, and that only registry declaration + a stub are IN scope. The live earners
are special-cased in THREE hardcoded lists in `index.mjs`, none of which include `earn/<sub>`:
- `index.mjs:318` earn-classification gate: `['earn','yield','hl_trade','x402_sell','token_launch'].includes(slot)`.
  For `earn/gig` this is false ⇒ `classifyEarnResult` never runs ⇒ `profitable` (initialized false at
  `index.mjs:309`) is always recorded false for every nested earn slot. The CCs' earners can never be
  classified profitable.
- `index.mjs:373` `EARN_SLOT_DIRS` (path + override gate) — excludes `earn/<sub>`.
- `index.mjs:439-440` `EARN_SLOTS` (env injection gate) — `'earn/gig' in EARN_SLOTS` is false ⇒ the slot
  gets only `{...base, ANICCA_ARGS, WAKE_ID}` (`index.mjs:451`); it receives NO `EARN_MODE`, NO
  `EARN_STRATEGY`, and NO `EARN_LEDGER`.

The declared IN-scope (registry rows + stub + a unit test) is insufficient to make `earn/gig` behave like
the existing earners; code edits in three locations are required and are not acknowledged anywhere in the
spec. Evidence: `index.mjs:309, 318, 373, 439-451`; spec lines 14-15, 17-24, REQ-5.

## FIND-003 (Completeness/Gaps, requirement_mismatch, HIGH) — two-ledger conflation; `EARN_LEDGER` not passed to nested slots so REQ-5 record-earn cannot be correlated
REQ-4 says "the loop SHALL ... append one ledger line"; REQ-5 says each slot "call record-earn(INV-7)
internally." These are two different ledgers: the loop's wake ledger
(`state/ledger.jsonl`, written `index.mjs:353`) vs the earn-ledger
(`skills/earn/state/earn-ledger.jsonl`, read by `earn-detect.mjs:58-64`, correlated by WAKE_ID at
`earn-detect.mjs:40`). The spec never distinguishes them. Worse: because nested earn slots are excluded
from `EARN_SLOTS` (`index.mjs:440`), the child never receives `EARN_LEDGER`, so a CC's `run.sh` cannot be
told where to write the line the loop would correlate, and the loop never reads it for `earn/<sub>` anyway
(FIND-002). The E2E "ledger.jsonl gains a line" (spec line 48) is therefore satisfiable by the wake-ledger
line alone, which proves nothing about earning. Evidence: `index.mjs:319-323, 353, 440, 451`;
`earn-detect.mjs:40, 58-64`; spec REQ-4, REQ-5, line 48.

## FIND-004 (Edge Cases, requirement_mismatch, HIGH) — `ANICCA_EARN_SKILL` override is NOT honored for nested slots, but the established test harness depends on it
The only integration harness for the loop (`__tests__/integration.test.mjs`) stubs the skill exclusively
via the `ANICCA_EARN_SKILL` env override (e.g. lines 169, 271, 318, 428). In the live loop that override
is gated by `EARN_SLOT_DIRS` (`index.mjs:374`), so for `earn/_probe`/`earn/gig` it is IGNORED and the path
falls to `index.mjs:379` (`skills/earn/_probe/run.sh` under ANICCA_HOME). The spec's REQ-6 stub E2E (spec
lines 40-42, 48) must therefore place a real executable at `<tmpHome>/skills/earn/_probe/run.sh` and CANNOT
reuse the override pattern every existing integration test uses. The spec/verification-architecture do not
state this; verification-architecture line 17 literally says "runSkill('earn/_probe') with stub", which
points a builder at the dead exported `runSkill` (FIND-001). Evidence: `index.mjs:374, 379`;
`integration.test.mjs:169, 271, 428`; verification-architecture line 17; spec lines 40-42.

## FIND-005 (Completeness/Gaps, spec_gap, HIGH) — the registry is read from the code repo, not ANICCA_HOME, so a tmp-home E2E cannot prove "liveSlotNames surfaces a live earn sub-slot"
`index.mjs:97-98` reads `registry.json` from `repoRoot` (`.../anicca/skills/registry.json`), while skill
`run.sh` is executed from `ANICCA_HOME` (`index.mjs:377, 379`). The E2E plan (verification-architecture
line 18, spec line 48) uses "a stub brain + tmp ANICCA_HOME"; flipping `earn/_probe` to `live` in a tmp
registry has NO effect because the loop reads the repo registry. The forced-tool-call E2E thus bypasses
the menu entirely and never exercises REQ-3's "liveSlotNames → brain menu" path through the real loop.
Scope item (4) (spec line 22) is unverifiable by the planned E2E. Evidence: `index.mjs:97-104, 377-379`;
spec lines 22, 48; verification-architecture line 18.

## FIND-006 (Completeness/Gaps, requirement_mismatch, HIGH) — REQ-3 "buildSystemPrompt SHALL surface them so the brain can pick" is contradicted by hardcoded prompt copy that the spec leaves out of scope
`liveSlotNames` returns full keys including the slash (`prompt.mjs:32-36`), and `getToolDefinitions` puts
them in the enum (`prompt.mjs:121-126`), so the round-trip is mechanically possible (see FIND-010,
positive). BUT the dominant prompt copy is hardcoded to the old five and actively steers AWAY from an
`earn/*` slot:
- `prompt.mjs:69-101` "## Your earn tools" enumerates only yield/x402_sell/hl_trade/token_launch/cook.
- `getToolDefinitions` description (`prompt.mjs:132-138`) says "there is NO generic 'earn' slot".
- `buildUserMessage` (`prompt.mjs:199-206`) lists only the same five and "there is no generic 'earn'".

A model reading this would be discouraged from picking `earn/gig`. REQ-3 (spec line 32-33) treats prompt
surfacing as already-done/reuse; making the brain actually aware of `earn/<sub>` requires editing this
hardcoded copy, which is excluded from IN-scope (spec lines 17-24). Evidence: `prompt.mjs:69-101, 132-138,
199-206`; spec REQ-3, lines 17-24.

## FIND-007 (Edge Cases, requirement_mismatch, MEDIUM) — `slot.replace('/', path.sep)` replaces only the FIRST slash; the single-level assumption is undocumented
Both the cited `resolveSkillPath` (`run-skill.mjs:114`) and the live inline resolver (`index.mjs:379`) use
`String.prototype.replace` with a string first arg, which replaces only the FIRST occurrence. For
`earn/gig` (one slash) this is correct, so REQ-2's claim holds for single-level nesting only. The spec
declares only `earn/<sub>` slots, but never states "single-level only" as an invariant; a CC naming a slot
`earn/clip/jp` would silently mis-resolve on Windows (`earn\clip/jp`). The spec should pin the single-slash
constraint or use a global/`split.join` replace. Evidence: `run-skill.mjs:114`; `index.mjs:379`; spec
REQ-2 line 30-31 ("cross-platform sep").

## FIND-008 (Verification Readiness, test_quality, HIGH) — the REQ-6 stub E2E passes for ANY exit-0 slot, so it does not prove earner integration
The loop appends a `kind:'wake'` line with `slot` + `result` for any exit-0 skill that is NOT in the earn
list (`index.mjs:309, 318, 331-353`). `self/issue-dev` already does exactly this today. So "ledger.jsonl
gains a line recording earn/_probe ran" (spec line 48) would be GREEN even though the earn-specific wiring
(classification FIND-002, `EARN_LEDGER` FIND-003) is entirely dead for nested slots. The acceptance test is
tautological w.r.t. the feature's actual goal (a per-method EARNER on the loop). Evidence: `index.mjs:309,
318, 331-353`; spec lines 44-49.

## FIND-009 (Structural Integrity, structural, MEDIUM) — duplicated path+env resolution; the spec reuses the dead copy and is unaware of the live one
Skill-path resolution and env-build exist in TWO places: `run-skill.mjs:79-115` (exported, dead in the
loop) and `index.mjs:363-452` (inline, live). The verification-architecture "reuse" claim
(verification-architecture lines 5-6) points at the dead copy. The integration should either consolidate
the two or explicitly target `index.mjs`'s inline resolver; otherwise REQ-2's pure-function test and the
real behavior will drift. Evidence: `run-skill.mjs:79-115`; `index.mjs:363-452`; verification-architecture
lines 4-12.

## FIND-010 (positive evidence for the parts that DO hold)
Verified working so a re-spec does not over-correct:
- Tool-call round-trip for a nested name is mechanically sound: enum carries `earn/gig`
  (`prompt.mjs:121-126`) → `parseToolCall` returns `slot:'earn/gig'` via `parsed.slot ?? function.name`
  (`parse-tool-call.mjs:41, 56`) → `index.mjs:269, 301` runs it → `index.mjs:379` resolves
  `skills/earn/gig/run.sh`.
- `liveSlotNames` includes nested live keys and excludes `declared` ones
  (`prompt.mjs:32-36`) — REQ-3's filtering half holds; the registry schema already holds `earn/*` keys
  (`registry.json:25 "self/spawn"`, `:34 "self/issue-dev"` prove slash keys are accepted).
- notFound-not-crash for a declared-but-missing slot holds: `index.mjs:382-383` → `notFound:true` →
  `index.mjs:312` `kind:'skill_missing'`, loop survives (REQ-5 second clause).

---

## convergenceSignals
- findingCount: 9 (FIND-001..009)
- top must-fix (blocking exit):
  1. FIND-001 `index.mjs:30/301/363/379` — re-ground REQ-2/REQ-3 on the LIVE resolver
     (`runSkillWithKillRef` inline), not the dead exported `runSkill`/`resolveSkillPath`.
  2. FIND-002 `index.mjs:318/373/439` — spec must add the three hardcoded-list edits (or explicitly
     redesign nested earn slots to be self-contained) so `earn/<sub>` is classified + env-wired.
  3. FIND-003/004 `index.mjs:440/374`, `earn-detect.mjs:40` — define which ledger REQ-4 vs REQ-5 write,
     and how `EARN_LEDGER`/WAKE_ID reach a nested slot (override is ignored for `earn/<sub>`).
  4. FIND-005 `index.mjs:97-98` — registry read from repoRoot, not ANICCA_HOME; the tmp-home E2E cannot
     prove menu surfacing.
  5. FIND-008 — replace the tautological stub-E2E with an assertion that actually distinguishes a wired
     earner from any exit-0 script.

## Spec gate decision
**NOT ready to exit the spec gate.** The grounding citations (REQ-2 `resolveSkillPath`, the line-13
"runSkill → ledger" claim, the "same pattern" claim) do not match the code the loop actually executes, and
the declared IN-scope is insufficient to make a nested earn slot earn/record. Re-author the spec against
`index.mjs`'s live path (FIND-001/002/003), then re-review.
