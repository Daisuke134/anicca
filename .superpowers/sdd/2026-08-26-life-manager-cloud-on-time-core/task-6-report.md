# Task 6 report — session-scoped Calendar consent

STATUS: READY FOR REVIEW (acceptance remains with the parent/reviewer)

## Changes

- Added `apps/life-manager/lib/calendar-onboard.js` (82 production LOC) with the two exact
  `/api/panel/onboarding/calendar/start` and `/api/panel/onboarding/calendar/status` adapters.
- Session cookie resolution and current uid/chat binding reuse `panel-auth.js` and
  `createSupabaseCommandStore`; request body/query `uid`/`tg` values are ignored.
- Start enforces exact HTTPS panel Origin, panel CSRF, and JSON; an HMAC over a random nonce plus
  verified uid/chat produces the existing 43-character state shape. Only `sha256(state)` is persisted
  through `createOAuthState`, then the existing `startCalendarOAuth` is called once.
- Existing ACTIVE reconnects return connected without minting OAuth. Missing/disabled/inactive status
  is action-required; only validated HTTPS provider redirects are returned. Provider/store failures
  return the generic `calendar_unavailable` response and no raw provider data is logged or serialized.
- Wired only the two onboarding paths in `apps/life-manager/server.js`, passing Supabase, panel origin,
  panel session secret, and existing Composio config. The legacy panel API and OAuth callback are unchanged.
- Preserved `panelScopeCookie` renewal on both onboarding responses so a rotating 12-hour panel session
  remains usable through a delayed OAuth callback.

## RED

Before the production module existed, `node --test lib/calendar-onboard.test.js` failed with
`MODULE_NOT_FOUND` for `calendar-onboard.js`.

## GREEN evidence

```text
cd apps/life-manager
node --test lib/calendar-onboard.test.js lib/panel-control-center.test.js \
  lib/panel-permanent-session.test.js test/calendar-connect-signature-contract.test.js \
  test/onboarding-resume-contract.test.js
62 tests, 62 pass, 0 fail

node --check lib/calendar-onboard.js
node --check lib/calendar-onboard.test.js
node --check server.js
git diff --check
all exited 0
```

The focused tests cover session-only actor derivation, unauthenticated/rebound 401 before provider
effects, exact Origin/CSRF/JSON, malformed WHATWG-normalized origins, hash-only state persistence,
43-character HMAC scope binding, ACTIVE-only status, sanitized provider errors, HTTPS redirect
validation, and the existing callback's atomic replay/expiry/cross-scope/ACTIVE readback behavior.

## Mutation proof

- Replacing the verified session scope with body/query uid/tg made the actor-isolation test fail.
- Replacing the HMAC chat scope with a forged value made the deterministic state test fail.
- Treating `DISABLED` as connected made the ACTIVE-only status test fail.
- Persisting the raw state instead of its SHA-256 made the hash-only persistence test fail.
- Removing strict raw `https://`/trim validation made the malformed-origin test return 200 instead of 403.
- Removing panel session-cookie renewal made the rotation response lose its replacement cookie.
All mutations were restored before commit.

## Commit

- `4f0c87d10` — `feat(life-manager): add session scoped calendar consent`
- `a9c385cad` — `fix(life-manager): renew calendar panel sessions`
- Pushed to `origin/codex/lm-cloud-core-spec`.

## Concerns

- No live Composio/Telegram provider E2E was run; provider behavior is covered with bounded injected
  transports and the existing production helper contracts. Parent/reviewer owns final acceptance.
