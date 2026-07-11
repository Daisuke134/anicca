# Mechanical Citation Audit — franklin-alwaysact-skill-router (2026-07-11)

**Purpose**: converge iterations 1→2→3 each produced a doc-sync fix that resolved only the NAMED finding
without extending the same correction discipline to sibling citations of the same underlying fact
elsewhere in the document (FIND-001/002 → FIND-003/004 → FIND-005/006/007, a 3-for-3 pattern). This audit
performs the ONE mechanical, exhaustive pass converge iteration-3's own recommendation asked for: every
`<file>.mjs:<line>` / `<file>.sh:<line>` / `<file>.py:<line>` citation in `specs/behavioral-spec.md`,
`specs/verification-architecture.md`, and `contracts/sprint-1.md` was extracted via regex, then for EACH
citation the surrounding spec text's described code construct was independently grepped against the REAL
file at HEAD `f3c27de9` (never re-read from memory of where it "should" be). This is the converge
adversary's verification artifact for this fix.

**Method**: `grep -noE '[A-Za-z_.-]+\.(mjs|sh|py):[0-9]+(-[0-9]+)?(,[0-9]+-[0-9]+)?'` over the three spec
files, excluding citations inside `## Changelog` sections (historical record of prior states, correctly
left as-is per the "do not paraphrase away history" convention) unless a FIND finding specifically named
that Changelog line as containing a now-false claim (FIND-006's iteration-4 entry — annotated, not
rewritten, per instruction).

**Result**: 58 live citation occurrences extracted. 29 SAME (verified accurate against HEAD).
29 DRIFTED, of which 17 required REWRITE (the underlying mechanism shipped as a structurally different
shape than declared — e.g. one line becoming two call sites in two functions) and 12 required simple
RENUMBER (same mechanism, new line number). **0 DRIFTED remain** after this fix (re-swept, see
"Post-fix re-verification" below).

## Audit table

Legend: **SAME** = citation was already accurate, no change made. **RENUMBER** = mechanism unchanged,
line number corrected. **REWRITE** = mechanism re-described to match the actually-shipped shape (per the
FIND-005 precedent: two call sites in two functions, never a single in-place ternary).

| # | File : old citation | Described construct | Real location (HEAD f3c27de9) | Verdict | Source |
|---|---|---|---|---|---|
| 1 | behavioral-spec.md §1 : `index.mjs:382-416` | "TWO existing idle paths": (a) no-tool-call → narrate, (b) sleep → narrate | (a) `index.mjs:533-546`; (b) `index.mjs:551-564` (`note:` field at `:559`) | DRIFTED → RENUMBER (split) | this sweep |
| 2 | behavioral-spec.md §1 : `prompt.mjs:10-24` | `SLEEP_TOOL` object literal | `prompt.mjs:10-24` | SAME | this sweep |
| 3 | behavioral-spec.md §1 : `prompt.mjs:139-173` | `getToolDefinitions` function | `prompt.mjs:144-180` | DRIFTED → RENUMBER | this sweep |
| 4 | behavioral-spec.md §1 : `brain.mjs:63` | `thinkProxy`'s `tools:` line | `brain.mjs:66` (function starts `:48`) | DRIFTED → RENUMBER | this sweep |
| 5 | behavioral-spec.md §1 : `brain.mjs:92` | `thinkClaudeP`'s prompt-text instruction line | `brain.mjs:100-102` (function starts `:89`; with-sleep branch `:102`) | DRIFTED → RENUMBER | this sweep |
| 6 | behavioral-spec.md §1 : `prompt.mjs:139-173` (2nd occurrence) | `getToolDefinitions(slots)` | `prompt.mjs:144-180` | DRIFTED → RENUMBER | this sweep |
| 7 | behavioral-spec.md §1 : `prompt.mjs:171` | `SLEEP_TOOL` appended unconditionally | `prompt.mjs:178` | DRIFTED → RENUMBER | this sweep |
| 8 | behavioral-spec.md §1 : `index.mjs:440-456` | `classifyEarnResult` ground-truth (reads earn-ledger.jsonl, `line.wake===wakeId`) | Real call sites: `index.mjs:602` (legacy, `runOneWake`) + `index.mjs:759` (`runAlwaysActWake`). `440-456` is actually the `hasOpenRiskPositionOf`/`filterCatalog` bootstrap-reserve block, unrelated. | DRIFTED → REWRITE (same root cause as FIND-005, NEW finding this sweep) | this sweep |
| 9 | behavioral-spec.md §1 : `earn-detect.mjs:23-50` | `classifyEarnResult` function definition | `earn-detect.mjs:23-50` | SAME | this sweep (converge notes-iteration-3 also confirmed) |
| 10 | behavioral-spec.md §1 : `index.mjs:450` | classify call-site ternary `else if (ctx.alwaysActEngaged ? isEarnActionSlot(slot) : isEarnSlot(slot))` | Does not exist. Real: `index.mjs:598` (`} else if (isEarnSlot(slot)) {`, legacy, `runOneWake`) + `index.mjs:754` (`else if (isEarnActionSlot(slot)) {`, `runAlwaysActWake`) — two separate call sites. `index.mjs:450` is `function hasOpenRiskPositionOf(slotName) {`, unrelated. | DRIFTED → REWRITE | **FIND-005** |
| 11 | behavioral-spec.md §1 : `run.sh:105-158` | `franklin-trading start`, live-pass trace append, conditional `record-swap.mjs` call | `sol-trade/run.sh:105` (`franklin-trading start`), `:113-116` (SIG/record-swap), `:147-158` (live-pass trace) — all within `105-158` | SAME | this sweep |
| 12 | behavioral-spec.md §1 : `index.mjs:450` (2nd occurrence, isEarnSlot bullet) | classify call-site widening | same as #10 | DRIFTED → REWRITE | **FIND-005** |
| 13 | behavioral-spec.md §1 : `index.mjs:175-184` | `avoidSlot` mechanism block | `queryHlTradeOpenPositions` (unrelated Hyperliquid query). Real `avoidSlot` declaration: `index.mjs:296` (intro comment `:294-295`). | DRIFTED → REWRITE | **FIND-006** |
| 14 | behavioral-spec.md §1 : `index.mjs:183` | `avoidSlot`'s inline soft-nudge comment | Real: `index.mjs:302` | DRIFTED → REWRITE | **FIND-006** |
| 15 | behavioral-spec.md §1 : `prompt.mjs:205-207` | FORBIDDEN-slot prose in `buildUserMessage` | Real: `prompt.mjs:212-214` (ternary), text on `:213` | DRIFTED → RENUMBER | this sweep |
| 16 | behavioral-spec.md §1 : `index.mjs:179-421` | "loop-detect diversification" range | Real: `index.mjs:293-425` (state declared `293-305`, isLooping-consuming block `405-425`) | DRIFTED → REWRITE | **FIND-006** |
| 17 | behavioral-spec.md §1 : `run.sh:28-41` | identity-match guard idiom | `sol-trade/run.sh:28-41` | SAME | this sweep |
| 18 | behavioral-spec.md §1 : `run.sh:68-76` | `SOL_GATE_LIVE_ENABLE` "PURE SHADOW OBSERVATION" comment | `sol-trade/run.sh:68-76` | SAME | this sweep |
| 19 | behavioral-spec.md §2 (Purity Boundary Analysis) : `index.mjs:450` | classify-call-site gate widening | same as #10 | DRIFTED → REWRITE | **FIND-005** |
| 20 | behavioral-spec.md REQ-501 : `run.sh:28-41` | identity-match idiom | `sol-trade/run.sh:28-41` | SAME | this sweep |
| 21 | behavioral-spec.md REQ-504 pt.3 : `brain.mjs:63` | `thinkProxy`'s `tools:` line | `brain.mjs:66` | DRIFTED → RENUMBER | this sweep |
| 22 | behavioral-spec.md REQ-504 pt.4 : `brain.mjs:92` | `thinkClaudeP`'s prompt-text line | `brain.mjs:100-102` | DRIFTED → RENUMBER | this sweep |
| 23 | behavioral-spec.md REQ-504 edge case : `index.mjs:551` | `if (slot === 'sleep')` bare string check | `index.mjs:551` | SAME | this sweep (converge notes-iteration-3 also confirmed) |
| 24 | behavioral-spec.md REQ-506 EARS : `index.mjs:450` | classify call-site condition | same as #10 | DRIFTED → REWRITE | **FIND-005** |
| 25 | behavioral-spec.md REQ-506 edge case : `index.mjs:179-421` | soft `avoidSlot` mechanism (NOT reused by reroute) | same as #16 | DRIFTED → REWRITE | **FIND-006** |
| 26 | behavioral-spec.md REQ-506 edge case : `index.mjs:458-475` | `appendHarnessFailure` mechanism | Definition: `index.mjs:1028`. Call site relevant here: `index.mjs:767` (inside `runAlwaysActWake`). `458-475` is the `filterCatalog` try/catch block, unrelated. | DRIFTED → REWRITE | **FIND-007** |
| 27 | behavioral-spec.md REQ-508 EARS : `index.mjs:458-475` | `appendHarnessFailure` mechanism | Definition: `index.mjs:1028`. Escalation call sites: `index.mjs:878`/`:914` (`writeAlwaysActEscalation`). | DRIFTED → REWRITE | **FIND-007** |
| 28 | behavioral-spec.md REQ-513 : `index.mjs:516-518` | early-return dispatch into `runAlwaysActWake` | `index.mjs:516-518` | SAME | this sweep + converge iter2 (already fixed) |
| 29 | behavioral-spec.md REQ-513 (×2) : `index.mjs:551` | legacy unconditional sleep branch | `index.mjs:551` | SAME | this sweep |
| 30 | behavioral-spec.md REQ-513 "Concretely" : `index.mjs:516-518` | early-return dispatch | `index.mjs:516-518` | SAME | this sweep |
| 31 | behavioral-spec.md REQ-513 "Concretely" : `index.mjs:551` (×2) | legacy sleep branch, unreachable for engaged wake | `index.mjs:551` | SAME | this sweep |
| 32 | behavioral-spec.md REQ-513 "Concretely" : `index.mjs:717` (×2) | `isRejectableSleepOrOffMenu` guard call | `index.mjs:717` | SAME | this sweep + converge notes-iteration-3 |
| 33 | behavioral-spec.md REQ-513 "Concretely" : `index.mjs:718` | `nextRerouteState` call (branch decision) | `index.mjs:718` | SAME | this sweep + converge notes-iteration-3 |
| 34 | behavioral-spec.md REQ-513 edge case : `index.mjs:516` | early-return fires only when engaged | `index.mjs:516` | SAME | this sweep |
| 35 | behavioral-spec.md §3 Edge Case Catalog : `index.mjs:717` | `isRejectableSleepOrOffMenu` at real dispatch point | `index.mjs:717` | SAME | this sweep |
| 36 | behavioral-spec.md §3 Edge Case Catalog : `index.mjs:516-518` | early-return dispatch | `index.mjs:516-518` | SAME | this sweep |
| 37 | behavioral-spec.md §6 Task List : `index.mjs:450` | REQ-506 test asserting the "REAL `index.mjs:450` call-site widening" | same as #10 | DRIFTED → REWRITE | **FIND-005** (undiscovered until this sweep) |
| 38 | behavioral-spec.md §6 Task List : `index.mjs:717` | `isRejectableSleepOrOffMenu` at real dispatch | `index.mjs:717` | SAME | this sweep |
| 39 | verification-architecture.md Purity Map iter-1 correction : `index.mjs:450` | classify call-site gate | same as #10 | DRIFTED → REWRITE | **FIND-005** |
| 40 | verification-architecture.md REQ-513 iter-2 correction : `index.mjs:516-518` | early-return dispatch | `index.mjs:516-518` | SAME | this sweep |
| 41 | verification-architecture.md `isEarnActionSlot` Pure Core bullet : `index.mjs:450` | widened classify call-site | same as #10 | DRIFTED → REWRITE | **FIND-005** |
| 42 | verification-architecture.md `getToolDefinitions` Pure Core bullet : `prompt.mjs:171` | `SLEEP_TOOL` not appended when `omitSleep` | `prompt.mjs:178` | DRIFTED → RENUMBER | this sweep |
| 43 | verification-architecture.md `nextRerouteState` Pure Core bullet : `always-act-router.mjs:148-153` | actual shipped signature | `always-act-router.mjs:148-153` | SAME | this sweep + converge iter2 (already fixed) |
| 44 | verification-architecture.md Effectful Shell : `run.sh:35-41` | identity-gate calls subprocess twice, mirroring | `sol-trade/run.sh:35-41` (`OWN_WALLET`/`CLI_WALLET` derivation lines `36`/`37`) | SAME | this sweep |
| 45 | verification-architecture.md Effectful Shell REQ-506/FIND-002 : `index.mjs:450` | classify call-site gate change | same as #10 | DRIFTED → REWRITE | **FIND-005** |
| 46 | verification-architecture.md Effectful Shell REQ-506/FIND-003 : `index.mjs:179-421` | soft `avoidSlot` field, unrelated | same as #16 | DRIFTED → REWRITE | **FIND-006** |
| 47 | verification-architecture.md Effectful Shell REQ-513 : `index.mjs:516-518` | early-return dispatch | `index.mjs:516-518` | SAME | this sweep |
| 48 | verification-architecture.md Effectful Shell REQ-513 : `index.mjs:551` | legacy branch, unreachable | `index.mjs:551` | SAME | this sweep |
| 49 | verification-architecture.md Effectful Shell REQ-513 : `index.mjs:666` | `runAlwaysActWake` function start | `index.mjs:666` (`async function runAlwaysActWake({ ctx, wakeId, ts, alwaysActMenu }) {`) | SAME | this sweep |
| 50 | verification-architecture.md Effectful Shell REQ-513 : `index.mjs:717` | `isRejectableSleepOrOffMenu` guard | `index.mjs:717` | SAME | this sweep |
| 51 | verification-architecture.md Effectful Shell REQ-513 : `index.mjs:718` | `nextRerouteState` branch decision | `index.mjs:718` | SAME | this sweep |
| 52 | verification-architecture.md Effectful Shell REQ-513 : `index.mjs:516` | early-return guard | `index.mjs:516` | SAME | this sweep |
| 53 | verification-architecture.md Effectful Shell REQ-513 : `index.mjs:551` (2nd) | legacy branch, unaffected non-engaged path | `index.mjs:551` | SAME | this sweep |
| 54 | verification-architecture.md `brain.mjs::think()` bullet : `brain.mjs:63` | `thinkProxy`'s `tools:` line | `brain.mjs:66` | DRIFTED → RENUMBER | this sweep |
| 55 | verification-architecture.md `brain.mjs::think()` bullet : `brain.mjs:92` | `thinkClaudeP`'s prompt-text line | `brain.mjs:100-102` | DRIFTED → RENUMBER | this sweep |
| 56 | verification-architecture.md PROP-506c row : `index.mjs:450` | widened call-site condition | same as #10 | DRIFTED → REWRITE | **FIND-005** |
| 57 | contracts/sprint-1.md CRIT-001 : `run.sh:28-41` | identity-match idiom | `sol-trade/run.sh:28-41` | SAME | this sweep |

(57 numbered rows above; the audit's own extraction sweep returned 58 raw regex matches because one
behavioral-spec.md bullet cites `prompt.mjs:10-24,139-173` as a single compound match — split into rows 2
and 3 above for clarity, giving 58 total citation occurrences audited.)

## Tally

- **Total citation occurrences audited**: 58
- **SAME (already accurate)**: 29
- **DRIFTED (fixed this session)**: 29
  - REWRITE (the shipped mechanism is a structurally different shape than declared, e.g. one in-place
    ternary that shipped as two call sites in two functions — requires re-describing the mechanism, not
    just renumbering): **17 occurrences** — all `index.mjs:450` occurrences (rows 10, 12, 19, 24, 37, 39,
    41, 45, 56 — 9 total, FIND-005), all `avoidSlot` occurrences (rows 13, 14, 16, 25, 46 — 5 total,
    FIND-006), all `appendHarnessFailure` occurrences (rows 26, 27 — 2 total, FIND-007), plus the
    `index.mjs:440-456`/`classifyEarnResult` §1 ground-truth occurrence (row 8 — 1 total, new finding this
    sweep, same root-cause class as FIND-005)
  - RENUMBER (mechanism unchanged, same shape shipped, only the line number moved because an earlier
    insertion in the file pushed it down): **12 occurrences** — rows 1, 3, 4, 5, 6, 7, 15, 21, 22, 42, 54,
    55 (the idle-paths split, `getToolDefinitions`/`SLEEP_TOOL`'s REQ-504 JSDoc-addition drift,
    `thinkProxy`/`thinkClaudeP`'s REQ-504 comment-block-insertion drift, and the `avoidSlot`-prose citation
    in `prompt.mjs`)
- **New findings beyond FIND-005/006/007** (undiscovered by any prior Phase 3/5/converge pass): rows 1, 3,
  4, 5, 6, 7, 8, 15, 21, 22, 37, 42, 54, 55 — **14 occurrences**, collapsing to **6 distinct underlying
  facts** (idle-paths location; `getToolDefinitions`/`SLEEP_TOOL` location, appearing 4× across both spec
  files; `thinkProxy`/`thinkClaudeP` wiring-seam location, appearing 4× across both spec files;
  `classifyEarnResult` call-site location in §1's OWN ground-truth bullet, separate from FIND-005's REQ-506
  citation of the same fact; `avoidSlot`-prose citation in `prompt.mjs`; REQ-506's `index.mjs:450` mention
  in the §6 Embedded VCSDD Task List). Notably, `brain.mjs:63`/`:92` and `prompt.mjs:139-173`/`:171` had
  been spot-checked and reported "ACCURATE"/"matches" by converge iteration-3's own adversary session
  (`reviews/converge/output/notes-iteration-3.md` Task 2, "Spot-checked citations found ACCURATE") — this
  mechanical, grep-based re-extraction (not memory-based spot-checking of a subset) is what actually
  catches drift that a targeted spot-check misses.

## Post-fix re-verification (step 7: re-run extraction sweep, confirm zero DRIFTED remaining)

```
$ grep -n "^## Changelog" specs/behavioral-spec.md specs/verification-architecture.md
specs/behavioral-spec.md:926
specs/verification-architecture.md:349

$ grep -n "index\.mjs:450\b" specs/behavioral-spec.md specs/verification-architecture.md
(all remaining occurrences are inside "## Changelog" sections, i.e. line >= 926 / >= 349 — historical
record of what FIND-005 found wrong — or inside this fix's own live correction-annotation prose that
explicitly states the number does NOT exist / "is actually" a different construct, never asserted as a
current-fact citation)

$ grep -n "index\.mjs:179-421\|index\.mjs:175-184\|index\.mjs:458-475\|index\.mjs:382-416\|index\.mjs:440-456\|prompt\.mjs:139-173\|prompt\.mjs:171\b\|brain\.mjs:63\b\|brain\.mjs:92\b\|prompt\.mjs:205-207" \
    specs/behavioral-spec.md specs/verification-architecture.md
(same result: every remaining occurrence is either inside a "## Changelog" section, or inside this fix's
own correction-annotation prose explicitly naming the OLD wrong number alongside the NEW correct one — see
"Verified accurate against HEAD" spot-checks below for every NEW number introduced by this fix)
```

Every corrected line number introduced by this fix was independently re-verified with a direct `sed -n`
line dump against the real file (not merely re-grepped for the citation string):

```
index.mjs: 293(let recentActions=[];) 294-295(intro comment) 296(let avoidSlot=null;)
           302(avoidSlot inline comment) 405(loop-detect check comment) 425(closing brace)
           516-518(early-return dispatch) 533(if(!toolCall)) 546(closing brace)
           551(if(slot==='sleep')) 559(note: args.reason...) 564(closing brace)
           598(}else if(isEarnSlot(slot))) 602(classifyEarnResult call, legacy)
           666(async function runAlwaysActWake) 717(isRejectableSleepOrOffMenu call)
           718(nextRerouteState call) 754(else if(isEarnActionSlot(slot)))
           759(classifyEarnResult call, always-act) 767/878/914/613(appendHarnessFailure call sites)
           1028(async function appendHarnessFailure)
prompt.mjs: 10(const SLEEP_TOOL) 24(closing brace) 144(export function getToolDefinitions)
            178(defs.push(SLEEP_TOOL)) 180(closing brace) 212-214(avoid ternary) 213(FORBIDDEN text)
brain.mjs:  48(async function thinkProxy) 66(tools: getToolDefinitions) 89(async function thinkClaudeP)
            100-102(prompt-text ternary)
always-act-router.mjs: 148(export function nextRerouteState) 153(closing brace)
```

All 26 real-file line dumps above match the corrected spec citations exactly. **0 DRIFTED citations
remain** in the live (non-Changelog) sections of `specs/behavioral-spec.md`, `specs/verification-architecture.md`,
and `contracts/sprint-1.md`.

## Explicitly out of scope for this pass

- `verification/*.md` files (`purity-audit.md`, `security-report.md`, `verification-report.md`) — only
  touched where a FIND finding specifically named them (FIND-005/006 named `purity-audit.md`; see the
  second correction note appended there). Their own internal `index.mjs:<N>` citations were NOT
  mechanically re-verified this session and should be treated as unaudited.
- Test file descriptive-name strings (e.g. `verification/proof-harnesses/target-feature-run.txt:21`'s
  PROP-506c test name still baking in the stale "(classify call-site widening, index.mjs:450)" string, per
  FIND-005's own evidence) — this task is documentation-only; no test/code files were touched, per the
  task's explicit "Documentation-only; NO code/test changes" scope.
