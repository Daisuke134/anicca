# Mr.bot DAILY Late-Notice Approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close DAILY row #5 by making every external late email impossible until one durable user approval claim succeeds, while preserving exactly-once approved delivery and permanent no-send decisions.

**Architecture:** The late tick becomes detection plus draft creation only. A resolver gathers evidence in the required five-stage order and stores candidates without guessing an address. Telegram renders one approval card from stored facts. Only an authenticated callback can atomically claim `send`; the claimed worker sends once and records provider receipt. `do_not_send` is terminal and suppresses every future tick.

**Tech Stack:** Node.js CommonJS, `node:test`, Supabase/PostgreSQL atomic RPCs, Telegram Bot API, Composio Calendar/Gmail, approved Contacts, public-web evidence, Resend.

## Global Constraints

- DAILY numbering and done receipt stay in `docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md` row #5.
- Do not expose any of this surface in `/api/mobile/v1`.
- Organizer is a candidate; exclude only self, resource rooms, and declined attendees.
- A candidate is `{display_name,email,source,evidence_refs,confidence,event_role}`. Missing or ambiguous email is never synthesized.
- The card shows recipient, email, source/evidence, complete body, and ETA evidence with exactly `[Send] [Don't send]` or localized equivalents.
- No mail transport call occurs before a durable approval claim.

## File Structure

| File | Change |
|---|---|
| `apps/mr-bot/lib/late-recipient-resolver.js` | Add evidence stages, entity resolution, ambiguity rules |
| `apps/mr-bot/lib/late-recipient-resolver.test.js` | Add resolver contract tests |
| `apps/mr-bot/lib/late-approval.js` | Add draft, terminal decision, claim, delivery receipt state machine |
| `apps/mr-bot/lib/late-approval.test.js` | Add state-machine and mutation tests |
| `apps/mr-bot/lib/late-notice.js` | Replace direct send with draft/approval enqueue |
| `apps/mr-bot/lib/late-notice.test.js` | Prove tick cannot send and cannot re-present terminal rows |
| `apps/mr-bot/lib/telegram.js` | Route signed late-approval callback data |
| `apps/mr-bot/test/late-approval-http-contract.test.js` | Exercise authenticated callback and exact send boundary |
| `apps/mr-bot/migrations/2026-08-08-lm-late-approval.sql` | Add evidence, draft, decision, claim, receipt tables/RPCs |
| `docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md` | Add deployed completion receipt only after production verification |

### Task 1: Freeze Recipient Resolution

**Interface:**

```javascript
async function resolveLateRecipients({ uid, event, actorEmails }, deps)
// -> { status: "resolved"|"ambiguous"|"missing", candidates: RecipientCandidate[], evidenceRefs: string[] }
```

- [ ] Write resolver tests for organizer inclusion; self/resource/declined exclusion; Calendar attendee; connected Gmail; approved Contacts; public-web evidence; and one user-confirmation request after all earlier stages fail.
- [ ] Assert that conflicting candidates return `ambiguous`, expose no send action, and never fabricate an email.
- [ ] Run `cd apps/mr-bot && node --test lib/late-recipient-resolver.test.js`; record RED from the missing module.
- [ ] Implement the ordered resolver with injected evidence providers and deterministic entity merge by verified email plus evidence reference.
- [ ] Re-run the test and record GREEN.
- [ ] Commit and push the resolver slice.

### Task 2: Add the Durable Approval State Machine

**State contract:**

```text
draft -> awaiting_decision -> send_claimed -> sent
                         \-> do_not_send
draft -> recipient_missing | recipient_ambiguous
```

```javascript
async function createLateDraft(input, store)
async function decideLateDraft({ uid, draftId, decision, idempotencyKey }, store)
async function claimApprovedDelivery({ draftId, workerId }, store)
async function recordLateDelivery({ draftId, providerMessageId, deliveredAt }, store)
```

- [ ] Add SQL tables with unique `(uid,event_key)`, immutable evidence/body snapshot, terminal decision, claim token, and provider receipt.
- [ ] Add atomic RPCs so one decision wins, duplicate same decisions return the original row, conflicting decisions are rejected, and one worker can claim delivery.
- [ ] Write migration structure tests plus `late-approval.test.js` for double-tap, two workers, retry after worker interruption, permanent no-send, and recipient-missing/ambiguous states.
- [ ] Run the focused tests and record RED.
- [ ] Implement the Supabase store and pure state transition helpers.
- [ ] Re-run focused tests and apply the migration to staging; read the created schema/RPCs back.
- [ ] Commit and push the state-machine slice.

### Task 3: Remove Tick-Time External Delivery

- [ ] First add a test whose `sendLateNotice` dependency throws if invoked by `processLocationLateNotice()`.
- [ ] Assert a late decision creates one stored draft/card request and repeated ticks return the existing row.
- [ ] Assert missing/ambiguous recipients create no send button and no external operation.
- [ ] Run `node --test lib/late-notice.test.js`; record RED against the current direct call at `lib/late-notice.js`.
- [ ] Replace the direct call with recipient resolution, body/ETA snapshot, durable draft creation, and Telegram card enqueue.
- [ ] Delete the tick dependency on the mail sender. Keep the sender injectable only in the callback-owned delivery function.
- [ ] Re-run `lib/late-notice.test.js lib/late-recipient-resolver.test.js lib/late-approval.test.js` and record GREEN.
- [ ] Commit and push the no-send tick slice.

### Task 4: Wire the One-Decision Telegram Card

- [ ] Add callback contract tests for signed/owned `send`, `do_not_send`, replay, wrong user, expired card, missing recipient, and ambiguous recipient.
- [ ] Assert the rendered card includes the complete stored body, ETA basis, recipient identity, email, source, evidence, and exactly two decision buttons.
- [ ] Run `node --test test/late-approval-http-contract.test.js`; record RED.
- [ ] Route callback data through existing Telegram authentication, derive `uid` from chat ownership, and call `decideLateDraft`.
- [ ] For `send`, claim delivery before calling `sendLateNotice`; record Resend provider ID before posting one Telegram receipt.
- [ ] For `do_not_send`, perform zero external send and mark the row permanently terminal.
- [ ] Re-run callback, Telegram, and late suites; record GREEN.
- [ ] Commit and push the callback slice.

### Task 5: Prove the Side-Effect Boundary

- [ ] Add a source/contract test that permits the mail transport only behind `claimApprovedDelivery` and the authenticated callback entry point.
- [ ] Mutation-check the boundary by moving the sender before the claim; confirm the test fails, then restore the correct order.
- [ ] Run the focused suite plus `npm test`; compare full-suite failures to the clean-worktree baseline.
- [ ] Ask the fresh integrated reviewer to inspect approval, claim, retry, and no-send invariants.
- [ ] Fix concrete safety defects and repeat the focused suite.

### Task 6: Deploy and Record the DAILY Receipt

- [ ] Merge only this gate's diff over current `canonical/main` and push.
- [ ] Verify Railway deployment `commitHash` and `/health` build identity.
- [ ] With a real controlled event, observe draft/card creation and zero email before action.
- [ ] Tap `Don't send`; verify Resend external sends remain zero and another tick does not recreate the card.
- [ ] With a separate controlled event, tap `Send` twice; verify one Resend provider receipt and one Telegram delivery receipt.
- [ ] Verify missing and ambiguous recipients have no send control.
- [ ] Add the exact production evidence to DAILY row #5, commit, and push.

## Verification Commands

```bash
cd apps/mr-bot
node --test lib/late-recipient-resolver.test.js lib/late-approval.test.js lib/late-notice.test.js test/late-approval-http-contract.test.js
node --test test/telegram-callback-http-contract.test.js lib/telegram-onboard.test.js
npm test
git diff --check
```

The two focused commands must finish with zero failures. `npm test` must match or improve the clean installed baseline without changing an unrelated failing assertion.
