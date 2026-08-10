# Connector Bounded Telegram Delivery Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Own only `apps/life-manager/lib/connector-telegram-delivery.js` and `apps/life-manager/lib/connector-telegram-delivery.test.js`. You are not alone in the codebase; preserve/accommodate all other edits and do not commit or push.

**Goal:** Provide a Connector-local, bounded Telegram Bot API adapter so every-wake text and application evidence image delivery cannot hang behind OpenClaw gateway/plugin shutdown.

**Architecture:** Inject the private bot token and `fetch` at construction. POST text JSON to `sendMessage` and PNG multipart to `sendPhoto`, each with one bounded AbortSignal and zero automatic retry. Validate target, token shape, message/caption bounds, PNG signature/size, HTTP/provider response, and positive safe-integer `message_id`; return the existing `{ messageId: "<positive>" }` contract. Never include token, target, message, caption, or provider body in thrown errors.

**Ponytail full gate:** Required because official wake `wake-d94d51d12b091af392ae0337` spent more than five minutes in a child `openclaw` process after the 10-second gateway timeout and produced no delivery receipt. Reuse native `fetch`, `FormData`, `Blob`, and `AbortSignal`; add no SDK, queue, retry, persistence, worker, or OpenClaw configuration change.

**Soft target:** 2 new files, production ≤90 LOC, tests ≤100 LOC.

## Task 1: TDD the bounded adapter

- [ ] RED: text uses exact Telegram endpoint/body, one request, bounded signal, and returns a positive string ID.
- [ ] RED: PNG uses `sendPhoto` multipart, exact target/caption, one request, bounded signal, and returns a positive string ID.
- [ ] RED: network error, timeout, non-2xx, malformed/non-JSON body, `ok:false`, nonpositive/unsafe ID, invalid token/target/text/PNG all fail closed with a generic secret-free error and retry 0.
- [ ] GREEN: implement the smallest frozen adapter using web-platform primitives only.
- [ ] Run focused test, syntax, diff check; report exact RED/GREEN evidence to Sol.

## Deferred next slice

Allowlist the existing private default Telegram bot token and inject this adapter into `createMinimalProductionOperations` and `createMinimalEvidenceChain`. Do not change loader/factory/operations/evidence in this slice.
