# Task 5 report — authenticated Telegram onboarding entry

STATUS: READY FOR REVIEW (acceptance remains with the parent/reviewer)

## Changes

- `startReply` now validates an absolute HTTPS panel origin without credentials and emits exactly one
  Telegram `web_app` button at `/panel/onboarding`; the chat ID and legacy `?tg=` identity are not in
  the URL. `onboardLink` remains unchanged for the legacy/public QR and non-start flows.
- The real `/telegram` webhook `/start` branch now sends `startReply(..., LM_PANEL_BASE)` instead of
  the legacy `sendStage` path. `/start` payloads and the generic slash router remain intact.
- `GET /panel/onboarding` is routed through the existing `handlePanelRequest` login/session boundary;
  no second verifier or auth store was introduced. Existing `/panel` behavior remains covered.
- Added focused auth contracts for valid Telegram `initData` session creation, invalid/stale/replayed/
  cross-actor rejection, and query identity fallback rejection.

## RED evidence

```text
baseline focused suite: 42 tests, 42 pass, 0 fail
after task tests: 48 tests, 45 pass, 3 fail
  - startReply still emitted a normal ?tg= URL
  - invalid/missing panel origins did not fail closed
  - production GET /panel/onboarding returned 404
```

## GREEN evidence

```text
node --test apps/life-manager/lib/telegram-onboard.test.js apps/life-manager/lib/panel-auth.test.js apps/life-manager/test/telegram-slash-http-contract.test.js
48 tests, 48 pass, 0 fail

node --check apps/life-manager/lib/telegram.js
node --check apps/life-manager/server.js
node --check apps/life-manager/lib/telegram-onboard.test.js
node --check apps/life-manager/lib/panel-auth.test.js
node --check apps/life-manager/test/telegram-slash-http-contract.test.js
git diff --check
all exited 0
```

## Mutation proof

- Flipped HTTPS validation: onboarding-origin tests failed (including the expected throw cases); restored.
- Replaced `web_app` with a normal `url`: unit and production `/start` assertions failed; restored.
- Removed `/panel/onboarding` from the production route: the real HTTP contract failed with `404 != 200`; restored.
- Rewired production `/start` to `PUBLIC_BASE`: the real HTTP contract failed because the button origin was
  `https://lm.test` instead of the configured panel origin; restored.
- Mutated a malformed `https:panel.example` origin: the fail-closed origin test failed before the strict
  scheme check was restored.
- Mutated signed `initData` user content: the existing verifier returned `401 telegram_auth_rejected` and
  made zero Supabase/session writes; the signature-verification boundary stayed fail closed.

## Commit

- `511b0e5b8` — `feat(life-manager): open authenticated telegram onboarding`
- `fb71c3e5e` — `fix(life-manager): reject malformed telegram panel origin`
- Pushed to `origin/codex/lm-cloud-core-spec`.

## Concerns

- No live Telegram or Railway provider E2E was run; the requested checks use the production HTTP handler
  with bounded Telegram/Supabase transports. Parent/reviewer must perform the final integration decision.
