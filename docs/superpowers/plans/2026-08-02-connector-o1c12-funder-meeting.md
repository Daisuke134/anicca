# O1C-12 Funder Meeting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` inline. Subagents and human confirmation pauses are disabled for this execution.

**Goal:** Turn a verified meeting request into one conflict-free Calendar event, one source-bound interview brief, and one append-only receipt.

**Architecture:** Agent judgments own semantic scheduling and brief content. Deterministic modules bind evidence, check all-calendar free/busy, execute one existing gog Calendar transport write, validate positive provider evidence, and persist privacy-safe immutable state.

**Tech Stack:** Node.js CommonJS, `node:test`, gog 0.17.0, PostgreSQL 18, application-kit.

## Global Constraints

- No human confirmation wait.
- No Calendar write without an O1C-11 `meeting_requested` observation.
- No judgment by regex or keyword fallback.
- No raw Gmail sender, subject, body, or evidence quote in repository/ledger.
- Current live state has zero meetings, so current live Calendar effects must remain zero.

### Task 1: Meeting and brief plan

**Files:**
- Create: `apps/life-manager/lib/funder-meeting.js`
- Test: `apps/life-manager/lib/funder-meeting.test.js`
- Modify: `apps/life-manager/package.json`

- [ ] Write RED tests proving a source-bound agent schedule and six-section brief create one plan.
- [ ] Add rejection cases for non-meeting status, fabricated quote, conflict, bad duration/time zone, and unsafe brief source.
- [ ] Implement the minimum validator/planner and run focused tests GREEN.

### Task 2: Positive Calendar receipt and append-only store

**Files:**
- Modify: `apps/life-manager/lib/transport/calendar-gog.js`
- Modify: `apps/life-manager/lib/transport/transport-gog.test.js`
- Create: `apps/life-manager/lib/funder-meeting-store.js`
- Create: `apps/life-manager/migrations/2026-08-02-lm-funder-meeting-ledger.sql`
- Modify: `deploy/local/compose.yaml`

- [ ] Write RED tests proving gog event ID/URL readback, one create, no success on missing IDs, exact replay, tenant RLS, and no UPDATE.
- [ ] Implement positive Calendar receipt propagation and the store/migration.
- [ ] Run focused, transport, outbound, and runtime regressions GREEN.

### Task 3: Live zero-effect evidence

**Files:**
- Create: `docs/evidence/funding/2026-08-02-o1c12-funder-meeting.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

- [ ] Fresh-read Gmail typed-status DB and Calendar around the relevant window.
- [ ] Prove meeting-request count 0, meeting-ledger count 0, and no invented Calendar event.
- [ ] Record evidence, mark only O1C-12, machine-count 100 remaining, commit/push, and verify remote equality.
