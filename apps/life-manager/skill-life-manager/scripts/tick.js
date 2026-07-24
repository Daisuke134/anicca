// tick.js — wake-call pass entrypoint for OpenClaw cron.
// Calls scheduler.tick() once and exits. The OpenClaw gateway supplies all env vars
// (GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, PUBLIC_WSS, etc.).
// The setInterval loop in startScheduler() is NOT used here — the cron interval owns the cadence.
"use strict";

const sched = require("../../scheduler.js");

async function run(deps = sched) {
  await deps.tick();
}

if (require.main === module) {
  run()
    .then(() => process.exit(0))
    .catch((e) => { console.error(e); process.exit(1); });
}

module.exports = { run };
