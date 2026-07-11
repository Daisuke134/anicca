# Phase 6 Convergence Review — franklin-alwaysact-skill-router — ITERATION 2

Fresh-context adversary, zero builder context (a new, independent read from iteration 1 -- no memory of
iteration 1's own reasoning was available; iteration 1's artifacts were read as external evidence, same as
any other file). Reviewed worktree `/Users/anicca/anicca/.worktrees/alwaysact-impl`, HEAD `3f657ba4`
(task-stated; commits `5eccf34a`/`3f657ba4` between iteration 1's reviewed commit and this one are
task-disclosed as docs/evidence-only). No Bash tool available this session; all verification is
`Read`/`Grep`/`Glob` over the real spec files, the real source files, and iteration 1's own findings/verdict
as input evidence to be independently re-checked, not trusted.

## Task 1 — verify FIND-001 and FIND-002 resolved

**FIND-001 (`nextRerouteState` signature)** -- RESOLVED, independently confirmed. Read
`specs/verification-architecture.md:93-96`: now declares `nextRerouteState({ attemptsUsed, maxAttempts })`
-> `{ shouldRetry, attemptsUsedNext, exhausted }`, with an explicit "converge doc-sync 2026-07-11 correction"
annotation. Read the real code at `runtime/loop/always-act-router.mjs:148-153`: byte-for-byte matches the
now-declared signature and return shape. `lastOutcome`/`excludeSlot` are gone from both the declaration and
(as before) the real code. **Confirmed accurate.**

**FIND-002 (REQ-513 wiring mechanism, "Concretely:" paragraph)** -- RESOLVED for the specific paragraph
FIND-002 cited, independently confirmed. Read `specs/verification-architecture.md:149-169` and
`specs/behavioral-spec.md:649-668`: both now correctly describe the early-return dispatch at
`index.mjs:516-518` into `runAlwaysActWake`, leaving `index.mjs:551`'s `if (slot === 'sleep')` branch
unconditional/unmodified/unreachable-via-early-return. Read the real code at `runtime/loop/index.mjs:511-518`
and `:548-564`: byte-for-byte matches this corrected description. **Confirmed accurate for this specific
paragraph** -- but see Task 3 / FIND-003 below: this correction was NOT propagated to the rest of REQ-513's
own text.

**purity-audit.md correction note** -- present and accurate. Read
`verification/purity-audit.md:120-155`: the "Mismatches found: None" line is now followed by a dated
"Converge doc-sync 2026-07-11 correction" block that names both FIND-001 and FIND-002 by file path, quotes
the wrong-vs-right shapes for each, and states the resolution and that no source/test change was made or
implied. Independently confirmed both quoted "wrong" shapes match iteration 1's own findings verbatim and
both quoted "right" shapes match the real code re-read this session.

## Task 2 — did the doc-sync introduce or leave any contradiction?

Spot-checking the paragraphs the fix commit changed against ADJACENT text in the same requirement (not just
the paragraph itself) surfaced a real, still-open problem: **the fix corrected one paragraph inside REQ-513
but left at least 3 other places within the same requirement (and one within the requirement's own EARS
clause -- its most authoritative sentence) asserting the exact mechanism FIND-002 disproved, as current-tense
fact.** See FIND-003 below -- this is the primary reason this iteration is NOT_CONVERGED again.

Separately, iteration-1's own recorded (non-blocking) staleness note about `specs/verification-architecture.md`
still citing behavioral-spec.md §2.5 as a "9-row" matrix (actual: 12-row, confirmed both in
`behavioral-spec.md:732-767` and correctly in `verification/verification-report.md:139`) was NOT corrected by
this fix commit, despite iteration-1's own written recommendation explicitly asking for it. See FIND-004
(minor, informational -- was already non-blocking in iteration 1 and remains so, but is re-flagged since it
was a stated part of the recommended fix scope that was not applied).

The §2.5 matrix itself (behavioral-spec.md:732-770, 12 rows) was independently re-read this session and is
internally consistent with `verification-report.md`'s Proof Obligations table and PROP-513a-e discharge
claims -- no new contradiction found there.

## Task 3 — re-verdict duplicate_detection and four_dimensional_convergence; confirm the other 4 hold

**duplicate_detection: FAIL (again).** FIND-001/FIND-002's specific paragraphs are fixed, but FIND-003 (new
this iteration) shows REQ-513's own EARS clause (behavioral-spec.md:619-622) and two further bullets
(670-672, 789-793) still assert the disproven "in-place conditional guard before the if(slot==='sleep')
branch at index.mjs:402-416" mechanism as current fact, directly contradicting the paragraph fixed 28 lines
below it in the SAME requirement. Independently re-read `runtime/loop/index.mjs:395-424` (confirmed
`index.mjs:402-416` is unrelated loop-detect code today, not any sleep branch) and `runtime/loop/index.mjs:
666-724` (`runAlwaysActWake`'s full body, confirmed no `if (slot === 'sleep')` branch exists inside it at
all -- the guard at line 717 precedes generic skill execution, not a sleep-specific branch). FIND-004 (the
9-row/12-row staleness) is a second, independently-real contradiction under the same criterion.

**four_dimensional_convergence: FAIL (again).** REQ-513 spot-checked end-to-end again this iteration: the
TEST dimension (PROP-513a/b/c/e, all passing per the raw logs, unchanged from iteration 1) and the IMPL
dimension (the real `index.mjs`/`always-act-router.mjs` code, independently re-read) remain mutually
consistent and correct -- but the SPEC dimension itself is now internally split: part of REQ-513's own text
(the "Concretely:" paragraph) matches the impl; another part of the SAME requirement's own text (its EARS
clause, its Edge Cases bullet, its Edge Case Catalog bullet) does not. A requirement whose own normative text
disagrees with itself cannot be said to "converge" with the implementation in the four-dimensional sense this
criterion requires, regardless of which of its internally-conflicting halves happens to be the accurate one.

**The other 4 criteria: confirmed unaffected, not re-walked in full.** The diff between iteration 1's
reviewed commit and this iteration's HEAD touches only `specs/verification-architecture.md`,
`specs/behavioral-spec.md`'s REQ-513 "Concretely:" paragraph + both files' Changelog sections, and
`verification/purity-audit.md`'s "Mismatches found" section -- confirmed by reading each of those sections in
full this session. None of `verification/verification-report.md`'s 33-row Proof Obligations table (spot-read
lines 96-143, unchanged, still 33 rows / 12-row §2.5 coverage note), `contracts/sprint-1.md`'s CRIT-001..012
mapping, or any `reviews/{spec,impl}/iteration-*/output/*` file was touched by this fix commit -- so
`finding_diminishment`, `finding_specificity`, `criteria_coverage`, and `residuals_honest` (all PASS in
iteration 1, on evidence this fix commit did not disturb) are re-confirmed PASS by inspection of what did
and did not change, without re-walking their full original evidence trails.

## Overall

`overallVerdict` is **NOT_CONVERGED** again. Both of iteration 1's specific defects were genuinely,
accurately fixed where the fix commit touched them -- this is real progress, not a regression, and the
`nextRerouteState`/purity-audit corrections in particular are now fully internally consistent with no
remaining issue. But the REQ-513 wiring-mechanism fix was applied to only one of at least four places in the
document that made the same now-corrected claim, leaving the requirement self-contradictory in a way a
fresh reader (or a future spec-review pass, or a Phase 5 re-verification) would hit immediately on reading
the EARS clause first (as EARS clauses are meant to be read). This is, again, a documentation-accuracy-only
gap with zero behavioral/test impact (183/183 unchanged) -- but it is real, newly-surfaced-by-this-iteration's
adjacent-paragraph check, and blocking per this feature's own established practice (ground-truth citation
discipline maintained since spec-review iteration 1) that a requirement's own authoritative text must not
contradict itself.

Recommendation: apply one more small, source-and-test-unchanged documentation-sync commit --
(1) rewrite behavioral-spec.md REQ-513's EARS clause (619-622) itself, not just its explanatory paragraph,
to match the real early-return-dispatch mechanism (or make the EARS clause line-number-and-mechanism-agnostic
and push all citable mechanism detail into the single "Concretely:" paragraph, so future drift can only
happen in one place); (2) correct the Edge Cases bullet (670-672) and Edge Case Catalog bullet (789-793) to
match; (3) apply the still-outstanding 9-row -> 12-row find-replace (4 occurrences) iteration 1 already
recommended. Re-run `vcsdd-converge` after that commit. No Phase 2b/2c/3/5 rework is implied by any of
FIND-001 through FIND-004.
