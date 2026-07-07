# Resolution Notes — spec review iteration-18 (FIND-1701 + `decideColonySpawn`'s own full-signature closeout)

**Feature**: anicca-agent-spawn · **Result**: FIND-1701 resolved, plus a complete, dedicated
per-parameter closeout of `decideColonySpawn`'s ENTIRE 8-parameter signature (the specific function this
recurring failure class has now surfaced in THREE separate iterations — FIND-1101/1401/1501 for
`recentSpawnAttempts`/`childrenProvisioning`, now FIND-1701 for `colonySurplusUsd`); `behavioral-spec.md`
and `verification-architecture.md` bumped to **revision: iteration 18**.

---

## FIND-1701 (critical) — `decideColonySpawn`'s `colonySurplusUsd` gains a real-derivation binding rule

**Problem**: `colonySurplusUsd` — `decideColonySpawn`'s own FIRST-listed parameter, and the single most
consequential value the function consumes (gated only by the cooldown/concurrency checks, it determines
whether ANY spawn happens at all this wake) — had no "never hand-assembled, always the direct return
value of X()" binding sentence and no dedicated real-derivation proof obligation, unlike its immediate
signature-siblings `recentSpawnAttempts` (FIND-1401) and `childrenProvisioning` (FIND-1501), which had
both already received this exact treatment in prior iterations. REQ-102's own "multiple evaluations in
the same wake cycle" edge case already contemplates more than one `decideColonySpawn` evaluation running
per wake — meaning a stale/cached/hand-rolled `colonySurplusUsd` reused across evaluations, or a shortcut
inline recomputation that skips `filterProductiveCitizens`'s exclusion logic (e.g. accidentally including
a `"bootstrap_failed"` citizen's balance), was a real, concrete, previously-uncaught hazard nothing in
either spec document would have caught.

**Resolution**: `behavioral-spec.md`'s REQ-102 now states explicitly, in a new paragraph mirroring the
existing `recentSpawnAttempts`/`childrenProvisioning` treatment: `colonySurplusUsd` is never
hand-assembled by the calling orchestration — it is ALWAYS the DIRECT return value of THAT SAME
evaluation's `computeColonySurplusUsd({citizens: filterProductiveCitizens(...), perCitizenReserveUsd})`
(REQ-101) call, never a stale/earlier evaluation's cached aggregate.

**The "multiple evaluations in the same wake" edge case is explicitly resolved for this specific hazard**,
per the dispatch's own instruction to read REQ-103's current text first before asserting any safety claim
about it (to avoid repeating this spec's own earlier FIND-501 mistake, where an incorrect safety claim was
made about a different mechanism without first re-verifying it). I re-read REQ-103 in full
(`behavioral-spec.md` lines 957-1052 pre-edit) before writing anything: REQ-103's own statePath prose is
explicit that "REQ-101's earlier registry read and REQ-102's decision themselves run OUTSIDE the lock,
since REQ-102's gate function is pure and needs no mutual exclusion of its own — only the ACT of
proceeding on a `true` decision needs the lock" — i.e. the `"colony-spawn"` lock's critical section begins
only at REQ-201's wallet generation, strictly AFTER REQ-101/102's evaluation has already completed. This
means REQ-103's lock does **NOT** provide staleness protection for `colonySurplusUsd`, and the spec now
says so explicitly rather than inventing a false safety claim: THE SYSTEM SHALL compute `colonySurplusUsd`
via a FRESH `computeColonySurplusUsd(...)` call (over a fresh `filterProductiveCitizens(...)` call, over a
fresh `readChildren(...)`/registry read) for EVERY separate `decideColonySpawn` evaluation within one
wake — never reusing an earlier evaluation's already-returned aggregate.

A new proof obligation, **PROP-102k** (Tier 1/2, mirroring PROP-101j/PROP-102g/PROP-102i/PROP-202d's own
real-derivation discipline exactly), requires a control-flow read confirming the real orchestration passes
`computeColonySurplusUsd(...)`'s return value directly as `colonySurplusUsd` (with a separate call made
per evaluation, never a cached/shared one), PLUS an integration test writing real registry/ledger data,
running the real `readChildren`/registry read → `filterProductiveCitizens` → `computeColonySurplusUsd`
pipeline, and asserting `decideColonySpawn`'s real call site receives EXACTLY that value — including a
second fixture that mutates the underlying data BETWEEN two evaluations in the same simulated wake,
confirming the SECOND evaluation's `colonySurplusUsd` reflects the freshly-recomputed value, never the
FIRST evaluation's earlier aggregate. The Purity Boundary Map's `decideColonySpawn` row is updated to cite
this binding, and the Gate's item (1) is extended to require it (including the explicit requirement that
the adversary confirm REQ-103's lock is NOT cited as a substitute safety mechanism for this hazard).

---

## `decideColonySpawn`'s complete 8-parameter signature — full closeout table (per the dispatch's own
mandate to close this function out definitively, not stop at the one flagged parameter)

Read `decideColonySpawn`'s actual, current signature fresh from `behavioral-spec.md`'s own Acceptance
Criteria bullet (post-FIND-1701-fix): `decideColonySpawn({ colonySurplusUsd, spawnThresholdUsd,
recentSpawnAttempts, nowMs, cooldownDays, failureCooldownCap, childrenProvisioning, maxConcurrentSpawns })
→ { eligible: boolean, reason }` — exactly 8 parameters, confirmed by direct re-read (not assumed from
memory or from the iteration-17 table).

| # | Parameter | Classification | Treatment found | Verdict / action taken this iteration |
|---|---|---|---|---|
| 1 | `colonySurplusUsd` | DERIVED-BOUND | **Was UNRESOLVED (FIND-1701)** — only a generic EARS-clause tie-in ("WHEN REQ-101's colony surplus is computed"), no "never hand-assembled" sentence, no dedicated PROP | **FIXED this iteration.** New binding sentence in REQ-102 + REQ-102 Acceptance Criteria bullet, bound to THAT SAME evaluation's `computeColonySurplusUsd({citizens: filterProductiveCitizens(...), perCitizenReserveUsd})` return value; new PROP-102k (Tier 1/2); Purity Boundary Map row updated; Gate item (1) extended. The "multiple evaluations in one wake" edge case is explicitly resolved: each evaluation calls the pipeline fresh; REQ-103's lock is explicitly documented as NOT providing this protection (its critical section begins only at REQ-201, confirmed by direct re-read of REQ-103's own text before asserting this). |
| 2 | `spawnThresholdUsd` | DERIVED-BOUND (formula, not a single function's direct return value) | Already fully specified: `SPAWN_THRESHOLD_USD = MIN_SHELTER_USD * SAFETY_MARGIN_MULTIPLIER`, with `MIN_SHELTER_USD = max(deriveMeasuredShelterCostUsd({shelterCostLedgerRows: readShelterCostEntries(...)}), 5.00)` once non-`null` (behavioral-spec.md, REQ-102 formula paragraph); the Purity Boundary Map's `decideColonySpawn` row already states this formula explicitly; Gate item (1) already requires the adversary confirm this override is read via `deriveMeasuredShelterCostUsd` rather than an average/max/first-entry read (PROP-102j). | **Adequately treated, no fix needed.** This is the row the iteration-18 adversary's own independent full-table re-derivation explicitly agreed with the iteration-17 builder's table on (33/34 rows matched; this was one of the 33, not the 1 discrepancy). Unlike `colonySurplusUsd`, this value is a two-constant formula (`MIN_SHELTER_USD`/`SAFETY_MARGIN_MULTIPLIER`) rather than a single named function's direct return value, so the "never hand-assembled, always X()'s return value" sentence pattern does not map onto it as cleanly as it does onto `colonySurplusUsd`/`recentSpawnAttempts`/`childrenProvisioning` — its own upstream dependency, `deriveMeasuredShelterCostUsd`, already has its own dedicated real-derivation treatment via PROP-102j and the Gate's existing citation. |
| 3 | `recentSpawnAttempts` | DERIVED-BOUND | Already fixed, FIND-1401 (iteration 14→15): explicit "never hand-assembled... ALWAYS the direct return value of `deriveRecentSpawnAttempts({ledgerRows: readChildren(...)})`" sentence in REQ-102 Acceptance Criteria; PROP-102g (Tier 1/2) | **Confirmed fine, no fix needed.** Re-verified by direct re-read this iteration; unchanged. |
| 4 | `nowMs` | Raw runtime primitive (CONSTANT/ambient clock) | No explicit "this is the evaluation's own wall-clock time at the moment of the call" sentence exists anywhere in either spec document for this parameter specifically | **Confirmed exempt, no fix needed** — this is a genuine raw I/O leaf (the evaluation's own current time, captured at the moment of the call), not a value derived from another named pure function's output, exactly the category the dispatch itself named as needing no derivation treatment (mirroring how iteration 17 correctly left `selectCloudTarget`'s own 4 raw price/availability inputs unfixed as raw effectful leaves). Added one clarifying phrase to the Purity Boundary Map's `decideColonySpawn` row for completeness/future-proofing, but no behavioral-spec.md edit was needed — REQ-102's own "multiple evaluations in the same wake" edge case already establishes that a few milliseconds' difference in `nowMs` between two same-wake evaluations has no material consequence given `SPAWN_COOLDOWN_DAYS`'s 14-day window, unlike `colonySurplusUsd`'s own much more consequential staleness hazard. |
| 5 | `cooldownDays` | CONSTANT | Already explicit: "`cooldownDays` defaults to `14`, identical to `SPAWN_COOLDOWN_DAYS`'s own default above (resolves FIND-1301) — never independently configurable to a different value" — stated at BOTH the EARS-clause level and the Acceptance-Criteria level | **Confirmed fine, no fix needed.** |
| 6 | `failureCooldownCap` | CONSTANT | Already explicit: "`failureCooldownCap` defaults to `3` — identical to REQ-305's own cap, the SAME number, never independently configurable to a different value" — stated at BOTH levels | **Confirmed fine, no fix needed.** |
| 7 | `childrenProvisioning` | DERIVED-BOUND | Already fixed, FIND-1501 (iteration 15→16): explicit "never hand-assembled... ALWAYS the direct return value of `countChildrenProvisioning({ledgerRows: readChildren(...)})`" sentence in REQ-102 Acceptance Criteria; PROP-102i (Tier 1/2) | **Confirmed fine, no fix needed.** Re-verified by direct re-read this iteration; unchanged. |
| 8 | `maxConcurrentSpawns` | CONSTANT | Default (`1`) was stated ONLY in REQ-102's EARS clause ("fewer than `MAX_CONCURRENT_SPAWNS` (default `1`) children") — **never restated at the Acceptance-Criteria level**, unlike its two sibling constants (`cooldownDays`/`failureCooldownCap`), both of which get an explicit Acceptance-Criteria-level default statement | **Minor asymmetry found and closed preemptively this iteration** (no new FIND number, not independently raised by the adversary — found during this mandated full-signature sweep). Added a clause to the same Acceptance Criteria bullet: "`maxConcurrentSpawns` defaults to `1`, identical to `MAX_CONCURRENT_SPAWNS`'s own default above — never independently configurable to a different value." No new proof obligation needed — `maxConcurrentSpawns`'s actual gating behavior is already directly tested by the existing PROP-102c. |

**Result of this closeout**: exactly **one** parameter (`colonySurplusUsd`) was genuinely UNRESOLVED
(FIND-1701, now fixed), one further parameter (`maxConcurrentSpawns`) had a minor default-restatement
asymmetry (now closed), and the remaining six parameters (`spawnThresholdUsd`, `recentSpawnAttempts`,
`nowMs`, `cooldownDays`, `failureCooldownCap`, `childrenProvisioning`) were independently re-verified and
confirmed already adequately treated, each landing cleanly in exactly one of the four categories the
dispatch specified (DERIVED-BOUND-with-binding-sentence-and-PROP, CONSTANT-with-explicit-default,
AGENT-CHOICE — none of this function's own 8 parameters are agent-choice, that carve-out belongs to
REQ-202's `initialSkills` — or a genuine raw runtime primitive needing no derivation). This function's own
complete parameter list is now, to the best of this independent re-derivation, exhaustively closed out.

---

## `specs/behavioral-spec.md` edits

| Location | Change |
|---|---|
| Revision header (top of file) | Bumped `iteration 17` → `iteration 18`; new lead paragraph describing the FIND-1701 fix, prior iteration-17 content preserved as a subordinate `— AND spec review iteration-17 finding FIND-1601 resolved —` clause, following the exact chaining pattern every prior revision bump uses. |
| REQ-102, new paragraph pair **"Deriving `colonySurplusUsd` from real system state"** + **"Each separate `decideColonySpawn` evaluation... MUST call `computeColonySurplusUsd` fresh"**, inserted immediately after the Cooldown Check section, before the existing "Deriving `recentSpawnAttempts` from real ledger rows" paragraph | States `colonySurplusUsd` is never hand-assembled — always `computeColonySurplusUsd({citizens: filterProductiveCitizens(...), perCitizenReserveUsd})`'s direct return value for THAT SAME evaluation — and explicitly resolves the "multiple evaluations in one wake" edge case for this hazard, stating REQ-103's lock does NOT cover this (its critical section begins only at REQ-201). |
| REQ-102 Acceptance Criteria, first bullet | Appended `maxConcurrentSpawns`'s explicit default-restatement clause. |
| REQ-102 Acceptance Criteria, new bullet inserted immediately after the first bullet, before the `recentSpawnAttempts` bullet | "**(new, resolves FIND-1701)** `colonySurplusUsd` is never hand-assembled..." |
| New `## Changelog (iteration 18 spec review → iteration 19)` section (inserted immediately after the existing `## Changelog (iteration 17 spec review → iteration 18)` section, before `## Scope of this increment (read first)`) | Added, with a `\| Finding \| Severity \| Resolution \|` table containing one row for FIND-1701, plus narrative describing the full-signature closeout and the preemptive `maxConcurrentSpawns` fix. |

## `specs/verification-architecture.md` edits

| Location | Change |
|---|---|
| Revision header (top of file) | Bumped `iteration 17` → `iteration 18`; condensed lead paragraph covering the FIND-1701 fix and the full-signature closeout. |
| Purity Boundary Map — `decideColonySpawn` row | Extended with the new `colonySurplusUsd` real-derivation binding sentence (citing the REQ-103 lock-scope clarification), plus a brief `nowMs`-is-a-raw-primitive clarification and a `maxConcurrentSpawns`-default-symmetry note. |
| Proof Obligations table — new row **PROP-102k** (inserted directly after PROP-102j, before PROP-103a) | Real-derivation integration check for `colonySurplusUsd`, Tier 1/2, mirroring PROP-101j/PROP-102g/PROP-102i/PROP-202d. |
| Verification tiers narrative — Tier 2 list | New clause citing PROP-102k. |
| Verification Strategy — Tier 2 list | New clause citing PROP-102k. |
| Gate — item (1) | Extended with the `colonySurplusUsd` real-derivation binding requirement (PROP-102k), including the explicit requirement that the adversary confirm REQ-103's lock is NOT cited as a substitute safety mechanism. |

---

## Note on revision numbering

Confirmed by direct read of both spec files' revision headers at the start of this task: the on-disk
revision was **iteration 17** (produced by the prior task's resolution of FIND-1601, per
`reviews/spec/iteration-17/RESOLUTION-NOTES.md`'s own numbering note). This task's dispatch was for
`reviews/spec/iteration-18/`'s `verdict.json`, which reviewed that revision-17 spec and raised FIND-1701.
Following the SAME convention every prior iteration's own resolution note established (review round
directory `iteration-N` reviews the spec at revision `N-1` and, once resolved, the spec is bumped to
revision `N`), this task resolves `reviews/spec/iteration-18/`'s finding against a spec that was at
revision 17, so the spec is bumped to revision **18** — consistent with the task list's own next item,
"P3 spawn spec iteration-19待ち", i.e. the NEXT review round (directory `iteration-19`) will review this
now-produced revision 18. No `state.json`/review-manifest files were touched by this task per its own
instructions, so the orchestrator can advance `state.json` and create the `iteration-19` review directory
separately.

---

## Verification of internal consistency (post-edit)

- Grep-confirmed `PROP-102k` appears exactly once as a table-row definition in
  `verification-architecture.md`'s Proof Obligations table (no ID collision with any existing `PROP-102*`
  row), correctly ordered (directly after `PROP-102j`, before `PROP-103a`).
- `FIND-1701` referenced consistently across both spec files (5 occurrences in `behavioral-spec.md`, 6 in
  `verification-architecture.md`).
- Both revision headers confirmed bumped to `iteration 18` by direct grep re-read after editing.
- Confirmed the fix does NOT modify `~/anicca/skills/self/spawn/lib/treasury-gate.mjs`,
  `~/anicca/skills/self/spawn/lib/ledger.js`, or any other implementation file description — this is
  purely an additive spec-text extension (two new binding paragraphs + one new Acceptance Criteria bullet
  + one Acceptance Criteria clause + one new proof obligation + one Purity Boundary Map extension + one
  Gate extension), consistent with the discipline every prior FIND-14xx/15xx/16xx fix in this document
  already established.
- Confirmed, before writing any safety claim about REQ-103's lock, a direct re-read of REQ-103's own
  current text (`behavioral-spec.md`, pre-edit lines 957-1052) — its statePath prose explicitly states
  "REQ-101's earlier registry read and REQ-102's decision themselves run OUTSIDE the lock... only the ACT
  of proceeding on a `true` decision needs the lock" — confirming the lock does NOT cover REQ-101/102's
  evaluation step, so this resolution states plainly that the lock does NOT protect against
  `colonySurplusUsd` staleness, rather than inventing a false safety claim (the specific error mode the
  dispatch warned against, citing this spec's own earlier FIND-501 mistake for a different mechanism).
- No edits were made to `state.json`, review manifest/verdict files, or the `iteration-19` review
  directory — those remain the orchestrator's responsibility per this task's own instructions. No
  commit/push was performed.
