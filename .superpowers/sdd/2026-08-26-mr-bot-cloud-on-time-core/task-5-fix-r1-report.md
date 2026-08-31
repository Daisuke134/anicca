# Task 5 fix R1 report — exact `/start` delivery

STATUS: READY FOR REVIEW (acceptance remains with the parent/reviewer)

## Findings closed

- The production `/start` branch now requires `sendMessage` to return `{ ok: true }`. An explicit
  Telegram `{ ok: false }` raises the generic `onboarding web app button send failed` error into the
  existing webhook catch; the update still returns HTTP 200 and no provider/token/chat detail is logged.
- `parseUpdate.isStart` now uses the exact `/^\/start(?:@[A-Za-z0-9_]+)?(?:\s|$)/i` boundary. Real HTTP
  coverage preserves `/start payload` and `/start@Bot payload`, while `/start-foo` and `/start?` are
  handled as unknown input and never open onboarding or emit `?tg=`.
- A narrow server guard keeps punctuation-prefixed `/start` lookalikes out of the free-text onboarding
  path; the existing slash router continues to own alphanumeric unknown commands such as `/startfoo`.

## GREEN evidence

```text
node --test apps/mr-bot/lib/telegram-onboard.test.js apps/mr-bot/lib/panel-auth.test.js apps/mr-bot/test/telegram-slash-http-contract.test.js
48 tests, 48 pass, 0 fail

node --check apps/mr-bot/lib/telegram.js
node --check apps/mr-bot/server.js
node --check apps/mr-bot/lib/telegram-onboard.test.js
node --check apps/mr-bot/lib/panel-auth.test.js
node --check apps/mr-bot/test/telegram-slash-http-contract.test.js
git diff --check
all exited 0
```

The real webhook fixture also observed one failed Telegram send, HTTP 200, one generic error line, and
no `fixture-token`, `chat_id=200`, or provider description in captured errors.

## Mutation proof

- Removed the `/start` `sent.ok` check: the real HTTP test failed because the generic delivery failure
  was not observed; restored.
- Replaced the exact `isStart` boundary with the old `startsWith("/start")`: `/start-foo` reached the
  onboarding reply and the real HTTP test failed; restored.
- Removed the punctuation-prefixed lookalike guard: `/start-foo` fell through to the legacy onboarding
  stage and the real HTTP test failed; restored.

## Commit

- `f3cb316d3` — `fix(mr-bot): enforce exact start delivery`
- Pushed to `origin/codex/lm-cloud-core-spec`.

## Concerns

- No live Telegram or Railway provider E2E was run; this R1 proof uses the production HTTP handler with
  a bounded Telegram transport fixture. Parent/reviewer must make the final acceptance decision.
