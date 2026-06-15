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
 * Build the plain-text question email body for a given event.
 *
 * @param {object} event  GCal event resource
 * @returns {string}  email body
 */
function buildQuestionBody(event) {
  const title = (event.summary || "").trim() || "(no title)";
  const when = event.start?.dateTime
    ? new Date(event.start.dateTime).toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" })
    : "日時不明";
  return (
    `Anicca より確認です。\n\n` +
    `予定「${title}」(${when})の場所が未設定です。\n` +
    `場所・住所・目的地を返信してください。\n` +
    `Anicca が自動でカレンダーに反映します。\n\n` +
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
  return `${ASK_PREFIX}場所を教えて — ${title}`;
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
    location,
    extendedProperties: {
      private: newPrivate,
    },
  };
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
  detectMissingLocations,
  buildQuestionBody,
  buildQuestionSubject,
  parseLocationFromReply,
  buildLocationPatch,
  buildAskPendingPatch,
  ASK_PREFIX,
  AGENTMAIL_PENDING_PROP,
  AGENTMAIL_QUESTION_ID_PROP,
};
