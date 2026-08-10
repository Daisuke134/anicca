# Connector Gateway Report Send Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Own only `apps/life-manager/lib/outbound-guardian.js`, `outbound-guardian.test.js`, `connector-minimal-operations.js`, and `connector-minimal-operations.test.js`. You are not alone in the codebase; preserve all other edits. Do not commit or push.

**Goal:** Deliver every-wake Connector reports through the existing OpenClaw Gateway without the message CLI's fixed 10-second timeout, while making a retry for the same wake idempotent.

**Architecture:** Keep OpenClaw/Gateway/Telegram as owner. Replace only `notifyOpenClaw` text delivery with the installed and live-proven `openclaw gateway call send --timeout 60000 --params <json> --json`. Operations supplies the exact safe wake ID as `idempotencyKey`. Validate inputs before spawn and keep positive top-level `messageId` as the sole success receipt. Photo delivery remains unchanged in this slice.

**Ponytail full gate:** Reuse the existing OpenClaw binary, Gateway `send` method, spawn boundary, parser, safe wake ID, and receipt store. Add no raw Bot API, token wiring, queue, retry, backoff, service, global config, or Gateway restart.

**Soft target exception:** 4 files, production ≤30 LOC, tests ≤75 LOC. Four files are the irreducible adapter+caller contract required to avoid a random idempotency key and duplicate external notifications.

## Task 1: TDD the durable text send

- [ ] RED: `notifyOpenClaw` invokes `openclaw gateway call send`, exact 60000ms timeout, JSON params with telegram channel/target/message/caller idempotency key, and `--json`; it returns a positive top-level message ID.
- [ ] RED: missing/malformed idempotency key fails before spawn; nonpositive/missing message ID remains failure.
- [ ] RED: current and historical wake report deliveries pass their own exact wake ID as idempotency key.
- [ ] GREEN: implement only the minimum argument/validation changes; retain `spawnSync` and no retry.
- [ ] Run outbound guardian and operations focused tests plus runner/production/native integration, syntax, and diff checks.

## Acceptance

One wake causes one Gateway `send` request keyed by that wake ID. The command has a 60-second bounded Gateway timeout, no retry, and no raw credential in argv. A Gateway timeout remains a hard current-report failure and creates no local delivery receipt; later same-wake recovery uses the same idempotency key.
