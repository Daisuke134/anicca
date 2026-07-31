# CORE 8d — VCSDD Phase 2b minimal GREEN only

Fresh `gpt-5.6-sol`. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` at exact clean commit `3e8c6df947bb7280e7fa9b37a1749d3c60bf0c4d`, PR #330. No sub-agent.

Read project rules, installed VCSDD/TDD Phase 2b instructions, state/approved contract/reviews, behavioral spec, verification architecture exact matrix, Phase2a RED tests/evidence, and root canonical §9.5/§10 row 8d/§10.2/§10.3. This order is minimal GREEN only. Do not weaken/delete/skip/rename RED tests or change exact counts. No provider/network/L3, no successful production report, no deploy/merge, no Phase 2c refactor, no root spec edit.

Using atomic VCSDD tooling, legally enter `2b`. Implement the smallest production and verifier-helper changes that make the approved RED contract GREEN:

- Bot API, Resend, gog per-call timeout 15000ms; Telegram/email/parallel hard deadlines 179000/120000/179000ms; exact attempt/delay and one-shot budgets unchanged;
- closed final success validator/schema, current internal run correlation -> one-way runRef, per-dependency checkedAt same-run boundary, no raw correlation/PII/arbitrary fields, separate closed non-final failure channel;
- atomic mode-0600 output via temp file + fsync + rename; failure cleanup leaves no final artifact;
- four future verifier helpers at the exact approved paths/contracts: phase2 process, final artifact, ISO-aware safe scan, controlled-L3 gates. They must be deterministic, argv-closed, sanitized, credential/network-free;
- only the planned three production modules may change unless a new production module is strictly necessary and then it must be declared and independently covered later.

GREEN acceptance before commit: app new tests exact `63/63/0/0`; helper exact `12/12/0/0`; baseline focused `51/51`; baseline full `371/371`; full final arithmetic `434/434`; eval `33/33`; temporal `18/18`; poll `12/12`; schema `45/45`; purity `32/32`. Record exact commands/exits/counts and source hashes in named Phase2 evidence and `sprint-1-green-phase.log` with `target-feature-tests: PASS` and `regression-baseline: PASS`. No final-report JSON and no provider credentials/network.

Update all 75 test beads from red to green only through installed atomic traceability tooling; state remains `2b`, sprintCount=0. Validate state/runtime/schemas/traceability/diff/safe scan/historical and review immutability, exact production scope, clean tests, and PR equality. Commit/push only implementation, helpers, GREEN evidence, and allowed state/history artifacts.

Return RESULT=GREEN-READY or BLOCKED; exact count table; production files; state/beads; validation; commit; push; NEXT=separate Phase2c refactor/final verification only.
