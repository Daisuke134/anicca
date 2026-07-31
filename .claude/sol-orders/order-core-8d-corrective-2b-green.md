# CORE 8d — Phase 3 iteration 1 corrective Phase 2b GREEN

You are a fresh `gpt-5.6-sol` builder. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` on `feature/lm33d-daily-preflight`. No sub-agents. Read this order, the feature `state.json`, the Phase 3 verdict and exactly FIND-001..FIND-011, then the corrective RED summary/tests. The canonical product spec is `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` at root commit `7f400ad181fb8c4d92c26964a46f4dc8b4507da2`; treat §9, §9.5, §10, §10.0, §10.2 and §10.3 as immutable requirements for this build.

## Entry gate

- Fetch first. Require local HEAD = upstream = `14001b501b4da0a6f866193813cb1a3989483fe2` and a clean worktree.
- Require `currentPhase=2a`, `sprintCount=0`, exactly 75 test beads = 13 RED + 62 GREEN, and 11 adversary-finding beads OPEN.
- Re-run the corrective tests before production edits and prove the intended starting RED: app tests `63 = 55 pass / 8 fail`; verifier contracts `12 = 7 pass / 5 fail`. Also prove the existing focused/baseline/eval suites remain GREEN.
- If any entry invariant differs, stop with `RESULT=BLOCKED`; do not normalize evidence or rewrite tests to fit implementation.

## Build — minimal GREEN for all 11 findings

Implement the production behavior demanded by the existing executable RED tests. Do not weaken assertions, replace runtime tests with source regex, or edit old Phase 2/3 review evidence.

1. **Actual CLI artifact / closed final report — FIND-001, 005, 011**
   - The real offline CLI execution path must build and atomically publish the same closed, typed 9/9 final report validated by the contract; do not leave a disconnected builder abstraction or publish the legacy shape.
   - Preserve `0600`, temp cleanup and fail-closed behavior. No hand-authored output fixture may stand in for the actual CLI artifact.
2. **Production purity — FIND-002**
   - Exported production `main` accepts no caller-controlled env/fetch/transport/dependency injection. A forged argument must be rejected before it can run.
   - Testability belongs in explicit test-support boundaries, not public production entrypoint injection.
3. **Real cancellation — FIND-003, 004**
   - Per-call timeout and hard deadline must abort/cancel the underlying in-flight provider operation, not merely reject a wrapper promise.
   - Thread `AbortSignal` through every relevant collector/provider operation and polling wait. Preserve exact attempt/delay/deadline boundaries and prohibit attempt 7 / poll 4.
4. **Substantive verifiers — FIND-006, 007, 008, 009, 010**
   - `verify-phase2-process.mjs` validates the actual historical hash/mode/trace/schema/scope/current HEAD/coverage evidence it claims to validate.
   - `verify-final-artifact.mjs` parses and applies the full closed schema plus identity/order/time/run binding/effect constraints; `{}` and every mutation fixture must fail.
   - `verify-safe-scan.mjs` reads the supplied files and fails safely on secrets, email, phone, raw correlation and provider IDs without echoing leaked content.
   - `verify-controlled-l3-gates.mjs` binds current HEAD and clean tree to exact green counts, coverage thresholds, schema proof, safe-scan proof, digest and output-absence/presence rules. Mutation fixtures must fail.
   - Helpers must use phase-appropriate inputs and must not depend accidentally on the mutable current phase.

## State/evidence discipline

- Use legal VCSDD tooling/transition `2a -> 2b`; keep `sprintCount=0` unless the official tooling explicitly requires otherwise.
- When and only when all 75 test beads pass, mark all 75 GREEN with real evidence links. Resolve/close the 11 finding beads only with the exact GREEN test/evidence that addresses each finding; retain their Phase 3 provenance.
- Create new iteration-specific corrective GREEN evidence under `evidence/sprint-1/`; never overwrite corrective RED evidence, Phase 2 evidence, Phase 3 verdict/review/gate, historical artifact, or canonical/root spec.
- Run state/runtime validators. Keep global VCSDD active feature unchanged (`fable5-config-slimdown`).

## Required fresh verification

- Existing focused baseline, full app baseline and calendar/late eval all GREEN with exact counts recorded.
- Corrective app tests: `63/63` GREEN.
- Verifier contracts: `12/12` GREEN.
- Poll/deadline `12/12`; final schema `45/45`; purity `6/6`; purity/provenance arithmetic remains `32/32`.
- All 75 test beads GREEN, 0 RED; 11 findings resolved with evidence; state `2b`; `sprintCount=0`.
- Coverage for each of the four production modules remains at least 90% lines and 90% functions; record exact module values and the exact command.
- `git diff --check`, VCSDD state/runtime validation, clean worktree after commit, HEAD=upstream after push.

## Prohibited in this atomic

- No provider/network calls, production L3, TG/email/call send, final production report, deploy, merge, panel, marketing/M-2, or canonical root spec edit.
- No test deletion/skipping/loosening, no fake evidence, no mutation of historical review artifacts, no global index ownership change.
- Do not use `git add -A`; stage only intended paths explicitly.

## Finish

Commit and push the implementation and then the immutable execution evidence (separate commits if evidence embeds the implementation SHA). Return one terminal marker:

- `RESULT=CORRECTIVE-2B-GREEN` with exact test/coverage/ledger/state counts, finding resolutions, changed files, commits, upstream SHA, and `NEXT=corrective Phase 2c`; or
- `RESULT=BLOCKED` with the exact failed gate and untouched-state proof.
