# Connector Gateway Report Send Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Own only `apps/mr-bot/lib/outbound-guardian.js`, `outbound-guardian.test.js`, `connector-minimal-operations.js`, and `connector-minimal-operations.test.js`. You are not alone in the codebase; preserve all other edits. Do not commit or push.

**Goal:** Deliver every-wake Connector reports through the existing OpenClaw Gateway without the message CLI's fixed 10-second timeout, while making a retry for the same wake idempotent.

**Architecture:** Keep OpenClaw/Gateway/Telegram as owner. Replace only `notifyOpenClaw` text delivery with the installed and live-proven `openclaw gateway call send --timeout 60000 --params <json> --json`. Operations supplies the exact safe wake ID as `idempotencyKey`. Validate inputs before spawn and keep positive top-level `messageId` as the sole success receipt. Photo delivery remains unchanged in this slice.

**Ponytail full gate:** Reuse the existing OpenClaw binary, Gateway `send` method, spawn boundary, parser, safe wake ID, and receipt store. Add no raw Bot API, token wiring, queue, retry, backoff, service, global config, or Gateway restart.

**Reviewed scope correction:** The first 4-file draft made the global legacy sender require a key and broke evidence, coverage, and legacy outbox callers. The shipped design preserves the legacy sender and adds a separate Gateway sender. All four active Connector text callers migrate with their existing stable IDs. Actual scope is 10 files, production +46/-12 and tests +126/-4; the expansion is required to prevent partial external effects and duplicate reports at every existing caller.

## Task 1: TDD the durable text send

- [x] RED: the separate Gateway sender invokes `openclaw gateway call send`, exact 60000ms timeout, JSON params with telegram channel/target/message/caller idempotency key, and `--json`; it returns a positive top-level message ID.
- [x] RED: missing/malformed idempotency key fails before spawn; nonpositive/missing message ID remains failure.
- [x] RED: current/historical operations, evidence, coverage, and legacy outbox deliveries pass an existing stable lineage ID.
- [x] GREEN: retain the legacy sender unchanged; add the minimum separate Gateway sender and migrate only Connector text callers. Retain `spawnSync` and no retry.
- [x] Run focused tests plus runner/production/native integration, syntax, diff, and fresh re-review.

## Acceptance

One wake causes one Gateway `send` request keyed by that wake ID. The command has a 60-second bounded Gateway timeout, no retry, and no raw credential in argv. A Gateway timeout remains a hard current-report failure and creates no local delivery receipt; later same-wake recovery uses the same idempotency key.
