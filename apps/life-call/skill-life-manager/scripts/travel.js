// travel.js — travel-fill pass entrypoint for OpenClaw cron.
// Calls scheduler.travelTick() once and exits. Runs every 30 min (configured in cron jobs.json).
// Inserts [Travel] calendar blocks for events missing departure time so the wake pass always has
// correct leave times. Requires COMPOSIO_API_KEY, LIFE_MAPS_KEY (or GOOGLE_API_KEY), GEMINI_API_KEY.
"use strict";

const sched = require("../../scheduler.js");

async function run(deps = sched) {
  await deps.travelTick();
}

if (require.main === module) {
  run()
    .then(() => process.exit(0))
    .catch((e) => { console.error(e); process.exit(1); });
}

module.exports = { run };
