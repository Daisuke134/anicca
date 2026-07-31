# CORE 8d — VCSDD Phase 2a RED only

Fresh `gpt-5.6-sol`. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` at exact clean commit `8bac59bb0e9902fdbd3afdefd5550b9220ffecac`, PR #330. No sub-agent.

Read project rules, installed VCSDD/TDD Phase 2a instructions, state, approved contract/review, behavioral spec, verification architecture exact matrix, prior reviews, and root canonical §9.5/§10 row 8d/§10.2/§10.3. This order is RED only. Do not implement or edit production modules, call providers, create a successful final report, enter 2b, deploy, merge, or update root canonical spec.

Using installed atomic tooling, create the Phase 2a test beads/traceability and only the exact future test/helper surfaces required by the approved matrix:

- `apps/life-call/lib/daily-preflight-poll-boundaries.test.js`: exact 12 cases;
- `apps/life-call/lib/daily-preflight-final-schema.test.js`: exact 45 cases with same-run/checkedAt boundaries and closed schema;
- `apps/life-call/lib/daily-preflight-purity-contract.test.js`: exact 6 cases;
- `.vcsdd/features/life-manager-daily-preflight/tests/verifier-contracts.test.mjs`: exact 12 helper-contract cases;
- helper files only if VCSDD Phase 2a requires absent/minimal stubs to produce intentional product RED; never make them GREEN in this order.

First capture immutable baseline evidence from the approved source snapshot: focused 51/51, full 371/371, eval 33/33, historical hashes/modes, source snapshot. Then run new tests and prove intentional RED is caused by missing required production behavior/helpers—not syntax, missing fixture, wrong path, wrapper, credential, or network failure. Each of the three app test files must have at least one genuine assertion failure; helper contracts must RED as specified. Record exact commands, exits, TAP counts/failures, source hashes, and markers `new-feature-tests: FAIL` and `regression-baseline: PASS` in the approved `evidence/sprint-1-red-phase.log` and named evidence paths. No provider credentials/network.

Validate state remains `2a`, adversary/human/contract gates PASS, sprintCount=0; state/runtime/schemas/traceability/diff/safe scan/immutable prior artifacts pass. Ensure production diff from `8bac59bb0` is empty and no final-report JSON exists. Commit/push tests, Phase2a evidence, allowed state/history/bead artifacts only; verify local/upstream/origin/PR equality.

Return: RESULT=RED-READY or BLOCKED; exact baseline counts; exact new-test counts/exits and genuine failing requirements; state; validation; commit; push; NEXT=separate Phase2b GREEN builder only.
