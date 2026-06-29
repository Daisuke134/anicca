// lib/maybe-start-loops.js — decide whether THIS process runs the in-process scheduler loops.
//
// SINGLE-WRITER (B2 FIND-005): exactly ONE writer of the wake/travel/ask loops at a time.
//   - Railway Node app (today / standalone): LIFE_RUN_LOOPS unset or "true" → run the loops in-process.
//   - OpenClaw VOICE DAEMON (B3): LIFE_RUN_LOOPS="false" → DO NOT run the loops here; the OpenClaw
//     cron-COMMAND jobs (B2) own them. server.js still serves the always-on /ws Telnyx⇄Gemini-Live voice
//     bridge + the /test-call and /telegram HTTP endpoints — those are independent of the loops.
// At B4 cutover the switch is: enable the cron jobs AND set LIFE_RUN_LOOPS=false on the voice daemon, so
// the loops never have two writers.
"use strict";

// PURE: (env, starters) -> {started, reason}. Calls the 4 starters ONLY when loops are enabled.
// Default is ENABLED so existing Railway behaviour is unchanged unless LIFE_RUN_LOOPS is explicitly "false".
function maybeStartLoops(env, starters) {
  const flag = String((env && env.LIFE_RUN_LOOPS) || "").trim().toLowerCase();
  if (flag === "false" || flag === "0" || flag === "off") {
    return { started: false, reason: "LIFE_RUN_LOOPS=" + flag + " — scheduler loops owned by OpenClaw cron (single-writer); voice daemon only" };
  }
  starters.startScheduler();
  starters.startTravelLoop();
  starters.startAskLoop();
  starters.startOnboardLoop();
  return { started: true, reason: "in-process scheduler loops started (Railway/standalone mode)" };
}

module.exports = { maybeStartLoops };
