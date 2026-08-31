"use strict";

const { createHash } = require("node:crypto");

const { buildRuntimeJob, enqueueJobAt } = require("./runtime-job-store.js");
const { isVerifiedRollingEventCoverage } = require("./rolling-event-coverage.js");
const {
  isVerifiedConnectorCoverageContinuation,
} = require("./connector-coverage-continuation.js");

const CAPABILITY = "connector.coverage.refresh";
const LOOP_ID = "connector.coverage";
const IDENTITY_REF = /^identity:\/\/[a-z0-9._-]+\/[a-z0-9._-]+$/i;
const BROWSER_REF = /^browser-profile:\/\/cloakbrowser\/[a-z0-9._-]+$/i;
const CALENDAR_REF = /^calendar:\/\/google\/[a-z0-9._-]+$/i;

function invalid(message = "Connector coverage job invalid") { throw new Error(message); }

function reference(value, pattern) {
  const text = String(value == null ? "" : value).trim();
  if (!pattern.test(text)) invalid();
  return text;
}

function buildConnectorCoverageJob(input = {}) {
  const coverage = input.coverage;
  const continuation = input.continuation;
  const tenantId = String(input.tenantId == null ? "" : input.tenantId).trim();
  if (
    !isVerifiedRollingEventCoverage(coverage)
    || !isVerifiedConnectorCoverageContinuation(continuation)
    || !tenantId || tenantId !== coverage.tenant_id
    || continuation.coverage_snapshot_id !== coverage.coverage_snapshot_id
  ) invalid();
  if (
    continuation.status !== "continue"
    || continuation.open_date_count < 1
    || !continuation.next_run_at
  ) invalid("Connector coverage job complete");
  const coverageHash = String(coverage.coverage_snapshot_id).replace(/^event-coverage:/, "");
  const continuationHash = String(continuation.continuation_id)
    .replace(/^connector-coverage-continuation:/, "");
  if (!/^[0-9a-f]{64}$/.test(coverageHash) || !/^[0-9a-f]{64}$/.test(continuationHash)) invalid();
  const identityRef = reference(input.identityRef, IDENTITY_REF);
  const browserProfileRef = reference(input.browserProfileRef, BROWSER_REF);
  const calendarRef = reference(input.calendarRef, CALENDAR_REF);
  const jobHash = createHash("sha256").update(
    `${tenantId}\n${coverageHash}\n${continuationHash}\n${identityRef}`,
    "utf8",
  ).digest("hex");
  return buildRuntimeJob({
    jobId: `connector-coverage:${jobHash}`,
    tenantId,
    loopId: LOOP_ID,
    capability: CAPABILITY,
    effectClass: "none",
    effectKey: null,
    inputRefs: {
      coverage_snapshot_ref: `event-coverage://${tenantId}/${coverageHash}`,
      continuation_ref: `connector-continuation://${tenantId}/${continuationHash}`,
      identity_ref: identityRef,
      browser_profile_ref: browserProfileRef,
      calendar_ref: calendarRef,
    },
    maxAttempts: 20,
  });
}

async function enqueueConnectorCoverageContinuation(input = {}, storeOptions = {}, dependencies = {}) {
  const enqueue = dependencies.enqueueJobAt || enqueueJobAt;
  const job = buildConnectorCoverageJob(input);
  return enqueue(job, input.continuation.next_run_at, storeOptions);
}

module.exports = {
  CAPABILITY,
  LOOP_ID,
  buildConnectorCoverageJob,
  enqueueConnectorCoverageContinuation,
};
