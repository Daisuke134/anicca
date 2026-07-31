# CORE 8d — VCSDD Phase 3 preparation only

You are a fresh `gpt-5.6-sol` process with no Builder conversation context. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` at exact clean commit `8275d5d9fd2b0ecf79d1e52270960b3ad61f40dd`, PR #330. No sub-agent. Do not review or modify production/source/tests/spec/contract/evidence.

Read project rules and the installed VCSDD adversary skill/command. Read only the feature-local state, approved sprint-1 contract, contract-review PASS verdict, behavioral spec, verification architecture, Phase 2c evidence, and exact `8bac59bb0..HEAD` production/test/process diff needed to construct the implementation-review manifest.

Validate the strict contract gate before writing anything: approved contract exists, CRIT-001..005 are present, contract review is PASS, reviewContext contract path/digest still matches the approved contract, and iteration equals negotiationRound+1. This feature intentionally preserves `sprintCount=0` from its corrective history while its approved artifacts are named `sprint-1`; use review scope `reviews/sprint-1` and do not renumber/migrate the sprint or alter the approved contract.

Legally enter feature-local Phase `3` from `2c` using installed atomic state tooling. Do not take over or modify repo-wide `.vcsdd/index.json` or `.vcsdd/active-feature.txt`; both must remain byte-identical to the starting commit with global active `fable5-config-slimdown`. Keep `sprintCount=0`.

Create only `.vcsdd/features/life-manager-daily-preflight/reviews/sprint-1/input/manifest.json`. It must be closed and explicit:

- `reviewType=implementation`, feature name, sprintNumber=1, approved `contractPath`, exact contract digest from the PASS review;
- authoritative spec inputs: behavioral spec, verification architecture, root canonical §9.5/§10 row 8d/§10.2/§10.3;
- every production module changed from `8bac59bb0`: the four production modules plus `daily-preflight.test-support.js` identified separately as test support;
- every new/changed app test, all four feature verifier helpers/tests, state, approved contract+contract review, Phase 2 RED/GREEN evidence, current source snapshot/hash/diff/coverage/logs;
- five exact review dimensions and mandatory categories from the installed adversary skill;
- explicit review base/source commits `8bac59bb0e9902fdbd3afdefd5550b9220ffecac` and `8275d5d9fd2b0ecf79d1e52270960b3ad61f40dd`;
- reviewer write scope only `reviews/sprint-1/output/**`, no network/provider/L3/final-report/deploy/merge.

Validate JSON schema/paths/digest and exact artifact coverage. Commit/push only feature-local `state.json`/history if required by legal tooling plus the new input manifest. Global index files must be absent from diff. Stop before creating output/verdict/findings or performing the review.

Return `RESULT=PHASE3-MANIFEST-READY` or `BLOCKED`, gate validation, state, manifest counts, commit, push, and `NEXT=fresh artifact-only adversary`.
