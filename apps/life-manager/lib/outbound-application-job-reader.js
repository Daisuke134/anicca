"use strict";

const { isDeepStrictEqual } = require("node:util");
const { buildRuntimeJob } = require("./runtime-job-store.js");

const STATUSES = new Set(["queued", "running", "reconciling", "completed", "dead_letter"]);
const FIELDS = Object.freeze([
  "job_id", "tenant_id", "loop_id", "capability", "effect_class",
  "effect_key", "input_refs", "max_attempts",
]);

function unavailable() { throw new Error("outbound application job reader unavailable"); }

function createOutboundApplicationJobReader(dependencies = {}) {
  if (typeof dependencies.query !== "function") unavailable();
  return Object.freeze({
    async read(input) {
      let expected;
      try { expected = buildRuntimeJob(input); } catch { unavailable(); }
      let rows;
      try {
        rows = (await dependencies.query(`
          SELECT
            job_id, tenant_id, loop_id, capability, effect_class,
            effect_key, input_refs, max_attempts, status
          FROM public.lm_runtime_jobs
          WHERE job_id = $1 AND tenant_id = $2
          LIMIT 2
        `, [expected.job_id, expected.tenant_id])).rows;
      } catch { unavailable(); }
      if (!Array.isArray(rows) || rows.length > 1) unavailable();
      if (rows.length === 0) return null;
      const row = rows[0];
      if (!row || !STATUSES.has(row.status)) unavailable();
      const actual = Object.fromEntries(FIELDS.map((field) => [field, row[field]]));
      const wanted = Object.fromEntries(FIELDS.map((field) => [field, expected[field]]));
      if (!isDeepStrictEqual(actual, wanted)) unavailable();
      return Object.freeze({ status: row.status });
    },
  });
}

module.exports = { createOutboundApplicationJobReader };
