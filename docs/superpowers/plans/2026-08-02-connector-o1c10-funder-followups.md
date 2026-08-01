# O1C-10 Funder Follow-ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Subagents are disabled for this user-directed execution.

**Goal:** Send at most two source-bound follow-ups per successful funder thread, at day 3 and day 7, while stopping immediately on any inbound message, bounce, malformed thread, or missing Gmail receipt.

**Architecture:** Agent judgment supplies each personalized follow-up draft and its source-bound rationale. Deterministic Life Manager code owns timing, thread normalization, sender direction, the two-send ceiling, exact-replay ledger writes, and the one-effect Gmail boundary. The 2026-08-02 live threads remain scheduled or suppressed; none is sent early.

**Tech Stack:** Node.js CommonJS, `node:test`, `gog` Gmail CLI, PostgreSQL 18, Docker Compose.

## Global Constraints

- Always answer Dais in Japanese.
- Use the existing `gog` OAuth account and original Gmail thread; do not create a second mail transport.
- First follow-up is due 72 hours after initial send; second is due 96 hours after the first verified follow-up.
- Never send more than two follow-ups for one initial outreach.
- Any non-owner message after the initial send, including delivery failure, stops all follow-ups until O1C-11 classifies it.
- Semantic copy/rationale is an explicit `agent_judgment`; regex is used only for fixed machine formats and placeholders.
- No premature live send during O1C-10 because the current initial messages are less than 72 hours old.
- Repository evidence stores hashes and provider IDs, not raw recipient addresses or message bodies.

---

### Task 1: Follow-up decision and Gmail boundary

**Files:**
- Create: `apps/life-manager/lib/funder-followup.js`
- Create: `apps/life-manager/lib/funder-followup-gmail.js`
- Test: `apps/life-manager/lib/funder-followup.test.js`
- Modify: `apps/life-manager/package.json`

**Interfaces:**
- Consumes: one O1C-09 outreach receipt, a normalized Gmail thread, prior verified follow-up receipts, `now`, and an agent-authored draft.
- Produces: `planFunderFollowup(input)` with `scheduled | suppressed_inbound | complete | due`, and `deliverFunderFollowup(plan, dependencies)` returning a privacy-safe positive-ID receipt.

- [x] Write failing tests proving day-3 scheduling, day-7 scheduling, inbound/bounce suppression, malformed/cross-thread refusal, a hard maximum of two, one threaded send, and positive Gmail IDs.
- [x] Run `node --test lib/funder-followup.test.js`; verify RED because the modules do not exist.
- [x] Implement the minimum planner and delivery boundary needed for GREEN.
- [x] Re-run the focused test and verify every behavior is GREEN.

### Task 2: Append-only follow-up ledger

**Files:**
- Create: `apps/life-manager/lib/funder-followup-store.js`
- Create: `apps/life-manager/migrations/2026-08-02-lm-funder-followup-ledger.sql`
- Modify: `apps/life-manager/lib/funder-followup.test.js`
- Modify: `deploy/local/compose.yaml`

**Interfaces:**
- Consumes: a verified receipt from `deliverFunderFollowup`.
- Produces: `appendFunderFollowupReceipt(receipt, {query})`, allowing insert or exact replay only.

- [x] Extend the focused test first to require tenant-bound RLS, no UPDATE, unique follow-up number, and exact replay.
- [x] Run the focused test and verify RED because store/migration are absent.
- [x] Implement migration and store, then add the migration to local Compose order.
- [x] Re-run the focused test and verify GREEN.

### Task 3: Live no-early-send state and evidence

**Files:**
- Create: `docs/evidence/funding/2026-08-02-o1c10-funder-followups.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

**Interfaces:**
- Consumes: fresh Gmail headers for Evio, YeetVC, and J-Seed plus their O1C-09 ledger rows.
- Produces: exact due timestamps for Evio/J-Seed, permanent current suppression for YeetVC bounce, zero live follow-up sends, and remaining-item count 102.

- [x] Apply the migration to local PostgreSQL and persist privacy-safe scheduled/suppressed state without sending mail.
- [x] Run `npm run test:outbound`, `npm run test:runtime-up`, JSON validation, `git diff --check`, and machine-count unchecked items.
- [x] Record evidence and update O1C-10 only when fresh Gmail/DB readback matches the planner.
- [x] Commit implementation and documentation separately, push, and verify local HEAD equals remote branch HEAD.
