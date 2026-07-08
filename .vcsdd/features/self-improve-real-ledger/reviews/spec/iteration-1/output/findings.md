# Spec Review Findings — self-improve-real-ledger (Phase 1c, iteration 1)

Reviewer: fresh-context VCSDD adversary (Opus). Reviewer's Write of this file was blocked by a
harness guard; content below persisted verbatim by the orchestrator from the reviewer's report.

## F-1 — BLOCKING (verification_readiness)
Target: verification-architecture.md PROP-RL-LIVE1/2/3 + behavioral-spec.md Done-table verification row.

The default-path safety argument is "correct BY CONSTRUCTION" via __file__-relative resolution —
true for the three production bodies (~/anicca, ~/.anicca, ~/.blockrun), NOT true for the dev
worktree this feature is built in: skills/*/state/ is gitignored (.gitignore:37), so
~/anicca/.worktrees/self-improve-real-ledger/ has NO skills/earn/state/ at all; __file__-relative
resolution from the worktree computes a nonexistent path and silently degrades to all-zero
(resolved:true, row_count:0). PROP-RL-LIVE1/3 cannot be satisfied from the worktree; neither
document states WHERE the live-tier proofs must run. Dangerous "fix" available to an implementer:
symlink/copy real state/ into the worktree = cross-checkout financial-state leak, the exact class
this feature exists to close.

Fix required: state explicitly that PROP-RL-LIVE1/2/3 and the Done verification row MUST run from
the merged ~/anicca main checkout (never the feature worktree); worktree tests use hand-constructed
tmp_path/temp-HOME fixtures only; NEVER symlink/copy any real skills/*/state/ into any worktree.

## F-2 — minor (spec_fidelity)
REQ-RL17 says "BOTH branches"; actual promote_gate_run.py has THREE decide_promotion call sites
(209 not-eligible / 225 adversary-unavailable / 234 adversary-succeeded). Prose must match code.

## F-3 — minor (verification_readiness)
PROP-RL-WIRE1 verifies call shape (realized_gate= keyword present) but not that the value is
genuinely sourced from compute_realized_gate(...) rather than a hardcoded stub literal. Name this
check explicitly in REQ-RL17 or Phase-3 review scope.

## F-4 — note (verification_readiness)
"realized_gate=None → vacuous pass" vs "resolved:False → block" not asserted as one explicit
side-by-side property; add one.

## Verified-clean (for the record)
DEFAULT_LEDGER_PATH hardcode + is_profitable no-HL logic match claims (ledger_reader.py:36-38,83-86);
ledger.mjs hyperliquid disjunct matches REQ-RL5 verbatim; decide_promotion signature/call-site
premises hold; promote.py commit-prefix matches REQ-RL12 verbatim; scope_guard has no RL19 entries
yet; real ledgers lack edge/confidence/liquidity/price fields (grounds RL14/RL15); 44 tests
collected; run_evolve.sh OBSERVE uses no path override (RL16 zero shell changes); no AI-disclosure /
weasel wording / strategy leakage / invariant weakening; untouched files correctly declared.

## Summary
| ID | Severity | Dimension |
|---|---|---|
| F-1 | BLOCKING | verification_readiness |
| F-2 | minor | spec_fidelity |
| F-3 | minor | verification_readiness |
| F-4 | note | verification_readiness |
Blocking: 1. Major: 0. Minor: 2.
