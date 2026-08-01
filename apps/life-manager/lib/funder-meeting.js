"use strict";

const { createHash } = require("node:crypto");
const { evaluateEventCalendarAvailability } = require("./event-calendar-availability.js");

const DIGEST = /^[0-9a-f]{64}$/;
const HEX_ID = /^[0-9a-f]{16,32}$/i;
const SECTION_KEYS = Object.freeze([
  "objective", "company_snapshot", "funder_fit", "likely_questions",
  "questions_to_ask", "risks",
]);
const sha = (value) => createHash("sha256").update(String(value), "utf8").digest("hex");

function fail(message = "funder meeting invalid") { throw new Error(message); }
function finiteTime(value) {
  const ms = Date.parse(String(value || ""));
  if (!Number.isFinite(ms)) fail();
  return ms;
}

function validateBinding(input) {
  const outreach = input.outreachReceipt;
  const status = input.statusObservation;
  const message = input.message;
  if (!outreach || outreach.schema_version !== 1 || !String(outreach.tenant_id || "")
    || !/^funder-outreach:[0-9a-f]{64}$/.test(String(outreach.outreach_id || ""))
    || !String(outreach.candidate_id || "") || !String(outreach.funder_name || "")
    || !/^https:\/\/[^\s]+$/.test(String(outreach.source_url || ""))
    || !HEX_ID.test(String(outreach.provider_thread_id || ""))
    || !status || status.schema_version !== 1 || status.status !== "meeting_requested"
    || !/^funder-inbound-status:[0-9a-f]{64}$/.test(String(status.observation_id || ""))
    || status.tenant_id !== outreach.tenant_id || status.outreach_id !== outreach.outreach_id
    || status.candidate_id !== outreach.candidate_id
    || status.provider_thread_id !== outreach.provider_thread_id
    || !message || message.provider_message_id !== status.provider_message_id
    || message.provider_thread_id !== status.provider_thread_id
    || message.observed_at !== status.observed_at
    || !message.body || !message.sender || !message.subject
    || sha(message.sender) !== status.sender_sha256
    || sha(message.subject) !== status.subject_sha256
    || sha(message.body) !== status.body_sha256) fail();
  return { outreach, status, message };
}

function validateSchedule(judgment, message, nowMs) {
  if (!judgment || judgment.kind !== "agent_judgment"
    || String(judgment.time_zone || "") !== "Asia/Tokyo") fail();
  const rationale = String(judgment.rationale || "").trim();
  const title = String(judgment.title || "").trim();
  const location = String(judgment.location || "").trim();
  const quotes = judgment.evidence_quotes;
  const startMs = finiteTime(judgment.start_at);
  const endMs = finiteTime(judgment.end_at);
  const duration = (endMs - startMs) / 60_000;
  if (!rationale || rationale.length > 2000 || !title || title.length > 160
    || !location || location.length > 500 || startMs <= nowMs
    || duration < 15 || duration > 120 || !Number.isInteger(duration)
    || !Array.isArray(quotes) || quotes.length < 1 || quotes.length > 3) fail();
  const normalizedQuotes = quotes.map((value) => String(value || "").trim());
  if (normalizedQuotes.some((quote) => quote.length < 3 || quote.length > 500
    || !message.body.includes(quote))) fail();
  return {
    rationale, title, location, startMs, endMs, duration,
    evidenceHash: sha(normalizedQuotes.join("\n")),
    rationaleHash: sha(rationale),
  };
}

function allowedSource(ref, outreach) {
  const value = String(ref || "");
  return /^application-kit:\/\/(?:KIT\.md|answers\/q(?:0[1-9]|10)_[a-z0-9_]+\.(?:en|ja)\.md)$/.test(value)
    || value === outreach.source_url;
}

function validateBrief(judgment, outreach, kitSnapshot) {
  if (!kitSnapshot || kitSnapshot.schema_version !== 1
    || kitSnapshot.root_ref !== "application-kit://current"
    || !DIGEST.test(String(kitSnapshot.kit_digest || ""))
    || !judgment || judgment.kind !== "agent_judgment"
    || !String(judgment.rationale || "").trim()
    || !judgment.sections || typeof judgment.sections !== "object"
    || Array.isArray(judgment.sections)
    || JSON.stringify(Object.keys(judgment.sections)) !== JSON.stringify(SECTION_KEYS)) fail();
  const output = {};
  for (const key of SECTION_KEYS) {
    const section = judgment.sections[key];
    const text = String(section && section.text || "").trim();
    const refs = section && section.source_refs;
    if (!text || text.length > 4000 || !Array.isArray(refs) || refs.length < 1
      || refs.length > 5 || refs.some((ref) => !allowedSource(ref, outreach))) fail();
    output[key] = Object.freeze({ text, source_refs: Object.freeze([...refs]) });
  }
  const markdown = SECTION_KEYS.map((key) => (
    `## ${key.replaceAll("_", " ")}\n\n${output[key].text}\n\nSources: ${output[key].source_refs.join(", ")}`
  )).join("\n\n");
  return {
    sections: Object.freeze(output),
    markdown,
    briefHash: sha(markdown),
    briefRationaleHash: sha(String(judgment.rationale).trim()),
    kitDigest: kitSnapshot.kit_digest,
  };
}

function planFunderMeeting(input = {}) {
  const { outreach, status, message } = validateBinding(input);
  const nowMs = finiteTime(input.now);
  const schedule = validateSchedule(input.scheduleJudgment, message, nowMs);
  const brief = validateBrief(input.briefJudgment, outreach, input.kitSnapshot);
  let availability;
  try {
    availability = evaluateEventCalendarAvailability({
      window_start: new Date(schedule.startMs - 60_000).toISOString(),
      window_end: new Date(schedule.endMs + 60_000).toISOString(),
      freebusy: input.freebusy,
      candidates: [{
        event_ref: `funder-meeting://${status.observation_id}`,
        start_at: new Date(schedule.startMs).toISOString(),
        end_at: new Date(schedule.endMs).toISOString(),
        travel_before_minutes: 0,
        travel_after_minutes: 0,
      }],
    });
  } catch { fail(); }
  if (availability.eligible_event_refs.length !== 1) fail("funder meeting calendar conflict");
  const seed = [outreach.tenant_id, outreach.outreach_id, status.observation_id,
    new Date(schedule.startMs).toISOString(), new Date(schedule.endMs).toISOString(),
    schedule.evidenceHash, brief.briefHash, brief.kitDigest].join("\n");
  const meetingId = `funder-meeting:${sha(seed)}`;
  return Object.freeze({
    status: "ready",
    schema_version: 1,
    meeting_id: meetingId,
    tenant_id: outreach.tenant_id,
    outreach_id: outreach.outreach_id,
    candidate_id: outreach.candidate_id,
    status_observation_id: status.observation_id,
    provider_message_id: status.provider_message_id,
    provider_thread_id: status.provider_thread_id,
    schedule_evidence_sha256: schedule.evidenceHash,
    schedule_rationale_sha256: schedule.rationaleHash,
    brief_sha256: brief.briefHash,
    brief_rationale_sha256: brief.briefRationaleHash,
    kit_digest: brief.kitDigest,
    brief_sections: brief.sections,
    brief_markdown: brief.markdown,
    calendar: Object.freeze({
      title: schedule.title,
      start_at: new Date(schedule.startMs).toISOString(),
      end_at: new Date(schedule.endMs).toISOString(),
      duration_minutes: schedule.duration,
      time_zone: "Asia/Tokyo",
      location: schedule.location,
    }),
  });
}

async function deliverFunderMeeting(plan, dependencies = {}) {
  if (!plan || plan.status !== "ready" || !dependencies.calendar
    || typeof dependencies.calendar.createEvent !== "function") fail();
  const result = await dependencies.calendar.createEvent(plan.tenant_id, {
    calendar_id: "primary",
    summary: plan.calendar.title,
    start_datetime: plan.calendar.start_at,
    event_duration_hour: Math.floor(plan.calendar.duration_minutes / 60),
    event_duration_minutes: plan.calendar.duration_minutes % 60,
    location: plan.calendar.location,
    description: `Life Manager funder meeting\n${plan.outreach_id}\n${plan.status_observation_id}\nbrief-sha256:${plan.brief_sha256}`,
  });
  if (!result || result.successful !== true || !String(result.event_id || "").trim()
    || !/^https:\/\/calendar\.google\.com\//.test(String(result.html_link || ""))) {
    throw new Error("funder meeting Calendar receipt invalid");
  }
  const recordedAt = new Date(finiteTime((dependencies.observedAt || (() => new Date().toISOString()))())).toISOString();
  return Object.freeze({
    schema_version: 1,
    meeting_id: plan.meeting_id,
    tenant_id: plan.tenant_id,
    outreach_id: plan.outreach_id,
    candidate_id: plan.candidate_id,
    status_observation_id: plan.status_observation_id,
    provider_message_id: plan.provider_message_id,
    provider_thread_id: plan.provider_thread_id,
    scheduled_start_at: plan.calendar.start_at,
    scheduled_end_at: plan.calendar.end_at,
    provider_event_id: String(result.event_id),
    provider_event_url: String(result.html_link),
    schedule_evidence_sha256: plan.schedule_evidence_sha256,
    schedule_rationale_sha256: plan.schedule_rationale_sha256,
    brief_sha256: plan.brief_sha256,
    brief_rationale_sha256: plan.brief_rationale_sha256,
    kit_digest: plan.kit_digest,
    recorded_at: recordedAt,
  });
}

module.exports = { planFunderMeeting, deliverFunderMeeting };
