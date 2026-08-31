# Task 4 report — One-Decision Telegram Card

STATUS: DONE

## Scope

Task 4 owns the signed Telegram late-approval callback, chat-to-uid ownership check, delivery claim,
Resend idempotency key, provider receipt, and one Telegram receipt.  The scheduler/tick remains a
draft/card path and has no mail transport.

Owned implementation paths:

- `apps/mr-bot/lib/late-approval.js`
- `apps/mr-bot/lib/late-notice.js`
- `apps/mr-bot/lib/mail-resend.js`
- `apps/mr-bot/lib/notify.js`
- `apps/mr-bot/lib/telegram.js`
- `apps/mr-bot/server.js`
- `apps/mr-bot/test/late-approval-http-contract.test.js`

## RED

The required callback contract was written before the implementation and initially failed because
`createLateApprovalCallbackData` and `handleLateApprovalCallback` were not exported.  The previous
Telegram router also had no `late` callback branch.

## GREEN

The callback data is a signed, expiring HMAC token that stays within Telegram's 64-byte limit.  The
webhook rejects malformed/tampered/expired callbacks and callbacks whose Telegram actor/chat does not
own the `lm_users` row.  The send path is ordered:

```text
authenticated callback
  -> decideLateDraft
  -> claimApprovedDelivery
  -> Resend with stable Idempotency-Key
  -> recordLateDelivery(provider id)
  -> one Telegram delivery receipt
```

`do_not_send` is terminal and performs no mail call. Missing and ambiguous recipient rows remain
terminal and cannot claim a send.  The card renders the immutable stored recipient identity/email,
source/evidence, full body, ETA basis, and exactly two signed decision buttons.

Verification:

```text
cd apps/mr-bot && node --test test/late-approval-http-contract.test.js
  4 tests, 4 pass, 0 fail

cd apps/mr-bot && node --test lib/late-recipient-resolver.test.js lib/late-approval.test.js lib/late-notice.test.js test/late-approval-http-contract.test.js
  55 tests, 55 pass, 0 fail

cd apps/mr-bot && node --test test/telegram-callback-http-contract.test.js lib/telegram-onboard.test.js
  33 tests, 33 pass, 0 fail

cd apps/mr-bot && node --test lib/late-approval-boundary.test.js lib/mail-resend.test.js && git diff --check
  7 tests, 7 pass, 0 fail; diff check passed
```

The HTTP contract boots the actual `server.js`, posts a Telegram callback, verifies one Resend call,
one durable receipt RPC, one Telegram receipt, stable provider idempotency, replay suppression, and
cross-tenant suppression.  Local dependencies were installed with `npm ci --ignore-scripts` only to
run this real HTTP contract; no package files changed.

## Remaining gate

Task 5 must run the full `npm test` against the installed baseline and obtain the integrated fresh
review. Task 6 remains deployment-gated; no production state or external provider was mutated here.
