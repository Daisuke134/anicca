# Phase 3 implementation review — franklin-alwaysact-skill-router — iteration 1

Fresh-context adversary review. Reviewed commits 6539394 (GREEN) + 939f3da (refactor) on
`feature/franklin-alwaysact-skill-router` in worktree `/Users/operator/anicca/.worktrees/alwaysact-impl`.

## Tool constraint (disclosed, not hidden)

This adversary session's available tools were Read/Write/Edit/Grep/Glob only -- no Bash/shell tool was
provided, so `git diff origin/main...HEAD --stat`, `git diff 826c7f6..HEAD`, and `node --test` could not
be executed directly as the review manifest instructed. Every finding below is grounded instead in:
- Full-file `Read` of every implementation file in scope (index.mjs, always-act-router.mjs, brain.mjs,
  prompt.mjs, context.mjs, catalog-gate.mjs, skills/_shared/lib/ledger.mjs) and every new/changed test
  file (all 4 always-act-*.test.mjs files + the shared harness helper), line-cited throughout.
- Repo-wide `Grep` sweeps used as a substitute for `git diff --stat` scope-boundary checks (e.g. searching
  `skills/` for any franklin-alwaysact reference, searching the whole repo for `router_menu_empty` and
  `always_act_go_live` to confirm zero production writer sites).
- Line-by-line tracing of `runAlwaysActWake()`'s control flow against every row of behavioral-spec.md
  sec2.5's 12-row attempt-state transition matrix and against every PROP-ID in verification-architecture.md.

Builder-reported test counts (53 new + 212 pre-existing = 265/265, `evidence/green-phase.md`) were **not**
independently re-executed by this adversary and should not be treated as adversary-confirmed until a
review pass with real command execution happens. This does not change the two findings below, which are
about code/spec/test-coverage gaps that exist regardless of whether the reported suite passes.

## Blocking findings (2)

1. **FIND-001 (spec_fidelity / implementation_correctness / verification_readiness, critical)**:
   REQ-502's empty-menu edge case requires a `kind:'router_menu_empty'` ledger line, distinguishable from
   the ordinary bounds-exhausted `kind:'router_no_realized_action'` escalation. The implementation's single
   `writeAlwaysActEscalation()` helper (index.mjs:847-866) hardcodes `router_no_realized_action`
   unconditionally for all three escalation triggers (empty menu, empty reroute-target set, bounds
   exhausted). `router_menu_empty` is never written anywhere in the codebase. The test that claims to cover
   PROP-502d only checks the pure `assembleAlwaysActMenu` return value, never the real ledger kind a live
   empty-menu wake would produce -- a tautological-coverage gap that would pass even with today's defect.

2. **FIND-002 (spec_fidelity / edge_case_coverage, critical)**: REQ-512's second observability half -- a
   one-time operational "go-live" action appending `kind:'always_act_go_live'` -- is entirely unimplemented
   and untested. This was explicitly flagged during spec review (`reviews/spec/iteration-2/output/notes.md`
   observation #2), which recommended Phase 2a build a small, unit-tested `recordGoLive()`-style function.
   Neither Phase 2a nor Phase 2b did this. `isPostGoLiveRegression`'s consumer-side detector (the actual
   REQ-512 regression-catching mechanism) can therefore never fire in production, because nothing ever
   writes the `always_act_go_live` anchor line it depends on. The `always_act_go_live` string only appears
   as a synthetic literal inside `isPostGoLiveRegression`'s own unit-test fixtures, never as output of a
   real production code path.

## Process observation (not one of the 5 binary dimensions, reported for the state-machine owner)

`state.json` declares `"mode": "strict"` and the feature's own Embedded VCSDD Task List (behavioral-spec.md
sec6, item 7) requires a `contracts/sprint-1.md` mapping CRIT-* criteria to REQ-501..513 to be authored
*before* Phase 3 adversarial review. No such file exists anywhere under
`.vcsdd/features/franklin-alwaysact-skill-router/` (confirmed via Glob). This review therefore proceeded
directly against `behavioral-spec.md`/`verification-architecture.md` per the explicit task instructions
given to this adversary, but the strict-mode contract gate itself remains unsatisfied independent of the
two findings above.

## Positive evidence (dimensions that passed)

- **Money safety (REQ-509)**: Grep across `skills/` for any franklin-alwaysact/alwaysAct/ALWAYS_ACT
  reference returned zero hits. `catalog-gate.mjs` read in full: `DEFAULT_BOOTSTRAP_RESERVE_USDC` constant
  and `filterCatalog`/`hasOpenRiskPositionOf*` logic are byte-identical to their documented pre-existing
  contract, with no franklin-alwaysact markers. No evidence of any touch to
  `skills/earn/*/run.sh`, `skills/earn/*/lib/resolve-max-spend.sh`, or `skills/_shared/lib/earn-guard.mjs`.
- **The two uninstructed production additions called out in the review manifest**:
  - `looksLikeFranklinHome(home)` (index.mjs:223-225) is a strict-equality fast path
    (`ANICCA_HOME === path.join(home,'.blockrun')`) that only ever short-circuits to "definitely not
    Franklin" (`return false`) for instances that fail it; it never grants engagement by itself -- a home
    that DOES match still falls through to the full real subprocess wallet-derivation check
    (`checkAlwaysActIdentity`'s `match` computation). Traced and confirmed this cannot weaken the identity
    guard or misclassify a non-Franklin instance as Franklin; it is a legitimate performance-only
    optimization, not a money-safety regression.
  - The 500ms `ALWAYS_ACT_IDENTITY_SETTLE_FLOOR_MS` floor (index.mjs:234) only adds latency to wakes that
    already passed the fast path (i.e. only Franklin's own body pays it), is negligible against the 120s
    default `SLEEP_BASE_S` cadence, and does not alter the identity-match boolean outcome. Not a
    money-safety or correctness concern; a reasonable, well-documented engineering addition beyond the
    spec's letter but consistent with its intent.
- **Test-fixture faithfulness**: `writeMockEarnSkill`'s `profitable:true` fixture line was cross-checked
  against the REAL, unmodified `skills/_shared/lib/ledger.mjs::isProfitable` contract (net_usdc>0,
  external:true, sig+confirmed:true for the Solana path) and matches it exactly -- the state.json-claimed
  "fixture fix" genuinely tightened the fixture to match production truth; it was not loosened to make a
  test pass.
- **REQ-513/REQ-506 dispatch-guard wiring**: `isRejectableSleepOrOffMenu` is invoked against the retry
  loop's own per-attempt `currentOfferedSlots` local variable (never the static `ctx.alwaysActMenu`) at
  both the baseline-reject and reroute-reject call sites; branch selection is keyed exclusively on the
  `attemptsUsed` local variable, never on array identity -- matches the FIND-301 spec-review fix precisely.
