// notify-logic.js — pure business logic for B-notify (spec27 WF-B B-notify).
//
// B-notify flow (spec27 §2 + spec26 §B-notify detail):
//   1. heartbeat detects late-risk: travel block start < now
//   2. Anicca emails Dais with the draft + "reply OK to send"
//   3. AgentMail Drafts holds the pending message
//   4. Dais replies "OK" → webhook fires → Anicca sends to attendees
//
// Approval channel: email only (Telegram optional for opt-in location users).
// Send channel: email (AgentMail / Gmail).
//
// This module contains ONLY pure functions — no network I/O, no env reads.
// The Netlify handler (life-notify.js) wires in GCal / AgentMail calls.
// Pattern mirrors travel-logic.js (proven template for WF-B skills).

const TRAVEL_PREFIX = "[Travel] ";

/**
 * Returns true if an event summary is an auto-inserted travel block.
 * @param {string} summary
 * @returns {boolean}
 */
function isTravelBlock(summary) {
  return typeof summary === "string" && summary.startsWith(TRAVEL_PREFIX);
}

/**
 * Returns true when a travel block has already started (owner is running late).
 *
 * @param {object} opts
 * @param {number} opts.travelStartMs - Travel block start time in milliseconds
 * @param {number} opts.nowMs         - Current time in milliseconds
 * @returns {boolean}
 */
function isLateRisk({ travelStartMs, nowMs }) {
  return nowMs > travelStartMs;
}

/**
 * Given a list of GCal event objects and current time, return events that
 * have a matching [Travel] block that has already started (late-risk state).
 *
 * Rules:
 *   - Only timed events (with start.dateTime) are considered.
 *   - An event is "at risk" when its matching [Travel] block started before nowMs.
 *   - Events with no [Travel] block are skipped (B-travel should insert one first).
 *
 * @param {Array<object>} events - GCal event resource list (today's events)
 * @param {number} nowMs         - Current time in ms (injected for testability)
 * @returns {Array<{event: object, travelEvent: object, isLate: boolean}>}
 */
function detectLateRiskEvents(events, nowMs) {
  if (!Array.isArray(events)) return [];

  // Build a map of travel blocks keyed by destination title
  const travelBlocks = new Map();
  for (const e of events) {
    if (!e.start || !e.start.dateTime) continue;
    if (!isTravelBlock(e.summary || "")) continue;
    const destinationTitle = (e.summary || "").slice(TRAVEL_PREFIX.length).trim();
    travelBlocks.set(destinationTitle, e);
  }

  const risks = [];

  for (const e of events) {
    // Skip all-day events
    if (!e.start || !e.start.dateTime) continue;
    // Skip travel blocks themselves
    if (isTravelBlock(e.summary || "")) continue;

    const title = (e.summary || "").trim();
    const travelBlock = travelBlocks.get(title);
    if (!travelBlock) continue; // no travel block → not our concern here

    const travelStartMs = new Date(travelBlock.start.dateTime).getTime();
    const late = isLateRisk({ travelStartMs, nowMs });

    if (late) {
      risks.push({ event: e, travelEvent: travelBlock, isLate: true });
    }
  }

  return risks;
}

/**
 * Estimate minutes late based on how far past the travel block start we are.
 * Clamps to a minimum of 5 and rounds to the nearest 5 minutes.
 *
 * @param {object} opts
 * @param {number} opts.travelStartMs - Travel block start time in ms
 * @param {number} opts.nowMs         - Current time in ms
 * @returns {number} Estimated minutes late (≥5, rounded to nearest 5)
 */
function estimateMinutesLate({ travelStartMs, nowMs }) {
  const diffMin = Math.round((nowMs - travelStartMs) / 60_000);
  const clamped = Math.max(5, diffMin);
  return Math.round(clamped / 5) * 5;
}

/**
 * Build the short draft message to send to event attendees.
 *
 * @param {object} opts
 * @param {string} opts.eventSummary - Title of the event being attended
 * @param {number} opts.minutesLate  - Estimated minutes late
 * @returns {string}
 */
function buildAttendeeDraft({ eventSummary, minutesLate }) {
  return (
    `I'll be approximately ${minutesLate} minutes late to "${eventSummary}". ` +
    `Apologies for the short notice — I'm on my way.`
  );
}

/**
 * Build the approval email to send to the calendar owner (Dais).
 * Dais replies "OK" → AgentMail webhook → Anicca sends draft to attendees.
 *
 * @param {object} opts
 * @param {string}          opts.ownerEmail    - Calendar owner's email address
 * @param {string}          opts.eventSummary  - Title of the event
 * @param {Array<{email}>}  opts.attendees     - GCal attendees (may be empty)
 * @param {string}          opts.draftBody     - Message to send to attendees
 * @param {string}          opts.draftId       - AgentMail draft ID (for traceability)
 * @returns {{ to: string, subject: string, body: string }}
 */
function buildApprovalEmail({ ownerEmail, eventSummary, attendees, draftBody, draftId }) {
  const recipientList =
    attendees && attendees.length > 0
      ? attendees.map((a) => a.email).join(", ")
      : "(no attendees found — reply OK to dismiss)";

  const subject = `[Anicca] Late alert for "${eventSummary}" — reply OK to notify`;

  const body = [
    `You appear to be running late for: "${eventSummary}"`,
    ``,
    `Anicca will send the following to: ${recipientList}`,
    ``,
    `───────────────────────────────`,
    draftBody,
    `───────────────────────────────`,
    ``,
    `Reply "OK" to this email to approve and send.`,
    `Reply anything else (or ignore) to cancel.`,
    ``,
    `Draft ID: ${draftId}`,
    `Powered by Anicca B-notify (spec27)`,
  ].join("\n");

  return { to: ownerEmail, subject, body };
}

/**
 * Parse an inbound email reply body to determine if the owner approved.
 *
 * Recognised approval tokens (case-insensitive, leading/trailing whitespace stripped):
 *   EN: "ok", starts with "ok"
 *   JA: "はい"
 *
 * @param {string} replyBody - Raw text body of the reply email
 * @returns {boolean}
 */
function extractApproval(replyBody) {
  if (typeof replyBody !== "string") return false;
  const trimmed = replyBody.trim();
  const lower = trimmed.toLowerCase();
  if (lower === "ok" || lower.startsWith("ok!") || lower.startsWith("ok,") || lower.startsWith("ok ")) {
    return true;
  }
  // Handle bare "ok" without punctuation (the most common case)
  if (lower === "ok") return true;
  if (trimmed === "はい" || trimmed.startsWith("はい")) return true;
  return false;
}

module.exports = {
  isTravelBlock,
  isLateRisk,
  detectLateRiskEvents,
  estimateMinutesLate,
  buildAttendeeDraft,
  buildApprovalEmail,
  extractApproval,
  TRAVEL_PREFIX,
};
