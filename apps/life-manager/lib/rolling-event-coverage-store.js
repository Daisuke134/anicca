"use strict";

const { isDeepStrictEqual } = require("node:util");
const {
  buildRollingEventCoverage,
  isVerifiedRollingEventCoverage,
} = require("./rolling-event-coverage.js");

const KEYS = Object.freeze([
  "calculated_at", "counts", "coverage_snapshot_id", "days", "horizon_days",
  "tenant_id", "timezone", "window_end_date", "window_start_date",
]);
const SNAPSHOT_ID = /^event-coverage:[0-9a-f]{64}$/;
const TENANT = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const DATE_KEY = /^\d{4}-\d{2}-\d{2}$/;
const STATUSES = new Set(["open", "covered_existing", "covered_new", "unavailable"]);
const SNAPSHOT_REF = /^event-coverage:\/\/([a-z0-9][a-z0-9._-]{0,199})\/([0-9a-f]{64})$/;

function invalid() { throw new Error("rolling coverage snapshot invalid"); }

function normalizeRow(row) {
  if (!row || typeof row !== "object" || Array.isArray(row)) invalid();
  if (Object.keys(row).sort().join(",") !== [...KEYS].sort().join(",")) invalid();
  if (!SNAPSHOT_ID.test(row.coverage_snapshot_id) || !TENANT.test(row.tenant_id)) invalid();
  if (typeof row.timezone !== "string" || row.timezone.length < 1 || row.timezone.length > 100) invalid();
  if (!DATE_KEY.test(row.window_start_date) || !DATE_KEY.test(row.window_end_date) || row.horizon_days !== 21) invalid();
  if (!Array.isArray(row.days) || row.days.length !== 21) invalid();
  const days = row.days.map((day) => {
    if (!day || Object.keys(day).sort().join(",") !== "date,evidence_refs,status") invalid();
    if (!DATE_KEY.test(day.date) || !STATUSES.has(day.status) || !Array.isArray(day.evidence_refs)) invalid();
    return { date: day.date, status: day.status, evidence_refs: [...day.evidence_refs] };
  });
  const counts = row.counts;
  if (!counts || Object.keys(counts).sort().join(",") !== "covered_existing,covered_new,open,unavailable") invalid();
  if (![counts.open, counts.covered_existing, counts.covered_new, counts.unavailable].every(Number.isInteger)) invalid();
  if (counts.open + counts.covered_existing + counts.covered_new + counts.unavailable !== 21) invalid();
  return { ...row, days, counts: { ...counts } };
}

const RETURNING = `
  coverage_snapshot_id, tenant_id, timezone,
  to_char(calculated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') AS calculated_at,
  window_start_date::text, window_end_date::text, horizon_days, days,
  jsonb_build_object(
    'open', open_count,
    'covered_existing', covered_existing_count,
    'covered_new', covered_new_count,
    'unavailable', unavailable_count
  ) AS counts
`;

function createRollingEventCoverageStore(options = {}) {
  if (typeof options.connect !== "function") throw new Error("rolling coverage store unavailable");
  return Object.freeze({
    async read(snapshotRef) {
      const match = SNAPSHOT_REF.exec(String(snapshotRef == null ? "" : snapshotRef).trim());
      if (!match) invalid();
      const tenantId = match[1];
      const snapshotId = `event-coverage:${match[2]}`;
      let client;
      try {
        client = await options.connect();
        if (!client || typeof client.query !== "function" || typeof client.release !== "function") invalid();
        const rows = (await client.query(`
          SELECT ${RETURNING}
          FROM public.lm_event_coverage_snapshots
          WHERE coverage_snapshot_id = $1 AND tenant_id = $2
          LIMIT 1
        `, [snapshotId, tenantId])).rows;
        if (rows.length !== 1) invalid();
        const stored = normalizeRow(rows[0]);
        if (stored.tenant_id !== tenantId || stored.coverage_snapshot_id !== snapshotId) invalid();
        const restored = buildRollingEventCoverage({
          tenantId: stored.tenant_id,
          timeZone: stored.timezone,
          now: stored.calculated_at,
          resolvedDays: stored.days.filter((day) => day.status !== "open"),
        });
        if (!isDeepStrictEqual(normalizeRow(restored), stored)) invalid();
        return restored;
      } catch {
        throw new Error("rolling coverage store unavailable");
      } finally {
        if (client) client.release();
      }
    },
    async save(snapshot) {
      if (!isVerifiedRollingEventCoverage(snapshot)) invalid();
      const expected = normalizeRow(snapshot);
      let client;
      try {
        client = await options.connect();
        if (!client || typeof client.query !== "function" || typeof client.release !== "function") invalid();
        await client.query("BEGIN");
        let rows = (await client.query(`
          INSERT INTO public.lm_event_coverage_snapshots (
            coverage_snapshot_id, tenant_id, timezone, calculated_at,
            window_start_date, window_end_date, horizon_days, days,
            open_count, covered_existing_count, covered_new_count, unavailable_count
          ) VALUES ($1, $2, $3, $4::timestamptz, $5::date, $6::date, $7, $8::jsonb, $9, $10, $11, $12)
          ON CONFLICT (coverage_snapshot_id) DO NOTHING
          RETURNING ${RETURNING}
        `, [
          expected.coverage_snapshot_id, expected.tenant_id, expected.timezone, expected.calculated_at,
          expected.window_start_date, expected.window_end_date, expected.horizon_days, JSON.stringify(expected.days),
          expected.counts.open, expected.counts.covered_existing, expected.counts.covered_new, expected.counts.unavailable,
        ])).rows;
        if (rows.length === 0) {
          rows = (await client.query(`SELECT ${RETURNING} FROM public.lm_event_coverage_snapshots WHERE coverage_snapshot_id = $1 AND tenant_id = $2`, [expected.coverage_snapshot_id, expected.tenant_id])).rows;
        }
        if (rows.length !== 1 || !isDeepStrictEqual(normalizeRow(rows[0]), expected)) invalid();
        await client.query("COMMIT");
        return snapshot;
      } catch {
        try { if (client) await client.query("ROLLBACK"); } catch { /* preserve generic failure */ }
        throw new Error("rolling coverage store unavailable");
      } finally {
        if (client) client.release();
      }
    },
  });
}

module.exports = { createRollingEventCoverageStore };
