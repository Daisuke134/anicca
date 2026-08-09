# Life Manager CFO Real Telegram Delivery Implementation Plan

> **Execution routing:** Ponytail full and Superpowers subagent-driven-development are mandatory. Sol owns this
> plan, review, live evidence, and spec state. Only a Luna implementer writes production code or tests.

**Goal:** Close CFO-1h by delivering the existing truthful assets/liabilities snapshot to the owner's real Telegram
exactly once and durably recording Telegram's positive provider `message_id`.

**Architecture:** Add one thin orchestration function around the existing renderer, delivery claim, Telegram
transport, and delivery receipt. A `sent` claim is a no-op. A `reconcile` claim never blindly resends. A `send` claim
renders, sends once, validates Telegram's real response, and then records the message ID. No new database object,
service, queue, scheduler, connector, framework, or dependency is allowed.

**Status:** ACTIVE — Luna implementation next.

## Ponytail size and scope gate

| Element | Files | Production LOC soft target | Why it exists |
|---|---:|---:|---|
| Delivery orchestrator | 1 new | <=70 | Connect four already-tested components |
| Focused contract test | 1 new | 0 | Prove one send and no duplicate/reconcile resend |
| Total | 2 | <=70 | Below the 3-file / 100-LOC slice limit |

Explicitly excluded: scheduler changes, Moneytree connector changes, schema changes, correction revisions, provider
outage UX, Binance, tax, business P&L, generic workflow abstractions, and broad hostile-object test matrices.

## Task 1: Deliver one truthful snapshot exactly once

**Files:**
- Create `apps/life-call/lib/cfo-telegram-send.js`
- Create `apps/life-call/lib/cfo-telegram-send.test.js`

**Interface:** `deliverCfoTelegram(input, options)` where `input` contains only the owner scope, destination,
Telegram token, immutable snapshot public reference, and the already-validated snapshot. `options` provides existing
claim, render, send, and record functions for focused tests.

- [ ] **RED:** One valid `send` claim renders the Japanese summary, calls Telegram exactly once with its existing
      inline buttons, requires `ok === true` and a positive safe-integer `result.message_id`, then records that exact
      ID against the claim.
- [ ] **Duplicate safety:** `sent` and `reconcile` each produce zero Telegram calls and zero receipt writes.
- [ ] **Failure safety:** An invalid/rejected Telegram provider response produces no receipt and exposes no token,
      chat ID, UID, snapshot, raw response, or financial amount in the error.
- [ ] **GREEN:** Implement the minimum orchestration only. Do not retry Telegram inside this function and do not log.
- [ ] **Verify:** Run the focused test, `npm run test:cfo`, the full `npm test`, LOC, and `git diff --check`.
- [ ] **Review:** Fresh Sol reviewer returns no Critical/Important findings.
- [ ] **Real E2E:** Sol reads a fresh real Moneytree snapshot, verifies the exact local render, performs one real send,
      verifies the positive provider `message_id`, and verifies the durable receipt without printing identifiers or
      credentials. If the claim says `sent` or `reconcile`, do not resend blindly.
- [ ] **Close:** Update the parent CFO spec to mark CFO-1h complete, commit, and push. CFO-1i becomes the only active
      item.

## Definition of done

CFO-1h is complete only after the owner's Telegram contains the real finance report and the same positive Telegram
`message_id` exists in the durable delivery receipt. Unit tests, previews, fake responses, or a delivery claim alone
do not satisfy this task.
