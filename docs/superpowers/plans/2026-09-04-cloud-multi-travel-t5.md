# Cloud Multi-Travel T-5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure one later-start physical Calendar event whose departure T-5 is already due cannot be blocked by an earlier-start event whose own reminder is not due, and an already-sent due event cannot starve another due event.

**Architecture:** Keep the existing Calendar, Transit/Google routing, Telegram send, `lm_travel_log` claim, and Telegram receipt paths unchanged. Preserve `nextReminderEvent()` for compatibility. `travelReminderOnce()` prepares eligible event route/due facts concurrently behind the existing provider timeout, orders currently-due candidates by due time, and claims them in order until one unsent candidate is acquired; only that candidate enters the existing single send/receipt path. Do not add a scheduler, database table, provider, or second send path.

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

### Task 1: Select and claim a currently-due reminder across eligible events

**Files:**
- Modify: `apps/life-manager/lib/travel-reminder.js`
- Test: `apps/life-manager/lib/travel-reminder-multi-due.test.js`
- Regression: `apps/life-manager/lib/travel-reminder.test.js`

**Interfaces:**
- Consumes: existing event objects, `directionsRoute(...)`, `isReminderDue(...)`, origin/destination resolution, durable claim/send/receipt functions.
- Produces: unchanged `travelReminderOnce(user, nowMs, deps)` result contract, but it may select a later-start event when that event's computed reminder is due and earlier-start events are not, and it skips already-claimed due events to reach another due event.

- [x] **Step 1: Write the failing later-start / earlier-departure regression**

The permanent regression creates an earlier 14:00 short trip and a later 14:20 long trip at 13:30. The first reminder is not due; the second is due exactly now. Expected: only the later event is claimed and sent.

- [x] **Step 2: Verify the first RED**

Run:

```bash
node --test \
  apps/life-manager/lib/travel-reminder-multi-due.test.js \
  apps/life-manager/lib/travel-reminder.test.js
```

GitHub Actions `33868126721`: 31 pass / 1 fail. The new test returned `status='suppressed'` instead of `status='sent'`, proving earliest event-start selection masked a due later-start trip.

- [x] **Step 3: Implement due-candidate preparation without serial provider starvation**

`nextReminderEvent()` remains compatible. Eligible timed non-helper events are prepared independently; route/due preparation starts concurrently so one slow Transit candidate cannot serially consume the 35-second reminder budget. Due selection uses computed departure T-5 rather than event-start order. The selected candidate alone reaches the existing Telegram effect path.

Fresh review found the first sequential implementation could make the provider budget `25s × N`. TDD run `33868805045` isolated this as `1 !== 2` route evaluations started before release. Final concurrency GREEN `33868886846` passed 33/33.

- [x] **Step 4: Close already-sent due-event starvation**

Fresh CodeRabbit/manual review found that if two trips share the same due time, an already-sent first trip could be selected every tick, fail its duplicate claim, and starve the second due trip. A permanent regression `an already-claimed due trip does not starve another due trip` reproduced the defect.

RED: GitHub Actions `33869645108` — 34 total, 33 pass / 1 fail (`suppressed` instead of `sent`).

Fix: order due candidates, attempt the existing durable `telegram-t5` claim in that order, skip candidates whose claim already exists, and send only the first due candidate whose claim is newly acquired. If every due candidate is already claimed, preserve `suppressed/duplicate`.

GREEN: GitHub Actions `33869733279` — focused suite succeeded and the CI-owned commit removed the temporary TDD workflow/script. The permanent suite is **34/34** after this fix.

- [x] **Step 5: Fresh review, clean integration, and production deploy**

Fresh review checked AC-18/19/24/25/26, privacy, replay safety, the slow-route deadline regression, and duplicate-due starvation. The TDD branch was replaced by clean PR `#4095`, containing one commit and only the final three production/test/docs files. PR `#4095` merged as `2ade8ec054188a98dbe19820d8d59b5c130927f6`.

Railway/GitHub commit-status readback for that exact merge is aggregate `success`: `Anicca - life-call` is success, `Anicca - money-printer-worker` is success, and `Anicca - x402-agents` reports `No deployment needed - watched paths not modified`. The current `main` still contains the due-candidate concurrent preparation and skip-already-claimed selection code.

The same watch-path isolation is still healthy on current main `5420430fefd32e7df89cf64489f8b7ed2b1c4842`: life-call, money-printer-worker, and x402-agents all report `No deployment needed - watched paths not modified`, with aggregate commit status `success`.

- [ ] **Step 6: Prove the multi-event production provider boundary without disturbing a real user schedule**

The pre-existing on-time-core Task 16AG already proves the single-event provider path: a controlled physical Calendar event produced one `provider=transit` Telegram send, durable positive `message_id=981`, and replay-zero on the next 60-second tick. That evidence does **not** prove this multi-event regression because it had only one non-helper reminder candidate.

Close this step only with one natural production window containing at least two eligible non-helper events where a later-start event has an earlier computed departure T-5, or with a separate beta tenant whose call lane is explicitly disabled. Require the later-start/earlier-departure event to receive one provider-backed Telegram message with a positive durable `telegram-t5` receipt; if an earlier due candidate is already claimed, require the next due candidate to send once. The following fixed-60-second tick must add Telegram sends `0` and leave both claims unchanged.

Do not create fake controlled physical events on Dais's live tenant merely to force this proof while `call_enabled=true` / `wake_policy=all-events`, because those test events would also create real T-10/T-5 phone effects. Do not weaken the call policy or manually trigger the scheduler to make the test convenient.
