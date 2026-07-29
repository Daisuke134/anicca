#!/usr/bin/env node
"use strict";

const {
  buildMarketingDailyGenerationJob,
} = require("../lib/marketing-daily-generation-adapter.js");
const { enqueueJob } = require("../lib/runtime-job-store.js");

const REQUIRED = [
  "tenant",
  "date",
  "bank-ref",
  "call-audio-ref",
  "stock-ref",
  "telegram-proof-ref",
  "whisper-ass-ref",
];

function parseArgs(argv) {
  if (argv[0] !== "enqueue") {
    throw new Error("usage: marketing-daily-generation-job.js enqueue --tenant <id> --date <YYYY-MM-DD> --bank-ref <ref> --call-audio-ref <ref> --stock-ref <ref> --telegram-proof-ref <ref> --whisper-ass-ref <ref>");
  }
  const values = {};
  for (let index = 1; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (!/^--[a-z-]+$/.test(String(flag || "")) || !value || String(value).startsWith("--")) {
      throw new Error("marketing generation enqueue arguments must be --name value pairs");
    }
    values[flag.slice(2)] = value;
  }
  for (const name of REQUIRED) {
    if (!values[name]) throw new Error(`--${name} is required`);
  }
  return values;
}

async function enqueueMarketingDailyGeneration(argv, deps = {}) {
  const args = parseArgs(argv);
  const job = buildMarketingDailyGenerationJob({
    tenantId: args.tenant,
    date: args.date,
    bankRef: args["bank-ref"],
    callAudioRef: args["call-audio-ref"],
    stockRef: args["stock-ref"],
    telegramProofRef: args["telegram-proof-ref"],
    whisperAssRef: args["whisper-ass-ref"],
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
  })}\n`);
  return result;
}

if (require.main === module) {
  enqueueMarketingDailyGeneration(process.argv.slice(2)).catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = { enqueueMarketingDailyGeneration, parseArgs };
