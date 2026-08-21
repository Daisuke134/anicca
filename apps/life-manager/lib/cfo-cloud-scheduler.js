"use strict";

const { buildRuntimeJob, enqueueJobAt, claimJobs, completeJob, failJob } = require("./runtime-job-store.js");

const ERROR = "cfo_cloud_scheduler_invalid:run";
const ID = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
function fail() { throw new Error(ERROR); }
function iso(value) { return typeof value === "string" && value.length <= 64 && Number.isFinite(Date.parse(value)); }
function validIdentity(value) { return typeof value === "string" && ID.test(value); }

function cfoJobInput({ tenantId, reportingDate, runId, maxAttempts = 3 } = {}) {
  if (!validIdentity(tenantId) || !DATE.test(reportingDate) || !validIdentity(runId)) fail();
  return {
    jobId: `cfo:${tenantId}:${reportingDate}:${runId}`,
    tenantId,
    loopId: "cfo-hourly",
    capability: "cfo.read",
    effectClass: "none",
    effectKey: null,
    inputRefs: { run_ref: [`cfo-run://${tenantId}/${reportingDate}/${runId}`] },
    maxAttempts,
  };
}
function buildCfoCloudJob(input = {}) {
  const job = buildRuntimeJob(cfoJobInput(input));
  const availableAt = input.availableAt;
  return availableAt == null ? job : { ...job, available_at: new Date(availableAt).toISOString() };
}

function buildCfoRunReceipt({ tenantId, reportingDate, runId, status, observedAt, durationMs, messageId = null } = {}) {
  if (!validIdentity(tenantId) || !DATE.test(reportingDate) || !validIdentity(runId)
    || !["sent", "quiet", "failed", "recovered"].includes(status) || !iso(observedAt)
    || !Number.isSafeInteger(durationMs) || durationMs < 0 || (messageId !== null && (!Number.isSafeInteger(messageId) || messageId < 1))) fail();
  return Object.freeze({ schemaVersion: 1, tenantId, reportingDate, runId, status, observedAt, durationMs, messageId });
}

async function enqueueCfoRun(input, opts = {}) { return enqueueJobAt(cfoJobInput(input), input.availableAt || new Date().toISOString(), opts); }
async function claimCfoRun({ workerId, tenantId, limit = 1, leaseSeconds = 180 } = {}, opts = {}) {
  if (!validIdentity(workerId) || !validIdentity(tenantId)) fail();
  return claimJobs({ workerId, tenantId, capabilities: ["cfo.read"], limit, leaseSeconds }, opts);
}
async function completeCfoRun(input, opts = {}) { return completeJob({ ...input, receipt: buildCfoRunReceipt(input) }, opts); }
async function failCfoRun(input, opts = {}) { if (!validIdentity(input && input.errorCode)) fail(); return failJob(input, opts); }

module.exports = { buildCfoCloudJob, buildCfoRunReceipt, enqueueCfoRun, claimCfoRun, completeCfoRun, failCfoRun };
