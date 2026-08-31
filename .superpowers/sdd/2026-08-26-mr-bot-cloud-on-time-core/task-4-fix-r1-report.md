# Task 4 fix R1 report — bound reminder and call isolation

STATUS: DONE

## Findings closed

- `wakeUserOnce` now bounds the deadline-critical call with the existing 20-second
  `WAKE_USER_TIMEOUT_MS` default (`wakeTimeoutMs`/`callTimeoutMs` test seams). A timed-out call is
  logged by uid and the function continues to organs/reminder; the call remains first.
- `organ:travel-reminder` now bounds live-location, routing, claim, and Telegram work with a
  15-second `REMINDER_TIMEOUT_MS` default (`reminderTimeoutMs`/`travelReminderTimeoutMs` seams), so
  a never-resolving reminder cannot hold the same user's late or later organs.
- Scheduler wake logs no longer print Calendar event titles; the canonical `travel-reminder.js`
  success receipt remains the sole `[travel-reminder]` receipt with event-key hash, provider, and
  Telegram message ID.
- Added bounded timeout, same-user continuation, safe console logging, and single-receipt tests.

## GREEN evidence

```text
node --test test/wake-loop-isolation.test.js
22 tests, 22 pass, 0 fail
node --test test/wake-levels.test.js test/wake-catchup.test.js test/wake-claim-token.test.js
13 tests, 13 pass, 0 fail
node --test lib/travel-reminder.test.js
13 tests, 13 pass, 0 fail
node --test lib/care-scan-wiring.test.js lib/diet-scan-wiring.test.js lib/precepts-wiring.test.js lib/mental-lookback-wiring.test.js lib/relations-wiring.test.js
41 tests, 41 pass, 0 fail
node --test test/inngest.test.js
34 tests, 34 pass, 0 fail
node --test test/daily-journey-contract.test.js test/wake-miss-record.test.js
12 tests, 12 pass, 0 fail
node --check scheduler.js && node --check test/wake-loop-isolation.test.js && git diff --check
all exited 0
```

## Mutation proof

- Removed the `wakeUserOnce` call timeout: 21/22; the never-resolving call test failed.
- Removed the reminder timeout wrapper: 21/22; the same-user late-continuation test failed.
- Restored event summary in the WAKE console line: the notifications-disabled console-leak test
  failed.
- Restored the scheduler's duplicate success line: the canonical receipt test found two lines and
  failed.

All mutations were reverted before commit.

## Commits

- `22386d785` — `fix(mr-bot): bound reminder and call isolation`
- Pushed to `origin/codex/lm-cloud-core-spec`.

## Concerns

- The timeout boundary abandons a still-running provider promise (the same behavior as the existing
  per-tenant timeout); durable claim/retry behavior remains owned by the travel reminder organ.
- No production provider/Telegram E2E was run; all new checks use bounded injected seams.
