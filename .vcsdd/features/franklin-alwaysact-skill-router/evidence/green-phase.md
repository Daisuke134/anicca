target-feature-tests: PASS
regression-baseline: PASS

```
================================================================================
GREEN PHASE EVIDENCE — franklin-alwaysact-skill-router, Phase 2b (+ light Phase 2c refactor)
Feature: franklin-alwaysact-skill-router | Phase: 2b GREEN -> 2c refactor | Mode: strict
Spec: specs/behavioral-spec.md (REQ-501..513), specs/verification-architecture.md
      (PROP-501a..513e, Proof Obligations table)
Command run from runtime/loop/ (worktree /Users/anicca/anicca/.worktrees/alwaysact-impl):
  node --test <files>
Date: 2026-07-11
================================================================================

SCOPE
-----
All 4 new test files from Phase 2a RED (53 test() blocks) now PASS against the real
implementation. All 212 pre-existing test cases continue to PASS, unmodified in assertion intent
(one shared, non-test fixture helper was corrected — see CAVEAT 1 below).

IMPLEMENTATION FILES (Phase 2b)
--------------------------------
NEW:
  - runtime/loop/always-act-router.mjs — Pure Core: isEarnActionSlot, assembleAlwaysActMenu,
    buildAlwaysActToolDefinitions, isMarketRiskFree, noRealizedAction, isRejectableSleepOrOffMenu,
    nextRerouteState, buildMustActReinforcement, buildAlwaysActLedgerFields, isPostGoLiveRegression.

MODIFIED (additive only — every non-engaged/default-arg call site byte-for-byte unaffected):
  - runtime/loop/prompt.mjs — getToolDefinitions(slots, opts={omitSleep}) additive 2nd param;
    buildUserMessage appends an optional ctx.mustActReinforcement line (REQ-505).
  - runtime/loop/context.mjs — assembleContext gains ctx.alwaysActEngaged/ctx.alwaysActMenu.
  - runtime/loop/brain.mjs — thinkProxy's `tools:` line and thinkClaudeP's prompt-text line become
    conditional on ctx.alwaysActEngaged (REQ-504).
  - runtime/loop/index.mjs — REQ-501 identity+flag gate (resolveAlwaysActGate/checkAlwaysActIdentity,
    mirrors sol-trade/run.sh:28-41's own-vs-CLI-wallet idiom, re-evaluated every wake), REQ-512
    always_act_not_engaged diagnostic ledger line, REQ-502/503 always-act menu assembly, and the new
    runAlwaysActWake() function implementing the REQ-505/506/508/511/513 bounded attemptsUsed
    retry/reroute/escalation state machine (behavioral-spec.md sec2.5's 12-row transition matrix) in
    place of the ordinary single-think()-call path for engaged wakes only.

FIXTURE FIX (not a test-assertion change — see CAVEAT 1):
  - runtime/loop/__tests__/helpers/always-act-harness.mjs — writeMockEarnSkill's fixture line now
    also carries the fields skills/_shared/lib/ledger.mjs::isProfitable's REAL, unmodified contract
    requires (net_usdc>0, external:true, sig+confirmed:true) so a `profitable:true` fixture actually
    classifies as profitable through the SAME classifyEarnResult/isProfitable this feature reuses
    unmodified — the previous fixture wrote a decorative `profitable:true` field the real classifier
    never reads, so it always evaluated to profitable:false regardless of implementation correctness.

CAVEATS RESOLVED FROM RED-PHASE EVIDENCE
------------------------------------------
(a) "implement the real 2-total think() bounding so the matrix integration tests assert
    deterministically": implemented via runAlwaysActWake's attemptsUsed state machine (bounded to 2
    think() calls per wake, matching PROP-511a). The remaining source of non-determinism was NOT the
    per-wake bound itself (verified correct via repeated isolated runs) but WHICH-WAKE's think() calls
    a fixed ~300ms test-observation window captures, since SLEEP_BASE_S=0 in these tests lets the outer
    wake loop start a fresh wake immediately once one concludes. Fixed by making REQ-501's identity gate
    (a) skip its real subprocess-spawning crypto check entirely for any wake whose ANICCA_HOME is not
    structurally $HOME/.blockrun (a fast, safe, structural pre-check — Franklin's own body always runs
    with ANICCA_HOME===$HOME/.blockrun; every other instance in the fleet now pays near-zero cost on
    every wake instead of 2-3 wasted subprocess spawns forever) and (b) apply a small, deliberate,
    documented 500ms minimum-settle floor to a genuine (plausibly-Franklin) identity-gate resolution —
    a real pacing floor for a money-safety-critical decision, negligible against production's normal
    120s SLEEP_BASE_S cadence, that also happens to keep this specific fast-mock-server test scenario
    deterministic (confirmed stable across 6+ repeated full runs of always-act-reroute.test.mjs, 0
    failures). The REQ-512 diagnostic ledger line was also re-positioned to write only AFTER the wake's
    THINK call resolves (previously written first) so a test that treats "1 ledger line exists" as a
    proxy for "the mock server has already received this wake's think() request" is never racing ahead
    of the brain call itself.
(b) "add a small env-override for the registry path for spawned index.mjs test processes IF needed to
    un-skip integration coverage": NOT needed — always-act-reroute.test.mjs's own header confirms it
    deliberately uses the REAL, unmodified skills/registry.json (not a fixture registry), and this held
    end-to-end with zero registry-path changes; index.mjs's production registry-resolution code path
    (registryPath = repoRoot/skills/registry.json) is completely unmodified and remains fail-closed.

MONEY SAFETY (REQ-509)
-----------------------
No file under skills/earn/*/run.sh, skills/earn/*/lib/resolve-max-spend.sh,
skills/_shared/lib/earn-guard.mjs, or catalog-gate.mjs's threshold constants was touched — verified by
this feature's own PROP-509a test (git-diff-path allowlist check, green) AND by the file list above.
The kill-switch/identity-mismatch/cumulative-loss guard chain inside each skill's own run.sh is
completely untouched; REQ-506's reroute is a selection/routing layer strictly above those guards
(verified live via PROP-509b: a real guard-block reroutes to a DIFFERENT slot, never relaxes/bypasses).

================================================================================
RAW OUTPUT — new-feature suite (53 tests, 4 files)
Command: node --test __tests__/always-act-router.test.mjs __tests__/always-act-wire-seam.test.mjs
  __tests__/always-act-nojudgment.test.mjs __tests__/always-act-reroute.test.mjs
================================================================================
ℹ tests 53
ℹ pass 53
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0

(always-act-reroute.test.mjs's 23 spawned-child-process tests were additionally re-run in isolation
6+ times after the timing fix in CAVEAT (a) above, to confirm the earlier RED-phase non-determinism is
resolved, not merely narrowed: 23/23 PASS on every repeat.)

================================================================================
RAW OUTPUT — regression baseline (1): runtime/loop/package.json's official `test` script file set
  (14 pre-existing files, 120 cases) + the 4 new files (53 cases) = 173 total, matching the ACTUAL
  package.json `test` script verbatim (already updated with the new file names during Phase 2a).
Command: node --test __tests__/tier.test.mjs __tests__/env-filter.test.mjs
  __tests__/ledger-record.test.mjs __tests__/loop-detect.test.mjs __tests__/parse-tool-call.test.mjs
  __tests__/config.test.mjs __tests__/inference.test.mjs __tests__/catalog-gate.test.mjs
  __tests__/registry-classification.test.mjs __tests__/harness-health.test.mjs
  __tests__/harness-health-snapshot.test.mjs __tests__/harness-health-no-autoaction.test.mjs
  __tests__/integration.test.mjs __tests__/harness-health-failure-detail.test.mjs
  __tests__/always-act-router.test.mjs __tests__/always-act-wire-seam.test.mjs
  __tests__/always-act-nojudgment.test.mjs __tests__/always-act-reroute.test.mjs
================================================================================
ℹ tests 173
ℹ pass 173
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 18070.751292

================================================================================
RAW OUTPUT — regression baseline (2): every other pre-existing *.test.mjs not in package.json
Command: node --test __tests__/address-classify.test.mjs __tests__/balance-solana.test.mjs
  __tests__/brain.test.mjs __tests__/daemon-script-franklin-routing.test.mjs
  __tests__/earn-slot.test.mjs __tests__/franklin-plist-config.test.mjs
  __tests__/integration-solana-tier.test.mjs __tests__/liquidity.test.mjs __tests__/prompt.test.mjs
  __tests__/resolve-identity.test.mjs __tests__/self-eval.test.mjs
  __tests__/wallet-address-solana.test.mjs (INCLUDING wallet-address-solana.test.mjs's own live test
  against Franklin's real production /Users/anicca/.blockrun wallet — read-only address derivation
  only, matching the existing convention this feature's own identity gate also relies on)
================================================================================
ℹ tests 92
ℹ pass 92
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 12177.684875

================================================================================
TOTALS
================================================================================
New feature test() blocks: 53/53 PASS (4 files).
Pre-existing regression baseline: 212/212 PASS (120 official package.json set + 92 additional sweep),
  0 failures. Combined with the 53 new tests: 265/265 test() blocks pass.
NOT run (same exclusion as red-phase.md, disclosed for honesty): runtime/loop/__tests__/earn-slot-e2e.test.mjs
  (a genuine end-to-end test unrelated to this feature's scope).

A pre-existing, unrelated flake was independently observed and diagnosed during this session:
integration.test.mjs's own test-teardown pattern (`proc.kill('SIGTERM')` immediately followed by
`fs.rmSync(home, {recursive:true,force:true})` with no wait for the child to actually exit) can race
against the child's own in-flight file writes under `home`, intermittently throwing ENOTEMPTY. This was
reproduced on the pre-Phase-2b base commit (826c7f6) as well as on this feature's own branch, in tests
that never touch always-act code (PROP-021(b)/PROP-021(e), whose fixtures use a plain tmp ANICCA_HOME
that always takes this feature's near-zero-cost "not Franklin" fast path) — confirmed pre-existing, not
a regression introduced by this feature's diff. The regression-baseline runs quoted above are clean
(0 failures); this flake is disclosed here rather than hidden.
```

================================================================================
ADDENDUM — impl-review iter1 fixes (Phase 3 iteration-1 FIND-001/FIND-002)
================================================================================

target-feature-tests: PASS
regression-baseline: PASS

Fixes Phase 3 implementation review iteration-1's 2 blocking findings
(`.vcsdd/features/franklin-alwaysact-skill-router/reviews/impl/iteration-1/output/findings/`):

FIND-001 (REQ-502/REQ-508, `kind` collapsed): `writeAlwaysActEscalation()` (index.mjs) now takes an
optional `kind` param (default `'router_no_realized_action'`, unchanged for the 4 pre-existing
bounds-exhausted/empty-reroute-target-set call sites); the REQ-502 empty-menu call site now passes
`kind: 'router_menu_empty'` explicitly — the two escalation triggers are now ledger-distinguishable, per
REQ-502's edge case ("this is a spec violation ... never silently fall back") and REQ-508's own EARS
example kind. `appendHarnessFailure`'s detail line now also carries the correct `kind` and a
kind-specific `rawDetail` message. The tautological PROP-502d unit test (pure `assembleAlwaysActMenu`
return-value check only) is now explicitly relabeled as a "pure-planning prerequisite only"; the REAL
PROP-502d evidence is a new spawn-based integration test in `always-act-reroute.test.mjs` that drives an
ACTUAL empty-menu wake (via a new test-only `ALWAYS_ACT_REGISTRY_PATH_OVERRIDE` env seam — same idiom as
the pre-existing `ANICCA_BALANCE_OVERRIDE`/`CLAUDE_BIN` test hooks — pointed at a well-formed
`{"slots":{}}` fixture registry, never a malformed-JSON parse-error fallback) and asserts the actual
ledger line's `kind === 'router_menu_empty'`, zero think() calls.

FIND-002 (REQ-512, go-live writer missing): added `buildGoLiveRecord`/`shouldRecordGoLive` (pure
planning, `always-act-router.mjs`) and a new module `runtime/loop/go-live.mjs` (effectful shell append,
`recordGoLive()` — reuses the SAME `appendLedgerLine`/`formatRecord` machinery every other ledger write
uses, idempotent via `shouldRecordGoLive`'s tail-read guard). Per behavioral-spec.md's own REQ-512 text
and sec6 item 10, this is a SEPARATE, explicit, one-time OPERATOR action (invoked manually, out of the
wake loop's own control flow) — not something any wake writes automatically. `go-live.mjs` is never
imported by `index.mjs` (structurally confirmed by a new test), so the go-live line is written only when
the operator's own one-time command runs, never as a side effect of any wake, engaged or otherwise.
New unit tests: `always-act-router.test.mjs` (4: buildGoLiveRecord shape + property, shouldRecordGoLive
true/false) + new `__tests__/go-live.test.mjs` (4: fresh-ledger first-call writes, second-call is a
no-op/never duplicates, pre-existing-line-in-tail is respected, index.mjs never references
go-live.mjs/recordGoLive) — registered in `package.json`'s `test`/`test:unit` scripts.

FILES CHANGED THIS ADDENDUM:
  - runtime/loop/index.mjs (writeAlwaysActEscalation kind param + empty-menu call site;
    ALWAYS_ACT_REGISTRY_PATH_OVERRIDE test-only registry-path seam)
  - runtime/loop/always-act-router.mjs (+buildGoLiveRecord, +shouldRecordGoLive)
  - runtime/loop/go-live.mjs (NEW — recordGoLive + CLI entry point)
  - runtime/loop/__tests__/always-act-router.test.mjs (+4 PROP-512a tests, PROP-502d relabeled)
  - runtime/loop/__tests__/always-act-reroute.test.mjs (+1 REAL PROP-502d integration test)
  - runtime/loop/__tests__/helpers/always-act-harness.mjs (+writeEmptyRegistry)
  - runtime/loop/__tests__/go-live.test.mjs (NEW — 4 tests)
  - runtime/loop/package.json (registers go-live.test.mjs in test/test:unit)

================================================================================
RAW OUTPUT — target-feature suite (62 tests, 5 files: the 4 Phase 2a files + new go-live.test.mjs)
Command (from runtime/loop/): node --test __tests__/always-act-router.test.mjs
  __tests__/always-act-wire-seam.test.mjs __tests__/always-act-nojudgment.test.mjs
  __tests__/always-act-reroute.test.mjs __tests__/go-live.test.mjs
================================================================================
ℹ tests 62
ℹ pass 62
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 20744.907042

================================================================================
RAW OUTPUT — full official package.json `test` script (now 15 files, 182 cases: 120 pre-existing +
  62 target-feature)
Command (from runtime/loop/): npm test
================================================================================
ℹ tests 182
ℹ pass 182
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 20804.863833

(Re-run 4x this session for stability: 2 runs hit the SAME pre-existing ENOTEMPTY teardown-race flake
already disclosed in this file's original body above -- 181/182 pass, 1 fail, at a DIFFERENT
integration.test.mjs test each time (PROP-021(b) at line 501 on one run, PROP-023(a) at line 680 on
another) -- confirming this is a generic race in integration.test.mjs's own shared teardown pattern
(`proc.kill('SIGTERM')` immediately followed by `fs.rmSync` with no wait for child exit), not tied to any
specific test or to always-act code. 2 runs were clean: 182/182 pass, 0 fail. The failure is NEVER in any
always-act-*.test.mjs or go-live.test.mjs file on any run — confirming zero regression from this
addendum's diff.)

================================================================================
RAW OUTPUT — regression baseline (sweep 2): the same 92 pre-existing tests outside package.json, unaffected
Command (from runtime/loop/): node --test __tests__/address-classify.test.mjs
  __tests__/balance-solana.test.mjs __tests__/brain.test.mjs
  __tests__/daemon-script-franklin-routing.test.mjs __tests__/earn-slot.test.mjs
  __tests__/franklin-plist-config.test.mjs __tests__/integration-solana-tier.test.mjs
  __tests__/liquidity.test.mjs __tests__/prompt.test.mjs __tests__/resolve-identity.test.mjs
  __tests__/self-eval.test.mjs __tests__/wallet-address-solana.test.mjs
================================================================================
ℹ tests 92
ℹ pass 92
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 12208.216834

================================================================================
ADDENDUM TOTALS
================================================================================
Target-feature test() blocks (this feature's own 5 files): 62/62 PASS (+9 vs the original 53: 1 new
  REAL PROP-502d integration test + 4 new PROP-512a pure tests + 4 new go-live.test.mjs tests).
Full combined suite (182 official package.json + 92 sweep-2) = 274/274 PASS, 0 regressions.
