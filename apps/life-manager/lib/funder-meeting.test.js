"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const { planFunderMeeting, deliverFunderMeeting } = require("./funder-meeting.js");
const { appendFunderMeetingReceipt } = require("./funder-meeting-store.js");

const DIGEST = "a".repeat(64);
const OUTREACH = Object.freeze({
  schema_version: 1,
  tenant_id: "dais-local",
  outreach_id: "funder-outreach:" + "b".repeat(64),
  candidate_id: "example-vc",
  funder_name: "Example VC",
  source_url: "https://example.vc/thesis",
  provider_thread_id: "19fc000000000001",
});
const MESSAGE = Object.freeze({
  provider_message_id: "19fc000000000002",
  provider_thread_id: OUTREACH.provider_thread_id,
  observed_at: "2026-08-03T01:00:00.000Z",
  sender: "partner@example.vc",
  subject: "Re: Anicca",
  body: "This looks relevant. Can we meet Tuesday, August 11 at 10:00 JST for 30 minutes on Google Meet?",
});
const STATUS = Object.freeze({
  schema_version: 1,
  observation_id: "funder-inbound-status:" + "c".repeat(64),
  tenant_id: OUTREACH.tenant_id,
  outreach_id: OUTREACH.outreach_id,
  candidate_id: OUTREACH.candidate_id,
  status: "meeting_requested",
  provider_message_id: MESSAGE.provider_message_id,
  provider_thread_id: MESSAGE.provider_thread_id,
  observed_at: MESSAGE.observed_at,
  sender_sha256: "0a3d7f9ce67af98d76c00f2f20e89d89f39cf0eb2d7dc18695bbe28f464e1196",
  subject_sha256: "d".repeat(64),
  body_sha256: "placeholder-overridden-in-test",
  evidence_sha256: "e".repeat(64),
  rationale_sha256: "f".repeat(64),
});

function sha(value) {
  return require("node:crypto").createHash("sha256").update(value, "utf8").digest("hex");
}

function status() {
  return {
    ...STATUS,
    sender_sha256: sha(MESSAGE.sender),
    subject_sha256: sha(MESSAGE.subject),
    body_sha256: sha(MESSAGE.body),
  };
}

function schedule() {
  return {
    kind: "agent_judgment",
    rationale: "The counterpart proposed an exact future slot and duration.",
    evidence_quotes: ["Tuesday, August 11 at 10:00 JST for 30 minutes"],
    title: "Anicca × Example VC",
    start_at: "2026-08-11T01:00:00.000Z",
    end_at: "2026-08-11T01:30:00.000Z",
    time_zone: "Asia/Tokyo",
    location: "Google Meet",
  };
}

function brief() {
  const section = (text, source_refs) => ({ text, source_refs });
  return {
    kind: "agent_judgment",
    rationale: "The brief emphasizes verified company facts and the funder's official thesis.",
    sections: {
      objective: section("Confirm thesis fit and agree on a concrete next diligence step.", ["application-kit://KIT.md"]),
      company_snapshot: section("Anicca is an autonomous behavior-change AI built in Tokyo.", ["application-kit://KIT.md"]),
      funder_fit: section("Connect the product's agent infrastructure to Example VC's stated thesis.", [OUTREACH.source_url]),
      likely_questions: section("Be ready to explain traction, defensibility, and the autonomous operating model.", ["application-kit://answers/q04_traction.en.md", "application-kit://answers/q07_competition.en.md"]),
      questions_to_ask: section("Ask which proof points are required for a partner meeting.", [OUTREACH.source_url]),
      risks: section("Separate verified traction from planned capabilities and avoid unsupported claims.", ["application-kit://answers/q10_risks.en.md"]),
    },
  };
}

function freebusy(busy = []) {
  return { calendars: { primary: { busy }, work: { busy: [] } } };
}

function input(overrides = {}) {
  return {
    outreachReceipt: OUTREACH,
    statusObservation: status(),
    message: MESSAGE,
    scheduleJudgment: schedule(),
    briefJudgment: brief(),
    kitSnapshot: { schema_version: 1, root_ref: "application-kit://current", kit_digest: DIGEST },
    freebusy: freebusy(),
    now: "2026-08-03T02:00:00.000Z",
    ...overrides,
  };
}

test("verified meeting judgment creates one conflict-free Calendar plan and six-section brief", () => {
  const plan = planFunderMeeting(input());
  assert.equal(plan.status, "ready");
  assert.equal(plan.calendar.start_at, "2026-08-11T01:00:00.000Z");
  assert.equal(plan.calendar.end_at, "2026-08-11T01:30:00.000Z");
  assert.equal(plan.calendar.duration_minutes, 30);
  assert.match(plan.meeting_id, /^funder-meeting:[0-9a-f]{64}$/);
  assert.match(plan.brief_sha256, /^[0-9a-f]{64}$/);
  assert.deepEqual(Object.keys(plan.brief_sections), [
    "objective", "company_snapshot", "funder_fit", "likely_questions", "questions_to_ask", "risks",
  ]);
  assert.equal(JSON.stringify(plan).includes(MESSAGE.body), false);
});

test("non-meeting status, fabricated quote, conflict, bad duration/timezone, and unsafe source fail closed", () => {
  assert.throws(() => planFunderMeeting(input({ statusObservation: { ...status(), status: "reply_received" } })), /funder meeting/i);
  assert.throws(() => planFunderMeeting(input({ scheduleJudgment: { ...schedule(), evidence_quotes: ["invented confirmation"] } })), /funder meeting/i);
  assert.throws(() => planFunderMeeting(input({ freebusy: freebusy([{ start: "2026-08-11T01:10:00Z", end: "2026-08-11T01:20:00Z" }]) })), /calendar conflict/i);
  assert.throws(() => planFunderMeeting(input({ scheduleJudgment: { ...schedule(), end_at: "2026-08-11T04:00:00Z" } })), /funder meeting/i);
  assert.throws(() => planFunderMeeting(input({ scheduleJudgment: { ...schedule(), time_zone: "UTC" } })), /funder meeting/i);
  const unsafe = brief();
  unsafe.sections.risks = { text: "Use private notes.", source_refs: ["file:///tmp/private"] };
  assert.throws(() => planFunderMeeting(input({ briefJudgment: unsafe })), /funder meeting/i);
});

test("one Calendar write requires positive event ID and URL and returns a privacy-safe receipt", async () => {
  const plan = planFunderMeeting(input());
  let calls = 0;
  const receipt = await deliverFunderMeeting(plan, { calendar: { createEvent: async (_uid, event) => {
    calls += 1;
    assert.equal(event.summary, "Anicca × Example VC");
    return { successful: true, event_id: "calendar-event-123", html_link: "https://calendar.google.com/calendar/event?eid=abc" };
  } }, observedAt: () => "2026-08-03T02:00:01.000Z" });
  assert.equal(calls, 1);
  assert.equal(receipt.provider_event_id, "calendar-event-123");
  assert.equal(receipt.provider_event_url, "https://calendar.google.com/calendar/event?eid=abc");
  assert.equal("brief_markdown" in receipt, false);
  await assert.rejects(() => deliverFunderMeeting(plan, { calendar: { createEvent: async () => ({ successful: true }) } }), /Calendar receipt/i);
});

test("meeting receipt store is tenant-bound append-only exact replay", async () => {
  const migration = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-02-lm-funder-meeting-ledger.sql"), "utf8");
  assert.match(migration, /CREATE TABLE IF NOT EXISTS public\.lm_funder_meeting_ledger/i);
  assert.match(migration, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(migration, /UNIQUE \(tenant_id, status_observation_id\)/i);
  assert.doesNotMatch(migration, /UPDATE public\.lm_funder_meeting_ledger/i);
  const plan = planFunderMeeting(input());
  const receipt = await deliverFunderMeeting(plan, { calendar: { createEvent: async () => ({ successful: true, event_id: "calendar-event-123", html_link: "https://calendar.google.com/calendar/event?eid=abc" }) }, observedAt: () => "2026-08-03T02:00:01.000Z" });
  const calls = [];
  const saved = await appendFunderMeetingReceipt(receipt, { query: async (sql, params) => {
    calls.push({ sql, params });
    return { rows: [{ meeting_id: params[1], inserted: true }] };
  } });
  assert.equal(saved.meeting_id, receipt.meeting_id);
  assert.match(calls[0].sql, /ON CONFLICT DO NOTHING/i);
  assert.doesNotMatch(calls[0].sql, /UPDATE/i);
  assert.equal(calls[0].params.some((value) => String(value).includes("Confirm thesis fit")), false);
});
