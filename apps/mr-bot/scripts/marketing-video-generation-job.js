#!/usr/bin/env node
"use strict";

const {
  buildMarketingVideoGenerationJob,
} = require("../lib/marketing-video-generation-adapter.js");
const {
  enqueueJob,
  closeRuntimeJobStore,
} = require("../lib/runtime-job-store.js");

const REQUIRED = [
  "tenant",
  "product",
  "format",
  "locale",
  "slot",
  "pack-ref",
];
const ALLOWED = new Set([...REQUIRED, "media-ref"]);

function parseArgs(argv) {
  if (argv[0] !== "enqueue") {
    throw new Error(
      "usage: marketing-video-generation-job.js enqueue --tenant <id> --product <id> --format <id> --locale <locale> --slot <ISO instant> --pack-ref <ref> --media-ref <ref> [--media-ref <ref>]",
    );
  }
  const values = { "media-ref": [] };
  for (let index = 1; index < argv.length; index += 2) {
    const flag = String(argv[index] || "");
    const value = argv[index + 1];
    const name = flag.slice(2);
    if (
      !/^--[a-z-]+$/.test(flag)
      || !value
      || String(value).startsWith("--")
      || !ALLOWED.has(name)
    ) {
      throw new Error("marketing video enqueue arguments are invalid");
    }
    if (name === "media-ref") {
      values[name].push(value);
    } else {
      if (Object.hasOwn(values, name)) {
        throw new Error("marketing video enqueue arguments must be unique");
      }
      values[name] = value;
    }
  }
  for (const name of REQUIRED) {
    if (!values[name]) throw new Error(`--${name} is required`);
  }
  if (values["media-ref"].length < 1) {
    throw new Error("--media-ref is required");
  }
  return values;
}

async function enqueueMarketingVideoGeneration(argv, deps = {}) {
  const args = parseArgs(argv);
  const job = buildMarketingVideoGenerationJob({
    tenantId: args.tenant,
    productId: args.product,
    formatId: args.format,
    locale: args.locale,
    slot: args.slot,
    packRef: args["pack-ref"],
    mediaRefs: args["media-ref"],
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
  enqueueMarketingVideoGeneration(process.argv.slice(2))
    .catch((error) => {
      process.stderr.write(`${error.message}\n`);
      process.exitCode = 1;
    })
    .finally(() => closeRuntimeJobStore());
}

module.exports = {
  enqueueMarketingVideoGeneration,
  parseArgs,
};
