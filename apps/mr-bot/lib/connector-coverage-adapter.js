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
const PLAN_STATUSES = new Set(["complete", "enqueued", "waiting", "unavailable", "exhausted", "no_candidates"]);
const PLAN_KEYS = Object.freeze([
  "candidate_count", "coverage_snapshot_id", "date", "event_ref", "inventory_snapshot_id",
  "job_ref", "open_date_plan_id", "runnable_candidate_count", "skip_reason_counts", "status",
]);

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

function openDatePlanContract(value, coverage) {
  if (
    !value || typeof value !== "object" || Array.isArray(value)
    || Object.keys(value).sort().join(",") !== [...PLAN_KEYS].sort().join(",")
    || !/^connector-open-date-plan:[0-9a-f]{64}$/.test(String(value.open_date_plan_id || ""))
    || value.coverage_snapshot_id !== coverage.coverage_snapshot_id
    || !/^luma-date-inventory:[0-9a-f]{64}$/.test(String(value.inventory_snapshot_id || ""))
    || !PLAN_STATUSES.has(value.status)
    || !Number.isInteger(value.candidate_count) || value.candidate_count < 0
    || !Number.isInteger(value.runnable_candidate_count) || value.runnable_candidate_count < 0
    || value.runnable_candidate_count > value.candidate_count
    || !Array.isArray(value.skip_reason_counts)
    || value.skip_reason_counts.some((row) => (
      !row || typeof row !== "object" || Array.isArray(row)
      || Object.keys(row).sort().join(",") !== "count,reason"
      || !/^[a-z][a-z0-9_]{0,99}$/.test(String(row.reason || ""))
      || !Number.isInteger(row.count) || row.count < 1
    ))
    || value.skip_reason_counts.reduce((sum, row) => sum + row.count, 0)
      !== value.candidate_count - value.runnable_candidate_count
  ) invalid();
  if (value.status === "complete") {
    if (
      coverage.counts.open !== 0 || value.date !== null || value.event_ref !== null || value.job_ref !== null
      || value.candidate_count !== 0 || value.runnable_candidate_count !== 0
    ) invalid();
    return value;
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value.date || ""))) invalid();
  const day = coverage.days.find((candidate) => candidate.date === value.date);
  if (!day || (value.status === "unavailable" ? day.status !== "unavailable" : day.status !== "open")) invalid();
  const hasJob = ["enqueued", "waiting"].includes(value.status);
  if (hasJob) {
    const job = /^runtime-job:\/\/([a-z0-9][a-z0-9._-]{0,199})\/([0-9a-f]{64})$/.exec(String(value.job_ref || ""));
    if (
      !/^luma-event:\/\/event\/[A-Za-z0-9_-]+$/.test(String(value.event_ref || ""))
      || !job || job[1] !== coverage.tenant_id
    ) invalid();
  } else if (value.event_ref !== null || value.job_ref !== null) invalid();
  return value;
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
        || Object.keys(result).sort().join(",") !== "coverage,observedOutcomes,openDatePlan"
        || !isVerifiedRollingEventCoverage(result.coverage)
        || result.coverage.tenant_id !== contract.tenantId
        || !Array.isArray(result.observedOutcomes)
      ) invalid();
      const openDatePlan = openDatePlanContract(result.openDatePlan, result.coverage);
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
        open_date_plan_ref: `connector-open-date-plan://${contract.tenantId}/${openDatePlan.open_date_plan_id.replace(/^connector-open-date-plan:/, "")}`,
        open_date_plan_status: openDatePlan.status,
        open_date_candidate_count: openDatePlan.candidate_count,
        open_date_runnable_candidate_count: openDatePlan.runnable_candidate_count,
        open_date_skip_reason_counts: openDatePlan.skip_reason_counts,
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
        || !Number.isInteger(receipt.open_date_count) || receipt.open_date_count < 0 || receipt.open_date_count > 28
        || !PLAN_STATUSES.has(receipt.open_date_plan_status)
        || !Number.isInteger(receipt.open_date_candidate_count) || receipt.open_date_candidate_count < 0
        || !Number.isInteger(receipt.open_date_runnable_candidate_count) || receipt.open_date_runnable_candidate_count < 0
        || receipt.open_date_runnable_candidate_count > receipt.open_date_candidate_count
        || !Array.isArray(receipt.open_date_skip_reason_counts)
      ) invalid();
      return Object.freeze({
        status: receipt.status,
        open_date_count: receipt.open_date_count,
        open_date_plan_status: receipt.open_date_plan_status,
        open_date_candidate_count: receipt.open_date_candidate_count,
        open_date_runnable_candidate_count: receipt.open_date_runnable_candidate_count,
        open_date_skip_reason_counts: receipt.open_date_skip_reason_counts,
      });
    },
  });
}

module.exports = { createConnectorCoverageLoopAdapter };
