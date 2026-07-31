# PANEL-0 corrective-3 — four substantive blockers only

## Role and scope

You are the fresh Sol builder. Work only in `/Users/anicca/anicca-project/.worktrees/lm-panel-control-center` on branch `feature/lm-panel-control-center`, exact base `3e23328d9436835945c13da64b526202f94f90ac` / PR #331. Build, execute, verify, write evidence, commit, and push. Do not edit the canonical consolidation spec; the manager owns it. Do not deploy, merge, apply production migrations, start OAuth, send Telegram/email/calls, or mutate any external provider/account.

Use TDD: first add genuine behavior RED tests and commit them separately; then minimal GREEN, evidence, fresh verification, commit, push. Never replace behavior execution with source regex. Do not chase VCSDD/process/style/legacy whole-module coverage nits.

## Exact remaining blockers

1. **Real selectable settings UI.** `call_language`, `call_time_zone`, and `wake_policy` must expose user-selectable valid options reflecting current scoped values. A real DOM/browser interaction must select a non-default value and prove the exact payload reaches the shared `/api/panel/commands` handler, reloads, and reads back the scoped value. A marker-only test or handcrafted HTTP payload is insufficient. Mobile and desktop controls must remain semantic/clickable.
2. **Concurrency-safe rotation.** The real panel starts six API requests concurrently. Two or more requests using the same pre-rotation cookie must all converge on one valid replacement; no response may set a deleted/invalid child. RED must use distinct generated child bytes and out-of-order completion, then resolve every returned replacement against the state machine. Implement atomically in the SQL RPC/protocol; do not serialize the UI as the sole fix. Preserve hash-only storage, current uid+chat binding, logout/rebind/revoke, and lost-response recovery.
3. **Active-session continuity.** A bookmarked session used continuously must not die at day 30 or an unconditional day 180. Extend idle expiry from verified activity and define an explicit rotation/session-family lifecycle consistent with §9.9: normal use continues until logout, rebind, security revoke, or browser storage removal. RED must clock-advance beyond 30 and 180 days with periodic use, plus prove genuinely idle session expiry/revocation remains safe. Cookie Max-Age must match the server result, not a hardcoded stale bound.
4. **Batch scheduler fail-closed.** In production `listPaidUsers`/batch path, a 200 response with malformed/non-array preferences JSON must set calls/notifications/DAILY false for all affected users, never reapply DEFAULTS=true. Preserve valid empty-array semantics (no preference row means documented defaults) only after a successful array parse.

## Positive controls and non-regression

Preserve the already-closed behavior: fresh bootstrap/query stripping/login page; current-binding rejection for page/API/OAuth; exact provider account readback/rollback; oversize late-error handling; single-user Inngest and discovery fail-closed; tenant isolation; CSRF/origin/content-type/idempotency; Connect/Reconnect/Disconnect; honest unavailable connectors.

## Required verification

- RED commit: only tests/fixtures/evidence metadata; each of the 4 tests fails for its intended production reason; existing focused tests still pass.
- GREEN: new four-behavior tests 100%; `node --test lib/panel-permanent-session.test.js`; focused panel tests; full `npm test`; `npm run eval`; API/UI smoke; `git diff --check`.
- Inspect modified existing tests for weakening and list every changed assertion in evidence.
- Evidence: `.vcsdd/features/life-manager-panel-control-center/evidence/panel-corrective3-four-blockers.md` with exact commands/counts/commits and side effects=`0`.
- Push branch and report exact RED SHA, GREEN/evidence SHA, upstream/PR head equality, worktree cleanliness, and remaining product blockers. Do not claim done or L3.
