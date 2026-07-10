new-feature-tests: FAIL
regression-baseline: PASS

```
================================================================================
RED PHASE EVIDENCE — franklin-alwaysact-skill-router, Phase 2a
Feature: franklin-alwaysact-skill-router | Phase: 2a (RED) | Mode: strict
Spec: specs/behavioral-spec.md (REQ-501..513), specs/verification-architecture.md
      (PROP-501a..513e, Proof Obligations table)
Command run from runtime/loop/ (worktree /Users/operator/anicca/.worktrees/alwaysact-impl):
  node --test <files>
Date: 2026-07-11
================================================================================

SCOPE OF THIS EVIDENCE
-----------------------
"new-feature-tests: FAIL" covers the 4 NEW test files below (53 individual `test()` blocks total),
covering every REQ-501..513 and every PROP-ID in verification-architecture.md's Proof Obligations
table. None of the always-act-router feature exists yet (Phase 2b): there is no
runtime/loop/always-act-router.mjs module, no ctx.alwaysActEngaged/ctx.alwaysActMenu wiring in
brain.mjs/prompt.mjs, no identity gate / attemptsUsed retry loop / dispatch-rejection guard /
always_act_* ledger kinds in index.mjs. Every "new capability" assertion therefore fails, for one of
two RIGHT reasons:
  (a) import-time failure — ERR_MODULE_NOT_FOUND for `runtime/loop/always-act-router.mjs`
      (always-act-router.test.mjs, always-act-nojudgment.test.mjs: the latter reads the module's own
      SOURCE via fs.readFile for its static grep check, so it fails with ENOENT instead of
      ERR_MODULE_NOT_FOUND — same underlying cause: the module does not exist yet).
  (b) assertion failure against the REAL, unmodified runtime/loop/index.mjs / brain.mjs behavior —
      sleep is still offered on the real outbound wire, index.mjs runs unbounded wakes with no
      attemptsUsed ceiling (observed request counts of 6-183 instead of the required exactly-2 ceiling
      across the sec2.5 transition-matrix tests — always vastly > 2, never crashing, confirming the
      RED signal is the ABSENCE of a bound, not a broken test), and a fabricated slot:"sleep" is
      silently honored as today's ordinary idle/sleep outcome instead of being rejected.

10 assertions across always-act-wire-seam.test.mjs (2) and always-act-reroute.test.mjs (3, after the
PROP-512a fix below) + 5 total (2+3) are DELIBERATELY labeled non-regression/baseline-holds and are
EXPECTED to already pass today — they assert behavior that must be true BOTH before and after Phase 2b
(e.g. "a non-always-act ctx still offers sleep", "an identity-MISMATCHED instance never engages
always-act regardless of the flag", "the model's args still reach skill execution unmodified", "this
feature's current diff touches no money-safety guard file yet"). These passes are intentional
regression/guardrail confirmations, not a Red-phase violation — no NEW capability is asserted by them.
One test (PROP-512a) was tightened mid-session after an initial version was found to pass VACUOUSLY
(asserting only the ABSENCE of a not-yet-implemented ledger kind, which trivially held before any code
existed) — it now also asserts the POSITIVE engagement signal (sleep withheld on the wire), which
correctly fails today; see git history on this file for the fix.

Assumed REQ-501(b) config-flag name (behavioral-spec.md names no literal string): fixed as
ALWAYS_ACT_ENABLED for this Phase 2a commit's test fixtures — Phase 2b may rename it, updating this
test file's constant accordingly.

"regression-baseline: PASS" covers:
  1. The OFFICIAL runtime/loop/package.json `test` script's pre-existing 14 files (120 pre-existing
     test cases, unmodified) — 120/120 PASS, 0 failures.
  2. An ADDITIONAL sweep of every other pre-existing *.test.mjs file in runtime/loop/__tests__/ not
     enumerated in package.json's `test` script (address-classify, balance-solana, brain,
     daemon-script-franklin-routing, earn-slot, franklin-plist-config, integration-solana-tier,
     liquidity, prompt, resolve-identity, self-eval, wallet-address-solana — INCLUDING
     wallet-address-solana.test.mjs's own live test against Franklin's real production
     /Users/operator/.blockrun wallet) — 92/92 PASS, 0 failures.
  Combined: 212/212 pre-existing test cases PASS, unmodified, after this commit's changes (4 new test
  files + 1 new non-test helper module + 2 lines added to package.json's test-script file lists +
  1 precision-only edit to behavioral-spec.md). No source module under runtime/loop/ was touched by
  this Phase 2a commit — only test/evidence/spec files were added or edited, so a pre-existing-test
  regression was never mechanically possible; this sweep is the empirical confirmation.
  NOT run: runtime/loop/__tests__/earn-slot-e2e.test.mjs (a genuine end-to-end test unrelated to this
  feature's scope, excluded from both this run and the official `test` script; disclosed for honesty).

NEW TEST FILES (4, 53 `test()` blocks total)
---------------------------------------------
- runtime/loop/__tests__/always-act-router.test.mjs      (26 tests) — Pure Core: REQ-502/503/504(a)/
    506(pure)/507(pure property)/510/511/512(b); PROP-502a/b/c/d, 503a/b, 504a, 506e/f, 510a, 511a,
    512b, plus isEarnActionSlot/isRejectableSleepOrOffMenu/nextRerouteState structural tests.
- runtime/loop/__tests__/always-act-wire-seam.test.mjs   (3 tests) — REQ-504's real outbound wire:
    PROP-504b (money-doctrine-critical).
- runtime/loop/__tests__/always-act-reroute.test.mjs     (23 tests) — the REAL index.mjs wake-loop
    integration harness: REQ-501 (PROP-501a/b/c), the sec2.5 transition matrix rows 1-12 (PROP-505a,
    506a/b/d/g, 511a, 513a/b/c/d/e), REQ-506's classify-call-site widening (PROP-506c), REQ-507's
    concrete args pass-through (PROP-507a), REQ-509 (PROP-509a/b), REQ-512 (PROP-512a).
- runtime/loop/__tests__/always-act-nojudgment.test.mjs  (1 test) — REQ-507's static guard: PROP-507b.
- runtime/loop/__tests__/helpers/always-act-harness.mjs  — shared, non-test spawn/mock-server/identity-
    fixture helper module (not itself a test file; not enumerated in package.json's test scripts).

================================================================================
RAW OUTPUT — always-act-router.test.mjs
Command: node --test __tests__/always-act-router.test.mjs
================================================================================
node:internal/modules/esm/resolve:275
    throw new ERR_MODULE_NOT_FOUND(
Error [ERR_MODULE_NOT_FOUND]: Cannot find module
  '/Users/operator/anicca/.worktrees/alwaysact-impl/runtime/loop/always-act-router.mjs'
  imported from
  '/Users/operator/anicca/.worktrees/alwaysact-impl/runtime/loop/__tests__/always-act-router.test.mjs'
✖ __tests__/always-act-router.test.mjs (75.7655ms)
ℹ tests 1
ℹ pass 0
ℹ fail 1
Result: module-load failure — ALL 26 authored test() blocks in this file are blocked by the missing
runtime/loop/always-act-router.mjs module (the correct RED signal for every PROP this file covers).

================================================================================
RAW OUTPUT — always-act-nojudgment.test.mjs
Command: node --test __tests__/always-act-nojudgment.test.mjs
================================================================================
✖ PROP-507b (static, Tier 0): always-act-router.mjs contains no RegExp/.match(/.test( call, ...
  AssertionError: always-act-router.mjs must exist for this static check to run (RED phase:
  ENOENT: no such file or directory, open '.../runtime/loop/always-act-router.mjs')
ℹ tests 1
ℹ pass 0
ℹ fail 1

================================================================================
RAW OUTPUT — always-act-wire-seam.test.mjs
Command: node --test __tests__/always-act-wire-seam.test.mjs
================================================================================
✖ PROP-504b (money-doctrine-critical): thinkProxy's REAL outbound request body has NO tool named
  "sleep" when ctx.alwaysActEngaged===true and ctx.alwaysActMenu is set (10.1ms)
  AssertionError: the REAL outbound tools array must NOT include sleep when always-act is engaged
  true !== false
✔ PROP-504b (non-regression): thinkProxy's outbound tools array STILL includes sleep when
  ctx.alwaysActEngaged is falsy/absent (4.6ms)
✔ PROP-504b (non-regression): ctx.alwaysActEngaged === false (explicit) behaves identically to
  absent (1.1ms)
ℹ tests 3
ℹ pass 2  (intentional non-regression/baseline-holds, see SCOPE above)
ℹ fail 1

================================================================================
RAW OUTPUT — always-act-reroute.test.mjs (final run, after the PROP-512a tightening fix)
Command: node --test __tests__/always-act-reroute.test.mjs
================================================================================
✔ PROP-501a: identity MISMATCH -> always-act NOT engaged (sleep tool still on the real outbound
  wire), regardless of the flag (251.5ms)                          [intentional non-regression]
✖ PROP-501b: identity MATCH + flag unset -> always-act NOT engaged; ledgers
  kind:always_act_not_engaged reason:flag_unset (REQ-512) (106.0ms)
✖ PROP-501b: identity MATCH + flag malformed ("yes") -> always-act NOT engaged; ledgers
  reason:flag_malformed (108.5ms)
✖ PROP-501c: identity MATCH + flag "1" -> always-act ENGAGED (sleep withheld on the real outbound
  wire, run_skill enum = the always-act menu) (104.0ms)
✖ Row 1 / PROP-506b: valid slot picked, execution completes, earnLine !== null -> immediate
  EXECUTE, 1 think() call total, no reroute (259.5ms)
✖ Row 2 / PROP-505a: no-tool-call -> reprompt -> valid pick, earnLine !== null -> EXECUTE via
  reprompt, exactly 2 think() calls (156.4ms)
  AssertionError: exactly 2 think() calls: baseline no-tool-call + 1 reprompt, never 3 — 9 !== 2
✖ Row 3 / PROP-513e (money-safety-critical, FIND-301 direct regression): no-tool-call -> reprompt
  -> fabricated slot:"sleep" -> ESCALATE, exactly 2 think() calls, never 3, no skill execution
  (407.5ms)
  AssertionError: must escalate truthfully via REQ-508, never accept the fabricated sleep
✖ Row 4 / PROP-505a: no-tool-call -> reprompt -> no-tool-call again -> ESCALATE, exactly 2
  think() calls (454.4ms) — AssertionError: 156 !== 2 (unbounded retry today, no ceiling exists)
✖ Row 5 / PROP-506a (hard tool-enum exclusion): capital slot picked, earnLine===null -> reroute
  EXCLUDES the just-picked slot from the REAL schema -> valid safe reroute pick, earnLine!==null ->
  EXECUTE, 2 think() calls (261.3ms)
  AssertionError: the just-picked slot must be structurally absent from the reroute schema
✖ Row 6 / PROP-513b/c (money-safety-critical, FIND-201): reroute in flight, model re-emits the
  just-excluded capital slot -> REJECTED, no execution, no 3rd think() call, direct ESCALATE
  (502.7ms) — AssertionError: never a 3rd think() call — 180 !== 2
✖ Row 6b / PROP-513c: reroute in flight, model emits a DIFFERENT capital slot -> REJECTED,
  ESCALATE (502.6ms) — AssertionError: 163 !== 2
✖ Row 7 / REQ-506 edge case: reroute's own pick ALSO produces earnLine===null -> ESCALATE, never a
  3rd think() call (503.4ms) — AssertionError: 61 !== 2
✖ Row 8 / PROP-513a (structural, FIND-103 direct regression): fabricated slot:"sleep" on the VERY
  FIRST think() call -> REJECTED -> reprompt -> valid pick -> EXECUTE, 2 think() calls (273.8ms)
  AssertionError: 6 !== 2
✖ Row 9 / PROP-506g (money-safety-critical, FIND-301 REQ-506 symmetric extension): no-tool-call ->
  reprompt -> VALID pick but earnLine===null -> ESCALATE directly, NO reroute (466.9ms)
  AssertionError: a no-op on the REPROMPT attempt must never trigger a reroute — 103 !== 2
✖ Row 10 (iteration-5 notes.md fix): fabricated -> reprompt -> fabricated AGAIN -> ESCALATE,
  exactly 2 think() calls (455.2ms) — AssertionError: 183 !== 2
✖ Row 11 (iteration-5 notes.md fix): fabricated -> reprompt -> no tool call -> ESCALATE, exactly 2
  think() calls (402.0ms) — AssertionError: 180 !== 2
✖ Row 12 (iteration-5 notes.md fix): fabricated -> reprompt -> VALID pick but earnLine===null ->
  ESCALATE, NO reroute, exactly 2 think() calls (402.3ms) — AssertionError: 69 !== 2
✖ PROP-506c: economy/gig pick with earnLine===null triggers the SAME reroute path as any
  isEarnSlot member (classify call-site widening, index.mjs:450) (304.8ms) — 7 !== 2
✖ PROP-506c: economy/lending pick with earnLine===null ALSO triggers the reroute path (270.3ms)
  AssertionError: 18 !== 2
✔ PROP-507a: the model's chosen args reach the skill's WAKE_ID-scoped execution UNMODIFIED
  (353.3ms)                                                        [intentional non-regression]
✔ PROP-509a (money-safety-critical, Tier 0 static guard): current diff touches no money-safety
  guard file (79.0ms)                                              [intentional, green by design]
✖ PROP-509b (money-safety-critical): a REAL guard-block on the first pick triggers a reroute to a
  DIFFERENT slot, guard skip record preserved verbatim (253.1ms)
  AssertionError: the reroute must pick a DIFFERENT slot, never retry earn/sol-trade with a
  relaxed guard — actual 'earn/sol-trade', expected 'economy/gig'
✖ PROP-512a: a Franklin-identity wake with the flag set to "1" takes the ENGAGED path (sleep
  withheld on the real wire) and never ledgers a stray always_act_not_engaged line (102.7ms)
  AssertionError: flag=1 + identity match must actually ENGAGE always-act (sleep withheld on the
  real wire) — expected false, actual true

ℹ tests 23
ℹ pass 3   (intentional non-regression: PROP-501a mismatch, PROP-507a args pass-through,
             PROP-509a static diff guard)
ℹ fail 20
ℹ cancelled 0
ℹ duration_ms ~7300

NOTE on non-determinism of the exact overshoot counts (9/156/180/163/61/6/103/183/180/69/7/18):
these spawned-child-process tests observe the REAL, currently-unbounded index.mjs wake loop
(SLEEP_BASE_S=0) racing against a fixed ~300ms assertion-window grace period before SIGTERM — the
EXACT number of extra wakes squeezed into that window is a real-clock timing artifact, not a
meaningful signal. What IS deterministic and IS the RED signal: every one of these counts is always
far greater than the required ceiling of 2, proving no attemptsUsed bound exists yet (a false-negative
in the other direction — "happens to land on exactly 2 by chance" — was never observed across 2
independent full runs of this file).

================================================================================
RAW OUTPUT — regression baseline (1): runtime/loop/package.json's own `test` script file set
Command: node --test __tests__/tier.test.mjs __tests__/env-filter.test.mjs
  __tests__/ledger-record.test.mjs __tests__/loop-detect.test.mjs __tests__/parse-tool-call.test.mjs
  __tests__/config.test.mjs __tests__/inference.test.mjs __tests__/catalog-gate.test.mjs
  __tests__/registry-classification.test.mjs __tests__/harness-health.test.mjs
  __tests__/harness-health-snapshot.test.mjs __tests__/harness-health-no-autoaction.test.mjs
  __tests__/integration.test.mjs __tests__/harness-health-failure-detail.test.mjs
================================================================================
ℹ tests 120
ℹ pass 120
ℹ fail 0
ℹ duration_ms 14025.072375

================================================================================
RAW OUTPUT — regression baseline (2): every other pre-existing *.test.mjs not in package.json
Command: node --test __tests__/address-classify.test.mjs __tests__/balance-solana.test.mjs
  __tests__/brain.test.mjs __tests__/daemon-script-franklin-routing.test.mjs
  __tests__/earn-slot.test.mjs __tests__/franklin-plist-config.test.mjs
  __tests__/integration-solana-tier.test.mjs __tests__/liquidity.test.mjs __tests__/prompt.test.mjs
  __tests__/resolve-identity.test.mjs __tests__/self-eval.test.mjs
  __tests__/wallet-address-solana.test.mjs
================================================================================
ℹ tests 92
ℹ pass 92
ℹ fail 0
ℹ duration_ms 12293.424458

================================================================================
TOTALS
================================================================================
New feature test() blocks authored: 53 (4 files)
New feature tests: import/module-load failure = 26 (always-act-router.test.mjs, blocked as 1 file-
  level failure) + ENOENT static-check failure = 1 (always-act-nojudgment.test.mjs) + assertion
  failures against real unmodified code = 1 (always-act-wire-seam.test.mjs) + 20
  (always-act-reroute.test.mjs) = 22 discretely-reported failing test() blocks + 26 blocked-but-
  authored = 48 of 53 authored blocks are RED for the correct reason.
Intentional non-regression/baseline-holds passes: 5 (2 in wire-seam, 3 in reroute) — asserted
  behavior that is unchanged by this feature and must remain true after Phase 2b too.
Pre-existing regression baseline: 212/212 PASS (120 official package.json set + 92 additional sweep),
  0 failures, 0 files touched by this Phase 2a commit's source-level changes.
```
