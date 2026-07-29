# Loop adapter registry proof

This evidence closes Task 6 Steps 1–2 of
`2026-07-29-openclaw-to-life-manager-portable-runtime.md`. It does not disable
or edit any legacy scheduler.

## Proven contract

| Gate | Result |
|---|---|
| Required methods | every adapter must implement `plan`, `execute`, `reconcile`, `verify`, and `report` |
| Routing | duplicate adapter, loop, and capability identifiers fail closed |
| Portability | absolute paths, traversal, URI module paths, OpenClaw/Profitable Claude/v0 roots, and credential-shaped fields fail closed |
| First registration | `financial-report-telegram` owns `report.financial.telegram` |
| Worker dispatch | the capability worker resolves execution through the configured registry |
| External effect | no new effect was triggered for this registry-only slice; the registered adapter retains the real Telegram `message_id=432` proof from `2026-07-29-local-financial-report-job.md` |
| Legacy safety | `ai.anicca.life-manager-financial-report` remains loaded until seven expected replacement receipts pass |

## Verification

```text
cd apps/life-manager
npm run test:runtime-adapters
node --test scripts/runtime-up.test.js lib/maybe-start-loops.test.js
```

## Source basis

- [Amazon SQS at-least-once delivery](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html):
  applications must be idempotent because message copies can be delivered more
  than once.
- [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests):
  retries use the same idempotency key and receive the stored first result
  instead of creating a second effect.
- [Temporal Activity definition](https://docs.temporal.io/activity-definition):
  externally interacting work is isolated behind a named Activity definition;
  the Life Manager registry applies the same bounded adapter boundary while
  retaining its own PostgreSQL job and receipt protocol.
