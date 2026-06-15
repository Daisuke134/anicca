// travel-logic.js — pure business logic for B-travel (spec27 WF-B B-travel).
//
// Anicca reads the user's calendar, calculates Google Maps Directions travel
// time, and inserts "[Travel] <title>" blocks before each event so the full
// schedule (including commute time) is visible at a glance.
//
// This module contains ONLY pure functions — no network I/O, no env reads.
// The Netlify handler (life-travel.js) wires in the GCal + Maps API calls.
// Pattern mirrors telemetry-schema.js / telemetry-verify.js.

const TRAVEL_PREFIX = "[Travel] ";
const TRAVEL_COLOR_ID = "7"; // Peacock — visually distinct from regular events

/**
 * Prefix a human-readable title with the "[Travel]" marker.
 * @param {string} title - Original event title.
 * @returns {string}
 */
function travelBlockTitle(title) {
  return `${TRAVEL_PREFIX}${(title || "").trim()}`;
}

/**
 * Returns true if an event summary is an auto-inserted travel block.
 * @param {string} summary
 * @returns {boolean}
 */
function isTravelBlock(summary) {
  return typeof summary === "string" && summary.startsWith(TRAVEL_PREFIX);
}

/**
 * Convert a Unix timestamp (seconds) to an ISO 8601 string.
 * @param {number} unixSec
 * @returns {string}
 */
function secondsToIso(unixSec) {
  return new Date(unixSec * 1000).toISOString();
}

/**
 * Build a GCal-compatible event object for a travel block.
 *
 * The block occupies the window [eventStart - durationSec, eventStart] so it
 * ends exactly when the target event begins — the canonical "travel time"
 * visual in Google Calendar.
 *
 * @param {object} opts
 * @param {string}  opts.calendarId  - GCal calendar ID (e.g. "primary")
 * @param {string}  opts.eventTitle  - Title of the destination event
 * @param {number}  opts.eventStart  - Unix seconds; the travel block ends here
 * @param {number}  opts.durationSec - Travel time in seconds (from Maps API)
 * @returns {object} GCal event resource (ready for calendar.events.insert)
 */
function buildTravelBlock({ calendarId, eventTitle, eventStart, durationSec }) {
  const endSec = eventStart;
  const startSec = eventStart - durationSec;

  return {
    calendarId,
    summary: travelBlockTitle(eventTitle),
    description: `Auto-inserted by Anicca B-travel (spec27). Travel time to: ${eventTitle}`,
    colorId: TRAVEL_COLOR_ID,
    start: { dateTime: secondsToIso(startSec) },
    end: { dateTime: secondsToIso(endSec) },
    // Prevent GCal from sending reminders for auto-inserted blocks
    reminders: { useDefault: false, overrides: [] },
    // Tag so the heartbeat can identify and clean/update stale blocks
    extendedProperties: {
      private: {
        anicca_travel_block: "true",
        destination_event_title: (eventTitle || "").trim(),
      },
    },
  };
}

/**
 * Given a list of GCal event objects, return those that need a travel block
 * inserted (i.e. they are timed events that do NOT already have a matching
 * "[Travel] <title>" block earlier in the list).
 *
 * Rules:
 *   - Skip all-day events (no `start.dateTime` field).
 *   - Skip events that are themselves travel blocks.
 *   - An event is "covered" if there exists another event with summary
 *     "[Travel] <eventTitle>" (exact match after trim).
 *
 * @param {Array<object>} events - GCal event resource list
 * @returns {Array<object>} subset that need a travel block
 */
function detectMissingTravelBlocks(events) {
  if (!Array.isArray(events)) return [];

  // Build a set of covered titles from existing travel blocks
  const coveredTitles = new Set(
    events
      .filter((e) => isTravelBlock(e.summary || ""))
      .map((e) => (e.summary || "").slice(TRAVEL_PREFIX.length).trim())
  );

  return events.filter((e) => {
    const summary = (e.summary || "").trim();
    // Skip all-day events — no departure time to anchor the block
    if (!e.start || !e.start.dateTime) return false;
    // Skip events that are themselves travel blocks
    if (isTravelBlock(summary)) return false;
    // Skip if already covered
    if (coveredTitles.has(summary)) return false;
    return true;
  });
}

module.exports = {
  travelBlockTitle,
  isTravelBlock,
  secondsToIso,
  buildTravelBlock,
  detectMissingTravelBlocks,
  TRAVEL_PREFIX,
  TRAVEL_COLOR_ID,
};
