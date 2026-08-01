// Decide whether THIS deployment role runs the in-process scheduler loops.
// The local/cloud topology has explicit api, scheduler, and worker roles. Only scheduler may start
// loops, and it must carry the owner identity whose database lease was acquired by its supervisor.
// An unset role preserves the current standalone Railway behavior until the later cutover task.
"use strict";

const DEPLOYMENT_ROLES = new Set(["api", "scheduler", "worker"]);

function maybeStartLoops(env, starters) {
  const flag = String((env && env.LIFE_RUN_LOOPS) || "").trim().toLowerCase();
  const role = String((env && env.LM_DEPLOYMENT_ROLE) || "").trim().toLowerCase();
  const owner = String((env && env.LM_SCHEDULER_OWNER) || "").trim();

  if (flag === "false" || flag === "0" || flag === "off") {
    return {
      started: false,
      reason: `scheduler loops disabled by deployment flag LIFE_RUN_LOOPS=${flag}`,
    };
  }
  if (role && !DEPLOYMENT_ROLES.has(role)) {
    return { started: false, reason: "unsupported deployment role; scheduler loops disabled" };
  }
  if (role === "api" || role === "worker") {
    return { started: false, reason: `${role} deployment does not own scheduler loops` };
  }
  if (role === "scheduler" && !owner) {
    return { started: false, reason: "scheduler owner is required before loops start" };
  }

  starters.startScheduler();
  // The dial runs on its own timer (spec §3.1 method A). Starting it here rather than inside
  // startScheduler keeps the two loops independently startable and independently stoppable.
  starters.startWakeLoop();
  starters.startTravelLoop();
  starters.startAskLoop();
  starters.startOnboardLoop();
  starters.startDiscoveryLoop();
  return {
    started: true,
    owner: role === "scheduler" ? owner : "standalone-transition",
    reason: role === "scheduler"
      ? `scheduler deployment loops started for owner ${owner}`
      : "standalone transition loops started",
  };
}

module.exports = { maybeStartLoops };
