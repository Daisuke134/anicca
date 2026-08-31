# Task 5 report — Side-Effect Boundary and Review Fixes

STATUS: DONE WITH OUT-OF-SCOPE FULL-SUITE NOTE

## Boundary proof

`apps/mr-bot/lib/late-approval-boundary.test.js` scans the production JavaScript surface with
an explicit allowlist and pins all required relationships:

- `late-notice.js` and the scheduler contain no mail transport dependency.
- An unallowlisted production mail caller is a negative fixture and fails the scan (RED before the
  scanner implementation).
- The only `sendLateNotice` caller is inside the authenticated `handleLateApprovalCallback` body.
- `late-approval.js` invokes `sendLateNotice` only after `claimApprovedDelivery` returns a claim.
- `recordLateDelivery` is after the provider call.
- The Telegram delivery receipt is after the durable provider receipt.

The mutation probe moves the sender token before the claim in an in-memory source mutation and
asserts that the order contract fails.  The production source is not changed by the probe.

The integrated review also found that the migration revokes direct draft-table access from
`service_role` while the callback lookup still used a PostgREST table GET.  The fix adds the
tenant-filtered `lm_get_late_draft(text,text)` `SECURITY DEFINER` RPC, grants only its execution to
`service_role`, and pins the adapter/HTTP contract to that RPC.  Direct table access remains
revoked; the callback cannot read another tenant's draft.

The Telegram receipt is now a durable outbox on the draft row.  Four SECURITY DEFINER RPCs queue,
claim, record, and release the receipt.  The claim is row-locked and lease-based, so concurrent
callbacks produce one receipt sender; a failed Telegram send releases the claim and the next
callback retries only Telegram while retaining the provider receipt/idempotency key.  A stale
callback snapshot that observes a newly durable provider receipt also recovers the outbox without
resending the provider email.

## Round 2 — accepted Telegram edit ambiguity

The approval card's Telegram `chat_id` and `message_id` are now durable on the late draft through
the idempotent `lm_record_late_approval_card` RPC.  The receipt path edits that original card and
removes its buttons; it does not send a second Telegram message.  If Telegram accepted the edit but
the caller sees a timeout, or if the receipt record fails after Telegram accepted the edit, the
claim is released for retry while the provider delivery remains durable.  The retry edits the same
original message, so the provider email stays exactly once and the visible receipt stays exactly
once.  A deterministic pre-accept Telegram `{ok:false}` still releases the claim and retries.

### RED contracts before the fix

```text
cd apps/mr-bot && node --test --test-name-pattern='accepted Telegram edit followed by' test/late-approval-http-contract.test.js
  timeout case: not ok — Expected retry.ok=true, received false
  receipt-record-failure case: not ok — Expected retry.ok=true, received false
```

The same pre-fix command also reported the existing dependency issue for the production HTTP
contract (`Cannot find module 'ws'`) before `npm ci` restored `node_modules`; that was unrelated to
the new RED assertions.

### GREEN contracts after the fix

```text
cd apps/mr-bot && npm ci --ignore-scripts --no-audit --no-fund
  added 452 packages in 8s (peer/deprecation warnings only)

cd apps/mr-bot && node --test test/late-approval-http-contract.test.js
  9 tests, 9 pass, 0 fail

cd apps/mr-bot && node --test lib/late-recipient-resolver.test.js lib/late-approval.test.js lib/late-notice.test.js test/late-approval-http-contract.test.js
  64 tests, 64 pass, 0 fail

cd apps/mr-bot && node --test test/telegram-callback-http-contract.test.js lib/telegram-onboard.test.js
  33 tests, 33 pass, 0 fail

cd apps/mr-bot && node --test lib/late-approval-boundary.test.js lib/mail-resend.test.js && git diff --check
  9 tests, 9 pass, 0 fail; diff check passed

cd apps/mr-bot && node --test test/daily-journey-contract.test.js
  2 tests, 2 pass, 0 fail
```

The new HTTP contracts assert both accepted-edit failure modes, one provider mail call, two
attempts against the same Telegram `(chat_id,message_id)`, and one durable receipt message id.

## Round 3 — idempotent no-op and durable target precedence

Telegram's exact `{ok:false, description:"Bad Request: message is not modified"}` response now
counts as successful receipt delivery: the durable receipt record is written against the original
approval card.  Any other `{ok:false}` still releases the receipt claim for retry.  The edit target
selection now orders durable stored card `chat_id`/`message_id` before callback/options values, so
a stale replay cannot redirect the receipt to another message.

### RED contracts before the fix

```text
cd apps/mr-bot && node --test --test-name-pattern='accepted Telegram edit followed by|replayed callback message id' test/late-approval-http-contract.test.js
  3 tests, 0 pass, 3 fail
  timeout retry: false !== true
  receipt-record-failure retry: false !== true
  durable target: actual messageId 777, expected 700
```

### GREEN contracts after the fix

```text
cd apps/mr-bot && node --test --test-name-pattern='accepted Telegram edit followed by|replayed callback message id' test/late-approval-http-contract.test.js
  3 tests, 3 pass, 0 fail

cd apps/mr-bot && node --test test/late-approval-http-contract.test.js
  10 tests, 10 pass, 0 fail

cd apps/mr-bot && node --test lib/late-recipient-resolver.test.js lib/late-approval.test.js lib/late-notice.test.js
  55 tests, 55 pass, 0 fail

cd apps/mr-bot && node --test test/telegram-callback-http-contract.test.js lib/telegram-onboard.test.js
  33 tests, 33 pass, 0 fail

cd apps/mr-bot && node --test lib/late-approval-boundary.test.js lib/mail-resend.test.js && git diff --check
  9 tests, 9 pass, 0 fail; diff check passed

cd apps/mr-bot && node --test test/daily-journey-contract.test.js
  2 tests, 2 pass, 0 fail
```

The first GREEN contract covers both accepted-edit uncertainty paths: the second same-card edit
returns `message is not modified`, the email count remains one, and the durable Telegram receipt
status becomes sent.  The adversarial contract supplies callback message `777` while the durable
approval card is `700` and asserts that only `700` is edited.

## Focused verification

```text
cd apps/mr-bot && node --test lib/late-approval-boundary.test.js lib/mail-resend.test.js && git diff --check
  9 tests, 9 pass, 0 fail; diff check passed

cd apps/mr-bot && node --test lib/late-recipient-resolver.test.js lib/late-approval.test.js lib/late-notice.test.js test/late-approval-http-contract.test.js
  64 tests, 64 pass, 0 fail

cd apps/mr-bot && node --test test/daily-journey-contract.test.js
  2 tests, 2 pass, 0 fail; tick creates a durable awaiting-decision card and sends zero mail

cd apps/mr-bot && node --test test/telegram-callback-http-contract.test.js lib/telegram-onboard.test.js
  33 tests, 33 pass, 0 fail

cd apps/mr-bot && node --test lib/late-approval-boundary.test.js lib/mail-resend.test.js && git diff --check
  9 tests, 9 pass, 0 fail; diff check passed
```

## Full-suite baseline note

`npm ci --ignore-scripts --no-audit --no-fund` restored the installed dependency baseline without
changing `package.json` or `package-lock.json`.  The post-fix `npm test` now passes the updated DAILY
journey contract and stops with one unrelated legacy-path failure:

```text
apps/mr-bot/scripts/connector-host-bridge-boot.sh:6
apps/mr-bot/scripts/deploy-connector-runtime.sh:7
ENV_FILE="${LM_CONNECTOR_ENV_FILE:-${HOME}/.openclaw/.env}"
```

Those two existing out-of-scope shell references are reported by
`scripts/scan-legacy-paths.test.js`; no connector/mobile/geocode files were changed.  The full run
otherwise reaches the legacy-path stage with the reviewed suites green.

## Review handoff

The source, mutation, tenant-read, callback, concurrent receipt, accepted-edit retry, Telegram
retry, and no-send contracts are green.  The focused full-late suite is 64/64, the DAILY journey is 2/2, the Telegram
callback/onboard suite is 33/33, and the boundary/mail suite is 9/9.  No production provider,
database, deploy, or merge was touched.
