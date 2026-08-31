# Task 6 fix R1 report — atomic session-scoped Calendar consent

STATUS: READY FOR REVIEW (acceptance remains with the parent/reviewer)

## Findings closed

- Calendar start/status now preserve the existing `panelScopeCookie` replacement, so a 12-hour
  rotating session remains usable for a delayed OAuth callback.
- `composioCalendarStatus` and `composioCalendarStart` require exact owned `status=ACTIVE`,
  `is_disabled !== true`, and `enabled === true`; missing `enabled` is no longer connected.
- Added `2026-08-27-lm-panel-oauth-atomic.sql`: it cleans obsolete/duplicate rows, adds a unique
  partial live-state index per uid/chat/provider, and defines a service-role-only SECURITY DEFINER
  `create_lm_panel_oauth_state` RPC that atomically expires used/old rows and returns a boolean claim.
- `createSupabaseCommandStore.createOAuthState` now calls that RPC and throws the sanitized
  `oauth_state_in_progress` conflict when the claim is false. Calendar onboarding maps it to HTTP 409
  before any provider link; existing command execution therefore cannot create a duplicate link.
- State remains a random-nonce HMAC with the existing 43-character opaque shape; only SHA-256 is
  persisted. Provider failures leave the one live state in place, blocking duplicate links until expiry.

## GREEN evidence

```text
cd apps/mr-bot
node --test lib/calendar-onboard.test.js lib/panel-control-center.test.js \
  lib/panel-permanent-session.test.js test/calendar-connect-signature-contract.test.js \
  test/onboarding-resume-contract.test.js
68 tests, 68 pass, 0 fail

node --test lib/panel-api.test.js lib/panel-delegation-honesty.test.js \
  lib/panel-auth.test.js lib/panel-zero-link.test.js
42 tests, 42 pass, 0 fail

node --check lib/calendar-onboard.js
node --check lib/calendar-onboard.test.js
node --check lib/panel-api.js
node --check lib/panel-control-center.test.js
node --check lib/panel-permanent-session.test.js
node --check server.js
git diff --check
all exited 0
```

The new regressions cover rotated-session renewal, explicit state-secret fail-closed behavior,
same-scope repeat/expiry, false RPC conflict handling, strict provider enabled truth, migration
guards, and provider-link suppression on concurrent control-center starts.

## Mutation proof

- Removed the explicit state-secret guard: missing-secret test observed a provider effect.
- Removed the calendar 409 claim guard: repeat start returned 502 instead of 409.
- Removed `oauth_state_in_progress` from `createOAuthState`: the false-RPC store test lost its rejection.
- Reverted either helper's `enabled === true` check: missing-enabled helper test returned `ACTIVE` or
  connected instead of failing closed.
- Removed the migration's unique live-state index: the additive migration contract test failed.
- Removed session-cookie renewal: rotated-session response lost `Set-Cookie`.
All mutations were restored before commit.

## Commits

- `9b1f0585e` — `fix(mr-bot): make calendar consent atomic`
- Pushed to `origin/codex/lm-cloud-core-spec`.

## Concerns

- No live Composio/Telegram production E2E was run; provider behavior remains bounded injected
  transport coverage. Parent/reviewer owns final acceptance and migration deployment/readback.
