# PANEL-0 permanent personalized control center — six-blocker RED → GREEN

Fresh `gpt-5.6-sol` builder. Work only in `/Users/anicca/anicca-project/.worktrees/lm-panel-control-center`, branch `feature/lm-panel-control-center`, exact clean `HEAD==upstream==PR #331 head` at `c3fbf22ebe3148a52d4768dd36d00d4230e3fa28`. Do not delegate. If the base moved, stop with the exact mismatch; do not silently build on another SHA.

The product SSOT is canonical spec §9.9 and §10 row 8d.1. The previous corrective commits are positive control: RED `5f8db7f13`, GREEN `1c74ff0f7`, evidence `c3fbf22eb`; preserve their focused 39/39, full test, eval 33/33, API 5/5 and UI 6/6 results. Ignore VCSDD metadata/style nits. A fresh product-only review at exact HEAD reproduced six remaining production blockers: durable access, production runtime toggles, rebind validation, exact provider readback/rollback, personalized settings/control, and oversize-stream safety. Close these six; do not expand scope.

No deploy, merge, production request, real provider/OAuth, Telegram/email/phone send, Dais account mutation, or L3. Local deterministic TDD only.

Research basis: OWASP Session Management Cheat Sheet permits a short renewal safety interval for the previous ID (`https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html#renewal-timeout`); RFC 9700 §4.14.2 requires invalidating the previous rotating token while retaining family relationship (`https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14.2`); Supabase documents bounded refresh-token reuse detection (`https://supabase.com/docs/guides/auth/sessions#what-is-refresh-token-reuse-detection-and-what-does-it-protect-from`). Copy the principles, not an OAuth token implementation.

## Required product behavior

- `/panel?t=<5-minute-one-time-token>` remains login bootstrap only. It burns the token, sets a hash-only-at-rest HttpOnly/Secure/SameSite cookie, removes the token by redirecting to canonical `/panel`, and never embeds a permanent bearer in a URL.
- Canonical `/panel` is bookmarkable. A browser holding a valid cookie can reopen it directly after restart and after 24 hours. Replace the fixed 24-hour model with a rolling server-side session: rotate after 12 hours, use a 30-day rolling idle expiry and 180-day absolute expiry. Rotation creates a new random secret/hash, extends only the idle expiry within the absolute bound, invalidates the old family member atomically, and emits the replacement cookie. A dropped rotation response must not permanently lock out the browser: use a short pending-child promotion/reuse grace or an equivalently atomic, tested protocol. Do not mutate test clocks or weaken expiry comparisons.
- Missing/expired/revoked cookie on the **HTML `/panel` route** renders HTTP 200 human login guidance with one clickable Telegram deep link back to the same stable dashboard flow. It is not raw `401`, `403`, or a dead-end plaintext response. JSON APIs remain fail-closed 401.
- Add a visible accessible Logout control. `POST /panel/logout` must require exact same-origin + CSRF, revoke the current server-side session atomically, clear the cookie (`Max-Age=0`), and redirect to `/panel`. GET logout and cross-origin/bad-CSRF requests mutate nothing.
- Every session resolution revalidates current `lm_users.uid + telegram_chat_id`. A rebind makes the old session unusable and revoked; it cannot read or mutate any tenant. Security revoke can invalidate all live panel sessions for the exact current `uid + chat_id`, without affecting another user. Missing browser storage naturally returns the login guidance.
- Close the remaining TOCTOU surface: setting/user mutations must be conditioned on the current `uid + telegram_chat_id` at the write boundary, not only by an earlier read. A rebind between validation and mutation performs zero writes.
- Database changes are additive, service-role-only, RLS remains enabled, and raw session/token values never enter SQL rows, logs, HTML, JSON, or evidence. Existing live 24-hour rows fail closed or are safely migrated; do not grant anon/authenticated execution.
- Runtime OFF/ON must affect every real execution path. `supaUsers`, Inngest `getUserByUid`, and the default discovery selector must read the same per-user preferences. `call_enabled=false` blocks call, `daily_automation_enabled=false` blocks wake/travel/ask, and `notifications_enabled=false` blocks Telegram/discovery/late-notice delivery for that user while peers remain active. A preferences transport/read failure fails closed for the affected automated action; an explicit successful empty preference row may use documented defaults.
- Page rendering and OAuth callback use the same current `uid + telegram_chat_id` validator as JSON APIs before token/state claim or provider action. A rebound old session performs zero OAuth/provider mutation.
- Calendar reconnect/disconnect is bound to the exact mutated account ID. Success readback requires that same ID and full enabled truth (`status=ACTIVE`, not disabled, enabled). Rollback proves the same full state; otherwise report rollback failure and never tell the user the previous setting is unchanged.
- Personalization comes from the scoped user/preferences/provider rows, not global timezone or stale `calendar_provider` strings. Timeline/settings use the user's timezone and live Calendar truth. Call language, call timezone, and wake policy are visible clickable controls that use the existing shared `executeUserCommand` path; no separate mutation backend.
- On body >32 KiB, retain zero further bytes, settle once, perform zero mutation, and safely drain/destroy or keep a no-op error sink so a later socket error cannot become an unhandled process error.

## Mandatory RED-before-GREEN

Create focused permanent-session/production-path tests plus the minimum migration/API/UI tests. Before production edits, prove genuine failures against exact base and commit/push the RED tests separately. At minimum cover:

1. >24-hour clock advance still resolves a rolling session and rotates it to a different secret.
2. Old secret fails after successful atomic rotation; concurrent rotation yields at most one live replacement.
3. Rotation failure/lost response is fail-closed without permanently locking out the valid browser.
4. Missing/expired/revoked cookie gets the HTML login page with one validated Telegram deep link and no uid/token/session leak.
5. Bootstrap still burns once, redirects to stable `/panel`, and stores only SHA-256.
6. Logout happy path, GET/cross-origin/bad-CSRF negatives, cookie deletion, and post-logout denial.
7. Current `uid+chat_id` readback: rebind/revoke invalidates old session across HTML, API read and command action.
8. Rebind between command validation and write causes zero preference/user/provider mutation.
9. Revoke-all is exact-tenant and leaves a second isolated user live.
10. Cookie flags, rolling timestamps, revocation fields/RPC grants, mobile/desktop clickable Logout semantics.
11. Production `getUserByUid`, normal scheduler loops, Inngest invocation, and default discovery selector honor OFF per user; preference read failure is not fail-open.
12. Rebound old session cannot render authenticated data or claim OAuth state; current session still works.
13. Reconnect and disconnect/rollback reject a different account ID and disabled/non-enabled fake ACTIVE states; UI copy is honest on failure.
14. Two users with different timezone/language/wake policy/calendar truth render different values, and each visible control converges through the shared command handler.
15. Oversize body followed by a late request error produces no unhandled error, no retained bytes, one response, and zero command mutation.

The RED commit may change only tests/evidence. Show the failing assertion count and confirm production/auth/migration/UI implementation diff is zero before committing it.

## GREEN implementation constraints

- Prefer small explicit helpers in `lib/panel-auth.js` and atomic SQL RPCs in a **new additive migration** `migrations/2026-07-22-lm-panel-durable-sessions.sql`; do not rely on editing an already-applied migration. Useful existing copy+tweak reference is `apps/api/src/services/auth/refreshStore.js` for family metadata only; its split validate/rotate and missing atomic revoke guard are not safe to copy verbatim. Wire only the required routes in `server.js` and semantic Logout/settings UI in `lib/panel-ui.js`.
- Session RPCs must atomically resolve current binding, begin/promote rotation, revoke one session/family, and keep all functions service-role-only. Prefer `__Host-lm_panel_session` with `Path=/; HttpOnly; Secure; SameSite=Lax`; read the legacy cookie only long enough to exchange/clear it.
- Update `scheduler.js` selectors, `lib/feature-discovery.js` default selector, `panel-api.js` OAuth/provider/personalization/body paths, and their direct tests. Do not use injected already-enriched user fixtures as the only runtime-toggle proof.
- Keep session hashes opaque and use constant-time CSRF comparison. Never expose the service role key client-side.
- Do not implement a forever cookie or a static reusable URL token. Persistence comes from rolling server-side rotation, not URL credentials.
- Do not game coverage with line compaction, dead branches, ignored files, or test-only production injection. Add tests for behaviorally meaningful uncovered branches only.
- Do not alter canonical spec in this feature branch. Record truthful local evidence under the feature evidence directory; no self-authored PASS and no finding closure before fresh review.

## Verification and delivery

Run the new six-blocker suite, all panel auth/API/control/UI tests, prior corrective positive control, full `npm test`, eval 33/33, panel API/UI smokes, `git diff --check`, and secret/PII scan. Require >=90% line/function coverage for the newly changed authentication/session modules and directly changed helper modules; report exact table. Existing untouched aggregate coverage is not part of this corrective gate.

Make a separate GREEN implementation/evidence commit, fetch/rebase safely, push, and prove clean `HEAD==upstream==PR #331 head`. Do not merge or deploy. End with `RESULT=PRODUCT-LOCAL-GREEN` and exact RED/GREEN counts, commit SHAs, route/session/tenant evidence, or `RESULT=BLOCKED` with the exact substantive blocker.
