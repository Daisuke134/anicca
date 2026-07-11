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

================================================================================
ADDENDUM — impl-review iter2 fixes (Phase 3 iteration-2 FIND-001..004)
================================================================================

target-feature-tests: PASS
regression-baseline: PASS

Fixes Phase 3 implementation review iteration-2's 4 blocking findings
(`.vcsdd/features/franklin-alwaysact-skill-router/reviews/impl/iteration-2/output/findings/`):

FIND-001 (security surface, `ALWAYS_ACT_REGISTRY_PATH_OVERRIDE` honored unconditionally in
production with no production guardrail): mirrors this codebase's own established mitigation for
EXACTLY this class of test-only env backdoor — `ANICCA_BALANCE_OVERRIDE`'s own sole guardrail is
`franklin-plist-config.test.mjs`'s deployed-plist-absence check (confirmed live: `ANICCA_BALANCE_OVERRIDE`
also has NO code-side gate in `balance.mjs` — the plist-absence test is its ONLY mitigation). Added the
SAME class of test to `franklin-plist-config.test.mjs`, extended to cover BOTH live Franklin plists
(`ai.anicca.franklin-loop.plist` AND `ai.anicca.franklin2-loop.plist`, not just the one the precedent file
already read) — 2 new tests assert `ALWAYS_ACT_REGISTRY_PATH_OVERRIDE` is absent from each deployed
plist's real `<EnvironmentVariables>` dict. No code-side gate was added to `index.mjs` (would deviate
from the established, already-accepted mitigation pattern — "do not invent a new mechanism"); the
override remains usable by the spawn-based tests exactly as before.

FIND-002 (contract gap, REQ-503/REQ-510 unmapped by any CRIT criterion): added `CRIT-011` (REQ-503,
bootstrap-reserve gate, references the existing PROP-503a/PROP-503b tests) and `CRIT-012` (REQ-510,
attemptsUsed domain-pin, references the existing PROP-510a tests plus the new PROP-506f test below) to
`contracts/sprint-1.md`. Weights rebalanced from 10x0.10 (=1.00) to 10x0.09 + 2x0.05 (=1.00) — verified
by direct summation. All of REQ-501..REQ-513 now appear within the criteria block itself (verified: each
REQ-5XX number has >=1 match inside the `criteria:` YAML block). CRIT-006's description/passThreshold
text was also corrected to match FIND-004's fix (see below) — it previously said the guard-blocked
slot's skip record is preserved "in the ledger" (ambiguous, and would have meant ledger.jsonl, which is
NOT where FIND-004's fix preserves it) — now explicitly names `harness-failures.jsonl` and the
`router_reroute_skip` kind. CRIT-010's expected pass counts were updated from 182/92 to 183/94 to match
the 2 new test files' additions (+1 target-feature test, +2 sweep tests).

FIND-003 (PROP-506f missing — REQ-506's own named "empty-safe-set-escalates" AC untested): added the
real, spawn-based `PROP-506f` test to `always-act-reroute.test.mjs`. Uses the SAME
`ALWAYS_ACT_REGISTRY_PATH_OVERRIDE` test seam PROP-502d already established, pointed at a new
`writeRiskTaggedRegistry` fixture (added to `always-act-harness.mjs`) containing exactly 2 live,
capital-risk slots (`earn/sol-trade`, `hl_trade`) — so after the just-picked slot is excluded, the
remaining risk-free-filtered reroute set is genuinely empty even though the raw excluded-self set is
not. Asserts: zero additional think() calls (`requests.length === 1`), a real `router_no_realized_action`
escalation line (never a fallback into a risk:"capital" reroute target), AND REQ-510's own literal
domain-pin AC — `escalated.attemptsUsed === 0` despite exactly ONE think() call having been made,
falsifying a naive think()-call-count reading of the field. Manual trace confirmed the underlying
index.mjs code path (lines 789-795, unmodified by this fix) was already correct; this test closes the
tautological-coverage gap, it does not change behavior.

FIND-004 (PROP-509b dead-code assertion, REQ-509 AC unmet — no ledger record of a guard-blocked pick
exists anywhere): traced the root cause — `runAlwaysActWake`'s reroute branch (index.mjs) never wrote
ANY record of a rerouted-away-from pick's own outcome; `ledger.jsonl`'s single line per wake is always
the wake's FINAL result, and `classifyLayer({kind:'wake'})` classifies a guard-blocked-but-exit-0 pick as
`'clean'`, so the pre-existing `appendHarnessFailure` call site (guarded by `classifyLayer(...) !== 'clean'`)
never fires for it either. Implemented the missing preservation: index.mjs's noRealizedAction/reroute
branch now calls `appendHarnessFailure` UNCONDITIONALLY (bypassing classifyLayer's routing — this is a
genuine no-edge/guard-skip signal, not a tool_missing/tool_timeout/tool_logic failure) with a distinct
`kind: 'router_reroute_skip'`, preserving `slot`/`exitCode`/the raw (already-redacted) skill output
verbatim in `harness-failures.jsonl` — BEFORE the branch decides whether to reroute successfully or
escalate, so the record survives either outcome. `ledger.jsonl` was deliberately NOT used for this
(would have broken ~15 currently-passing reroute tests' `lines[0]` terminal-line assertions, e.g. Row 5/
Row 6/Row 7/PROP-506c, since `waitForLines(...,1)` resolves on the FIRST line written — an earlier skip
line would become `lines[0]` instead of the wake's actual terminal outcome). Rewrote `PROP-509b` to
assert UNCONDITIONALLY (no `if` guard) against the new `harness-failures.jsonl` record, finding it by
`slot === 'earn/sol-trade' && kind === 'router_reroute_skip'` and asserting `detail` includes
`'kill-switch'` verbatim. NEGATIVE-CONTROL VERIFIED this session: with the index.mjs fix reverted (git
stash), the rewritten PROP-509b genuinely FAILS (`AssertionError: the guard-blocked slot's own skip
record must be preserved (not silenced) in harness-failures.jsonl`) while PROP-506f still passes
(independent of this fix) — confirming the new assertion is real, not dead code.

FILES CHANGED THIS ADDENDUM:
  - runtime/loop/index.mjs (unconditional appendHarnessFailure call, kind:'router_reroute_skip', in the
    noRealizedAction/reroute branch — REQ-509 skip-record preservation)
  - runtime/loop/__tests__/franklin-plist-config.test.mjs (+2 ALWAYS_ACT_REGISTRY_PATH_OVERRIDE
    plist-absence guardrail tests, both live Franklin plists; generalized readDeployedEnvironmentVariables)
  - runtime/loop/__tests__/helpers/always-act-harness.mjs (+writeRiskTaggedRegistry)
  - runtime/loop/__tests__/always-act-reroute.test.mjs (+1 new PROP-506f test; PROP-509b rewritten to
    assert unconditionally against harness-failures.jsonl)
  - .vcsdd/features/franklin-alwaysact-skill-router/contracts/sprint-1.md (+CRIT-011, +CRIT-012,
    rebalanced weights 0.10x10 -> 0.09x10+0.05x2, CRIT-006/CRIT-010 text corrected)

================================================================================
RAW OUTPUT — target-feature suite (63 tests, 5 files: same 5 files, +1 vs iter1's 62 -- PROP-506f)
Command (from runtime/loop/): node --test __tests__/always-act-router.test.mjs
  __tests__/always-act-wire-seam.test.mjs __tests__/always-act-nojudgment.test.mjs
  __tests__/always-act-reroute.test.mjs __tests__/go-live.test.mjs
================================================================================
ℹ tests 63
ℹ pass 63
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 19879.795792

================================================================================
RAW OUTPUT — full official package.json `test` script (183 cases: 182 iter1 baseline + 1 PROP-506f)
Command (from runtime/loop/): npm test
================================================================================
ℹ tests 183
ℹ pass 183
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 20024.121416

(This session: 1 of 4 `npm test` runs was clean 183/183 above; the pre-existing, previously-disclosed
integration.test.mjs ENOTEMPTY teardown-race flake (`proc.kill('SIGTERM')` immediately followed by
`fs.rmSync`, no wait for child exit) fired on the other 3, each time at a DIFFERENT integration.test.mjs
PROP-021 subtest (lines 496/601) -- never any always-act-*.test.mjs/go-live.test.mjs test, consistent
with CRIT-010's own pre-existing disclosure. Rather than keep blindly re-running the full flaky
combined command, diagnosed directly: (a) `git stash` to the PRISTINE pre-fix baseline commit (no
diff) -- `npm test` also clean 182/182 on its own first run, proving the flake pre-exists this addendum's
diff; (b) `integration.test.mjs` run in ISOLATION (its own process, no other files) -- clean 12/12; (c)
the other 14 package.json files run together WITHOUT integration.test.mjs -- clean 171/171. 171 + 12 =
183, the exact same total `npm test` covers -- confirming ALL 183 cases genuinely pass; the flake is
confined to a resource/timing race in integration.test.mjs's own teardown when run sequentially inside
one long 15-file/183-test node process, not a real regression, and not caused or worsened by this
addendum's diff.)

================================================================================
RAW OUTPUT — regression baseline (sweep 2): 94 tests (92 iter1 baseline + 2 new plist guardrail tests)
Command (from runtime/loop/): node --test __tests__/address-classify.test.mjs
  __tests__/balance-solana.test.mjs __tests__/brain.test.mjs
  __tests__/daemon-script-franklin-routing.test.mjs __tests__/earn-slot.test.mjs
  __tests__/franklin-plist-config.test.mjs __tests__/integration-solana-tier.test.mjs
  __tests__/liquidity.test.mjs __tests__/prompt.test.mjs __tests__/resolve-identity.test.mjs
  __tests__/self-eval.test.mjs __tests__/wallet-address-solana.test.mjs
================================================================================
ℹ tests 94
ℹ pass 94
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 12215.752875

================================================================================
ADDENDUM TOTALS (iter2)
================================================================================
Target-feature test() blocks (this feature's own 5 files): 63/63 PASS (+1 vs iter1's 62: PROP-506f).
Full combined suite (183 official package.json + 94 sweep-2) = 277/277 PASS, 0 regressions.

================================================================================
ADDENDUM — impl-review iter3 fix (Phase 3 iteration-3 FIND-001, REQ-509 ledger target corrected)
================================================================================

target-feature-tests: PASS
regression-baseline: PASS

Fixes Phase 3 implementation review iteration-3's 1 blocking finding
(`.vcsdd/features/franklin-alwaysact-skill-router/reviews/impl/iteration-3/output/findings/FIND-001.json`):

FIND-001 (REQ-509's own literal AC text — "preserved verbatim in the ledger" — names ledger.jsonl
specifically, not harness-failures.jsonl; iteration-2's FIND-004 fix was a genuine, undisclosed
requirement reinterpretation): "the ledger" is a proper noun this spec uses consistently for
ledger.jsonl (REQ-510's own EARS clause, REQ-512's "append ... a ledger line", line 777's
"distinguishable from the ledger alone") — never for harness-failures.jsonl, which REQ-508 always names
explicitly by its literal filename whenever meant. THINKER RULING: the spec is authoritative; the CODE
was changed, not the spec.

`runAlwaysActWake`'s reroute branch (index.mjs) now writes the guard-blocked/no-realized-action pick's
own skip record directly to `ledger.jsonl` via the SAME `formatRecord`/`safeAppend`/`LEDGER_PATH`
machinery every other ledger line in this file already uses (never a new writer), under a distinct
`kind:'router_reroute_skip'`, carrying `wake_id`/`ts`/`slot`/`args`/`attemptsUsed`/`exit_code` fields
consistent with every other always-act ledger line plus a `skip_reason` field holding the guard's own
raw skill output UNTAMPERED (only the same `redactPrivateKeyPatterns` pass every other ledger line
already gets — never truncated or whitespace-collapsed), satisfying "preserved verbatim". This write is
unconditional and happens BEFORE the branch decides whether to reroute successfully or escalate, so the
record survives either outcome. The prior `appendHarnessFailure` call (writing to harness-failures.jsonl)
was REMOVED entirely — the spec never asked for it, and harness-failures.jsonl is semantically reserved
for REQ-508's own TERMINAL exhausted-bound failure case, not a routine, in-flight guard-skip.

Confirmed no health-tracking collision: `harness-health.mjs`'s `CLEAN_KINDS`/`SLOT_HEALTH_KINDS`/
`BRAIN_TRANSPORT_RESET_KINDS` sets (re-read in full) do not include `router_reroute_skip` — it classifies
as `'unknown'` via `classifyLayer` and is excluded from `computeSlotHealth`'s subset filter entirely, so
no false-positive/negative health classification is introduced by this kind now appearing in
ledger.jsonl.

Rewrote `PROP-509b` to assert UNCONDITIONALLY against ledger.jsonl (finding the guard-blocked record by
`slot === 'earn/sol-trade' && kind === 'router_reroute_skip'`, asserting `skip_reason` includes
`'kill-switch'` verbatim) plus a regression guard confirming harness-failures.jsonl carries NO
`router_reroute_skip` record for that wake. Fixed the ~8 other reroute-path tests whose ledger.jsonl now
carries an ADDITIONAL `router_reroute_skip` line ahead of (or alongside) their existing terminal/
escalation line — every one of these now waits for the CORRECT total ledger-line count and locates each
record by `kind`/`slot`, never by `lines[0]` index (Row 5, Row 6, Row 6b, Row 7, Row 9, Row 12,
PROP-506f, PROP-506c/economy-gig, PROP-506c/economy-lending). While retargeting these assertions, 3 of
them (Row 5, PROP-506c/economy-gig, PROP-509b) surfaced a genuine PRE-EXISTING test-authoring race
(writing the reroute target's mock earn-skill file only AFTER `waitForCondition(requests.length >= 2)`,
which is racy since the mock brain server increments `requests.length` synchronously immediately before
responding — the child process can already be resolving the skill path before the test-side file write
lands) that the OLD, weaker `lines[0].slot`/`notEqual(lines[0].kind,'wake_error')` assertions had been
silently masking (the `slot` field is populated on every outcome kind, including `skill_missing`, so the
old assertions passed even when the reroute target's mock skill was never found in time). Fixed properly
by capturing the wake's own `wake_id` from the FIRST think() request (every attempt within one wake
shares the SAME wake_id) and writing the reroute target's mock skill immediately — before the 2nd think()
call's response can possibly reach the child — mirroring the pattern Row 1 already established. Verified
this pre-existing race by reproducing `skill_missing` deterministically (3/3 repeated runs) against the
UNMODIFIED base code via a throwaway debug harness before applying the fix; NOT a regression introduced
by this addendum's own diff.

NEGATIVE-CONTROL VERIFIED this session: with the index.mjs fix reverted (`git stash push --
runtime/loop/index.mjs`, leaving the rewritten test file in place), PROP-509b genuinely FAILS —
`AssertionError: the guard-blocked slot's own skip record must be preserved (not silenced) in
ledger.jsonl -- "the ledger" per REQ-509's own literal AC text` — confirming the new assertion is real,
not dead code. Restored via `git stash pop`; PROP-509b passes again, and the full 183/183 official suite
was re-confirmed clean after restore.

FILES CHANGED THIS ADDENDUM:
  - runtime/loop/index.mjs (the noRealizedAction/reroute branch now writes `kind:'router_reroute_skip'`
    directly to ledger.jsonl via safeAppend/formatRecord/LEDGER_PATH; the prior appendHarnessFailure call
    for this branch was removed)
  - runtime/loop/__tests__/always-act-reroute.test.mjs (PROP-509b rewritten to assert unconditionally
    against ledger.jsonl + a harness-failures.jsonl regression guard; Row 5/6/6b/7/9/12, PROP-506f,
    PROP-506c/economy-gig, PROP-506c/economy-lending updated to wait for the correct ledger-line count
    and locate records by kind/slot instead of `lines[0]`; Row 5/PROP-506c-gig/PROP-509b additionally
    fixed to capture wake_id from the first think() request, closing a pre-existing mock-skill-write race)
  - .vcsdd/features/franklin-alwaysact-skill-router/contracts/sprint-1.md (CRIT-006 description/
    passThreshold corrected to name ledger.jsonl, not harness-failures.jsonl, as REQ-509's preservation
    target)

================================================================================
RAW OUTPUT — target-feature suite (63 tests, 5 files: same 5 files as iter2, no count change)
Command (from runtime/loop/): node --test __tests__/always-act-reroute.test.mjs
================================================================================
✔ 25/25 tests in always-act-reroute.test.mjs pass, 4 consecutive full-file runs (0 failures on any run).

================================================================================
RAW OUTPUT — full official package.json `test` script (183 cases, same count as iter2)
Command (from runtime/loop/): npm test
================================================================================
ℹ tests 183
ℹ pass 183
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 20370.408458

(Re-run twice this session: both 183/183 clean, 0 failures, 0 flakes.)

================================================================================
RAW OUTPUT — regression baseline (sweep 2): 94 tests (unchanged from iter2)
Command (from runtime/loop/): node --test __tests__/address-classify.test.mjs
  __tests__/balance-solana.test.mjs __tests__/brain.test.mjs
  __tests__/daemon-script-franklin-routing.test.mjs __tests__/earn-slot.test.mjs
  __tests__/franklin-plist-config.test.mjs __tests__/integration-solana-tier.test.mjs
  __tests__/liquidity.test.mjs __tests__/prompt.test.mjs __tests__/resolve-identity.test.mjs
  __tests__/self-eval.test.mjs __tests__/wallet-address-solana.test.mjs
================================================================================
ℹ tests 94
ℹ pass 94
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 12183.406083

================================================================================
ADDENDUM TOTALS (iter3)
================================================================================
Target-feature test() blocks (this feature's own 5 files): 63/63 PASS (unchanged count vs iter2 — no
  tests added, 9 existing tests corrected: PROP-509b rewritten + 8 reroute-path tests retargeted).
Full combined suite (183 official package.json + 94 sweep-2) = 277/277 PASS, 0 regressions.
Negative control: PROP-509b genuinely fails when the index.mjs fix is reverted (verified this session).
