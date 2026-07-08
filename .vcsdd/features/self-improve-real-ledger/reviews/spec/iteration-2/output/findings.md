# Spec Review Findings — self-improve-real-ledger (Phase 1c, iteration 2)

Reviewer: fresh-context VCSDD adversary (Opus). findings.md write was blocked by harness guard;
content persisted verbatim by orchestrator from the reviewer's report.

## Iteration 1 findings — verified resolved
F-1 (BLOCKING execution-locus) / F-2 / F-3 / F-4: all RESOLVED, independently verified against
current spec text + real code (EDGE-RL5a + execution-locus paragraph; 3 call sites at
promote_gate_run.py:209/225/234 confirmed as the ONLY production call sites; stub-source check
sentence present; PROP-RL-GATE-NONE added).

## F-5 — BLOCKING (spec_fidelity / gate un-gameability)
REQ-RL19's denylist additions do not match realistic Python import text under
scan_denylisted_imports's plain-substring scan: "ledger_reader.py" (a .py-suffixed form never
appears in import statements) and "is_profitable" (snake_case Python symbol) is MISSING entirely —
pre-existing denylist has only JS camelCase "isProfitable" (scope_guard.py:44), a different string.
Hand-traced: `from lib import ledger_reader` + `ledger_reader.is_profitable(row)` matches ZERO of
the seven proposed entries → an evolved candidate can reach this feature's ledger-observation
machinery undetected. PROP-RL-SAFE1 would pass while the protection stays bypassable (it asserts
only "denylist contains every REQ-RL19-listed string", and the list itself is wrong).
Fix: add "is_profitable"; use "ledger_reader"/"promotion_history" without .py suffix; add
executable bypass-reproduction asserts to PROP-RL-SAFE1.

## F-6 — minor (verification_readiness)
DEFAULT_LEDGER_PATH now honors ANICCA_HOME at import time (REQ-RL3 via REQ-RL1) → the pre-existing
unmodified endswith assertion (tests/test_ledger_reader.py:191-192) becomes environment-sensitive:
non-deterministic failure if the regression shell exports ANICCA_HOME. Fix: document the regression
execution environment (ANICCA_HOME unset) or require monkeypatch isolation.

## F-7 — minor (spec_fidelity)
No single canonical key schema for the realized_gate dict; decide_promotion and
promote_gate_run.py::main could consume differently-named keys and only fail at Green test time.
Fix: one explicit schema table.

## Verified-clean (record)
ledger.mjs HL disjunct matches REQ-RL5 verbatim (ledger.mjs:62); promote.py commit prefix matches
REQ-RL12 (promote.py:48); 44 tests counted exactly (5+5+5+2+14+7+6); DEFAULT_LEDGER_PATH hardcode +
missing HL disjunct in is_profitable verified live (the gaps are real); __file__-relative math
verified for all three instance bodies incl. Franklin's rsynced copy at
~/.blockrun/skills/earn/self-improve/lib/ledger_reader.py; pm_backtest_strategy uses
edge/confidence/liquidity/price fields absent from real ledgers (grounds RL14/RL15); no
AI-disclosure/weasel wording/strategy leakage/invariant weakening.

| ID | Severity | Dimension |
|---|---|---|
| F-5 | BLOCKING | spec_fidelity |
| F-6 | minor | verification_readiness |
| F-7 | minor | spec_fidelity |
