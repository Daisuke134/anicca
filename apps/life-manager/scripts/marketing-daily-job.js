#!/usr/bin/env node
"use strict";

const { buildMarketingDailyJob } = require("../lib/marketing-daily-adapter.js");
const { enqueueJob } = require("../lib/runtime-job-store.js");

function parseArgs(argv) {
  if (argv[0] !== "enqueue") {
    throw new Error("usage: marketing-daily-job.js enqueue --tenant <id> --creative <id> --video-ref <ref> --caption-ref <ref> --approval-ref <ref>");
  }
  const values = {};
  for (let index = 1; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (!/^--[a-z-]+$/.test(String(flag || "")) || !value || String(value).startsWith("--")) {
      throw new Error("marketing enqueue arguments must be --name value pairs");
    }
    values[flag.slice(2)] = value;
  }
  for (const name of ["tenant", "creative", "platform", "video-ref", "caption-ref", "approval-ref"]) {
    if (!values[name]) throw new Error(`--${name} is required`);
  }
  return values;
}

async function enqueueMarketingDaily(argv, env = process.env, deps = {}) {
  const args = parseArgs(argv);
  const job = buildMarketingDailyJob({
    tenantId: args.tenant,
    creativeId: args.creative,
    platform: args.platform,
    videoRef: args["video-ref"],
    captionRef: args["caption-ref"],
    approvalRef: args["approval-ref"],
    instagramProfileRef: "profile://instagram/life-manager",
    postizTokenRef: "secret://postiz/api-key",
    tiktokIntegrationRef: "integration://postiz/tiktok/life-manager",
  });
  const enqueue = deps.enqueueJob || enqueueJob;
  const result = await enqueue({
    jobId: job.job_id,
    tenantId: job.tenant_id,
    loopId: job.loop_id,
    capability: job.capability,
    effectClass: job.effect_class,
    effectKey: job.effect_key,
    inputRefs: job.input_refs,
    maxAttempts: job.max_attempts,
  }, deps.storeOptions || {});
  (deps.stdout || process.stdout).write(`${JSON.stringify({
    created: result.created,
    job_id: result.job.job_id,
    tenant_id: result.job.tenant_id,
    capability: result.job.capability,
    effect_key: result.job.effect_key,
  })}\n`);
  return result;
}

if (require.main === module) {
  enqueueMarketingDaily(process.argv.slice(2)).catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = { enqueueMarketingDaily, parseArgs };
