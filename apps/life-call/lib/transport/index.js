// lib/transport/index.js — #74 convergence: pick the calendar/mail transport by LIFE_TRANSPORT env.
// composio (default) = cloud managed-OAuth. gog (slice 5) = local BYOK CLI. The life-logic modules call
// getCalendar() and never touch a provider directly, so one JS codebase deploys cloud OR local.
"use strict";

const { makeComposioCalendar } = require("./calendar-composio.js");
const { makeUnipileMail } = require("./mail-unipile.js");

function getCalendar(opts = {}) {
  const kind = (process.env.LIFE_TRANSPORT || opts.kind || "composio").toLowerCase();
  switch (kind) {
    // case "gog": return makeGogCalendar(opts); // slice 4
    case "composio":
    default:
      return makeComposioCalendar(opts);
  }
}

function getMail(opts = {}) {
  const kind = (process.env.LIFE_TRANSPORT || opts.kind || "composio").toLowerCase();
  switch (kind) {
    // case "gog": return makeGogMail(opts); // slice 4 (local gog Gmail)
    case "composio":
    default:
      return makeUnipileMail(opts); // cloud mail provider is Unipile
  }
}

module.exports = { getCalendar, getMail };
