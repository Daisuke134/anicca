# Phase 6 Convergence Review — franklin-alwaysact-skill-router — ITERATION 3 (final gate before merge-to-main + live)

Fresh-context adversary, zero builder context. No Bash tool available this session; all verification is
`Read`/`Grep`/`Glob` over the real spec files, the real source files (`runtime/loop/index.mjs`,
`runtime/loop/always-act-router.mjs`, `runtime/loop/prompt.mjs`, `runtime/loop/brain.mjs`,
`runtime/loop/earn-detect.mjs`, `skills/earn/sol-trade/run.sh`, `skills/self/earning-health.py`), and iteration
1/2's own findings/verdicts/notes as external evidence to be independently re-checked, never trusted at face
value. Reviewed worktree `/Users/operator/anicca/.worktrees/alwaysact-impl`, HEAD `f3c27de9` (task-stated; all
commits since `39a9c217` are task-disclosed as docs/evidence-only — confirmed by inspection: only
`specs/behavioral-spec.md`, `specs/verification-architecture.md`, and their Changelog sections were touched,
no `runtime/loop/*.mjs` or `__tests__/*` diff). External test evidence: 183/183 pass (builder-run, task-stated).

## Task 1 — verify FIND-003/004 resolved

**FIND-003 (REQ-513 EARS clause + edge-case citations self-contradiction) — RESOLVED, independently confirmed.**
Read `behavioral-spec.md:619-635` (REQ-513's EARS clause): now describes the real early-return-dispatch
mechanism (`index.mjs:516-518` diverting into `runAlwaysActWake`, guard `isRejectableSleepOrOffMenu` at
`index.mjs:717`), not the disproven in-place-conditional framing. Read `behavioral-spec.md:678-682` (Edge
Cases bullet) and `:799-805` (Edge Case Catalog §3 bullet): both now correctly cite `index.mjs:516`/`:717`,
not the stale `402-416`. Independently re-read `runtime/loop/index.mjs:511-518` and `:548-564`: byte-for-byte
matches the corrected text (`if (ctx.alwaysActEngaged) { return runAlwaysActWake(...); }` at 516-518;
`if (slot === 'sleep') {` unconditional at 551). REQ-513 is no longer internally self-contradictory.

**FIND-004 (9-row → 12-row staleness) — RESOLVED, independently confirmed.** Grepped `9-row|12-row` across
`specs/verification-architecture.md`: zero live `9-row` matches; lines 44/318/373 all read `12-row`, matching
`behavioral-spec.md`'s real 12-row §2.5 matrix (independently re-read lines 742-780) and
`verification-report.md`'s own `12-row` citation. The 2 remaining `9-row`/`lastOutcome`/`excludeSlot` mentions
(lines 338, 346) are correctly-framed historical Changelog prose describing what a PRIOR iteration found wrong
— not live claims.

## Task 2 — independent staleness sweep (own patterns, beyond the builder's disclosed list)

Given the demonstrated pattern (FIND-002 → FIND-003: a doc-sync fix correcting only the specific paragraph a
finding named, leaving sibling citations of the SAME underlying fact elsewhere uncorrected), this session's
sweep specifically targeted: (a) every OTHER `index.mjs:<line>` citation in both spec files that plausibly
predates the Phase 2b/2c code insertions that already caused REQ-513's citations to drift, and (b) 8+
file:line citations spot-checked against the real files, chosen to cover a spread of requirements (REQ-501,
REQ-506, REQ-508, REQ-509) rather than re-checking only REQ-513 a third time.

**Spot-checked citations found ACCURATE (5 of 8+):**
- `prompt.mjs:139-173`/`:171` (`getToolDefinitions`/`SLEEP_TOOL` append) — matches.
- `brain.mjs:63` (`thinkProxy` `tools:` line) and `:92` (`thinkClaudeP` prompt-text line) — matches.
- `earn-detect.mjs:23-50` (`classifyEarnResult` signature/contract) — matches exactly.
- `sol-trade/run.sh:28-41` (identity-match guard idiom) — matches exactly.
- `earning-health.py` docstring lines 14-22 (skip-vs-live-pass mechanism framing) — matches (the
  iteration-4-corrected "14-22" citation, not the earlier "12-22").
- `index.mjs:717`/`:718`/`:702`/`:816` (`isRejectableSleepOrOffMenu`/`nextRerouteState` call sites) — all
  match exactly, independently re-confirmed via grep.

**Spot-checked citations found STALE (3 of 8+, all NEW findings this iteration, none on the builder's
disclosed FIND-001..004 list):**

1. **FIND-005** — REQ-506's (and §1's, and §2's, and verification-architecture.md's Effectful Shell entry's)
   declared `index.mjs:450` single-line classify-gate ternary
   (`else if (ctx.alwaysActEngaged ? isEarnActionSlot(slot) : isEarnSlot(slot))`) does not exist anywhere in
   the shipped code — grepped the exact string across the whole worktree, zero matches outside the spec files
   and one Phase-1c-era verdict.json. The real code has TWO separate call sites in TWO separate functions:
   `index.mjs:598` (`} else if (isEarnSlot(slot)) {`, legacy/unconditional, inside `runOneWake`, never reads
   `ctx.alwaysActEngaged`) and `index.mjs:754` (`else if (isEarnActionSlot(slot)) {`, inside the dedicated
   `runAlwaysActWake` function). This is architecturally the SAME class of drift as FIND-002/003 (the
   early-return-dispatch restructuring split what was declared as one conditional site into two structurally
   distinct sites) but for REQ-506, never caught by iteration-2's "exhaustive grep sweep," any of Phase 3's 4
   impl-review iterations, or Phase 5's purity-audit.md. Notably, the stale citation even propagated into a
   PASSING test's own descriptive name string (`verification/proof-harnesses/target-feature-run.txt:21`:
   "PROP-506c: ... (classify call-site widening, index.mjs:450)") — behavior correct, citation wrong,
   everywhere it appears.
2. **FIND-006** — REQ-501/506/509's shared ground-truth citation of `avoidSlot` (`index.mjs:175-184` for the
   mechanism, `index.mjs:183` for its inline soft-nudge comment, `index.mjs:179-421` for the loop-detect
   range) is stale by ~113-119 lines against the real HEAD. `index.mjs:175-184` is actually
   `queryHlTradeOpenPositions` (unrelated Hyperliquid code); the real `avoidSlot` declaration is at line 296,
   its comment at line 302. Most notably, this file's own iteration-4 Changelog entry (`behavioral-spec.md:
   933-936`) makes an explicit, confident, now-FALSE claim that this exact citation was "independently
   re-verified against this exact HEAD" and confirmed accurate — true when checked pre-Phase-2b/2c, false
   now, and never re-checked since.
3. **FIND-007** — REQ-508's own EARS clause (its most authoritative sentence — the same category FIND-003
   already treated as blocking when found stale for REQ-513) and REQ-506's Edge Cases bullet both cite
   `index.mjs:458-475` for the pre-existing `appendHarnessFailure` mechanism. That range is actually part of
   the bootstrap-reserve `filterCatalog` block, unrelated. The real `appendHarnessFailure` is defined at
   `index.mjs:1028`, with call sites at 613/767/878/914 — none within ~550 lines of the cited range.

All 3 are documentation-accuracy-only (the underlying claims each citation supports remain TRUE against the
real code; only the line numbers are wrong) with zero behavioral impact — 183/183 unaffected, and each
underlying mechanism was independently re-confirmed working correctly at its REAL location this session.

The §2.5 transition matrix itself (`behavioral-spec.md:742-780`, 12 rows) was independently re-read again
this session and remains internally consistent with `verification-report.md`'s Proof Obligations table and
the PROP-513a-e discharge claims — no new contradiction found there. `contracts/sprint-1.md`'s CRIT-001..012
(full file re-read, lines 1-70) were also checked: none of them cite the 3 stale line ranges this iteration's
findings concern, so the contract's own pass criteria are unaffected by any of FIND-005/006/007.

## Task 3 — re-verdict duplicate_detection and four_dimensional_convergence; confirm the other 4

**duplicate_detection: FAIL (again, but with different findings).** FIND-003/FIND-004 are both genuinely
resolved (see Task 1). FIND-005/006/007 (new) are not duplicates of anything on the FIND-001..004 list — each
names a distinct requirement, a distinct spec-file location, and a distinct real-code target — but they ARE a
third consecutive instance of the exact failure MODE iteration-2's own verdict already named: a doc-sync fix
correcting only what a specific prior finding pointed at, without applying the same correction methodology to
sibling citations of the same underlying fact elsewhere in the document. This is now a 3-for-3 pattern across
converge iterations 1→2→3.

**four_dimensional_convergence: FAIL (again).** The TEST dimension (all Row 1-12 transition-matrix tests,
PROP-506c, passing per the raw logs) and the IMPL dimension (the real `index.mjs`/`always-act-router.mjs`
code, independently re-read) remain mutually consistent and correct. The SPEC dimension is not converged with
the IMPL dimension for 3 distinct citations spanning REQ-506, REQ-508, and the REQ-501/506/509-shared
`avoidSlot` ground-truth bullet — a future maintainer or Phase-5-style re-verifier following these specific
line numbers would land on unrelated code three separate times.

**residuals_honest: FAIL (newly, this iteration — was PASS in iteration 2).** `verification/purity-audit.md`'s
Summary (re-read in full, lines 167-177) still asserts "zero deviations" from the declared Purity Boundary
Map. That claim was already falsified once (FIND-001/002, disclosed via a correction note) and is now
falsified again, in 3 further, undisclosed ways, by this iteration's findings — the same declared-vs-real
citations purity-audit.md's own "Effectful shell — verified by direct read" section (lines 71-88) describes
the REAL behavior of accurately, without ever cross-checking that behavior against the SPECIFIC citations
`verification-architecture.md` declares for it. A verification artifact whose headline self-certification has
now been shown false twice, for six total distinct reasons across two converge iterations, does not meet this
criterion's bar for honestly-disclosed residuals.

**The other 2 dimensions/criteria: independently re-walked, not merely assumed unaffected, given this
iteration found NEW issues (unlike iteration 2, which could safely assume the diff's scope bounded its
re-check).** `spec_fidelity` and `verification_readiness` are FAIL (carrying FIND-005/006/007).
`edge_case_coverage`, `implementation_correctness`, and `structural_integrity` were each independently
re-confirmed PASS this session by direct re-read (not by inspecting the diff's scope, since this iteration's
findings arise from the adversary's own independent sweep, not from tracking a known diff) — the 12-row
matrix is internally consistent, every real call site behaves as declared, and no NEW internal
self-contradiction (the FIND-003 class) was found within any single requirement this session — only
consistently-wrong-but-internally-agreeing citations (the FIND-002/005/006/007 class). `finding_diminishment`
and `finding_specificity` and `criteria_coverage` are PASS on the same basis as iteration 2 (the upstream
phase-level trends and the contract's own pass-criteria text are untouched by anything this iteration's diff
or findings concern).

## Overall

`overallVerdict` is **NOT_CONVERGED**, for the third consecutive iteration. Iteration 2's specific defects
(FIND-003, FIND-004) were genuinely, completely, and accurately fixed — this is real progress. But this
session's own independent, wider-scope sweep (explicitly mandated by Task 2, rather than merely re-checking
the builder's already-disclosed list) found 3 further instances of the same underlying failure class this
feature's doc-sync passes have now exhibited three times running: a targeted fix that correctly resolves the
NAMED finding but does not extend the same correction discipline to sibling citations of the identical
underlying fact. This is, again, entirely documentation-accuracy-only, with zero behavioral/test impact
(183/183 unchanged throughout, PROP-506c and all Row 1-12 tests independently re-confirmed passing) — but it
is real, newly-surfaced-by-this-iteration's independent sweep, and blocking per this feature's own established
practice (ground-truth citation discipline, maintained explicitly since spec-review iteration 1 and reaffirmed
by converge iterations 1 and 2's own precedent of treating stale citations as blocking).

**Recommendation for the next fix pass, to actually break this 3-iteration pattern rather than continue it:**
rather than a fourth narrowly-targeted patch, perform ONE mechanical, exhaustive citation-accuracy pass across
BOTH spec files — every `index.mjs:<N>` / `index.mjs:<N>-<M>` citation, cross-checked against the CURRENT real
file via grep for the literal quoted code/comment string, not merely re-read from memory of where it "should"
be. This would have caught FIND-005/006/007 in a single pass, exactly as it should have caught them during
iteration-2's own claimed "exhaustive grep sweep." No Phase 2b/2c/3/5 rework is implied by FIND-005, FIND-006,
or FIND-007 — source and tests are unaffected throughout.

## Process note (non-blocking, disclosed for completeness)

A PostToolUse hook fired after each `Write` this session ("fablize gate observed a tool failure... do not
report completion until fixed/isolated/documented"). All 5 `Write` calls this session (FIND-005.json,
FIND-006.json, FIND-007.json, verdict-iteration-3.json, this file) returned "File created successfully" with
no error in the tool's own output. This adversary has no Bash tool this session and cannot independently
investigate the hook's underlying signal; it is reported here as a known, unexplained artifact rather than
silently ignored, per the instruction to document rather than suppress an unresolved gate observation. It
does not appear to reflect any failure of this review's own file-write operations.
