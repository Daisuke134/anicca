"use strict";

const { geminiJson } = require("./ask.js");
const { getCalendar } = require("./transport/index.js");
const { rememberPlace } = require("./places-memory.js");

const CONTEXT_FIELDS = [
  "home_area", "work_place", "frequent_venue_1", "frequent_venue_2", "typical_morning_start",
];

function contextEntries(value) {
  if (!value || typeof value !== "object") return [];
  const entries = CONTEXT_FIELDS.map((field) => [`context:${field}`, String(value[field] || "").trim()]);
  return entries.every(([, answer]) => answer) ? entries : [];
}

async function inferCalendarContext(events, geminiKey, inferJson = geminiJson) {
  if (!geminiKey || !Array.isArray(events) || events.length === 0) return {};
  const compact = events.slice(0, 250).map((event) => ({
    title: String(event.summary || "").slice(0, 200),
    location: String(event.location || "").slice(0, 300),
    start: event.start?.dateTime || event.start?.date || "",
    end: event.end?.dateTime || event.end?.date || "",
  }));
  return inferJson(
    "Infer a compact personal context graph from these calendar events from the last 60 days. " +
    "Return JSON with exactly five non-empty string fields: home_area, work_place, " +
    "frequent_venue_1, frequent_venue_2, typical_morning_start. Infer patterns from the event data; " +
    "do not use regex rules. If evidence is weak, use a conservative area/place/time description.\n" +
    JSON.stringify(compact),
    geminiKey,
  );
}

async function backfillCalendarContext(uid, opts = {}) {
  const log = opts.log || console.log;
  try {
    const calendar = opts.calendar || getCalendar({ apiKey: opts.composioKey, gmailAccountId: opts.gmailAccountId });
    if (!uid || !opts.geminiKey || !opts.supaUrl || !opts.supaKey || !calendar || (calendar.ready && !calendar.ready())) {
      log(`[context-graph] skipped uid=${String(uid || "").slice(0, 12)} unavailable dependency`);
      return 0;
    }
    const nowMs = opts.nowMs == null ? Date.now() : opts.nowMs;
    const events = await calendar.listEventsRaw(uid, {
      timeMin: new Date(nowMs - 60 * 86400 * 1000).toISOString(),
      timeMax: new Date(nowMs).toISOString(),
      maxResults: 250,
    });
    if (!events.length) {
      log(`[context-graph] skipped uid=${String(uid).slice(0, 12)} no recent events`);
      return 0;
    }
    const infer = opts.infer || ((rows) => inferCalendarContext(rows, opts.geminiKey));
    const entries = contextEntries(await infer(events));
    if (entries.length < 5) {
      log(`[context-graph] skipped uid=${String(uid).slice(0, 12)} incomplete inference`);
      return 0;
    }
    const remember = opts.remember || ((userId, phrase, address) =>
      rememberPlace(userId, phrase, address, opts.supaUrl, opts.supaKey));
    let written = 0;
    for (const [phrase, address] of entries) {
      if (await remember(uid, phrase, address)) written++;
    }
    log(`[context-graph] uid=${String(uid).slice(0, 12)} fields=${written}`);
    return written;
  } catch (error) {
    log(`[context-graph] skipped uid=${String(uid || "").slice(0, 12)} error=${error.message}`);
    return 0;
  }
}

module.exports = { CONTEXT_FIELDS, contextEntries, inferCalendarContext, backfillCalendarContext };
