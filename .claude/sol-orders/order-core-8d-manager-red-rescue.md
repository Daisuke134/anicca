# CORE 8d — manager-review RED rescue after platform interruption

You are a fresh `gpt-5.6-sol` RED verification builder. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` on `feature/lm33d-daily-preflight`. Do not delegate. Preserve and complete the intentional uncommitted RED work left by the interrupted prior Sol. Do **not** implement GREEN.

## Sources of truth

- canonical product spec `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`, remote `feature/clip-rewards` commit `f717b4f068afb813fe3e549b97430fc3013686c4`; read §9, §9.5, §10 row 8d, §10.0, §10.2, §10.3
- original RED order `/Users/anicca/anicca-project/.claude/sol-orders/order-core-8d-final-review-red.md`
- interrupted log `/Users/anicca/anicca-project/.claude/sol-orders/logs/core-8d-final-review-red.log` — inspect only terminal cause and concise progress, do not dump it
- feature state/contract, prior Phase 3 verdict and FIND-001..FIND-011

## Entry gate — dirty state is intentional

- Fetch first. Require `HEAD == upstream == 05da7b34f685089b4402ef01f28ef40a1bc0eb2e`.
- The only intended dirty paths at entry are:
  - modified tests: `daily-preflight-final-schema.test.js`, `daily-preflight-poll-boundaries.test.js`, `daily-preflight-provenance.test.js`, `daily-preflight-purity-contract.test.js`, `transport/mail-gog-receipt.test.js`
  - new test: `daily-preflight-abort-lineage.test.js`
  - new evidence directory: `.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/manager-review-red-05da/`
- Require no production, verifier implementation, test-support implementation, state or history diff at entry.
- Re-run the current offline RED bundle exactly. Expected current observation is `112 tests = 97 PASS / 15 FAIL`; record the actual result. The 15 failures cover caller injection, deadline/abort lineage, actual observation/current-run binding and one-millisecond stale receipt.
- The previous process stopped only because Codex emitted a platform cybersecurity false positive while tests were being edited. Do not discard valid work. Use small `apply_patch` edits and compact test commands; do not paste or regenerate the already-created child-process fixture in prompts/tool calls unless a genuine test correction requires it.

## Complete the missing RED only

Finish the two missing blocker groups from the original order, primarily in `.vcsdd/features/life-manager-daily-preflight/tests/verifier-contracts.test.mjs` and isolated temp fixtures:

1. **Coverage gate bypasses**
   - missing `modules` must fail
   - extra, non-finite, or below-90 module data must fail
   - the coverage/process verifier must compare the complete changed production module set bound by baseline/green commits; the changed CLI `scripts/daily-preflight.js` must be mandatory
2. **Verifier claim bypasses**
   - safe scan must be caught ignoring a secret placed in a production `.js` fixture under a supplied directory, without echoing it
   - trace must reject broken REQ→PROP→CRIT/test reachability even when every ID token remains present
   - schemas must reject schema-invalid state/review artifacts that retain the superficial fields the current helper checks
   - scope must reject an unauthorized changed path and historical/root-spec mutation
   - stored controlled-L3 snapshot bound to `f9a35c8d2` must fail against current HEAD/tree `05da7b34f`

Mutation tests must execute the real verifier CLIs. Do not use source-regex-only assertions. Do not edit verifier implementations in this RED atomic.

## Audit all partial RED tests

- Keep every assertion only if it proves a contractual blocker and fails for the intended reason.
- It is acceptable to correct a test fixture or assertion, but it must remain RED against untouched implementation.
- Existing GREEN suites must not be weakened, deleted or skipped.
- Production `main` must be specified as zero-argument; env-only and fetch-only injection are separate failures.
- Cancellation tests target actual production signal/process boundaries. Do not demand magical cancellation of arbitrary non-cooperative JavaScript beyond the specified provider/process operations.
- One-millisecond stale receipt must remain stale through test support and fail production validation.

## Ledger/evidence discipline

- Keep `currentPhase=2b`, `sprintCount=0`; this is an in-phase manager corrective RED caught before Phase 2c. Do not fake phase transitions.
- Freshly prove the pre-existing 75 test beads remain GREEN. Create one new `test-case` bead per new executable RED assertion and link it bidirectionally to affected original FIND beads.
- Reopen the affected FIND-001..FIND-011 as OPEN using the traceability API. Do not claim any blocker resolved.
- Record exact RED/GREEN counts and commands under `evidence/sprint-1/manager-review-red-05da/`; preserve the reproduction JSON already there. Never overwrite historical evidence.
- Keep global active feature `fable5-config-slimdown` unchanged.
- Run installed VCSDD state/runtime validation and record honest incompatibilities; do not hand-edit around them.

## Prohibited

- No production/verifier/test-support implementation edits, provider/network/TG/email/call, L3, final production report, deploy, merge, panel, marketing, canonical root spec edit, or global index ownership change.
- Do not use `git add -A`; stage exact intended paths.

## Finish

- Run `git diff --check` for the new diff and the full intended RED suites.
- Prove implementation diff from `05da7b34f` is zero.
- Fetch, commit, push, then verify clean worktree and `HEAD == upstream`.
- Return one terminal marker:
  - `RESULT=MANAGER-REVIEW-RED` with commit, exact old/new total PASS/FAIL counts, new bead IDs/count, reopened findings, state and `NEXT=fresh corrective GREEN Sol`; or
  - `RESULT=BLOCKED` with exact invariant and preserved dirty-state proof.
