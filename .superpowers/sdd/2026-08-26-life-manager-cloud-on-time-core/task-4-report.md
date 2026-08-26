# Task 4 report — isolate call and reminder organs

STATUS: DONE

## Changes

- Wired `travelReminderOnce` into `organsUserOnce` as `organ:travel-reminder` under
  `notifications_enabled !== false`.
- Passed the wake tick's raw (lookback-inclusive) events, current Supabase-backed live location,
  home, timezone, maps/API keys, Telegram token, claim/release, send, and logging seams without
  adding Calendar fetches or event text to scheduler logs.
- Kept reminder eligibility independent of `call_enabled`; `wakeUserOnce` catches a call-organ
  throw and continues into the organs, while `runOrgan` contains reminder failures.
- Added isolation coverage for call/reminder ordering, throw/delay, call opt-in, notification
  opt-out, raw online lookback events, and cross-tenant reminder hangs.

## Verification

```text
node --test test/wake-loop-isolation.test.js
19 tests, 19 pass, 0 fail
node --test test/wake-levels.test.js test/wake-catchup.test.js
7 tests, 7 pass, 0 fail
node --test test/wake-claim-token.test.js
6 tests, 6 pass, 0 fail
node --test lib/travel-reminder.test.js
13 tests, 13 pass, 0 fail
node --test test/scheduler.test.js
2 tests, 2 pass, 0 fail
node --check apps/life-manager/scheduler.js
node --check apps/life-manager/test/wake-loop-isolation.test.js
git diff --check
all exited 0
```

Existing care/diet/precepts/mental-lookback/relations wiring suites also passed (41 tests).

## Mutation proof

- Removed the `wakeUserOnce` call catch: 18/19, the call-failure→reminder test failed; restored.
- Replaced the notification gate with `true`: 18/19, the notifications-disabled test failed; restored.
- Passed `futureEvents` instead of raw `events`: 18/19, the online lookback test failed; restored.

## Commit

- `b65f70f47` — `feat(life-manager): isolate call and reminder organs`
- Pushed to `origin/codex/lm-cloud-core-spec`.

## Concerns

- No production provider/Telegram E2E was run; all Task 4 tests use injected bounded seams as
  required. The requested full `npm test` remains for the parent integration pass.
