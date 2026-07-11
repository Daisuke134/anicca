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

## Test Execution Convention

Follows the precedent set by `runtime/loop/__tests__/daemon-script-franklin-routing.test.mjs`
(franklin-loop-revival): tests read the REAL `runtime/anicca-daemon.sh` source text, extract the
side-effect-free `is_franklin_instance()` function definition verbatim via a marker-based slice, and
execute it in a throwaway `/bin/bash -c` subshell (no git/curl/node/pkill side effects triggered). Static
regex assertions over the source text verify the 3 call sites were actually rewired (PROP-005).

This new test file is NOT added to `runtime/loop/package.json`'s `test` script, matching the existing,
established convention for this class of shell-source test (`daemon-script-franklin-routing.test.mjs`
and `franklin-plist-config.test.mjs` are likewise excluded from the `npm test` list and are run
standalone via `node --test <file>`) — so the `npm test` regression baseline (183 tests) is unaffected by
this feature.
