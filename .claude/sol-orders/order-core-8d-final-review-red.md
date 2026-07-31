# CORE 8d — manager/fresh-review FAIL corrective RED

You are a fresh `gpt-5.6-sol` verification builder. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` on `feature/lm33d-daily-preflight`. Do not delegate. This atomic is **RED + truthful ledger only**: do not implement GREEN fixes.

Read completely before acting:

- canonical product spec `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` at root commit `f93b949dc` — §9, §9.5, §10 row 8d, §10.0, §10.2, §10.3
- previous corrective order `/Users/anicca/anicca-project/.claude/sol-orders/order-core-8d-corrective-2b-green.md`
- feature state/contract, prior Phase 3 verdict, FIND-001..FIND-011, and `evidence/sprint-1/corrective-green-iteration-1/summary.md`

## Entry gate

- Fetch first. Require clean worktree and `HEAD == upstream == 05da7b34f685089b4402ef01f28ef40a1bc0eb2e`.
- Require state `currentPhase=2b`, `sprintCount=0`, 75 test beads GREEN, 11 finding beads RESOLVED.
- Re-run only enough offline baseline to prove current claims: corrective app `63/63`, verifier contracts `12/12`, focused `51/51`, baseline `371/371`, eval `33/33`. No provider/network/L3.
- Independently reproduce all six blockers below before editing tests. If any differs, record exact observation; never normalize evidence to the expected answer.

## Six manager/fresh-review blockers to encode as independent RED

1. **Caller injection still works**
   - `apps/life-call/scripts/daily-preflight.js#main` rejects only a `transport` property but accepts caller `env` and `fetchImpl`.
   - Add separate tests for `env`-only and `fetchImpl`-only injection. Do not bundle them with `transport`; each must reject before the fake is called.
   - Remove the contradictory expectation in provenance tests that production `main({ argv, env, fetchImpl, collectors })` is a valid test boundary. Production `main` must be zero-argument; testability belongs in explicit test-support entrypoints.
2. **Underlying deadline/cancellation is incomplete**
   - `withinDeadline` temporarily mutates `global.setTimeout`; a timer/effect created after the operation's first `await` can continue after rejection.
   - `mail-gog.js` uses synchronous `execFileSync` and accepts no AbortSignal, so the email hard deadline cannot cancel the inbox operation.
   - RED must prove: no global timer mutation; every real provider/poll/wait boundary receives the same abort lineage; the gog transport uses an abort-capable asynchronous process boundary and deadline abort prevents a post-deadline effect. Do not require impossible cancellation of arbitrary non-cooperative JavaScript; test the actual production operations and signal discipline.
3. **Final observation time/current-run binding is fabricated**
   - `buildFinalPreflightReport` creates correlation after collection and assigns every dependency `checkedAt=generatedAt` instead of actual observation time.
   - RED must require the run correlation/start to exist before collection, every dependency result to carry its actual `checkedAtMs` and the same internal correlation, reject absence/mismatch/stale/future, preserve distinct real observation times, and reject an arbitrary nonzero serialized `runRef` that is not bound to the current internal correlation.
4. **Coverage gate can be bypassed**
   - `verify-controlled-l3-gates.mjs` accepts evidence with `modules` deleted.
   - `verify-phase2-process.mjs coverage` omits changed production CLI/module enforcement.
   - RED must make missing/extra/nonfinite/below-90 module data fail and must derive/compare the complete changed production module set between the bound baseline and green commits. `scripts/daily-preflight.js` is mandatory for this change.
5. **Test harness rewrites stale receipt to fresh**
   - Remove the test expectation that permits `core8d-runtime-harness.js` to rewrite a receipt up to one second older than `afterMs`.
   - RED must demonstrate one-millisecond stale remains stale through the harness and is rejected by production validation. Do not edit production or harness GREEN behavior in this atomic.
6. **Declared verifiers do not verify their full claims**
   - safe scan directory traversal currently excludes production `.js`.
   - trace mode checks token presence rather than real REQ→PROP→CRIT/test reachability.
   - schemas mode checks a few fields rather than applying installed schemas.
   - scope mode checks HEAD/tree only, not the changed-path allowlist and historical/root-spec exclusions.
   - RED mutation fixtures must independently prove each bypass, including a secret in production JS, broken graph linkage with all IDs still present, schema-invalid state that preserves superficial fields, and an unauthorized changed path.
   - Stored controlled-L3 snapshot must be rejected when its green commit/tree is not current HEAD/tree.

## RED integrity

- Follow TDD: tests/fixtures first; run them and show genuine failures against untouched production/verifier implementation.
- Do not weaken/delete/skip existing tests. Do not patch production files, verifier implementation files, or test-support harness to make GREEN.
- New mutation tests must assert behavior, not source regex alone. Error output must not echo PII/secrets.
- Keep existing 75 beads GREEN only if freshly passing. Create exact new test-case beads for every new RED assertion and link them to the affected original finding beads. Reopen affected FIND-001..FIND-011 as OPEN using the traceability API; do not claim the six blockers resolved.
- Because the manager caught this before Phase 2c, keep `currentPhase=2b` and `sprintCount=0`; do not fake `2b→2a`, `2b→2c`, or Phase 3 transitions. Record this as an in-phase corrective RED audit in state/history/evidence.
- Evidence goes only under a new `evidence/sprint-1/manager-review-red-05da/` directory. Do not overwrite historical or previous corrective evidence.
- Keep global active feature `fable5-config-slimdown` unchanged.

## Required verification and finish

- Record exact baseline counts and exact new RED test IDs/counts.
- Prove production/verifier/test-support implementation diff is zero relative to `05da7b34f`; only new/updated tests, fixtures, feature state/history/review evidence are allowed.
- Run `git diff --check` on the new commit range; do not inherit the prior range's whitespace debt into new files.
- Run VCSDD state/runtime validators and report any honest incompatibility rather than hand-editing around it.
- Fetch, stage exact intended paths only, commit, push, verify clean and `HEAD==upstream`.
- No provider/network/TG/email/call, production L3, final production report, deploy, merge, panel, marketing, or canonical root spec edit.

Return exactly one terminal marker:

- `RESULT=MANAGER-REVIEW-RED` with commit, counts, reopened findings, state, and `NEXT=fresh corrective GREEN Sol`; or
- `RESULT=BLOCKED` with the exact failed invariant and untouched-state proof.
