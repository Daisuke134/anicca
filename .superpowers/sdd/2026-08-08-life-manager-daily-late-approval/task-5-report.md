# Task 5 report — Side-Effect Boundary and Review Fixes

STATUS: DONE WITH OUT-OF-SCOPE FULL-SUITE NOTE

## Boundary proof

`apps/life-manager/lib/late-approval-boundary.test.js` scans the production JavaScript surface with
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

## Focused verification

```text
cd apps/life-manager && node --test lib/late-approval-boundary.test.js lib/mail-resend.test.js && git diff --check
  9 tests, 9 pass, 0 fail; diff check passed

cd apps/life-manager && node --test lib/late-recipient-resolver.test.js lib/late-approval.test.js lib/late-notice.test.js test/late-approval-http-contract.test.js
  61 tests, 61 pass, 0 fail

cd apps/life-manager && node --test test/daily-journey-contract.test.js
  2 tests, 2 pass, 0 fail; tick creates a durable awaiting-decision card and sends zero mail

cd apps/life-manager && node --test test/telegram-callback-http-contract.test.js lib/telegram-onboard.test.js
  33 tests, 33 pass, 0 fail

cd apps/life-manager && node --test lib/late-approval-boundary.test.js lib/mail-resend.test.js && git diff --check
  9 tests, 9 pass, 0 fail; diff check passed
```

## Full-suite baseline note

`npm ci --ignore-scripts --no-audit --no-fund` restored the installed dependency baseline without
changing `package.json` or `package-lock.json`.  The post-fix `npm test` now passes the updated DAILY
journey contract and stops with one unrelated legacy-path failure:

```text
apps/life-manager/scripts/connector-host-bridge-boot.sh:6
apps/life-manager/scripts/deploy-connector-runtime.sh:7
ENV_FILE="${LM_CONNECTOR_ENV_FILE:-${HOME}/.openclaw/.env}"
```

Those two existing out-of-scope shell references are reported by
`scripts/scan-legacy-paths.test.js`; no connector/mobile/geocode files were changed.  The full run
otherwise reaches the legacy-path stage with the reviewed suites green.

## Review handoff

The source, mutation, tenant-read, callback, concurrent receipt, Telegram retry, and no-send
contracts are green.  The focused full-late suite is 61/61, the DAILY journey is 2/2, the Telegram
callback/onboard suite is 33/33, and the boundary/mail suite is 9/9.  No production provider,
database, deploy, or merge was touched.
