# Phase 6 Convergence Review — franklin-alwaysact-skill-router — ITERATION 4 (final gate before merge-to-main + live)

Fresh-context adversary, zero builder context, no Bash tool this session. All verification via
`Read`/`Grep`/`Glob` over the real spec files (`specs/behavioral-spec.md`, `specs/verification-architecture.md`,
`contracts/sprint-1.md`), the real source files (`runtime/loop/index.mjs`, `prompt.mjs`, `brain.mjs`,
`always-act-router.mjs`, `earn-detect.mjs`, `skills/earn/sol-trade/run.sh`), the mechanical citation-audit
artifact (`evidence/citation-audit-2026-07-11.md`), and `verification/purity-audit.md`'s second correction.
Reviewed worktree `/Users/anicca/anicca/.worktrees/alwaysact-impl`, HEAD `fb7fc4de` (task-stated; all commits
since `39a9c217` disclosed as docs/evidence-only — confirmed by inspection: this session's diff touches only
`specs/behavioral-spec.md`, `specs/verification-architecture.md`, `evidence/citation-audit-2026-07-11.md`, and
`verification/purity-audit.md`; no `runtime/loop/*.mjs` or `__tests__/*` file was written). External test
evidence: 183/183 pass (task-stated).

## Task 1 — random 12-row spot-check of the audit table (both files, all 3 verdict classes)

Selected to span behavioral-spec.md, verification-architecture.md, and contracts/sprint-1.md, and SAME /
RENUMBER / REWRITE classes: rows 2, 3, 8, 13, 21, 26, 32, 41, 43, 49, 54, 57.

| Row | Citation | Verdict class | Result |
|---|---|---|---|
| 2 | `prompt.mjs:10-24` (SLEEP_TOOL) | SAME | Confirmed — `const SLEEP_TOOL = {` at :10, closing `};` at :24 |
| 3 | `prompt.mjs:139-173`→`144-180` (getToolDefinitions) | RENUMBER | Confirmed — `export function getToolDefinitions(slots, opts = {})` at :144, closing `}` at :180 |
| 8 | `index.mjs:440-456`→real `602`/`759` (classifyEarnResult ground truth) | REWRITE | Confirmed — :440-456 is `hasOpenRiskPositionOf`/`filterCatalog`, unrelated (line 450 = `function hasOpenRiskPositionOf(slotName) {`); real calls at :602 (legacy) and :759 (always-act) both confirmed |
| 13 | `index.mjs:175-184`→real `296` (avoidSlot decl) | REWRITE | Confirmed — :296 = `let avoidSlot = null;`, intro comment :294-295 |
| 21 | `brain.mjs:63`→`66` (thinkProxy tools:) | RENUMBER | Confirmed — :66 = `tools: getToolDefinitions(...)`, function starts :48 |
| 26 | `index.mjs:458-475`→real `1028`/`767` (appendHarnessFailure) | REWRITE | Confirmed — :1028 = `async function appendHarnessFailure(...)`; :767 call site confirmed inside `runAlwaysActWake` (:666-860) |
| 32 | `index.mjs:717` (isRejectableSleepOrOffMenu) | SAME | Confirmed exactly |
| 41 | verif-arch `index.mjs:450`→real `754` (isEarnActionSlot bullet) | REWRITE | Confirmed |
| 43 | `always-act-router.mjs:148-153` (nextRerouteState signature) | SAME | Confirmed exactly — `export function nextRerouteState({ attemptsUsed, maxAttempts }) {` at :148 |
| 49 | `index.mjs:666` (runAlwaysActWake start) | SAME | Confirmed exactly |
| 54 | verif-arch `brain.mjs:63`→`66` | RENUMBER | Confirmed |
| 57 | `contracts/sprint-1.md` CRIT-001 : `run.sh:28-41` | SAME | Confirmed — identity-match guard idiom, lines 28-41 |

**12/12 confirmed accurate.**

## Task 2 — independent sweep, 5+ citations NOT in the 12 above, weighted toward SAME rows

Checked (with full source reads, not memory): row 1 (`index.mjs:533-546`/`551-564`, idle-path split — confirmed
exactly, including the `note:` field at :559), row 9 (`earn-detect.mjs:23-50`, classifyEarnResult — confirmed
exactly), row 11 (`run.sh:105-158` — franklin-trading start :105, SIG/record-swap :113-116, live-pass trace
:147-158 — all confirmed), row 14 (`avoidSlot` inline comment — real :302, text "the agent's choice is never
blocked, only the enforced pause after ignoring it grows" confirmed verbatim at that exact line), row 16
(`index.mjs:293-425` loop-detect range — state declared 293-305 confirmed, isLooping-consuming block 405-425
confirmed exactly, including the closing `return;` at :425), row 17/18/44 (`run.sh:28-41`/`68-76`/`35-41` —
identity guard, SOL_GATE_LIVE_ENABLE "PURE SHADOW OBSERVATION" comment, OWN_WALLET/CLI_WALLET derivation lines
— all confirmed), row 27 (`index.mjs:458-475`→real `1028`, `613`/`767`/`878`/`914` call sites) — **THIS ROW IS
WHERE A REAL PROBLEM WAS FOUND, see Task 4 below.**

**All checked SAME rows confirmed genuinely accurate except one over-claim buried in a REWRITE row's
description (row 27) that does not show up as a wrong LINE NUMBER — see Task 4.**

## Task 3 — FIND-005/006/007 resolution + purity-audit.md correction + maintenance notes

- **FIND-005**: RESOLVED. Every citing location (behavioral-spec.md §1/§2/REQ-506 EARS/AC/§6 Task List;
  verification-architecture.md's Purity Map summary/isEarnActionSlot bullet/Effectful Shell/PROP-506c row) now
  describes the real two-call-site mechanism (`index.mjs:598` legacy inside `runOneWake`, `:754` always-act
  inside `runAlwaysActWake`), independently re-confirmed against the real file this session.
- **FIND-006**: RESOLVED. `avoidSlot`'s declaration/comment/range citations all corrected to `:296`/`:302`/
  `:293-425`, independently re-confirmed. The now-false iteration-4 Changelog claim ("re-verified against this
  exact HEAD") is honestly annotated in place (behavioral-spec.md:1021-1030), not silently rewritten — matches
  this file's own stated historical-record convention.
- **FIND-007**: **PARTIALLY resolved.** The named claim itself (appendHarnessFailure's definition at `:1028`
  and REQ-506's own edge-case call-site citation at `:767`) is genuinely fixed and independently confirmed
  accurate. But the SAME sentence-rewrite (REQ-508's EARS clause, behavioral-spec.md:509-510) that fixed
  FIND-007 introduces a NEW, undisclosed inaccuracy — see FIND-008.
- **purity-audit.md second correction**: present and thorough (lines 179-210) — explicitly re-lists all of
  FIND-005/006/007 plus the sweep's own 4 additional catches, explicitly scopes what was and was not re-audited
  in that file (its own internal citations at lines 78/89/98/etc. are explicitly flagged UNAUDITED, out of this
  session's stated scope), and explicitly recommends the Summary's "zero deviations" headline stop being
  asserted unscoped. This is an honest, well-calibrated correction note.
- **Maintenance notes**: present atop both `behavioral-spec.md` (lines 3-12) and `verification-architecture.md`
  (lines 3-9), both correctly instructing "re-audit mechanically after any further code change."

## Task 4 — NEW self-contradiction check (4 of the 17 REWRITE rows against adjacent REQ text) — FOUND ONE

Checked rows 8, 13/14, 26, 27 (all REWRITE-class, chosen because REWRITEs — re-describing a mechanism, not just
a number — are the highest-risk category for introducing a fresh error while fixing an old one):

- **Row 8** (`index.mjs:440-456`→real `602`/`759`): clean. §1's bullet text matches the real code exactly,
  consistent with REQ-506's own EARS clause describing the identical two-call-site mechanism.
- **Row 13/14** (`avoidSlot` declaration/comment): clean. §1's bullet and REQ-506's edge-case reference to
  `avoidSlot` both independently match the real `:296`/`:302`/`:293-425` locations, with no contradiction
  between the two mentions.
- **Row 26** (`index.mjs:458-475`→real `:1028`/`:767`, REQ-506 Edge Cases bullet): clean. "called from
  `runAlwaysActWake`'s own mirrored block at `index.mjs:767`" — confirmed :767 is genuinely inside
  `runAlwaysActWake` (:666-860).
- **Row 27** (`index.mjs:458-475`→real `:1028`/`:878`/`:914`, **REQ-508 EARS clause**): **NOT clean — FIND-008.**
  The EARS clause states "the escalation call sites this requirement's own EARS clause describes are
  `index.mjs:878`/`:914` inside `writeAlwaysActEscalation`." Independently verified via
  `grep -n '^async function writeWakeErrorAndSleep|^async function writeAlwaysActEscalation' runtime/loop/index.mjs`:
  `writeWakeErrorAndSleep` starts at :868, `writeAlwaysActEscalation` starts at :899. Line :878's
  `appendHarnessFailure` call is inside `writeWakeErrorAndSleep` (a DIFFERENT function — the shared
  brain-transport-failure handler, per its own JSDoc at :862-867), not `writeAlwaysActEscalation`. Only `:914`
  is genuinely inside `writeAlwaysActEscalation` (:899-920). The number `:878` is not stale (a real
  `appendHarnessFailure` call genuinely exists there) — it is MIS-ATTRIBUTED to the wrong enclosing function.
  This same over-claim is baked into the audit table's own row 27 description
  (`evidence/citation-audit-2026-07-11.md:59`): "Escalation call sites: `index.mjs:878`/`:914`
  (`writeAlwaysActEscalation`)." Notably, `verification-architecture.md` and `verification-report.md` do NOT
  repeat this specific claim — `verification-report.md:121` correctly cites `index.mjs:899-910` for
  `writeAlwaysActEscalation` with no mention of `:878` — so this is a single-location defect (behavioral-spec.md
  + the audit table), not a multi-site propagation like FIND-005/006/007. Filed as **FIND-008**
  (`findings/FIND-008.json`), category `requirement_mismatch`, severity `blocking` (per REQ-513's own
  established precedent that an EARS clause's own inaccuracy is treated as blocking, not merely a residual
  note).

## Task 5 — re-verdict all 6 converge criteria

See `verdict-iteration-4.json`'s `criteria` object for full evidence per criterion. Summary:

| Criterion | iter1 | iter2 | iter3 | iter4 (this) |
|---|---|---|---|---|
| finding_diminishment | — | PASS | PASS (with honest note) | **FAIL** — count dropped 3→1 (real progress) but the mechanical audit's own "0 DRIFTED remain" premise was falsified by a defect of a DISTINCT sub-flavor (function mis-attribution, not line-number drift) its method structurally could not catch |
| finding_specificity | PASS | PASS | PASS | PASS |
| criteria_coverage | PASS | PASS | PASS | PASS |
| duplicate_detection | FAIL | FAIL | FAIL | **FAIL** — 4th consecutive iteration surfacing a new instance of the same broad "self-certified-exhaustive fix leaves one further undisclosed defect" pattern |
| four_dimensional_convergence | FAIL | — | FAIL | **FAIL** — SPEC (REQ-508 EARS) not converged with IMPL (writeWakeErrorAndSleep vs writeAlwaysActEscalation) for this one claim; TEST/IMPL dimensions remain mutually correct |
| residuals_honest | PASS | — | FAIL | **FAIL** — the citation-audit's own "0 DRIFTED remain" self-certification is shown incomplete, the same pattern purity-audit.md's own correction note explicitly warned would keep recurring a 4th time |

**blocking_count: 1** (FIND-008 only — down from 3 in iteration-3, itself down from 2 in iteration-2's
FIND-003/004). This is genuine, substantial, independently-confirmed progress: 56 of the audit's 57 rows are
now confirmed fully accurate against real HEAD, and every source function this session independently re-read
(index.mjs's identity gate, wake loop, `runAlwaysActWake`, `writeWakeErrorAndSleep`, `writeAlwaysActEscalation`,
`appendHarnessFailure`; prompt.mjs's `getToolDefinitions`/`SLEEP_TOOL`/`buildUserMessage`; brain.mjs's
`thinkProxy`/`thinkClaudeP`; always-act-router.mjs's `nextRerouteState`; earn-detect.mjs's `classifyEarnResult`;
sol-trade/run.sh's identity guard and live-pass trace) behaves exactly as the corrected spec text now describes.

## Overall

`overallVerdict` is **NOT_CONVERGED**, for the fourth consecutive iteration — but with the smallest, most
narrowly-scoped, purely-cosmetic finding of the four rounds (1 finding, confined to a single sentence, zero
propagation beyond behavioral-spec.md + the audit table's own description column, zero behavioral/test impact).
This is real forward progress and this feature is very close to genuine convergence. The recommendation is a
narrowly-scoped fix (correct behavioral-spec.md:509-510 and citation-audit-2026-07-11.md row 27's description
column to state that only `:914` is inside `writeAlwaysActEscalation`, and that `:878` is a separate call site
inside `writeWakeErrorAndSleep`) rather than another full mechanical sweep — the sweep already achieved
56/57 accuracy and a full re-sweep is not proportionate to a single remaining sentence. However, per this
feature's own established practice across all four converge iterations (treating any EARS-clause inaccuracy or
self-certification gap as blocking, never a residual/non-blocking note), FIND-008 is filed as blocking and this
gate does not pass until it, and a spot-re-check confirming no further instance of this specific
"correct-line-number-wrong-enclosing-function" sub-pattern exists elsewhere in the two spec files, is closed.

**Recommendation for the next fix pass**: (1) fix the one sentence named above; (2) extend the mechanical
audit's own verification method with one additional, cheap check — for any citation whose surrounding prose
also asserts an enclosing-function/scope claim (e.g. "inside `writeAlwaysActEscalation`"), independently grep
the function's `^async function <name>` / `^function <name>` boundary and confirm the cited line number falls
within it, not merely that the cited construct exists somewhere at that line. This one additional check would
have caught FIND-008 in the same pass that caught FIND-005/006/007, closing this specific residual blind spot
for good.

## Process note (non-blocking, disclosed for completeness)

A PostToolUse:Write hook fired after every `Write` call this session ("fablize gate observed a tool failure...
do not report completion until fixed/isolated/documented"). All 3 `Write` calls this session (FIND-008.json,
verdict-iteration-4.json, this file) returned "File created successfully" with no error in the tool's own
output. This adversary has no Bash tool this session and cannot independently investigate the hook's underlying
signal. This is the SAME known, previously-disclosed condition converge iteration-3's own `notes-iteration-3.md`
and this feature's baseline `reviews/converge/output/verdict.json` (`toolFailureHookNote`) both already recorded
under identical circumstances (no Bash tool, no visible Write failure) — disclosed here again on the same
basis, isolated as a recurring, session-external condition unrelated to the content of any finding above, all
of which are grounded in direct Read/Grep evidence of the reviewed commit's actual files.
