// lib/transport/index.js — #74 convergence: pick the calendar/mail transport by LIFE_TRANSPORT env.
// composio (default) = cloud managed-OAuth. gog (slice 5) = local BYOK CLI. The life-logic modules call
// getCalendar() and never touch a provider directly, so one JS codebase deploys cloud OR local.
"use strict";

const { makeComposioCalendar } = require("./calendar-composio.js");

function getCalendar(opts = {}) {
  const kind = (process.env.LIFE_TRANSPORT || opts.kind || "composio").toLowerCase();
  switch (kind) {
    // case "gog": return makeGogCalendar(opts); // slice 5
    case "composio":
    default:
      return makeComposioCalendar(opts);
  }
}

module.exports = { getCalendar };
