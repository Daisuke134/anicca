"use strict";

const { buildCfoCloudJob } = require("./cfo-cloud-scheduler.js");
const TENANT = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
function fail() { throw new Error("cfo_tenant_load_invalid:simulation"); }

/**
 * Replays redacted CFO adapter envelopes only. It never creates a DB job,
 * opens a browser, calls a provider, or estimates a financial amount.
 */
function simulateCfoTenantLoad({ tenantCount = 100, runsPerTenant = 1 } = {}) {
  if (!Number.isSafeInteger(tenantCount) || tenantCount < 1 || tenantCount > 1000
    || !Number.isSafeInteger(runsPerTenant) || runsPerTenant < 1 || runsPerTenant > 10) fail();
  const jobs = [], ids = new Set(); let crossTenantViolations = 0, secretLeaks = 0;
  for (let tenantIndex = 0; tenantIndex < tenantCount; tenantIndex += 1) {
    const tenantId = `tenant-${tenantIndex}`;
    if (!TENANT.test(tenantId)) fail();
    for (let run = 0; run < runsPerTenant; run += 1) {
      const job = buildCfoCloudJob({ tenantId, reportingDate: "2026-08-21", runId: `run-${run}` });
      if (ids.has(job.job_id)) crossTenantViolations += 1;
      ids.add(job.job_id);
      if (!job.job_id.includes(tenantId) || !job.input_refs.run_ref[0].includes(`/${tenantId}/`)) crossTenantViolations += 1;
      if (/secret|token|password|private/i.test(JSON.stringify(job))) secretLeaks += 1;
      jobs.push({ tenantId, jobId: job.job_id, capability: job.capability, effectClass: job.effect_class });
    }
  }
  return Object.freeze({ schemaVersion: 1, status: crossTenantViolations === 0 && secretLeaks === 0 ? "pass" : "fail", tenantCount, runsPerTenant, envelopeCount: jobs.length, crossTenantViolations, secretLeaks, externalCalls: 0, financialSideEffects: 0 });
}

module.exports = { simulateCfoTenantLoad };
