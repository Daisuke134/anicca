// ask-logic.js — pure business logic for B-ask (spec27 WF-B B-ask).
//
// When Anicca finds a GCal event with no location (or unknown travel origin),
// it emails Dais a question.  When Dais replies, the reply text is parsed and
// the GCal event's `location` field is patched.
//
// This module contains ONLY pure functions — no network I/O, no env reads.
// The Netlify handler (life-ask.js) wires in the GCal + AgentMail API calls.
// Pattern mirrors travel-logic.js.

"use strict";

// ── Constants ──────────────────────────────────────────────────────────────────

const ASK_PREFIX = "[Ask] ";
const AGENTMAIL_PENDING_PROP = "anicca_ask_pending";
const AGENTMAIL_QUESTION_ID_PROP = "anicca_ask_question_id";
// Exported so handleReply (life-ask.js) can guard against writing a
// duration-only reply as a bogus location. (Review point 3 — no ReferenceError.)
const DURATION_RE = /(?:所要|duration|時間)[：:\s]*([0-9０-９]{1,3})\s*(?:分|min)/i;

// ── Pure helpers ───────────────────────────────────────────────────────────────

/**
 * Returns true if the event needs a location question to be sent.
 * Rules:
 *   - Must be a timed event (has start.dateTime)
 *   - Must have no location field (or empty string)
 *   - Must not already have a pending ask (extendedProperties.private.anicca_ask_pending)
 *   - Must not be a travel block or another ask marker event
 *
 * @param {object} event  GCal event resource
 * @returns {boolean}
 */
function needsLocationAsk(event) {
  if (!event || !event.start || !event.start.dateTime) return false;
  const summary = (event.summary || "").trim();
  if (summary.startsWith("[Travel]") || summary.startsWith(ASK_PREFIX)) return false;
  if (event.location && event.location.trim() !== "") return false;
  const pending = event.extendedProperties?.private?.[AGENTMAIL_PENDING_PROP];
  if (pending === "true") return false;
  return true;
}

/**
 * Returns true if the event needs a duration question to be sent.
 * Duration unknown: no end.dateTime OR end<=start. start.dateTime required.
 *
 * @param {object} event  GCal event resource
 * @returns {boolean}
 */
function needsDurationAsk(event) {
  if (!event || !event.start || !event.start.dateTime) return false;
  const summary = (event.summary || "").trim();
  if (summary.startsWith("[Travel]") || summary.startsWith(ASK_PREFIX)) return false;
  if (event.extendedProperties?.private?.[AGENTMAIL_PENDING_PROP] === "true") return false;
  const endDt = event.end?.dateTime;
  if (!endDt) return true;
  return new Date(endDt).getTime() <= new Date(event.start.dateTime).getTime();
}

/**
 * Detect which kinds of info an event is missing.
 *
 * @param {object} event  GCal event resource
 * @returns {{ location: boolean, duration: boolean }}
 */
function detectAskKind(event) {
  return { location: needsLocationAsk(event), duration: needsDurationAsk(event) };
}

/**
 * Filter a list of GCal events to those that need a location question.
 *
 * @param {Array<object>} events  GCal event resource list
 * @returns {Array<object>}
 */
function detectMissingLocations(events) {
  if (!Array.isArray(events)) return [];
  return events.filter(needsLocationAsk);
}

/**
 * Filter events to those needing EITHER location OR duration.
 * Returns items: { event, kind }.
 *
 * @param {Array<object>} events  GCal event resource list
 * @returns {Array<{event: object, kind: {location: boolean, duration: boolean}}>}
 */
function detectMissingInfo(events) {
  if (!Array.isArray(events)) return [];
  return events
    .map((event) => ({ event, kind: detectAskKind(event) }))
    .filter(({ kind }) => kind.location || kind.duration);
}

/**
 * Build the plain-text question email body for a given event.
 *
 * @param {object} event  GCal event resource
 * @returns {string}  email body
 */
function buildQuestionBody(event) {
  const title = (event.summary || "").trim() || "(no title)";
  // Show the time in the EVENT's own timezone (Google provides start.timeZone) — never a hardcoded
  // zone — so it reads correctly for a user anywhere in the world.
  const when = event.start?.dateTime
    ? new Date(event.start.dateTime).toLocaleString(undefined, event.start.timeZone ? { timeZone: event.start.timeZone } : undefined)
    : "日時不明";
  const kind = detectAskKind(event);
  const wants = [];
  if (kind.location) wants.push(`・場所(住所・目的地)`);
  if (kind.duration) wants.push(`・所要時間(例: 所要 60分)`);
  const ask = wants.length ? wants.join("\n") : `・場所(住所・目的地)`;
  return (
    `Anicca より確認です。\n\n` +
    `予定「${title}」(${when})の以下が未設定です。\n${ask}\n` +
    `そのまま返信してください。Anicca が自動でカレンダーに反映します。\n\n` +
    `---\nEvent ID: ${event.id || "unknown"}`
  );
}

/**
 * Build the email subject for a location question.
 *
 * @param {object} event  GCal event resource
 * @returns {string}
 */
function buildQuestionSubject(event) {
  const title = (event.summary || "").trim() || "(no title)";
  const k = detectAskKind(event);
  const what = k.location && k.duration ? "場所と所要時間" : k.duration ? "所要時間" : "場所";
  return `${ASK_PREFIX}${what}を教えて — ${title}`;
}

/**
 * Parse a reply email body to extract the location string.
 * Strategy: return the first non-empty, non-metadata line.
 * The reply could be:
 *   - "新宿駅南口"                     → plain address
 *   - "場所: 渋谷ヒカリエ 8F"          → "場所:" prefix
 *   - "→ 東京ビッグサイト"             → arrow prefix
 *   - Reply quoting original + content
 *
 * @param {string} body  raw reply email body
 * @returns {string|null}  extracted location or null if not found
 */
function parseLocationFromReply(body) {
  if (!body || typeof body !== "string") return null;

  const lines = body
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
    // Exclude lines that are part of the original quoted message
    .filter((l) => !l.startsWith(">"))
    // Exclude lines that are the separator
    .filter((l) => l !== "---")
    // Exclude lines that contain the Event ID marker
    .filter((l) => !l.startsWith("Event ID:"));

  if (lines.length === 0) return null;

  let location = lines[0];

  // Strip common prefixes like "場所:", "場所：", "場所: ", "→", "address:"
  location = location.replace(/^(場所[：:]|address:|→|location:)\s*/i, "").trim();

  return location.length > 0 ? location : null;
}

/**
 * Parse minutes from "所要 60分" / "duration: 90 min" / a bare "N分" line.
 *
 * @param {string} body  raw reply email body
 * @returns {number|null}  minutes (1..1440) or null if not found
 */
function parseDurationFromReply(body) {
  if (!body || typeof body !== "string") return null;
  const norm = body.replace(/[０-９]/g, (d) => "0123456789"["０１２３４５６７８９".indexOf(d)]);
  const m =
    norm.match(/(?:所要|duration|時間)[：:\s]*([0-9]{1,3})\s*(?:分|min)/i) ||
    norm.match(/(?:^|\n)\s*([0-9]{1,3})\s*(?:分|min|m)\s*(?:$|\n)/i);
  if (!m) return null;
  const mins = parseInt(m[1], 10);
  return Number.isFinite(mins) && mins > 0 && mins <= 1440 ? mins : null;
}

/**
 * Build the GCal patch body to update the location field of an event.
 *
 * @param {string} location  The resolved location string
 * @param {object} existingEvent  The original GCal event (used to clear pending flag)
 * @returns {object}  GCal event resource patch (suitable for PATCH request)
 */
function buildLocationPatch(location, existingEvent) {
  const priorPrivate = existingEvent?.extendedProperties?.private || {};
  // Build new private extended properties: remove pending flag, keep others
  const newPrivate = Object.fromEntries(
    Object.entries(priorPrivate).filter(
      ([k]) => k !== AGENTMAIL_PENDING_PROP && k !== AGENTMAIL_QUESTION_ID_PROP
    )
  );

  return {
    ...(location ? { location } : {}),
    extendedProperties: {
      private: newPrivate,
    },
  };
}

/**
 * Build a GCal patch that sets end.dateTime = start + N min (when a duration is
 * supplied) and optionally the location, and clears the pending flag.
 *
 * @param {{ location?: string, durationMinutes?: number }} resolved
 * @param {object} existingEvent  The original GCal event
 * @returns {object}  GCal event resource patch
 */
function buildResolvePatch({ location, durationMinutes }, existingEvent) {
  const patch = buildLocationPatch(location || "", existingEvent);
  if (durationMinutes && existingEvent?.start?.dateTime) {
    const startMs = new Date(existingEvent.start.dateTime).getTime();
    patch.end = {
      dateTime: new Date(startMs + durationMinutes * 60000).toISOString(),
      ...(existingEvent.start.timeZone ? { timeZone: existingEvent.start.timeZone } : {}),
    };
  }
  return patch;
}

/**
 * Build the extendedProperties patch to mark an event as "ask pending".
 * Called after sending the question email to Dais.
 *
 * @param {string} questionId  AgentMail message ID of the sent question
 * @param {object} existingEvent  The original GCal event
 * @returns {object}  GCal event resource patch
 */
function buildAskPendingPatch(questionId, existingEvent) {
  const priorPrivate = existingEvent?.extendedProperties?.private || {};

  return {
    extendedProperties: {
      private: {
        ...priorPrivate,
        [AGENTMAIL_PENDING_PROP]: "true",
        [AGENTMAIL_QUESTION_ID_PROP]: questionId || "",
      },
    },
  };
}

// ── Exports ────────────────────────────────────────────────────────────────────

module.exports = {
  needsLocationAsk,
  needsDurationAsk,
  detectAskKind,
  detectMissingLocations,
  detectMissingInfo,
  buildQuestionBody,
  buildQuestionSubject,
  parseLocationFromReply,
  parseDurationFromReply,
  buildLocationPatch,
  buildResolvePatch,
  buildAskPendingPatch,
  ASK_PREFIX,
  DURATION_RE,
  AGENTMAIL_PENDING_PROP,
  AGENTMAIL_QUESTION_ID_PROP,
};
