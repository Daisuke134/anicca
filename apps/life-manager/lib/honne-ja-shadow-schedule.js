// honne-ja-shadow-schedule.js — the Honne JA shadow slot calendar.
//
// The legacy owner `ai.anicca.reelclaw-honne-ja` fires at StartCalendarInterval
// 12:30 and 21:30 local time (verified read-only via
// `plutil -p ~/Library/LaunchAgents/ai.anicca.reelclaw-honne-ja.plist`).
// The Life Manager shadow scheduler must encode the IDENTICAL cadence: the due
// slot for a wall-clock moment is the latest slot of the current local day that
// has already fired, expressed as the exact UTC instant of that local wall time
// so it satisfies the generation job's exact-instant slot contract.
"use strict";

const {
  zonedSlotInstant: zonedInstant,
  zonedWallClock,
} = require("./zoned-slot-instant.js");

const HONNE_JA_SLOTS = Object.freeze(["12:30", "21:30"]);
const LABEL = "honne JA schedule";

function wallClock(timeZone, date) {
  return zonedWallClock(timeZone, date, LABEL);
}

// Exact UTC instant of `slot` ("HH:MM") on the local calendar day `clock`
// ({year, month, day}) in `timeZone`. The inversion itself is shared with the
// financial report schedule (lib/zoned-slot-instant.js): two-pass wall-clock
// inversion plus a round-trip check so a DST gap fails loudly instead of
// silently drifting.
function zonedSlotInstant(clock, slot, timeZone) {
  return zonedInstant(clock, slot, timeZone, LABEL);
}

// The slot currently due at `nowMs` in `timeZone`: the latest HONNE_JA_SLOTS
// entry of the current local day whose wall time is <= now, as an exact UTC
// instant; null before the first slot of the local day. Every tick inside the
// same slot window resolves to the same instant, so the derived generation
// job_id is idempotent across scheduler polls.
function honneJaDueSlot(nowMs, timeZone = "Asia/Tokyo") {
  if (typeof nowMs !== "number" || !Number.isFinite(nowMs)) {
    throw new Error("honne JA schedule time is invalid");
  }
  const local = wallClock(timeZone, new Date(nowMs));
  const nowMinutes = local.hour * 60 + local.minute;
  let due = null;
  for (const slot of HONNE_JA_SLOTS) {
    const [hour, minute] = slot.split(":").map(Number);
    if (nowMinutes >= hour * 60 + minute) due = slot;
  }
  if (!due) return null;
  return zonedSlotInstant(
    { year: local.year, month: local.month, day: local.day },
    due,
    timeZone,
  );
}

module.exports = {
  HONNE_JA_SLOTS,
  honneJaDueSlot,
  zonedSlotInstant,
};
