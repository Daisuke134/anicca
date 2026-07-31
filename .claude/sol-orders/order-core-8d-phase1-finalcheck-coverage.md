# CORE-a 8d — final-check correction for FIND-006 coverage consistency

You are a fresh `gpt-5.6-sol` Phase 1 spec builder. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` at exact clean commit `157e67478db9c2734916788a78e4f27af697f236`, branch `feature/lm33d-daily-preflight`, PR #330. Do not spawn another agent.

This is one narrow orchestrator final-check correction within FIND-006. Do not change app source/tests, state phase/gates/history, contract approval/status, review artifacts, historical evidence, root canonical spec, providers, deployment, or PR merge state. No Phase 2/L3/network side effect.

Read the current behavioral spec, verification architecture lines 77-123, draft contract, iteration-2 resolution, state, and the actual `f6129abb5..58846034b` app diff plus the planned Phase 2 atomic-output requirement.

Correct the internal coverage contradiction:

- The exact coverage command currently includes planned production modules `lib/daily-preflight.js`, `lib/daily-preflight-collectors.js`, and `lib/transport/mail-gog.js`, because Phase 2 is expected to change the CLI/report writer for atomic output in addition to collector/mail behavior.
- The Coverage acceptance paragraph currently names only the latter two. Replace it so each of those three planned modules independently requires lines `>=90.00%` and functions `>=90.00%`, and every additional production module actually changed during Phase 2 is automatically subject to the same independent thresholds.
- The future `verify-phase2-process.mjs coverage` contract must compare the Phase 2 production diff against the coverage table and fail on any missing module, combined-only average, sub-threshold lines, or sub-threshold functions.
- Ensure the matrix row, Coverage acceptance paragraph, CRIT-005, and iteration-2 resolution are consistent. Do not alter fixed test arithmetic unless an actual contradiction is proven.

Freshly verify state/runtime, contract schema, traceability, `git diff --check`, exact allowed staged scope, iteration-1/2 review immutability, historical hashes/modes, safe scan, clean start, and local/upstream/origin/PR equality. Commit/push only the minimal Phase 1 spec/contract/resolution files actually needed; state and history should remain byte-identical unless installed tooling strictly requires otherwise. Verify final PR head equality.

Return exactly:

```text
RESULT: ITERATION-3-REVIEW-READY|BLOCKED
COVERAGE: <planned modules and dynamic changed-module rule>
STATE: <phase/gate/human/sprint unchanged>
VALIDATION: <fresh exits>
COMMIT: <hash or none>
PUSH: <local/upstream/origin/PR equality>
NEXT: fresh Phase 1c iteration-3 only
```
