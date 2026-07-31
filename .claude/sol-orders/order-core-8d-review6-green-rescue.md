# CORE 8d — review6 GREEN false-pass rescue

You are a fresh `gpt-5.6-sol` rescue builder. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` on `feature/lm33d-daily-preflight`. Do not delegate. The prior GREEN agent was stopped before commit because it produced a test-harness clock false PASS and a coverage regression. Preserve and audit the uncommitted work; correct it, then complete the original GREEN order. Do not discard useful changes and do not implement by weakening tests.

## Exact entry state

- Fetch first. Require `HEAD == upstream == 09dbd5ef546cec6027ea760c41bfbb1d27a27305`.
- There must be no commit after that SHA and exactly these eight dirty paths:
  - `.vcsdd/features/life-manager-daily-preflight/tests/verify-controlled-l3-gates.mjs`
  - `.vcsdd/features/life-manager-daily-preflight/tests/verify-final-artifact.mjs`
  - `.vcsdd/features/life-manager-daily-preflight/tests/verify-phase2-process.mjs`
  - `.vcsdd/features/life-manager-daily-preflight/tests/verify-safe-scan.mjs`
  - `apps/life-call/lib/daily-preflight-collectors.js`
  - `apps/life-call/lib/daily-preflight.js`
  - `apps/life-call/lib/daily-preflight.test-support.js`
  - `apps/life-call/test-support/core8d-runtime-harness.js`
- Current expanded suite may be `142/142`, but the coverage command is known to be `149 total / 148 pass / 1 fail` with `production receipt bounds come only from the gog parser`, and collectors line coverage `88.80%`. Treat that as RED, not progress.
- Read the original order `order-core-8d-review6-green.md`, canonical spec sections, RED evidence, and this rescue order completely.
- If the exact worktree topology differs, return `RESULT=BLOCKED` without normalization.

## Mandatory corrections before any commit

1. **Real receipt boundary — no harness false PASS**
   - Production currently records `sentAtMs` before awaiting Resend. That can accept a receipt before actual send.
   - In production `collectEmailWithSignal`, record the conservative boundary only after Resend returns a valid accepted ID and before inbox polling. A receipt one millisecond before that boundary must reject.
   - Restore the existing signal-aware conditional call shape so the immutable provenance test `/findReceipt\(\{ nonce, afterMs: sentAtMs \}\)/` remains GREEN; the real withinDeadline path must still pass `signal`.
   - In `core8d-runtime-harness.js`, delete `receiptUsesQuery`, `Date.now()+1`, function-arity inference, and all source rewriting of `sentAtMs`. No clock guessing or behavior-dependent clock. The harness may inject transports/nonces/sleep only; production computes its own boundary.
   - Re-run the receipt RED, six-attempt poll test, provenance test, and coverage command. All must pass.

2. **Coverage regression**
   - Do not add coverage ignore directives.
   - Restore all immutable test contracts. Get the exact coverage suite fully GREEN and all four changed modules to >=90% lines and >=90% functions.
   - Do not change tests to raise coverage.

3. **Exact proof closure**
   - Allowed post-implementation evidence directory is exactly `manager-review6-green-09db/`, not wildcard `manager-review6-[^/]+`.
   - Exact allowed paths after implementation: feature `state.json`, global `.vcsdd/history.jsonl`, FIND-012..017 resolution documents, and files below that one new GREEN evidence directory only.
   - RED evidence, any other evidence directory, old findings, tests, production, root spec, and global active-feature file must fail closure.
   - Both process and controlled-L3 verifiers must use the identical exact allowlist and descendant/app-tree rules.

4. **Privacy scanner without value-specific exemptions**
   - Remove global replacement/masking of `+818012345678` or any concrete phone/email/secret/correlation/provider value.
   - No production literal allowlist and no detector that silently skips arbitrary regex literals in production.
   - Self-literals may be handled only for the scanner's own detector-definition source in a deterministic narrow way, while every other scanned production/current evidence file receives the full detector set.
   - Fresh isolated fixtures for secret, email, phone, raw correlation, and provider ID must each exit nonzero with no matched content printed. Recursive positive scan must exit zero, exclude node_modules/build/dist/coverage/test fixtures, and output its measured unique path count.

5. **Same-run and portable schema**
   - Keep the useful removal of `CURRENT_RUN_REFS`; confirm production CLI performs live same-invocation validation before serialization/publication and a serialized report alone cannot claim same-run provenance.
   - Offline artifact verifier may validate closed shape only and must not claim same-run proof.
   - Injected `CLAUDE_PLUGIN_ROOT` must be honored exactly. Normal discovery must be portable/version-aware, contain no absolute `/Users/anicca` path, and fail closed when neither injected nor installed root exists.

## Completion topology

- Tests remain byte-identical to base `09dbd5ef5`.
- First create an implementation commit containing only the eight implementation/verifier/test-support paths above (or a strict subset). Before committing: expanded `142/142`, old `75/75`, focused `52/52`, full app `372/372`, eval `33/33`, deadline `6/6`, coverage 4/4 >=90, privacy positive and five negatives, state/runtime/schema/trace PASS.
- Then use official VCSDD APIs to set TEST-102..107 GREEN and FIND-012..017 RESOLVED with reciprocal links intact. Update only state/history, those six finding documents, and new immutable `manager-review6-green-09db/` evidence.
- The tracked snapshot binds the implementation commit and app tree. At final clean evidence commit, replay scope/coverage/final-artifact/controlled-L3 dry gates from tracked paths; all exit zero without provider/L3 execution.
- Preserve `currentPhase=2b`, `sprintCount=0`, active feature `fable5-config-slimdown`. No network/TG/email/call/provider/L3/deploy/merge/root-spec edit.
- Push both commits and prove clean `HEAD == upstream`.

Return `RESULT=REVIEW6-GREEN` with both SHAs, exact suite/coverage/privacy/closure/state counts and `NEXT=fresh artifact-only review`, or `RESULT=BLOCKED`.
