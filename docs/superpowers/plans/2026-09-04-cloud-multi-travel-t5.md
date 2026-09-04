# Cloud Multi-Travel T-5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure one later-start physical Calendar event whose departure T-5 is already due cannot be blocked by an earlier-start event whose own reminder is not due.

**Architecture:** Keep the existing Calendar, Transit/Google routing, Telegram send, `lm_travel_log` claim, and Telegram receipt paths unchanged. Preserve `nextReminderEvent()` for compatibility, but let `travelReminderOnce()` evaluate eligible events until it finds a currently-due event, then run the existing exactly-once claim/send/receipt path for that one event only. Do not add a scheduler, database table, provider, or second send path.

**Tech Stack:** Node.js CommonJS, built-in `node:test`, existing Life Manager Calendar/Transit/Telegram/Supabase adapters.

**Spec:** `docs/superpowers/specs/2026-08-26-life-manager-cloud-on-time-core-design.md` AC-18, AC-19, AC-24, AC-25, AC-26.

## Global Constraints

- `notifications_enabled!==false` and Telegram binding remain mandatory.
- Physical events notify at departure T-5; online/no-location events notify at event-start T-5.
- The 60-second owner may catch up only through the existing 15-minute window.
- Every event remains protected by the existing atomic `lm_travel_log(..., leg=telegram-t5)` claim.
- One invocation sends at most one event reminder; later ticks handle other due events through their independent claims.
- Preserve Telegram `message_id` receipt persistence and replay-zero behavior.
- No event title, location, phone, email, raw provider payload, or credential may enter success logs.
- No new table, scheduler, queue, route provider, or model call.

## Research Basis

1. Google Calendar Events API — https://developers.google.com/workspace/calendar/api/v3/reference/events
   - Core contract: each event carries its own `start.dateTime`; timezone is part of the event-time truth.
2. Google Cloud Tasks common pitfalls (Japanese) — https://docs.cloud.google.com/tasks/docs/common-pitfalls?hl=ja
   - Core contract: duplicate execution cannot be eliminated completely, so side effects must be designed to remain safe under replay.
3. Telegram `messages.sendMessage` — https://core.telegram.org/method/messages.sendMessage
   - Core contract: provider message identity is part of safe delivery semantics; Life Manager continues to persist the returned Telegram message ID.

---

### Task 1: Select a currently-due reminder across eligible events

**Files:**
- Modify: `apps/life-manager/lib/travel-reminder.js`
- Test: `apps/life-manager/lib/travel-reminder-multi-due.test.js`
- Regression: `apps/life-manager/lib/travel-reminder.test.js`

**Interfaces:**
- Consumes: existing event objects, `directionsRoute(...)`, `isReminderDue(...)`, origin/destination resolution, durable claim/send/receipt functions.
- Produces: unchanged `travelReminderOnce(user, nowMs, deps)` result contract, but it may select a later-start event when that event's computed reminder is due and earlier-start events are not.

- [x] **Step 1: Write the failing regression test**

The permanent regression creates an earlier 14:00 short trip and a later 14:20 long trip at 13:30. The first reminder is not due; the second is due exactly now. Expected: only the later event is claimed and sent.

- [x] **Step 2: Run the focused test and verify RED**

Run:

```bash
node --test \
  apps/life-manager/lib/travel-reminder-multi-due.test.js \
  apps/life-manager/lib/travel-reminder.test.js
```

Observed on GitHub Actions run `33868126721`: 31 pass / 1 fail. The new test returned `status='suppressed'` instead of `status='sent'`, proving the existing earliest-start selection masks the due later-start trip.

- [ ] **Step 3: Implement the minimum due-candidate selection**

Keep `nextReminderEvent()` unchanged. Extract the current per-event route/due preparation into one helper and iterate eligible timed non-helper events in stable start order until finding the first event for which `isReminderDue(now, dueAt)` is true. If no event is due, preserve `suppressed/not-due`; if no event exists, preserve `suppressed/no-event`. After selection, reuse the existing claim → send → Telegram receipt code unchanged.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the same focused command. Expected: all tests pass, including the new regression.

- [ ] **Step 5: Review and integrate safely**

Run `git diff --check`, perform a fresh read-only review for AC-18/19/24/25/26 and privacy/replay invariants, refresh from current `main`, preserve concurrent Lancers commits, remove temporary CI machinery, then open the bounded PR. Production E2E is a separate next task and is not claimed by unit-test GREEN.
