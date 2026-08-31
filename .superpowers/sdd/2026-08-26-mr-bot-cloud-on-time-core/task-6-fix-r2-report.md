# Task 6 fix R2 report — atomic tenant revalidation

STATUS: READY FOR REVIEW (acceptance remains with the parent/reviewer)

## Findings closed

- The atomic Calendar-state RPC now locks and revalidates the exact current
  `lm_users.uid = p_uid AND telegram_chat_id::text = p_chat_id` binding with `FOR SHARE` before
  deleting/inserting state. A rebound or missing tenant returns false without a state row.
- Calendar start now performs a strict provider status read first, returns immediately for ACTIVE,
  then claims the durable state before any mutating reconnect/provider operation. A failed claim is
  re-read against the session scope and becomes 401 for a rebound tenant or 409 for a live consent.
- Existing `composioCalendarStart` runs only after the atomic claim; the repeated-start and rebind
  fixtures therefore observe one state/provider link and zero provider mutations for stale binding.

## GREEN evidence

```text
cd apps/mr-bot
node --test lib/calendar-onboard.test.js lib/panel-control-center.test.js \
  lib/panel-permanent-session.test.js test/calendar-connect-signature-contract.test.js \
  test/onboarding-resume-contract.test.js
69 tests, 69 pass, 0 fail

node --check lib/calendar-onboard.js
node --check lib/calendar-onboard.test.js
node --check lib/panel-api.js
node --check lib/panel-control-center.test.js
node --check lib/panel-permanent-session.test.js
node --check server.js
git diff --check
all exited 0
```

The migration contract test asserts additive/no-new-table behavior, cleanup, the unique live-state
index, the service-role-only RPC, exact uid/chat predicate, and the row lock. Handler tests cover
status-read-before-claim ordering and a binding flip between status and claim returning 401 with
state/start/link effects all zero.

## Mutation proof

- Reordering provider status after state claim made the rebind test return 200 instead of 401.
- Removing the current-binding re-read on conflict changed the rebind response from 401 to 409.
- Removing `FOR SHARE` made the migration contract fail.
- Reverting strict `enabled === true` made missing-enabled provider truth report ACTIVE/connected.
- Removing the state-claim conflict handling allowed a repeated start to reach provider/link work.
- Removing the explicit state-secret guard caused provider work with no HMAC secret.
All mutations were restored before commit.

## Commit

- `31898fc55` — `fix(mr-bot): revalidate calendar tenant atomically`
- Pushed to `origin/codex/lm-cloud-core-spec`.

## Concerns

- No live Composio/Telegram production E2E or applied migration readback was run; parent/reviewer owns
  final acceptance and production migration deployment verification.
