# CORE 8d — VCSDD Phase 2c refactor and final verification only

Fresh `gpt-5.6-sol`. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` at exact clean commit `39fd2e00bb543bf90e1ec53a5f0af398419d69d9`, PR #330. No sub-agent.

Read project rules, installed VCSDD/TDD Phase 2c/refactor instructions, feature-local state, approved contract/review, behavioral spec, verification architecture, RED/GREEN evidence, production diff, and root canonical §9.5/§10 row 8d/§10.2/§10.3. No provider/network/L3/final-report/deploy/merge/root-spec changes.

Legally enter feature-local Phase `2c` using installed atomic tooling, but do not take over or modify repo-wide `.vcsdd/index.json` or `.vcsdd/active-feature.txt`; both must remain byte-identical to `39fd2e00b` with global active `fable5-config-slimdown`. If tooling temporarily requires registration, restore both before commit. Keep sprintCount=0.

Perform behavior-preserving refactor only where it materially improves the Phase2b implementation. Do not weaken, delete, skip, rename, or change the exact approved test arithmetic. Do not add feature behavior. Independently inspect timeout/deadline cleanup, AbortSignal/timer cleanup, one-shot send guarantees, final-schema closure, run-correlation removal, failure-channel isolation, atomic file cleanup, helper argv closure/sanitized errors, and symlink/path traversal concerns for output publication.

Fresh final acceptance:

- app new 63/63; helpers 12/12; baseline focused 51/51; baseline full 371/371; full final 434/434; eval 33/33; temporal 18/18; poll 12/12; schema 45/45; purity 32/32;
- per-module coverage independently lines/functions >=90.00% for every production file changed from `8bac59bb0`, at minimum `lib/daily-preflight.js`, `lib/daily-preflight-collectors.js`, `lib/transport/mail-gog.js`, and the necessary additional `scripts/daily-preflight.js`; combined-only coverage is failure. Do not omit a changed production module;
- all 75 test beads remain GREEN, state/runtime/schemas/traceability/contract/gates PASS, safe scan 0, historical/review evidence immutable, exact production scope, no final-report JSON, no provider credentials/network;
- refresh `sprint-1-green-phase.log` and named evidence with post-refactor commands, exits, counts, source commit/tree, and per-module coverage table.

Commit/push only minimal refactor/tests-if-strictly-needed/evidence/feature-local state+history. Global index files must be absent from diff. Stop at `2c` ready for a separate fresh artifact/code adversarial review; do not enter Phase 3 or merge.

Return RESULT=PHASE2C-REVIEW-READY or BLOCKED; exact count/coverage table; refactor summary; state/beads; validation; commit; push; NEXT=fresh adversarial code review only.
