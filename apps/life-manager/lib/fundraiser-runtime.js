"use strict";

const { createHash } = require("node:crypto");
const { buildRuntimeJob, enqueueJob } = require("./runtime-job-store.js");

const CAPABILITY = "fundraiser.acquire";
const LOOP_ID = "life-manager.fundraiser";
const SLOT_MS = 30 * 60 * 1000;

function slotStart(nowMs) {
  const value = Number(nowMs);
  if (!Number.isFinite(value)) throw new Error("fundraiser instant invalid");
  return Math.floor(value / SLOT_MS) * SLOT_MS;
}

function buildFundraiserJob(input = {}) {
  const tenantId = String(input.tenantId || "").trim();
  if (!tenantId) throw new Error("fundraiser tenant invalid");
  const slotMs = slotStart(input.nowMs);
  const slotIso = new Date(slotMs).toISOString();
  const digest = createHash("sha256").update(`${tenantId}\n${slotIso}`).digest("hex");
  return buildRuntimeJob({
    jobId: `fundraiser:${digest}`,
    tenantId,
    loopId: LOOP_ID,
    capability: CAPABILITY,
    effectClass: "none",
    effectKey: null,
    inputRefs: {
      slot_ref: `fundraiser-slot://${encodeURIComponent(tenantId)}/${encodeURIComponent(slotIso)}`,
      startup_context_ref: "repo://.agents/startup-context.json",
      prompt_ref: "repo://skills/fundraiser-agent/prompts/daily.md",
      founder_profile_ref: "private://life-manager/profile",
      browser_profile_ref: "browser-profile://cloakbrowser/daily-driver",
      x_profile_ref: "browser-profile://cloakbrowser/x-anicca",
    },
    maxAttempts: 5,
  });
}

async function fundraiserUserOnce(user, nowMs = Date.now(), deps = {}) {
  const job = buildFundraiserJob({ tenantId: user && user.uid, nowMs });
  const enqueue = deps.enqueueJob || enqueueJob;
  const result = await enqueue(job, deps.storeOptions || {});
  return {
    status: result.created ? "queued" : "already_queued",
    jobId: result.job.job_id,
    slotRef: job.input_refs.slot_ref,
  };
}

module.exports = { CAPABILITY, LOOP_ID, SLOT_MS, slotStart, buildFundraiserJob, fundraiserUserOnce };

