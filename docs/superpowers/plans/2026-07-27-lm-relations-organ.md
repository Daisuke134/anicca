# H5 ORG-relations Implementation Plan

> **For executor:** Use Superpowers test-driven-development and verification-before-completion. Execute one RED/GREEN slice at a time in the isolated worktree.

**Goal:** Detect stable person-specific interaction cadence from real cloud sources and send one source-honest, privacy-preserving suggestion.

**Architecture:** Normalize Calendar one-to-one events into opaque interaction records, reuse the care cadence stability guard, persist only hashed metrics, and share MENTAL's send budget.

**Tech Stack:** Node.js 20, `node:test`, Google Calendar/Composio adapter, Supabase/PostgREST, Telegram, Railway.

---

### Task 1: Pure detector

**Files:**
- Add: `apps/life-manager/lib/relation-detector.test.js`
- Add: `apps/life-manager/lib/relation-detector.js`
- Add: `apps/life-manager/eval/relation-cases.jsonl`
- Add: `apps/life-manager/eval/run-relation-eval.js`

1. RED: stable monthly cadence overdue, within-cadence silence, zero/single silence.
2. RED: three interactions and unstable cadence are observe-only.
3. RED: candidates contain only closed fields and sort by overdue ratio.
4. GREEN: group/dedupe/median/stability using `judgeCadenceStability`.
5. Run focused tests and deterministic eval.

### Task 2: Calendar adapter

**Files:**
- Modify: `apps/life-manager/lib/events-history.test.js`
- Modify: `apps/life-manager/lib/events.js`
- Add: `apps/life-manager/lib/relation-calendar.test.js`
- Add: `apps/life-manager/lib/relation-calendar.js`

1. RED: history projection preserves attendees/organizer without changing completeness.
2. RED: exactly-one external accepted attendee + provider displayName becomes one interaction.
3. RED: group meetings, declined/resource/self, all-day, unnamed attendees are excluded.
4. RED: output never contains email; same normalized email gives same HMAC key.
5. GREEN: minimal projection and adapter.

### Task 3: Runtime and ledger

**Files:**
- Add: `apps/life-manager/lib/relations-runtime.test.js`
- Add: `apps/life-manager/lib/relations-runtime.js`
- Add: `apps/life-manager/migrations/2026-07-27-lm-relations-log.sql`
- Add: `apps/life-manager/migrations/2026-07-27-lm-mental-send-log-relations-trigger.sql`
- Add: `apps/life-manager/lib/relations-migration.test.js`
- Modify: `apps/life-manager/lib/i18n.js`

1. RED: local 18:30 window, unknown timezone, mid-event, moving, MENTAL cap/spacing, weekly cooldown.
2. RED: strict history/read failure writes no claim; successful scan writes PII-free metrics.
3. RED: send flow claims attempt first, sends one source-honest line, writes delivery and MENTAL receipt.
4. RED: failed send never writes delivery and cannot retry through the weekly attempt gate.
5. GREEN: implement minimal runtime and append-only SQL.

### Task 4: Scheduler wiring

**Files:**
- Add: `apps/life-manager/lib/relations-wiring.test.js`
- Modify: `apps/life-manager/scheduler.js`
- Modify: `apps/life-manager/package.json`

1. RED: H5 runs after H4, only for notification-enabled users.
2. RED: H5 throw cannot break wake/care/diet/precepts; H4 throw cannot skip H5.
3. RED: kill switch accepts all operator spellings and defaults on.
4. GREEN: import, gate, isolated call, log, npm test/eval reachability.

### Task 5: Verify and release

1. Run focused suites and mutation checks.
2. Run `npm test` and `npm run eval`.
3. Commit/push; open and merge implementation PR.
4. Apply both additive migrations and read back table/constraints/grants/triggers.
5. Verify Railway exact SHA, health, startup logs.
6. Run production read-only Calendar source through the deployed adapter; current measured shape must abstain without invented names.
7. Update consolidation SSOT and merge evidence PR.

