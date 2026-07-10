# Phase 3 implementation review — franklin-alwaysact-skill-router — iteration 2

Fresh-context adversary review, zero builder context. Reviewed commit 706e8fcb on
`feature/franklin-alwaysact-skill-router` in worktree `/Users/anicca/anicca/.worktrees/alwaysact-impl`.
No Bash tool was available this session; test execution (182/182 pass) was independently performed by
the launching thinker and is treated as externally verified per the task instructions. This review is
grounded entirely in `Read`/`Grep`/`Glob` over the real source and test files, with every finding citing
a concrete file:line.

## Tool-failure hook note (disclosed)

A `PostToolUse:Write` hook fired after this session's `Write` calls stating "fablize gate observed a tool
failure. Do not report completion until it is fixed, isolated as a known baseline, or explicitly
documented." Every `Write` invocation in this session returned "File created successfully" with no error
surfaced to this adversary, and this adversary has no Bash/shell tool to independently investigate the
underlying fablize gate. This observation is disclosed here rather than hidden; it does not originate from
or relate to any of the code/spec findings below, all of which are grounded in direct `Read`/`Grep`
evidence of the reviewed commit's actual content.

## Iteration-1 findings: both genuinely resolved

**FIND-001 (empty-menu `kind:'router_menu_empty'`)**: Confirmed resolved. `writeAlwaysActEscalation`
(index.mjs:863) now takes a `kind` parameter defaulting to `'router_no_realized_action'`; only the
REQ-502 empty-menu terminal guard (index.mjs:673-676) passes `kind: 'router_menu_empty'` explicitly —
every other call site (bounds-exhausted after no-tool-call/rejected-slot, empty-reroute-target-set) is
unchanged from the default, confirmed by reading all four call sites. The fix's own regression test,
PROP-502d (always-act-reroute.test.mjs:437-451), is a genuine, non-tautological, spawn-based integration
test: it uses the new `ALWAYS_ACT_REGISTRY_PATH_OVERRIDE` seam to point a REAL spawned `index.mjs` child
process at a well-formed, zero-live-slot fixture registry, and asserts the ACTUAL ledger line written by
the live wake — not merely the pure `assembleAlwaysActMenu([])` return value iteration-1 flagged as
tautological.

**FIND-002 (REQ-512's go-live producer)**: Confirmed resolved, and confirmed to match the SPEC's actual
requirement (not merely the fix's convenience). REQ-512's EARS text literally names the go-live action
"the one-time operational action ... a separate, explicit, logged operational action" (behavioral-spec.md
sec6 item 10) — a standalone CLI script that is never invoked by the wake loop is the correct reading, not
a defect. `go-live.mjs::recordGoLive` is idempotent (`shouldRecordGoLive` scans the real ledger tail for an
existing anchor line before writing), writes the SAME `state/ledger.jsonl` path `index.mjs`'s own
`LEDGER_PATH` resolves to (so `isPostGoLiveRegression` can genuinely observe a real anchor line mixed with
real wake lines in production), and is verified by 4 real tests using real `fs`/tmp files (not fixtures
standing in for the real `recordGoLive` call) — including a dedicated structural test
(`go-live.test.mjs:66-70`) asserting `index.mjs` never imports or calls it.

## New blocking findings (4)

1. **FIND-001 (implementation_correctness/verification_readiness, major, security_surface)**: the
   FIND-001 fix's own testability seam, `ALWAYS_ACT_REGISTRY_PATH_OVERRIDE`, is read unconditionally in
   production code with no test-mode gate and no equivalent to this codebase's own established mitigation
   for this exact backdoor class (`franklin-plist-config.test.mjs`'s deployed-plist-absence check for
   `ANICCA_BALANCE_OVERRIDE`). It governs `riskTagBySlot`, the source of truth for REQ-506's
   money-safety-critical `isMarketRiskFree` reroute filter.

2. **FIND-002 (structural_integrity/verification_readiness, major, spec_gap)**: `contracts/sprint-1.md`'s
   10 CRIT criteria never name REQ-503 or REQ-510, despite behavioral-spec.md's own Embedded VCSDD Task
   List explicitly requiring the contract to map CRIT-* to REQ-501..REQ-513 in full. Both requirements ARE
   implemented and tested (PROP-503a/b, PROP-510a) — only the strict-mode grading contract itself is
   incomplete.

3. **FIND-003 (edge_case_coverage/spec_fidelity, critical, test_coverage)**: REQ-506's own named
   Acceptance Criteria test, PROP-506f ("empty-safe-set-escalates"), does not exist anywhere in the
   62-test suite — confirmed via exhaustive `test(` name enumeration across all 4 always-act-*.test.mjs
   files. This is also the only path that could exercise REQ-510's second literal-domain-pin AC. Manual
   trace of the corresponding code branch (index.mjs:789-795) suggests it is plausibly implemented
   correctly, but this is unverified by any test — the same tautological-coverage failure class iteration-1
   already flagged once this sprint.

4. **FIND-004 (implementation_correctness/edge_case_coverage, critical, test_quality +
   requirement_mismatch)**: PROP-509b's assertion of REQ-509's own stated AC ("the guard-blocked slot's own
   skip record is preserved verbatim in the ledger") is wrapped in an `if` guard
   (`if (skillErrorOrWakeForFirstPick)`) that is provably always false, since `runAlwaysActWake`'s reroute
   branch never writes any ledger line for the just-rerouted-away-from slot, and the guard-blocked-but-exit-0
   outcome classifies as `'clean'` so `appendHarnessFailure` is also never invoked. The assertion never
   executes, and ground truth confirms REQ-509's AC is genuinely unsatisfied: no file records the
   guard-blocked slot's skip reason for that wake.

## Positive evidence (dimensions/areas verified clean)

- **REQ-507 purity/no-judgment**: `always-act-router.mjs` read in full (257 lines) — imports only
  `./earn-slot.mjs`/`./prompt.mjs`, zero I/O imports, zero RegExp/`.match(`/`.test(`/`switch(slot)`-style
  branching over model-chosen content.
- **REQ-504 wiring**: `brain.mjs:63-69` (thinkProxy's `tools:` line) and `brain.mjs:100-102` (thinkClaudeP's
  prompt text) are both genuinely conditional on `ctx.alwaysActEngaged`, matching the spec's concrete
  mechanism exactly; `context.mjs:26-34`'s additive fields default safely for every non-always-act ctx.
- **REQ-501 identity gate**: `checkAlwaysActIdentity`/`envWithoutSolanaKey` (index.mjs:202-269) strips
  `ANICCA_SOLANA_PRIVATE_KEY` before either derivation, mirrors the sol-trade identity-match idiom, and
  fails closed on derivation error/mismatch/malformed flag.
- **REQ-513 dispatch guard**: `isRejectableSleepOrOffMenu(slot, currentOfferedSlots)` is invoked against
  the retry loop's own per-attempt local variable (index.mjs:717), never the static `ctx.alwaysActMenu`;
  branch selection is keyed exclusively on `attemptsUsed`, matching the FIND-301 spec-review fix.
