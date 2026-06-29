# VCSDD Adversary Verdict — earn-slot-loop-integration (PHASE 3 IMPLEMENTATION REVIEW, iteration 2, lean)

- feature: earn-slot-loop-integration
- reviewType: implementation (Phase 3)
- timestamp: 2026-06-29
- iteration: 2
- mode: lean
- context: ZERO builder context. Disk-only, under `/Users/operator/anicca-human-funded/`. Reviewed against
  `specs/behavioral-spec.md` (iteration 3, spec gate PASSED).
- ★ EXECUTION CAVEAT (HONESTY): the Bash tool is NOT enabled in this environment — I did NOT run
  `node --test`. I verified each prior finding by (a) reading the changed source on disk, (b) counting the
  `test()` declarations in each file, and (c) tracing every assertion against the implementation it calls,
  plus the committed baseline log. The builder's pass-counts are corroborated by that source-level trace, not
  by my own execution. Where a claim depends on a live run I say so.

## overallVerdict: **PASS**

| Dimension | iter-1 | iter-2 | Evidence |
|---|---|---|---|
| 1. Spec Fidelity | FAIL | **PASS** | REQ-1..7 wired; `earn/_probe` now `declared` (registry.json:118) |
| 2. Edge Case Coverage | FAIL | **PASS** | skill_missing E2E + classify non-profitable/no-line + path cases added |
| 3. Implementation Correctness | PASS | **PASS** | isProfitable `_shared` path fixed (index.mjs:84-89); no logic defect |
| 4. Structural Integrity | PASS | **PASS** | `earnSkillRelPath` extracted to pure module; inline resolver removed |
| 5. Verification Readiness | FAIL | **PASS** | classify unit tests + prompt regression guards + committed baseline |

`overallVerdict = PASS` (all 5 PASS, zero open blockers, zero new critical/major).
**Converges (4-D)? YES** — spec ✓ (REQ-1..7 implemented + the prod hazard removed), test ✓ (every iter-1
acceptance gap now has a test, counts traced), impl ✓ (the root-cause isProfitable path bug is fixed), required
verification ✓ (mechanism is unit-tested non-tautologically + a baseline proves the 2 prior failures were
pre-existing and the fix flips them green).

---

## Prior findings (FIND-IMPL-001..008) — resolution

### FIND-IMPL-001 (MAJOR — fake-earn slot in prod SSOT) → **RESOLVED**
`skills/registry.json:117-120` now ships `earn/_probe` with `"status": "declared"` (was `"live"`). Because
`liveSlotNames` only returns `status==='live'` slots (prompt.mjs:32-36) and `index.mjs:108` builds
`activeSkillSlots` from it, `_probe` no longer enters `activeSkillSlots`, the system-prompt slot list
(prompt.mjs:105-106), the `buildUserMessage` earn-subs menu (prompt.mjs:183), or the `run_skill` enum — so the
production model can no longer pick the no-op stub and pollute the real earn-ledger (HARD RULE 0.24 hazard
closed). The E2E does not need it live: the mock brain forces the slot via tool_calls and `runSkillWithKillRef`
runs it regardless of registry status (index.mjs:308, 384-392).
Evidence: `skills/registry.json:117-120`; `runtime/loop/prompt.mjs:32-36`; `runtime/loop/index.mjs:108`.

### FIND-IMPL-002 (MAJOR — GAP-A/REQ-2 untested, E2E tautological for the gate) → **RESOLVED**
GAP-A is now tested at unit level on BOTH halves of the gate condition `isEarnSlot(slot) ? classifyEarnResult(...)`:
- `isEarnSlot` — `earn-slot.test.mjs:11-13` (legacy slots true; every `earn/<sub>` incl `earn/_probe` true; cook/
  report/self/`''`/undefined/null false).
- `classifyEarnResult` — `earn-slot.test.mjs:40-57`, NON-tautological: a fully-qualifying line
  (`tx`+`status:0x1`+`net_usdc:2.5`+`external:true`, wake-correlated) → `profitable:true` (:40-45); a bare
  `{earn_usdc:0.01}` probe line → `false` (:46-51); a line for a DIFFERENT wake → `false` (:52-57). These call
  the REAL `classifyEarnResult` (earn-detect.mjs:23-50) + the REAL `isProfitable` (skills/_shared/lib/ledger.mjs:43-49),
  imported at `earn-slot.test.mjs:9-10` — so a regression in either is caught.
- The GATE COMPOSITION itself (index.mjs:325 `isEarnSlot(slot)`) is integration-exercised with `profitable:true`
  by `integration.test.mjs` PROP-021(a) for slot `earn`.
Observed (by reading): `earn-slot.test.mjs` = 13 `test()` declarations (lines 11,12,13,14,15,16,17,20,23,27,40,46,52)
⇒ matches the reported **13/13**.
RESIDUAL (NON-BLOCKING, see new note N-1): the GAP-A composition is asserted only for the legacy `earn` slot, not
for an `earn/<sub>` slot end-to-end; the predicate half is unit-guarded so this is acceptable for lean.
Evidence: `runtime/loop/earn-slot.test.mjs:9-13,40-57`; `runtime/loop/earn-detect.mjs:23-50`;
`skills/_shared/lib/ledger.mjs:43-49`; `runtime/loop/index.mjs:325-330`.

### FIND-IMPL-003 (MEDIUM — path resolution inline + untested) → **RESOLVED**
`earnSkillRelPath(slot)` is extracted into the pure module (`earn-slot.mjs:30-33`), exported, and is the SINGLE
resolver used by the loop (`index.mjs:384` `const rel = earnSkillRelPath(slot)` → `index.mjs:388`
`path.join(ANICCA_HOME,'skills',...rel.split('/'))`). The old inline `EARN_SLOT_DIRS` literal is gone (no second
copy of the rule remains in index.mjs). Unit-tested: legacy action slots → `earn/run.sh`
(`earn-slot.test.mjs:20-22`), `earn/<sub>` → `earn/<sub>/run.sh` (:23-26), non-earn → `<slot>/run.sh` (:27-30).
Evidence: `runtime/loop/earn-slot.mjs:30-33`; `runtime/loop/index.mjs:384-388`;
`runtime/loop/earn-slot.test.mjs:20-30`.

### FIND-IMPL-004 (MEDIUM — REQ-5 had no prompt regression guard) → **RESOLVED**
`prompt.test.mjs:101-111` adds the GAP-C guards: (i) `getToolDefinitions(...)` description must NOT match
`/no generic "?earn"? slot/i` AND must mention `earn/<sub>`/`gig` (:101-106) — the description at prompt.mjs:134-140
satisfies both; (ii) `buildUserMessage` with `activeSkillSlots:['yield','earn/gig','earn/clip']` must include
`earn/gig` and contain no denial (:107-111) — prompt.mjs:183-184,211 surfaces `earnSubs` dynamically. A re-introduced
denial (the original iter-1/2 failure mode) now fails the suite. Observed: `prompt.test.mjs` = 12 `test()`
declarations (lines 19,26,34,39,44,62,66,72,80,87,101,107) ⇒ matches reported **12/12**.
Evidence: `runtime/loop/__tests__/prompt.test.mjs:101-111`; `runtime/loop/prompt.mjs:134-140,183-184,211`.

### FIND-IMPL-005 (MEDIUM — skill_missing edge untested) → **RESOLVED**
`earn-slot-e2e.test.mjs:78-98` is a NO-MOCK E2E forcing `earn/_gone` (no run.sh created) through the real loop and
asserting the wake line `kind === 'skill_missing'` (:96). The path is real: `access` throws → `notFound:true`
(index.mjs:391-392) → `kind='skill_missing'` (index.mjs:319-320). Observed: `earn-slot-e2e.test.mjs` = 2 `test()`
declarations (lines 43, 78) ⇒ matches reported **2/2**. (Pass is logically sound by trace; not executed — see caveat.)
Evidence: `runtime/loop/__tests__/earn-slot-e2e.test.mjs:78-98`; `runtime/loop/index.mjs:319-320,391-392`.

### FIND-IMPL-006 (MEDIUM — isProfitable loaded from a non-existent path → always false) → **RESOLVED**
`index.mjs:84-89` now lists the REAL `skills/_shared/lib/ledger.mjs` FIRST (ANICCA_HOME then repoRoot) before the
legacy `skills/earn/lib/ledger.mjs` fallbacks. `repoRoot` = `resolve(dirname(index.mjs),'..','..')` =
`/Users/operator/anicca-human-funded`, and `…/skills/_shared/lib/ledger.mjs` EXISTS on disk and exports
`isProfitable` (verified, ledger.mjs:43). So the loop now loads the real classifier instead of `()=>false`.
Integration PROP-021: the committed baseline (`evidence/integration-baseline-main.txt`) shows PROP-021(a) FAILED on
main (`fail 1`) precisely because the old path resolved to nothing → `isProfitable=()=>false` → no wake ever
profitable. With the `_shared` candidate, PROP-021(a)'s profitable line (`tx`+`status:0x1`+`net_usdc:"1.5"`+
`external:true`, integration.test.mjs:409) satisfies `isProfitable` → wake `profitable:true` (assert at :440-441).
PROP-021(b) (no tx → false, :466) and PROP-021(e) (stale wake → false) remain false. ⇒ the reported **11/11** is
consistent with the source + baseline. ★ Not executed here (no Bash); judged from the baseline log + source trace. ★
Evidence: `runtime/loop/index.mjs:84-89`; `skills/_shared/lib/ledger.mjs:43-49`;
`runtime/loop/__tests__/integration.test.mjs:390,409,440-441,466`;
`.vcsdd/features/earn-slot-loop-integration/evidence/integration-baseline-main.txt:3-7`.

### FIND-IMPL-007 (LOW/MEDIUM, NON-BLOCKING — buildSystemPrompt earn menu didn't mention earn/<sub>) → **RESOLVED**
`buildSystemPrompt` now carries an `earn/<sub>` line (prompt.mjs:79-80: "`earn/<sub> : per-method earners (gig,
clip, affiliate, video, audit)… the LIVE ones are listed under 'Available skill slots' below; pick one`"), and the
DYNAMIC "## Available skill slots" list (prompt.mjs:105-106) still surfaces live earn slots. No denial string
remains. Resolved.
Evidence: `runtime/loop/prompt.mjs:79-80,105-106`.

### FIND-IMPL-008 (LOW/MEDIUM — "PROP failures pre-existing" claim unverifiable) → **RESOLVED**
A baseline run log is now committed: `evidence/integration-baseline-main.txt` records the main-branch run
("pass 10 / fail 1", the single failure = PROP-021(a)), documenting the failure as pre-existing and attributable to
the isProfitable path bug fixed by FIND-IMPL-006. The earlier "PROP-013 flaky" claim is no longer asserted in the
builder report (only PROP-021 a/b/e), and the baseline shows exactly one pre-existing failure, now fixed.
Evidence: `.vcsdd/features/earn-slot-loop-integration/evidence/integration-baseline-main.txt:1-8`.

---

## Observed test counts (by reading + tracing; NOT executed — no Bash tool)

| Suite | Builder report | Declarations counted | Trace verdict |
|---|---|---|---|
| earn-slot.test.mjs | 13/13 | 13 (lines 11-17, 20, 23, 27, 40, 46, 52) | all pass by trace against earn-slot.mjs + classifyEarnResult + isProfitable |
| earn-slot-e2e.test.mjs | 2/2 | 2 (lines 43, 78) | NO-MOCK E2E; pass by source trace of the real loop path |
| prompt.test.mjs | 12/12 | 12 (lines 19,26,34,39,44,62,66,72,80,87,101,107) | all pass; GAP-C guards match prompt.mjs copy |
| integration.test.mjs | 11/11 | (PROP-021 a/b/e read) | PROP-021(a) flips green via FIND-006 fix; baseline corroborates |

---

## New observations (this iteration)

### N-1 (verification, NON-BLOCKING — not a regression)
The end-to-end GAP-A *composition* for a per-method `earn/<sub>` slot is still not asserted with a live
`profitable` outcome: `earn-slot-e2e.test.mjs:61-71` asserts the earn-ledger line + `slot=earn/_probe` but never
the wake line's `kind`/`profitable`, and PROP-021(a) exercises the gate only via the legacy `earn` slot. If
`index.mjs:325` were reverted to a literal list that still contained `earn` but dropped `earn/<sub>`, PROP-021(a)
would stay green. This residual is contained because the predicate half (`isEarnSlot('earn/gig')===true`,
earn-slot.test.mjs:12) is unit-guarded and the gate literally reads `isEarnSlot(slot)` (index.mjs:325) — so the
regression would require also changing the predicate's call site, which the predicate test would surface in code
review. Acceptable for lean; recommend (future) seeding a profitable `earn/_probe` earn-ledger line in the E2E and
asserting `profitable:true` on the wake line. NO new finding ID raised (non-blocking, no open severity).

No NEW critical or major finding. No regression introduced by the fixes (earn-slot.mjs remains pure: only string
functions + a const, no fs/child_process/process/time/random — earn-slot.mjs:1-35).

---

## convergenceSignals
- findingCount carried: 8 (FIND-IMPL-001..008) — ALL resolved (001,002,005 MAJOR/MEDIUM blockers cleared;
  003,004 MEDIUM cleared; 006 root-cause fixed; 007,008 cleared).
- open blockers: 0
- new criticals/majors: 0
- non-blocking observation: N-1 (E2E GAP-A composition residual)
- 4-D convergence: **YES**

## decision: **PASS — converges (4-D). No re-review required.**
Note for the main agent: the adversary judges DISK only and could not execute the runner here. Before declaring
DONE, run the four suites yourself (`cd runtime/loop && node --test __tests__/{earn-slot,earn-slot-e2e,prompt,integration}.test.mjs`)
to confirm the 13/2/12/11 counts live, then do the NO-MOCK E2E per HARD 0.31.
