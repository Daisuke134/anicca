# PANEL-0 corrective-4 — rotated-session logout evidence

## Scope and provenance

- Exact base: `5353bc0c1713301d4f4c4194368cbd51296a2ab7` on `feature/lm-panel-control-center`.
- Tests-only RED: `6122c184e67ccb9ffdaaccf10f9c0864cfcc3bc5`.
- Minimal GREEN: `106edbb1ab851dddfc36e4627cc6320f03f067b9`.
- Canonical consolidation spec changes: 0.
- Deployment, merge, migration application, OAuth, messages, calls, email, and production-system mutations: 0.

## Root cause and authoritative contract

`resolvePanelSession()` returns a family-stable CSRF derived from the resolved `family_id`, and `renderPanelPage()` places that CSRF in the logout request. The base logout handler instead compares the request with `csrfToken(rawSession)`, so the actual UI request receives HTTP 403 and calls no revoke RPC.

The correction preserves POST and exact-Origin rejection before session resolution, resolves the presented session through `resolve_lm_panel_session` for the current uid/chat binding, and compares against the same `scope.csrf || csrfToken(session)` contract used by panel commands. It then calls the existing `revoke_lm_panel_session` family revoke, clears both cookie names, and redirects to `/panel`.

Security references:

- Source: [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#using-standard-headers-to-verify-origin) / Core quote: “Consider verifying the origin with standard headers”.
- Source: [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html#logout-button) / Core quote: “the web application must invalidate the session at least on server side”.
- Source: [MDN Set-Cookie](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie#max-agenumber) / Core quote: “A zero or negative number will expire the cookie immediately.”

## Genuine RED

- Command: `node --test --test-reporter=tap lib/panel-corrective4-logout.test.js`.
- Result at RED commit: 1 total, 0 pass, 1 fail.
- The production HTTP path starts with a real `resolve_lm_panel_session` response containing `family_id`, GETs `/panel` with the raw cookie, and extracts the exact family CSRF embedded in the rendered logout handler.
- Wrong Origin and forged CSRF each return HTTP 403 with zero revoke calls.
- The exact Origin plus rendered CSRF fails at base with the observed pair `{ status: 403, revokes: 0 }`, versus required `{ status: 303, revokes: 1 }`.

## GREEN behavior

1. Non-POST logout returns 405 before resolution or revoke.
2. A missing or non-exact Origin returns 403 before resolution or revoke.
3. The resolver enforces the current uid/chat binding and supplies the authoritative family CSRF; a missing scope or mismatched CSRF returns 403 with zero revoke calls.
4. A valid request invokes `revoke_lm_panel_session` with the hash of the presented bearer. The existing RPC revokes every row in that `family_id`.
5. The response is HTTP 303 to stable `/panel`, with `Max-Age=0` for both `__Host-lm_panel_session` and `lm_panel_session`.
6. An immediate revisit with the old cookie resolves no session and renders the login/new-link path.

## Fresh verification on GREEN

| Check | Result |
|---|---|
| `node --test --test-reporter=tap lib/panel-corrective4-logout.test.js` | 1/1 pass |
| `node --test --test-reporter=tap lib/panel-corrective3-four-blockers.test.js` | 4/4 pass |
| `node --test --test-reporter=tap lib/panel-permanent-session.test.js` | 17/17 pass |
| focused six-file panel/session suite | 63/63 pass |
| `npm test` | 378/378 pass, 0 fail |
| `npm run eval` | Calendar 21/21 plus Late 12/12 = 33/33 |
| `npm run smoke:panel-api` | 5/5 endpoints HTTP 200 |
| `npm run smoke:panel-ui` | 6/6 DOM sections present; semantic controls wired |
| `git diff --check` | exit 0 |

## Assertion-strength review

- Existing assertions removed or weakened: 0.
- The new corrective test adds assertions for the rendered family CSRF, raw-session CSRF mismatch, wrong-Origin/CSRF revoke count 0, successful 303/revoke count 1, stable redirect, both cookie clears, whole-family invalidation, and immediate login-path revisit.
- The permanent logout test keeps every prior assertion. Its resolver fixture and valid-CSRF inputs now model the production `family_id` contract; the wrong-Origin case is stronger because it carries the otherwise-valid family CSRF.

## Status boundary

This evidence addresses only the rotated-session logout blocker. It does not claim L3 or overall feature completion.
