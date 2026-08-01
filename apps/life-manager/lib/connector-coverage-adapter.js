"use strict";

const { isVerifiedRollingEventCoverage } = require("./rolling-event-coverage.js");
const { planConnectorCoverageContinuation } = require("./connector-coverage-continuation.js");
const {
  CAPABILITY,
  LOOP_ID,
  buildConnectorCoverageJob,
  enqueueConnectorCoverageContinuation,
} = require("./connector-coverage-job.js");

const RECEIPTS = new WeakSet();
const JOB_KEYS = Object.freeze([
  "browser_profile_ref", "calendar_ref", "continuation_ref",
  "coverage_snapshot_ref", "identity_ref",
]);
const COVERAGE_REF = /^event-coverage:\/\/([a-z0-9][a-z0-9._-]{0,199})\/([0-9a-f]{64})$/;

function invalid() { throw new Error("Connector coverage adapter invalid"); }

function jobContract(job) {
  const refs = job && job.input_refs;
  if (
    !job || job.capability !== CAPABILITY || job.loop_id !== LOOP_ID
    || job.effect_class !== "none" || job.effect_key !== null
    || !Number.isSafeInteger(job.attempt) || job.attempt < 1
    || !refs || typeof refs !== "object" || Array.isArray(refs)
    || Object.keys(refs).sort().join(",") !== [...JOB_KEYS].sort().join(",")
  ) invalid();
  const coverage = COVERAGE_REF.exec(String(refs.coverage_snapshot_ref || ""));
  if (!coverage || coverage[1] !== job.tenant_id) invalid();
  if (!/^connector-continuation:\/\/[a-z0-9][a-z0-9._-]{0,199}\/[0-9a-f]{64}$/.test(String(refs.continuation_ref || ""))) invalid();
  if (!/^identity:\/\/[a-z0-9._-]+\/[a-z0-9._-]+$/i.test(String(refs.identity_ref || ""))) invalid();
  if (!/^browser-profile:\/\/cloakbrowser\/[a-z0-9._-]+$/i.test(String(refs.browser_profile_ref || ""))) invalid();
  if (!/^calendar:\/\/google\/[a-z0-9._-]+$/i.test(String(refs.calendar_ref || ""))) invalid();
  return Object.freeze({
    tenantId: job.tenant_id,
    jobId: job.job_id,
    coverageSnapshotRef: refs.coverage_snapshot_ref,
    identityRef: refs.identity_ref,
    browserProfileRef: refs.browser_profile_ref,
    calendarRef: refs.calendar_ref,
  });
}

function createConnectorCoverageLoopAdapter(dependencies = {}) {
  const coverageStore = dependencies.coverageStore;
  const refreshCoverage = dependencies.refreshCoverage;
  const enqueueContinuation = dependencies.enqueueContinuation || enqueueConnectorCoverageContinuation;
  const now = dependencies.now || (() => new Date().toISOString());

  return Object.freeze({
    async plan(context = {}) {
      return [buildConnectorCoverageJob(context)];
    },

    async execute(job) {
      const contract = jobContract(job);
      if (
        !coverageStore || typeof coverageStore.read !== "function" || typeof coverageStore.save !== "function"
        || typeof refreshCoverage !== "function" || typeof enqueueContinuation !== "function"
      ) invalid();
      const current = await coverageStore.read(contract.coverageSnapshotRef);
      if (
        !isVerifiedRollingEventCoverage(current)
        || current.tenant_id !== contract.tenantId
        || contract.coverageSnapshotRef !== `event-coverage://${contract.tenantId}/${current.coverage_snapshot_id.replace(/^event-coverage:/, "")}`
      ) invalid();
      const result = await refreshCoverage(Object.freeze({
        coverage: current,
        tenantId: contract.tenantId,
        identityRef: contract.identityRef,
        browserProfileRef: contract.browserProfileRef,
        calendarRef: contract.calendarRef,
      }));
      if (
        !result || typeof result !== "object" || Array.isArray(result)
        || Object.keys(result).sort().join(",") !== "coverage,observedOutcomes"
        || !isVerifiedRollingEventCoverage(result.coverage)
        || result.coverage.tenant_id !== contract.tenantId
        || !Array.isArray(result.observedOutcomes)
      ) invalid();
      const saved = await coverageStore.save(result.coverage);
      if (saved !== result.coverage) invalid();
      const observedAt = now();
      const continuation = planConnectorCoverageContinuation({
        coverage: result.coverage,
        observedOutcomes: result.observedOutcomes,
        now: observedAt,
      });
      if (continuation.status === "continue") {
        await enqueueContinuation({
          tenantId: contract.tenantId,
          coverage: result.coverage,
          continuation,
          identityRef: contract.identityRef,
          browserProfileRef: contract.browserProfileRef,
          calendarRef: contract.calendarRef,
        }, dependencies.storeOptions || {});
      }
      const receipt = Object.freeze({
        kind: "connector_coverage_refresh",
        status: continuation.status,
        source_job_id: contract.jobId,
        coverage_snapshot_ref: `event-coverage://${contract.tenantId}/${result.coverage.coverage_snapshot_id.replace(/^event-coverage:/, "")}`,
        continuation_id: continuation.continuation_id,
        open_date_count: continuation.open_date_count,
        next_run_at: continuation.next_run_at,
      });
      RECEIPTS.add(receipt);
      return Object.freeze({ receipt });
    },

    async reconcile() {
      return Object.freeze({ state: "absent", receipt: { kind: "connector_coverage_no_effect" } });
    },

    verify(receipt, job) {
      return Boolean(receipt && RECEIPTS.has(receipt) && (!job || receipt.source_job_id === job.job_id));
    },

    report(receipt) {
      if (
        !receipt || receipt.kind !== "connector_coverage_refresh"
        || !["continue", "complete"].includes(receipt.status)
        || !Number.isInteger(receipt.open_date_count) || receipt.open_date_count < 0 || receipt.open_date_count > 21
      ) invalid();
      return Object.freeze({ status: receipt.status, open_date_count: receipt.open_date_count });
    },
  });
}

module.exports = { createConnectorCoverageLoopAdapter };
