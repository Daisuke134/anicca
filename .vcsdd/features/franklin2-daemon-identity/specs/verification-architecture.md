# Verification Architecture — franklin2-daemon-identity (lean VCSDD, P4-code)

## Purity Boundary Map

- **Pure Core**: `is_franklin_instance()` — a new POSIX shell function in `runtime/anicca-daemon.sh`.
  Deterministic function of one string argument (`$1`), no side effects, returns exit-status 0 (match)
  or 1 (no match). Formally trivial: a bounded `case` pattern over a finite-cardinality alphabet
  (letters + digits), fully enumerable by test.
- **Effectful Shell**: the 3 call sites that gate on `is_franklin_instance "$INSTANCE"` — brain-probe
  (curl + conditional `clawrouter` spawn), telemetry-poster selection (`pkill` + node spawn loop),
  wallet-address derivation (node subprocess, viem/solana). All unchanged bodies; only the branch
  condition changes from a literal string-equality to the shared predicate call.

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-001 | `is_franklin_instance franklin` → match (regression, unchanged original citizen) | 0 | true | node:test + bash subshell |
| PROP-002 | `is_franklin_instance franklin2` → match (the new capability) | 0 | true | node:test + bash subshell |
| PROP-003 | `is_franklin_instance` matches `franklin` + any digit-run (franklin3, franklin10, franklin99) | 1 | true | node:test, enumerated table |
| PROP-004 | `is_franklin_instance` does NOT match decoys: `clawrouter`, unset/empty, `franklinX`, `franklins`, `franklin-2`, `Franklin2` (case) | 0 | true | node:test, enumerated table |
| PROP-005 | All 3 daemon call sites use `is_franklin_instance "$INSTANCE"` — zero remaining literal `"$INSTANCE" = "franklin"` string-equality anywhere in the file | 0 | true | node:test, static source grep |
| PROP-006 | Non-franklin/PORT-resolution behavior from the pre-existing `daemon-script-franklin-routing.test.mjs` suite is untouched (regression) | 0 | true | pre-existing node:test file, re-run unmodified where possible |
| PROP-007 | `instanceHostLabel()` (telemetry-post-franklin.mjs) maps `franklin`/unset → `"Franklin"`, `franklin2` → `"Franklin2"`, `franklin<N>` → `"Franklin<N>"` (impl-review iteration-1 FIND-001 fix) | 0 | true | node:test, source-text function extraction + `node --eval` subprocess |
| PROP-008 | The franklin-branch telemetry `pkill -f` pattern in `anicca-daemon.sh` step 3 includes `$ANICCA_HOME`, and no unscoped script-path-only pkill pattern remains (impl-review iteration-1 FIND-002 fix) | 0 | true | node:test, static source-text regex assertion |
| PROP-009 | The dead `pkill -f "FRANKLIN_TELEMETRY_LOOP"` line (targeted an exported env var, which `pkill -f` can never match against argv) is absent from `anicca-daemon.sh` step 3; the unrelated `export FRANKLIN_TELEMETRY_LOOP=1` on the poster subshell remains untouched (impl-review iteration-2 FIND-002 fix) | 0 | true | node:test, static source-text regex assertion |
| PROP-010 | The franklin-branch telemetry `pkill -f` pattern, extracted VERBATIM from `anicca-daemon.sh` source text and expanded per the real `$ANICCA_HOME` value of each live instance, matches ONLY that instance's own new-format poster argv — never a sibling instance's, never a legacy markerless argv, and never `skills/earn/sol-trade/run.sh`'s own flagless one-shot telemetry POST invocation. No unscoped, end-anchored legacy-cleanup pkill pattern exists anywhere in the file (impl-review iteration-3 FIND-001/FIND-002 fix — this is the property whose absence let iteration-2's now-removed legacy sweep cross-kill sol-trade's one-shot caller on every restart) | 1 | true | node:test, verbatim source-text pattern extraction + grep -E ERE simulation |

## Verification Strategy

- **Tier 0** (no formal proof needed — direct assertion suffices for a bounded, enumerable string
  classifier): PROP-001, PROP-002, PROP-004, PROP-005, PROP-006. Exact literal-equality and static
  source inspection give 100% coverage of the finite decision space that matters (match vs. no-match on
  a controlled, human-authored vocabulary of instance names).
- **Tier 1** (light property-style enumeration, not full property-based fuzzing — the input space is a
  small finite alphabet, not a numeric domain needing generators): PROP-003 enumerates a representative
  table of digit-suffix values (2, 3, 10, 99) to catch off-by-one pattern bugs (e.g. accidentally
  requiring exactly one digit, or accidentally prefix-matching `franklin` inside `franklinX`).
- **Tier 2 / Tier 3**: not applicable. This is a POSIX `case`-pattern string classifier of bounded
  cardinality, not a numerical/algorithmic property — Kani/Hypothesis-class lightweight-or-strong formal
  methods would be disproportionate tooling for a 4-line shell predicate that is already 100%
  test-enumerable at Tier 0/1.
- PROP-007/PROP-008 (impl-review iteration-1 fixes) are the same Tier 0 class: `instanceHostLabel()` is a
  pure string-mapping function of bounded cardinality (Tier 0, direct assertion suffices), and the
  `pkill` scoping fix is a static source-text regex assertion (Tier 0, no execution of the actual `pkill`
  needed or wanted in a test).
- PROP-009 (impl-review iteration-2 fix) is Tier 0: a static absence assertion over source text (dead
  code removal, no execution semantics to verify).
- PROP-010 (impl-review iteration-3 fix) is Tier 1: it enumerates a representative argv table (both
  live instances' new-format posters, a legacy markerless argv, and `sol-trade/run.sh`'s own one-shot
  invocation) and feeds it through `grep -E` using the pkill pattern extracted VERBATIM (no
  re-escaping) from the real source text, so the test's ERE evaluation matches exactly what `pkill -f`
  itself would evaluate at runtime — this is what iteration-2's independently-re-escaped copy of the
  pattern failed to guarantee (FIND-002 iter3).
- **Migration edge case (impl-review iteration-3 FIND-001)**: the legacy-poster migration described in
  behavioral-spec.md REQ-002(b) "Deployment / migration runbook" is explicitly OPERATIONAL, not code —
  it is NOT a proof obligation in this table, and deliberately so. The property it depends on (telling
  a long-lived legacy poster LOOP apart from a short-lived legitimate one-shot caller like
  `sol-trade/run.sh`'s) is a judgment about process lineage/lifetime that no fixed argv pattern can
  encode without risking exactly the cross-kill regression FIND-001 found (iteration-2's now-removed
  sweep). Formalizing "the operator followed the runbook correctly" is out of scope for this feature's
  automated test suite; PROP-010 instead formally guarantees the narrower, code-level property that
  the removal was correct: the scoped pkill pattern that DOES remain in code never matches that
  one-shot caller.

## Test Execution Convention

Tests read the REAL `runtime/anicca-daemon.sh` / `runtime/dashboard/telemetry-post-franklin.mjs` source
text, extract the side-effect-free function definitions verbatim via a marker-based slice, and execute
them in a throwaway `/bin/bash -c` subshell or `node --eval` subprocess (no git/curl/node-service/pkill/
wallet-file/network side effects ever triggered). Static regex assertions over the source text verify
call-site wiring (PROP-005, PROP-008).

**impl-review iteration-1 FIND-003 fix**: `daemon-script-franklin-routing.test.mjs`,
`daemon-script-franklin2-identity.test.mjs`, `franklin-plist-config.test.mjs`, and the new
`telemetry-host-label.test.mjs` are now ALL wired into `runtime/loop/package.json`'s `test` script (no
longer excluded by convention) — these 4 files are exactly the regression protection for the bug this
feature fixes (a future edit reintroducing the literal `"$INSTANCE" = "franklin"` comparison, or
reintroducing an unscoped telemetry `pkill`/hardcoded `host` label, is now caught automatically by
`npm test`/CI, not only by someone remembering to run these files by hand). `npm test`'s baseline grew
from 183 to 207 at iteration-1 (183 + 18 pre-existing franklin/plist tests + 1 new FIND-002 static test
+ 5 new `telemetry-host-label.test.mjs` tests).

**impl-review iteration-2**: `daemon-script-franklin2-identity.test.mjs` grew from 9 to 12 tests (+1
FIND-001 legacy-cleanup-pkill-positioned test, +1 FIND-002 dead-env-var-pkill-removed test, +1
FIND-001 match-matrix simulation test) — `npm test` baseline grew from 207 to 210.

**impl-review iteration-3** (this iteration): `daemon-script-franklin2-identity.test.mjs` stays at 12
tests — the FIND-001 legacy-cleanup-pkill-positioned test (iteration-2) is REPLACED in place by a
regression guard asserting that pkill is absent and exactly one `telemetry-post-franklin.mjs` pkill
line remains, and the FIND-001 match-matrix test (iteration-2) is REWRITTEN in place to extract its
pattern verbatim from source and add a sol-trade non-match row (net test count unchanged: 12 → 12).
`npm test` baseline stays at 210 (210 → 210) — verified green in this worktree.
