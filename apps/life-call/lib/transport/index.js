// lib/transport/index.js — #74 convergence: pick the calendar/mail transport by LIFE_TRANSPORT env.
// composio (default) = cloud managed-OAuth. gog (slice 5) = local BYOK CLI. The life-logic modules call
// getCalendar() and never touch a provider directly, so one JS codebase deploys cloud OR local.
"use strict";

const { makeComposioCalendar } = require("./calendar-composio.js");
const { makeUnipileMail } = require("./mail-unipile.js");
const { makeGogCalendar } = require("./calendar-gog.js");
const { makeGogMail } = require("./mail-gog.js");

// Resolve the transport kind, failing LOUD on an unrecognized LIFE_TRANSPORT rather than silently
// defaulting (a typo'd env must not quietly route a local BYOK box at the cloud provider).
function resolveKind(opts) {
  const kind = (process.env.LIFE_TRANSPORT || opts.kind || "composio").toLowerCase();
  if (kind !== "composio" && kind !== "gog") {
    throw new Error(`Unknown LIFE_TRANSPORT="${kind}" (expected "composio" or "gog")`);
  }
  return kind;
}

function getCalendar(opts = {}) {
  return resolveKind(opts) === "gog" ? makeGogCalendar(opts) : makeComposioCalendar(opts);
}

function getMail(opts = {}) {
  return resolveKind(opts) === "gog" ? makeGogMail(opts) : makeUnipileMail(opts);
}

module.exports = { getCalendar, getMail };
