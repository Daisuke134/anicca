"use strict";

const { buildGraph, effectiveEntries } = require("./intent-graph.js");
const { buildRuntimeJob } = require("./runtime-job-store.js");

const LOOP_ID = "mr-bot.manager";
const CAPABILITY = "general-agent.work";

function buildGoalWorkItem(goal, nowMs) {
  if (!Number.isFinite(nowMs)) throw new Error("WorkItem observation time is required");
  const active = effectiveEntries(buildGraph([goal]), nowMs);
  if (active.length !== 1 || active[0].kind !== "explicit_goal") {
    throw new Error("WorkItem requires one active explicit goal");
  }
  const entry = active[0];
  return buildRuntimeJob({
    jobId: `goal:${entry.id}`,
    tenantId: entry.uid,
    loopId: LOOP_ID,
    capability: CAPABILITY,
    effectClass: "none",
    effectKey: null,
    inputRefs: {
      goal_ref: `intent-entry://${encodeURIComponent(entry.uid)}/${encodeURIComponent(entry.id)}`,
    },
    maxAttempts: 1,
  });
}

module.exports = { LOOP_ID, CAPABILITY, buildGoalWorkItem };
