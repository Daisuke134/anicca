# PANEL-0 corrective build for fresh-review blockers

Fresh `gpt-5.6-sol` builder in `/Users/anicca/anicca-project/.worktrees/lm-panel-control-center`, branch `feature/lm-panel-control-center`, exact start/local/origin `84e1cebae1b62908e2967c66398f81c65cdf02a3`, stacked PR #331 against `feature/lm33d-daily-preflight`. Do not spawn another agent.

The fresh artifact-only verdict is in `.claude/sol-orders/logs/panel-control-center-fresh-review.log`: `VERDICT: FAIL`, `BLOCKERS: 10`. Treat that exact fresh review output as ground truth; builder self-report/test totals never override it.

No merge/deploy, production `/panel` probe, provider call, real OAuth, Telegram/email/phone send, Dais connection disable, wallet/billing/schema-destructive action, or secret/PII output. Local/fixture TDD only. Preserve the stacked base; do not absorb unrelated root changes.

Read full installed VCSDD docs and use supported state APIs rather than direct state mutation. Read canonical §9.5, §9.9, §10 8d.1, §10.1 U5, current VCSDD artifacts, exact PR diff, and reviewer log. Use CodeGraph first for runtime tracing because `.codegraph/` exists. Search official Composio source only if the existing cited artifact is insufficient; use project-approved `crwl`/Context7/GitHub, cite source+URL+core quote, and do not invent provider semantics.

## Process correction first

1. Mechanically persist the fresh review verdict/findings from the reviewer log into the correct VCSDD sprint review paths with log SHA-256/provenance. Do not soften/reword blockers or fabricate reviewer approval.
2. Repair the invalid state using installed atomic VCSDD tooling. Record Phase 3 FAIL if supported, route through explicit Phase 4 to the earliest affected phase (2a for missing tests, then 2b). If the library refuses because the prior self-transition is invalid, stop and report the exact state-tool blocker; never hand-edit a PASS.
3. Strict contract is `amended` and lacks fresh contract-review PASS. You may correct its criteria so all 10 blockers are explicit, but never mark it approved or create a PASS. End this build no later than Phase 2c, awaiting fresh contract review + implementation adversary.

## Mandatory RED-before-GREEN

Write failing tests first and capture real RED evidence, while the current implementation remains unchanged. Each blocker needs a deterministic failing test/reproduction. Verify regression baseline separately. Only then implement minimal GREEN and capture formal evidence.

1. **Real runtime toggles** (`apps/life-call/lib/user-command.js:114`): `call_enabled`, notification, DAILY automation, and delegation must control the actual per-user runtime paths, not only a new dashboard table. Trace current scheduler/call/notification/delegated-action SSOTs and use/wire one user-scoped preference source. Tests must prove OFF prevents the actual relevant runtime side effect and ON permits it for that user, without cross-user effect. If a promised control has no safe runtime surface, expose honest unavailable state and no success action rather than a fake toggle; however §9.9-required supported controls must be genuinely wired before local PASS.
2. **Pending idempotency** (`user-command.js:104`): the same `uid + chat_id + idempotency_key` with pending/no-result must return deterministic in-progress/conflict and execute zero mutation/provider calls. Succeeded returns stored result; failed semantics are explicit. Concurrent duplicate test proves one mutation.
3. **Current identity rebinding** (`panel-api.js:370`): every authenticated panel read/action must revalidate session `uid + chat_id` against current `lm_users`; Telegram re-link/rebinding invalidates old sessions. Tenant tests include old-session read and action denial.
4. **Receipt tenant key** (`panel-api.js:289`): schema, unique/primary key, RLS, queries, read/finish all bind `uid + chat_id + idempotency_key`. Add cross-chat same-uid isolation and migration compatibility/rollback test.
5. **Provider account exactness** (`panel-api.js:311`): exact `user_ids=<uid>` plus Google Calendar toolkit request is necessary but response objects must also match expected user/toolkit; 0, >1, foreign, missing identity, mixed accounts fail closed as appropriate. Never choose arbitrary ACTIVE.
6. **Disable/reconnect same-account readback + rollback** (`panel-api.js:328`): verify post-PATCH account id/owner/toolkit and expected inactive/ACTIVE state. If disable verification fails after mutation, re-enable the exact same account and verify restoration; report rollback failure honestly. No UI/chat claim that state is unchanged without confirmed rollback.
7. **OAuth callback provider truth** (`panel-api.js:299`, `server.js:226`): state remains uid/chat/replay-bound; callback receives provider deps, resolves exactly one owned calendar account, requires ACTIVE readback before success, and renders/redirects honest failure otherwise. Replay cannot duplicate effects.
8. **Connect vs Reconnect** (`panel-ui.js:674`): missing/unlinked state renders native `Connect calendar`; known disabled state renders `Reconnect calendar`; ACTIVE renders `Disconnect calendar`. Each maps to a typed allowed command and semantic handler.
9. **Bounded request body** (`panel-api.js:255`): once >32 KiB, stop buffering immediately, settle once, safely drain/destroy according to Node server behavior, and never let later chunks grow retained `raw`. Tests stream many post-limit chunks and prove bounded memory/one response/no mutation.
10. **VCSDD correctness**: formal RED/GREEN logs, approved artifact snapshots only when actually approved, no self-authored fresh PASS, state validator/runtime verifier clean, `git diff --check` clean (remove blank EOF defect).

Also re-run existing tenant/CSRF/origin/content-type/idempotency/OAuth/Composio/UI/mobile tests, full `npm test`, eval 33/33, both panel smokes, focused coverage, secret/PII scan. No L3 claim.

Update worktree canonical row 8d.1/§10.0 with exact fresh FAIL and corrective results, but keep `pending — corrective local GREEN / fresh reviews required`. Stage only panel-owned source/tests/migration/VCSDD/spec files, commit, push rewritten stacked branch if needed, verify PR #331 base/head. Do not merge.

Return:

```text
RESULT: CORRECTIVE-LOCAL-GREEN | FAIL
BLOCKERS_CLOSED: <0-10 with test mapping>
VCSDD_STATE: <truthful phase/gates still required>
RED: <counts/exits/artifacts>
GREEN: <counts/exits/artifacts>
RUNTIME_TOGGLE_PROOF: <safe summary>
TENANT_PROVIDER_PROOF: <safe summary>
SPEC: pending
COMMIT: <hash or none>
PUSH: <remote equality>
PR: #331 NOT MERGED
NEXT_GATES: <fresh contract/spec/implementation reviews and L3>
```
