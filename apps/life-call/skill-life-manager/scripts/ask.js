// ask.js — ask/reply pass entrypoint for OpenClaw cron.
// Calls scheduler.askTickAll() once and exits. Runs every 20 min (configured in cron jobs.json).
// For each user: if an event has no resolvable location, asks via their connected channel
// (Telegram preferred, Gmail fallback); reads replies and fills in locations.
// The MODEL in lib/ask.js decides whether a location is findable, online, or genuinely unknown —
// no hardcoded regex judgment here. Requires COMPOSIO_API_KEY, GEMINI_API_KEY, SUPABASE_*.
"use strict";

const sched = require("../../scheduler.js");

async function run(deps = sched) {
  await deps.askTickAll();
}

if (require.main === module) {
  run()
    .then(() => process.exit(0))
    .catch((e) => { console.error(e); process.exit(1); });
}

module.exports = { run };
