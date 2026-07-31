# CORE-a / 8d proof correction rescue 2

Take over the dirty worktree at `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`, branch `feature/lm33d-daily-preflight`, committed head `145f18dd19b49096c4fdef46be5ce7f92df5e474`. A prior Sol was stopped immediately after adding `apps/life-call/lib/daily-preflight-provenance.test.js` because its Telegram test invented a nonexistent `lastUpdateId` correlation. No production implementation for this pass has been added yet.

Fix the four post-commit blockers with strict TDD, then update spec as pending, commit scoped files, and push. Do not use Railway/provider APIs, do not send Telegram/email, do not dial, do not run production smoke, do not deploy/merge, and do not spawn nested reviewers.

Working method: restate goal/done; verify head/status; check riskiest assumption first; RED→minimal GREEN→refactor; label VERIFIED/REASONED/ASSUMED; re-read order before finish.

## Hard correction to the saved RED

Telegram Bot API `getWebhookInfo` does not expose `lastUpdateId`, and a Telethon message ID is not a webhook `update_id`. Therefore:

- delete the `consumedUpdateId` / `lastUpdateId` exception from the saved test;
- do not introduce those fields or any equivalent self-reported correlation;
- the fixed same-run collector must perform the real round trip and then bounded-poll the actual `getWebhookInfo.pending_update_count` until it reaches 0;
- report green only when the final observed backlog is exactly 0, allowed updates are complete, URL is exact, provider error is absent, and proof freshness is valid;
- if backlog remains nonzero after the bounded poll, fail `telegram_backlog`. No exception.
- tests use injected poll samples and clock: `[1, 0]` passes after drain; `[1, 1, 1]` fails; missing allowed update fails; stale/malformed proof fails. No real network in this task.

## Required blockers

1. Remove public arbitrary `--proofs` JSON acceptance. A caller must not turn readiness green with booleans/current time/dummy hashes.
2. Add explicit same-run controlled mode using a fixed in-repo collector registry. Dependency injection is for tests only; production CLI cannot select arbitrary commands/files. Default mode stays read-only/fail-closed.
3. Email collector result requires attempted, provider accepted, owned recipient, inbox receipt, provider ref, Message-ID ref, and bounded checkedAt. Missing/false/stale/malformed fails.
4. A single report builder emits dependency results and validated `controlledL3` with checkedAt and hashed refs. No manual artifact mutation.
5. Final evidence uses closed allowlisted schemas. Safe booleans/numbers/enums/hash refs only. Unknown strings, names, opaque URLs/hosts/paths, error/provider-response strings, query/token/ID/phone/email/nested raw text are dropped or `[REDACTED]`.
6. Direct negative table tests: Telegram drain/missing updates; email required fields/freshness; Telnyx number↔connection/profile/webhook/WSS/auth/placeholder secret mismatches; Gemini Live bidi and standard generateContent missing; location stale/missing; all nonpass exits nonzero and timeout abort remains covered.
7. Preserve shared Maps acceptance and scheduler cohort semantics from head `145f18dd`.

Read the original review log at `/Users/anicca/anicca-project/.claude/sol-orders/logs/core-8d-postcommit-review.log` compactly. Existing artifact `.vcsdd/features/life-manager-daily-preflight/evidence/daily-preflight-20260721T064624Z.json` remains truthful historical 6/9 evidence and must not be rewritten as a new run.

Run focused tests, full `npm test`, `npm run eval`, changed-module coverage >=90% lines/functions, `node --check`, `git diff --check`, and sensitive-value scans. No production/network commands.

Update row 8d to remain `pending`, recording local RED/GREEN and that production is still the prior 6/9 pending a later controlled rerun. Do not touch 8e.

Fetch, stage explicit in-scope paths only, commit, push `feature/lm33d-daily-preflight`, verify remote equality and clean worktree. Final report: heads/files/RED/GREEN/full test/eval/coverage/no-side-effects/spec/commit/push/PR/remaining blockers.
