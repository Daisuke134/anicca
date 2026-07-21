# CORE 8d — manager-review corrective Phase 2b GREEN

You are a fresh `gpt-5.6-sol` implementation builder. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` on `feature/lm33d-daily-preflight`. Do not delegate. Implement and verify this one atomic only; do not advance to Phase 2c or run production side effects.

## Sources of truth

- canonical product spec `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`, root branch commit `face0dad28df390225ca9948fd635ea04e26bfcd`; read §9, §9.5, §10 row 8d, §10.0, §10.2 and §10.3
- this feature's `state.json`, approved sprint contract, Phase 3 verdict and exactly FIND-001..FIND-011
- RED evidence `.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/manager-review-red-05da/summary.md`
- executable tests at exact base `ba370ef67d4a85aa090d7711268059ed1521f4ca`; tests are the acceptance contract

## Entry gate

- Fetch first. Require clean worktree and `HEAD == upstream == ba370ef67d4a85aa090d7711268059ed1521f4ca`.
- Require `currentPhase=2b`, `sprintCount=0`, exactly 75 GREEN test beads + 26 RED test beads, and FIND-001..FIND-011 OPEN. Require global active feature remains `fable5-config-slimdown`.
- Re-run the exact full intended manager-review bundle before any implementation edit:

```text
node --test --test-concurrency=1 apps/life-call/lib/daily-preflight-final-schema.test.js apps/life-call/lib/daily-preflight-poll-boundaries.test.js apps/life-call/lib/daily-preflight-provenance.test.js apps/life-call/lib/daily-preflight-purity-contract.test.js apps/life-call/lib/transport/mail-gog-receipt.test.js apps/life-call/lib/daily-preflight-abort-lineage.test.js .vcsdd/features/life-manager-daily-preflight/tests/verifier-contracts.test.mjs
```

- Expected RED is `137 tests = 111 PASS / 26 FAIL`, and every failure name begins `manager RED:`. Separately reproduce the pre-existing selection as `75/75 GREEN` using the exact command in the RED summary.
- If entry facts differ, stop with `RESULT=BLOCKED`; do not normalize state or rewrite tests to fit implementation.

## TDD constraint

- The RED tests in `ba370ef67` are frozen. Do not edit, delete, skip, rename, weaken or replace them. Do not solve runtime contracts with source-regex-only assertions.
- Make the minimum production, verifier and explicit test-support implementation changes that turn all 26 genuine RED assertions GREEN while retaining every existing GREEN suite.

## Build requirements

1. **Zero-argument production entrypoint / caller purity**
   - Exported production `main` has arity zero and rejects any supplied argument before reading caller data or causing any side effect.
   - Caller-controlled env, fetch, transport, collectors or dependencies never enter production execution. Testing seams remain only in explicit test-support boundaries.

2. **Real abort lineage and deadline behavior**
   - Remove global timer mutation. Use owned timers and an `AbortController` lineage.
   - Thread the parent `AbortSignal` through every in-flight provider request, child process, inbox poll and wait used by the controlled path. Deadline rejection must abort those supported operations so they cannot create a later provider/process effect.
   - Replace synchronous gog process execution with the Node abort-capable async child-process API while preserving exact argv/env parsing, timeout/error mapping and receipt behavior.
   - Preserve all established attempt/poll/delay/deadline boundaries; attempt 7 and poll 4 remain forbidden. Do not claim magical cancellation for arbitrary non-cooperative JavaScript outside these owned provider/process boundaries.

3. **Actual observation and current-run binding**
   - Create the internal run correlation and run start before the first dependency collection.
   - Each collector returns its actual observation time and the same internal run correlation. Preserve each dependency's distinct `checkedAt`; never replace them with final `generatedAt`.
   - Reject missing, mismatched, pre-run, future or stale observations. Serialized validation must bind `runRef` to the current internal run rather than accepting an arbitrary nonzero digest. Raw correlation remains absent from serialization.

4. **Receipt freshness boundary**
   - Explicit test support must preserve source timestamps. A receipt even 1 ms before the send boundary remains stale and production validation rejects it. Do not rewrite stale fixtures to the send time.

5. **Complete changed-module coverage proof**
   - Coverage/process verification derives the complete changed production-module set from the baseline/green commit binding; it must not rely on a permissive fixed subset.
   - Changed `apps/life-call/scripts/daily-preflight.js` and every additional changed production module are mandatory. Missing/extra module entries, missing `modules`, non-finite values or lines/functions below 90% fail closed.
   - Generate real coverage for every changed production module. Each module must independently reach at least 90% lines and 90% functions; do not aggregate away a weak module.

6. **Substantive verifier behavior**
   - `verify-safe-scan.mjs` recursively scans the supplied eligible text, including production `.js`, and fails without echoing matched secret/PII/provider material.
   - trace verification parses the declared relations and proves REQ→PROP→CRIT→test reachability; mere ID-token presence is insufficient.
   - schema verification applies the installed VCSDD schemas to state/review/finding artifacts; superficial field checks are insufficient.
   - scope verification compares bound commits/trees and rejects unauthorized changed paths, historical evidence mutation and canonical root-spec mutation.
   - controlled-L3 gate requires a complete finite per-module coverage object, exact current HEAD/clean-tree binding and the other contract proofs. The historical `f9a35c8d2` snapshot must remain rejected against newer source.

## State and evidence

- Remain in `currentPhase=2b`, `sprintCount=0`; this is an in-phase manager correction. Do not fake a transition.
- Only after fresh GREEN, use the official traceability API to mark all 101 test beads GREEN and resolve FIND-001..FIND-011 with bidirectional links to the exact GREEN tests/evidence. Retain the original Phase 3 provenance.
- Write new immutable evidence under `.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/manager-review-green-ba370/`. Never overwrite prior RED/GREEN/L3/review evidence.
- Record exact commands, total counts, per-module coverage, changed-module derivation, state/runtime/schema validation, diff scope and commit binding. Evidence must describe actual command output, not self-attestation.
- Keep global active feature `fable5-config-slimdown` unchanged.

## Required fresh verification

- Full intended manager-review bundle: `137/137 PASS`, zero fail/skip/cancel.
- Pre-existing test-bead selection: `75/75 PASS`.
- Re-run the prior focused baseline, full app baseline and calendar/late eval commands from immutable evidence; all retain their recorded GREEN counts.
- Run the complete verifier-contract suite and all directly affected app suites, not only a name-filtered subset.
- Every changed production module: lines >=90% and functions >=90%, with exact real coverage command and artifact.
- Installed VCSDD state validator and runtime validator PASS; installed schema validation PASS for state, verdict and FIND-001..FIND-011.
- `git diff --check`, no test diff from `ba370ef67`, no historical evidence/root-spec/global-index mutation, and only authorized implementation/state/new-evidence paths changed.
- Ledger after verification: 101 GREEN test beads, 0 RED; 11 findings RESOLVED; state `2b`; `sprintCount=0`.

## Prohibited

- No provider/network/TG/email/call, production L3, final production report, deployment, PR merge, panel, marketing/M-2, canonical root-spec edit or global active-feature ownership change.
- No test modification, fake evidence, DB flag as proof, historical evidence mutation, dependency-version churn or unrelated refactor.
- Do not use `git add -A`; stage only exact intended paths.

## Finish

- Fetch, stage exact paths, commit and push. If evidence must bind the implementation commit, use a separate evidence/state commit.
- Verify clean worktree and `HEAD == upstream` after push.
- Return exactly one terminal marker:
  - `RESULT=MANAGER-REVIEW-GREEN` with implementation/evidence commits, `137/137`, `75/75`, per-module coverage, `101 GREEN / 0 RED`, `11 RESOLVED`, state/sprint, changed paths, upstream SHA and `NEXT=fresh artifact-only adversarial review`; or
  - `RESULT=BLOCKED` with the exact invariant and preserved-state proof.
