# CORE 8d — review6 corrective Phase 2b GREEN

You are a fresh `gpt-5.6-sol` Phase-2b GREEN builder. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` on `feature/lm33d-daily-preflight`. Do not delegate. Fix exactly the six executable RED contracts from commit `09dbd5ef546cec6027ea760c41bfbb1d27a27305`, verify them honestly, update VCSDD through official APIs, commit/push, and stop. Do not enter Phase 2c or perform any provider/L3 side effect.

## Sources and entry gate

- Fetch first. Require clean worktree and `HEAD == upstream == 09dbd5ef546cec6027ea760c41bfbb1d27a27305`.
- Read canonical spec §9, §9.5, §10 row 8d, §10.0, §10.2, §10.3.
- Read `.vcsdd/features/life-manager-daily-preflight/` state, contract, verification architecture, FIND-012..017, and RED evidence `evidence/sprint-1/manager-review6-red-a5dc/`.
- Reproduce exact RED first: expanded `142 total / 136 pass / 6 fail`, old selection `75/75`, focused/full/eval `52/372/33`, signal-aware deadline boundaries `6/6`, state/runtime/schema/trace PASS, 101 historical test beads GREEN + TEST-102..107 RED, 11 historical findings RESOLVED + FIND-012..017 OPEN, `currentPhase=2b`, `sprintCount=0`, global active feature `fable5-config-slimdown`.
- If any entry invariant differs, make no edits and return `RESULT=BLOCKED`.

## TDD and immutability

- The six RED tests and every earlier test are the contract. Do not skip, delete, rename, regex-substitute, weaken, or change expected outcomes.
- Implement the smallest production/verifier/test-support corrections. No dependency churn or unrelated refactor.
- Work one blocker at a time; after each fix run its exact RED test and the nearest regressions.
- Do not alter canonical root spec, panel, marketing, deployment, provider credentials, launchd, network, TG, email, or call behavior.

## Required GREEN behavior

1. **Tracked evidence closure without self-hash**
   - Replace exact-current-HEAD/self-reference logic with a non-circular proof.
   - A tracked snapshot binds an immutable implementation commit and exact `apps/life-call` tree.
   - Final HEAD must be a clean descendant; the current app tree must equal the bound tree.
   - Every commit/path after implementation must be inside a declared closure containing only current VCSDD state/history, FIND-012..017 resolution documents, and the new review6 GREEN evidence directory. Production, tests, root spec, global index, old findings, and historical evidence after the bound commit must fail.
   - Scope, coverage, final-artifact, and controlled-L3 gates must all evaluate the same final clean HEAD/app tree and be replayable from tracked files. No tracked file may be required to contain its own future commit hash. Record observed final HEAD only as post-run evidence, never as preauthorization.
   - Preserve and pass existing negative tests for unauthorized/historical/root-spec/app-tree changes.

2. **Same-invocation final-report provenance**
   - Remove `CURRENT_RUN_REFS`, empty-set fallback, and any module-global run history.
   - Building a report must create explicit ephemeral provenance tied to that invocation; live validation must require that exact provenance. A serialized report alone, a prior invocation, or a fresh-process arbitrary runRef must fail.
   - Keep raw correlation, provider IDs, and the provenance capability out of the serialized final report/evidence.
   - Production CLI must validate before atomic publication using the same invocation's provenance. Offline schema validation may validate shape, but may not claim same-run proof.

3. **Deadline truthfulness**
   - Remove test-support timer deletion/AsyncLocalStorage behavior that changes operation semantics.
   - Keep `withinDeadline` honest: abort signal lineage must reach every supported provider/process/poll/wait boundary; signal-aware operations cancel, while arbitrary non-cooperative JavaScript is not magically erased.
   - The six corrected signal-aware timeout/deadline tests and the non-cooperative timer test must all pass.
   - Ensure gog/process cancellation uses a supported abort/kill boundary with deterministic cleanup; no orphaned process/timer.

4. **Receipt boundary integrity**
   - Remove the harness source transform that subtracts 1000 ms or otherwise rewrites `sentAtMs`.
   - If deterministic time is needed, use a clock seam contained wholly in test support without modifying production source semantics.
   - Receipt at actual send minus 1 ms must reject; exact valid boundary remains accepted; nonce/identity/recipient constraints remain fail-closed.

5. **Portable VCSDD schema discovery**
   - Remove Dais-specific `/Users/anicca/.codex/plugins/cache/...` imports from repository verifiers.
   - Resolve the installed VCSDD plugin from explicit `CLAUDE_PLUGIN_ROOT` or another documented injected root, validate the expected module exists under that root, and fail closed with a clear non-sensitive error when absent.
   - The injected-root test must prove that root is actually used; normal installed state/runtime/schema/trace validation must still pass.

6. **Recursive privacy scan truthfulness**
   - Make the architecture-declared recursive scope deterministic and executable.
   - Exclude dependency/build/VCS directories and declared test fixtures without excluding changed production or required current feature/evidence artifacts.
   - Detector source literals must not self-trigger, while separate injected secret, email, phone, raw-correlation, and provider-ID fixtures must each fail.
   - Output the measured unique path count; no hardcoded count. Never print matched secret/PII content or provider IDs.
   - Existing safe-scan, scope, trace, coverage, schema, and final-artifact negative controls remain fail-closed.

## Commit/proof topology

Use two exact commits so the proof is non-circular:

1. **Implementation commit**: only production/verifier/test-support implementation paths necessary for the six fixes. Tests are already present and must remain byte-identical to RED base. Run the full expanded suite GREEN before committing.
2. **State/evidence commit**: through official VCSDD APIs, transition TEST-102..107 RED→GREEN and FIND-012..017 OPEN→RESOLVED with reciprocal links intact; update only state/history, those six finding resolution documents, and a new immutable evidence directory:
   `.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/manager-review6-green-09db/`.

The new tracked snapshot must bind the implementation commit/tree and declare the exact allowed post-implementation closure. Do not overwrite any prior evidence.

## Fresh verification before finish

At final clean HEAD run and record exact exit codes:

- expanded intended manager suite: all `142/142`;
- old selection `75/75`, focused `52/52`, full app `372/372`, eval `33/33`;
- corrected signal-aware boundaries `6/6`;
- module line/function coverage for daily-preflight, collectors, mail-gog, CLI all >=90%;
- official state/runtime validators plus repository schema/trace/scope/coverage/final-artifact/controlled-L3 gate dry checks;
- recursive privacy positive scope plus five isolated negative fixtures;
- 107 test beads GREEN, 17 findings RESOLVED, reciprocal links PASS;
- `currentPhase=2b`, `sprintCount=0`, active feature unchanged;
- no provider/network/TG/email/call/L3 side effect;
- clean `HEAD == upstream`.

Stage exact paths only. Push both commits to `origin/feature/lm33d-daily-preflight`. Return exactly one terminal marker:

- `RESULT=REVIEW6-GREEN` with implementation commit, evidence commit/final SHA, suite counts, coverage values, state/link counts, closure replay exits, privacy positive/negative exits, clean upstream SHA, `NEXT=fresh artifact-only review`; or
- `RESULT=BLOCKED` with the exact invariant and preserved-state proof.
