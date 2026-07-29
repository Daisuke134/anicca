# Local financial report job proof

This evidence closes the bounded Task 5 implementation slice in
`2026-07-29-openclaw-to-life-manager-portable-runtime.md`. It does not authorize
disabling the legacy launchd report. Scheduler cutover still requires the
seven-expected-run gate.

## Proven path

```text
Life Manager scheduler owner
  → PostgreSQL runtime job
  → report.financial.telegram worker
  → existing financial snapshot and renderer
  → Telegram Bot API
  → immutable PostgreSQL runtime receipt
```

The proof stack used the committed local Compose topology and production
connector values injected into the process from Railway. The new runtime did
not source or read `~/.openclaw/.env`. The temporary Compose services were
stopped after verification; their volumes remain available for audit.

## Real effect receipt

| Field | Verified value |
|---|---|
| Runtime job | `financial-report:c33330ee5e9389330e943bc38b46c3ebee65f83a63aa40a989550bccbf9bfc16` |
| Job status | `completed` |
| Receipt kind/status | `telegram_financial_report` / `sent` |
| Telegram `message_id` | `432` |
| Snapshot hash | `875512db42a415864a5bea7804722aa47ed158a11b12c5b11f4bbaa65c44e856` |
| Chat identity | SHA-256 only: `ae8d45da4675d2cf4894f3ccc91da9f296cc2c0b0f286f76bcf21376d27b0f32` |
| Provider sent time | `2026-07-29T12:19:57.000Z` |
| Report cutoff | `2026-07-29T12:19:00.000Z` |
| Latest measured cost row | `2026-07-26T15:00:00.001Z` |
| Latest measured earning row | unavailable, stored as `null` |
| Balance observation | `2026-07-29T12:19:00.000Z` |

The adapter also reconciled the existing real daily and weekly Telegram
effects into safe runtime receipts without sending duplicates:

| Report | Existing message | Snapshot hash |
|---|---:|---|
| Daily `2026-07-29` | `423` | `9afdc042185ff90445aafc1b64992f55e726d6fbeda05ae4986df06b6215f7d3` |
| Weekly `2026-W31` | `298` | `960112aef6b5422ce65099815ded2df131fca6ae68bc0e8efb17327090fdb301` |

## Restart and legacy safety

Restarting the report worker left the count of real `sent` runtime receipts at
exactly `1 → 1`. The completed job was not dispatched again. An error after a
Telegram request begins is classified as an unknown external effect and enters
reconciliation rather than blind retry.

The installed legacy report LaunchAgent remained loaded with `runs=403` and
`last exit code=0`. No existing OpenClaw or launchd scheduler was disabled,
edited, or unloaded during this proof.

## Source basis

- [Telegram Bot API `sendMessage`](https://core.telegram.org/bots/api#sendmessage):
  “On success, the sent Message is returned.”
- [Amazon SQS at-least-once delivery](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html):
  consumers must be idempotent because a message copy can be delivered more
  than once.
- [PostgreSQL `INSERT`](https://www.postgresql.org/docs/current/sql-insert.html):
  `ON CONFLICT` provides the atomic conflict path used by the durable job
  identity.
