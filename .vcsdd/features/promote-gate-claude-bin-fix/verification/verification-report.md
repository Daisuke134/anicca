# Verification Report

## Feature: promote-gate-claude-bin-fix | Sprint: 2 | Date: 2026-07-10

## Proof Obligations

`proofObligations` in `.vcsdd/features/promote-gate-claude-bin-fix/state.json` is the
empty array `[]`. There are **zero required Tier 2/3 (or higher) proof obligations**
recorded for this feature, and none are added by this hardening pass.

| ID | Tier | Required | Status | Tool | Artifact |
|----|------|----------|--------|------|----------|
| PROP-CB1 | 1 | not required (Tier 1) | proved | pytest (unit test) | `skills/earn/self-improve/tests/test_resolve_claude_bin.py::test_path_hit_returns_which_result_unchanged` |
| PROP-CB2 | 1 | not required (Tier 1) | proved | pytest (unit test) | `skills/earn/self-improve/tests/test_resolve_claude_bin.py::test_which_miss_falls_back_to_first_existing_known_good_path` |
| PROP-CB2b | 1 | not required (Tier 1) | proved | pytest (unit test) | `skills/earn/self-improve/tests/test_resolve_claude_bin.py::test_which_miss_prefers_local_bin_over_homebrew_when_both_exist` |
| PROP-CB2c | 1 | not required (Tier 1) | proved | pytest (unit test) | `skills/earn/self-improve/tests/test_resolve_claude_bin.py::test_which_miss_skips_candidate_that_exists_but_is_not_executable` |
| PROP-CB3 | 1 | not required (Tier 1) | proved | pytest (unit test) | `skills/earn/self-improve/tests/test_resolve_claude_bin.py::test_which_miss_and_no_fallback_exists_returns_original_default_string` |
| PROP-CB4 | 0 | not required (Tier 0) | proved | manual scope check (`git diff`/file-comparison, adversary review) | `.vcsdd/features/promote-gate-claude-bin-fix/reviews/implementation/iteration-2/output/verdict.json` (`spec_fidelity` dimension) |

Note: PROP-CB1 through PROP-CB4 are informational entries carried over from
`specs/verification-architecture.md`'s Proof Obligations table for traceability; they
are **not** registered in `state.json`'s `proofObligations[]` array because none of them
is `required: true` at Tier 2+ (the gate this phase exists to enforce). No entry in this
table blocks Phase 6 convergence — Phase 6 only requires `status: "proved"` for
`required: true` obligations, and there are none.

## Tier Rationale (why zero Tier 2/3 obligations)

Per `specs/verification-architecture.md` §"Verification Tier Rationale" (quoted in full):

> Tier 1 (property/unit test with monkeypatched I/O boundary) is sufficient — this is a
> pure path-selection function with no concurrency, no external side effects beyond a
> filesystem `stat`, and no security-sensitive input (no untrusted data reaches this
> function; it only reads fixed, hardcoded candidate strings plus the process `PATH`).
> Tier 0 (manual/diff-scope check) covers REQ-CB4. Lean mode: no Tier 2/3 obligations
> required for a fix this narrow.

This hardening pass independently re-confirms that rationale still holds: the
implementation actually shipped (`_resolve_claude_bin()`, 19 lines,
`skills/earn/self-improve/lib/promote_gate_run.py:104-111`) is a single-threaded,
synchronous, side-effect-free-beyond-`stat` path selector operating only on
process-local `PATH` env state and a fixed hardcoded tuple of 3 candidate strings — no
concurrency, no untrusted input, no financial/security-sensitive data flow (no wallet
keys, ledger, or spend-cap logic touched — see `verification/purity-audit.md` and
`security-report.md`). No degradation from a higher tier occurred because no higher
tier was ever warranted; this is documented explicitly rather than assumed.

## Test-Suite-Based Verification (Tier 1, already performed + re-confirmed this pass)

- **New feature tests**: 5/5 pass. Re-run fresh this hardening pass:
  `cd skills/earn/self-improve && rtk proxy python3 -m pytest tests/test_resolve_claude_bin.py -v`
  → `5 passed in 0.08s` (all of PROP-CB1, PROP-CB2, PROP-CB2b, PROP-CB2c, PROP-CB3 pass).
- **Full regression suite**: re-run fresh this hardening pass:
  `cd skills/earn/self-improve && rtk proxy python3 -m pytest tests/ -q`
  → `1 failed, 105 passed in 2.38s`. The 1 failure is
  `tests/test_ledger_reader.py::test_realized_summary_default_path_points_at_the_real_earn_ledger_location`,
  a pre-existing, unrelated worktree-directory-name artifact (the test asserts
  `DEFAULT_LEDGER_PATH.endswith("anicca/skills/earn/state/earn-ledger.jsonl")`, which is
  false when running from a path containing `.worktrees/promote-gate-claude-bin-fix/` —
  this fails identically on any worktree checkout regardless of this feature's change,
  is documented in
  `.vcsdd/features/promote-gate-claude-bin-fix/evidence/sprint-2-red-phase.log` and
  `sprint-2-green-phase.log` as present before this sprint's work began, and confirmed
  by the Phase 3 adversary review to pass on `main`). It is out of this feature's write
  scope (`skills/earn/self-improve/lib/promote_gate_run.py` and its test file only) and
  is not touched or masked by this hardening pass.
- **Mutation robustness**: manually traced during Phase 3 adversary review (iteration 2)
  — `os.X_OK -> os.F_OK`/`os.R_OK`, `and -> or`, and candidate-list-order mutations were
  each confirmed to be caught (cause at least one test failure) by the 5-test suite. See
  `.vcsdd/features/promote-gate-claude-bin-fix/reviews/implementation/iteration-2/output/verdict.json`,
  `edge_case_coverage` dimension.
- **Adversary review**: 2 independent fresh-context adversary reviews performed (spec
  review: 2 iterations, both PASS on iteration 2; implementation review: 2 iterations,
  iteration 1 FAILED on FIND-001 mutation-testing gap, fixed, iteration 2 PASS with zero
  blocking findings). See `state.json` `gates["1c"]` and `gates["3"]`.

## Security Hardening

See `verification/security-report.md` for full detail. Summary: Semgrep 1.168.0
(`--config auto`, 290 community rules, python + multilang) run against both changed
files — 0 findings (0 blocking). Wycheproof / cryptographic checks: not applicable (no
cryptographic code in this change). Raw output:
`verification/security-results/semgrep-promote_gate_run.json`,
`verification/security-results/semgrep-summary.txt`.

## Purity Boundary Audit

See `verification/purity-audit.md` for full detail. Summary: no drift detected between
the declared purity boundary (`_resolve_claude_bin()` impure/env+filesystem;
`lib/promote_gate.py` pure core untouched; `_invoke_adversary()`'s `subprocess.run`
unchanged) in `specs/behavioral-spec.md` / `specs/verification-architecture.md` and the
observed shipped implementation.

## Summary

- Required (Tier 2/3) proof obligations: 0
- Proved: 0 required / 5 Tier-1 + 1 Tier-0 informational obligations proved via test
  suite and manual scope check (all traceable to `specs/verification-architecture.md`'s
  Proof Obligations table, none `required: true` in `state.json`)
- Failed: 0
- Skipped: 0
- Degradation: none (no higher tier was ever warranted per the documented rationale;
  see "Tier Rationale" above)
- Security hardening: clean pass (Semgrep 0 findings; Wycheproof N/A)
- Purity audit: no drift detected
- Pre-existing unrelated failure documented and isolated:
  `tests/test_ledger_reader.py::test_realized_summary_default_path_points_at_the_real_earn_ledger_location`
  (worktree-path artifact, out of this feature's scope, present on `main` too)

**Phase 6 gate status**: No `required: true` proof obligations exist for this feature,
so there is nothing to block convergence on this axis. Formal hardening artifacts
(security-report.md, purity-audit.md, this report) are complete.
