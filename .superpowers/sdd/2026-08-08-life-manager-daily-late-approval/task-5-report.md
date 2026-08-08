# Task 5 report — Side-Effect Boundary

STATUS: DONE WITH BASELINE SUITE NOTE

## Boundary proof

`apps/life-manager/lib/late-approval-boundary.test.js` pins all four required relationships:

- `late-notice.js` and the scheduler contain no mail transport dependency.
- `late-approval.js` invokes `sendLateNotice` only after `claimApprovedDelivery` returns a claim.
- `recordLateDelivery` is after the provider call.
- The Telegram delivery receipt is after the durable provider receipt.

The mutation probe moves the sender token before the claim in an in-memory source mutation and
asserts that the order contract fails.  The production source is not changed by the probe.

## Focused verification

```text
cd apps/life-manager && node --test lib/late-approval-boundary.test.js lib/mail-resend.test.js && git diff --check
  7 tests, 7 pass, 0 fail; diff check passed

cd apps/life-manager && node --test lib/late-recipient-resolver.test.js lib/late-approval.test.js lib/late-notice.test.js test/late-approval-http-contract.test.js
  55 tests, 55 pass, 0 fail

cd apps/life-manager && node --test test/telegram-callback-http-contract.test.js lib/telegram-onboard.test.js
  33 tests, 33 pass, 0 fail
```

## Full-suite baseline note

`npm ci --ignore-scripts --no-audit --no-fund` restored the installed dependency baseline without
changing `package.json` or `package-lock.json`.  `npm test` now reaches the existing `CORE 8e`
`test/daily-journey-contract.test.js` assertion at line 218 and stops with one failure:

```text
late.sent: false !== true
```

That assertion still requires Task 3's retired tick-time direct email/report path.  Task 3's current
contract intentionally returns a durable draft/card with `sent: false`; this Task 5 slice does not
weaken the side-effect boundary or change an unrelated assertion to hide the mismatch.  The new
focused suites and the existing Telegram contract suite are green.

## Review handoff

The source and mutation contracts are green.  A fresh integrated reviewer should inspect the
approval/claim/retry/no-send invariants before any production mutation; no production provider or
database was touched in Task 5.
