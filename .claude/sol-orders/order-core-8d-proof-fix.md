# CORE-a / 8d proof-provenance correction order

You are a fresh builder Sol for PR #330. Fix only the four blockers from the post-commit artifact review with strict TDD. Do not call any production/provider API, do not send Telegram/email, do not dial, do not rerun production smoke, and do not merge. Update the spec truthfully, commit scoped changes, and push the existing branch.

Done means: a caller cannot forge green readiness with a JSON proof file; controlled L3 results are collected and bound by the same explicit runner and emitted by the report generator; final evidence serialization is allowlisted and cannot retain unclassified strings/opaque URLs/PII/provider errors; every critical negative branch has a direct test; all local tests/eval/coverage pass; 8d remains pending until a later fresh production run.

Working method (non-negotiable):
1. Restate the goal + done criterion.
2. Read actual files and verify paths/symbols.
3. Check the riskiest assumption first.
4. RED first, then minimal GREEN, then refactor.
5. Label VERIFIED / REASONED / ASSUMED.
6. Re-read this order before finishing.

## Workspace and source

- Worktree `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`
- Branch `feature/lm33d-daily-preflight`
- Start head `145f18dd19b49096c4fdef46be5ce7f92df5e474`
- PR `https://github.com/Daisuke134/anicca-products/pull/330`
- Spec row `8d CORE-a`, §10.2–10.3
- Existing production artifact remains truthful historical evidence: `.vcsdd/features/life-manager-daily-preflight/evidence/daily-preflight-20260721T064624Z.json`, 6/9 and pending. Do not rewrite it as if a new smoke occurred.
- Review log read-only: `/Users/anicca/anicca-project/.claude/sol-orders/logs/core-8d-postcommit-review.log`

Use CodeGraph first if the worktree has its own index; otherwise inspect exact files directly. Search existing repo/GitHub primary implementations before inventing a new proof mechanism. Use `gh`, `crwl`, or Context7 only; no WebSearch/WebFetch.

## Four verified blockers

1. `daily-preflight.js` accepts caller-supplied `proofs.email` booleans/current timestamp/dummy SHA and returns pass; even `attempted` is not required.
2. sanitizer retains opaque hostname, a person's name in a generic string, and provider error text.
3. artifact `controlledL3` is manually appended outside the report schema; the stated CLI command cannot generate it or preserve validated `checkedAt`, so artifact provenance/freshness is not reproducible.
4. tests do not independently mutate stale proof, Telegram pending/missing update, Telnyx number-connection/profile/webhook/WSS/auth mismatch, and both Gemini method failures.

## TDD requirements

Write failing tests first and record compact RED names/count for:

- public CLI rejects/removes arbitrary `--proofs <file>` as a route to green;
- email requires an actual same-run collector result with `attempted=true`, provider acceptance, owned recipient, inbox receipt, nonempty provider/message references, and bounded freshness;
- Telegram requires an actual same-run collector result, exact URL, allowed updates, no provider error, bounded freshness, and the backlog policy defined below;
- controlled results are included by report-generation code as `controlledL3`, with `checkedAt` and hashed references, and the JSON artifact is produced entirely by that code without manual patching;
- stale/missing/malformed collector results fail nonzero;
- Telegram pending backlog and missing allowed update each fail with the correct class; a completed same-run round trip cannot be overridden by a transient update that is proven to be the just-consumed request—design this explicitly, do not silently ignore arbitrary backlog;
- Telnyx number/connection/profile/webhook, WSS path/host, bridge auth-gate, and secret placeholder each fail independently;
- Gemini Live bidi missing and standard generateContent missing each fail independently;
- sanitizer replaces unknown string values, opaque/unapproved URL hosts or paths, names in generic strings, error/provider-response values, tokens, queries, IDs, phone/email, nested raw text;
- final serialization uses an explicit evidence schema/allowlist. Regex-only best effort is insufficient. Safe booleans/numbers/enums/hashes may remain; unknown strings become a redacted marker or are dropped.

## Implementation constraints

- Default preflight remains read-only and fail-closed when controlled L3 is absent.
- Controlled L3 must be an explicit mode in the same runner. It invokes fixed in-repo collectors/adapters; it must not accept arbitrary proof JSON/booleans from the caller.
- Collectors may be dependency-injected for tests. The production CLI wiring must point to fixed code paths, not an arbitrary command or proof file.
- The later production run is allowed to perform exactly one controlled TG/email proof, but this task must not execute it.
- `runPreflight` or a single higher-level report builder must emit validated `controlledL3` metadata and dependency results together. No manual artifact mutation.
- Preserve shared Maps acceptance and scheduler cohort contracts from head `145f18dd`.
- No production env/schema/credential/billing/deploy changes.

## Verification and git

Run exact exits/counts for focused tests, full `npm test`, `npm run eval`, coverage on changed production modules (>=90% lines/functions), `node --check`, `git diff --check`, and artifact/diff sensitive-value scans. Do not run Railway/provider commands.

Update spec row 8d as `pending` with local RED/GREEN evidence and the explicit statement that production remains the prior 6/9 artifact pending a later controlled rerun. Do not touch 8e.

Fetch, stage explicit scoped paths only, commit, push `feature/lm33d-daily-preflight`, verify remote head and clean worktree. Do not invoke nested review; main orchestrator handles fresh review after push.

Final stdout: start/end head, files, RED, GREEN, full test/eval/coverage, no-side-effect statement, spec state, commit/push/PR, and any blocker.
