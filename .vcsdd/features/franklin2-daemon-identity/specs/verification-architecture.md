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
`npm test`/CI, not only by someone remembering to run these files by hand). `npm test`'s baseline grows
from 183 to 207 (183 + 18 pre-existing franklin/plist tests + 1 new FIND-002 static test + 5 new
`telemetry-host-label.test.mjs` tests) — verified green in this worktree.
