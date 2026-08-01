"use strict";

const { createHash } = require("node:crypto");
const { isDeepStrictEqual } = require("node:util");
const { isVerifiedTalkApplicationTransition } = require("./talk-application-transition.js");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const PARTICIPATION = /^event-participation:[0-9a-f]{64}$/;
const TRANSITION_ID = /^talk-transition:[0-9a-f]{64}$/;
const SOURCE_REF = /^(?:evidence|provider-receipt|mail-receipt|object):\/\/[a-z0-9._~:/?#@!$&'()*+,;=%-]{1,950}$/i;
const STATES = new Set(["discovered", "submission_queued", "submitted", "accepted", "rejected", "withdrawn", "presented"]);
const KEYS = Object.freeze([
  "from_state", "observed_at", "participation_id", "reason", "source_refs",
  "tenant_id", "to_state", "transition_id",
]);
const VERIFIED_RECORDS = new WeakSet();

function invalid() { throw new Error("talk transition record invalid"); }

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

function buildTalkApplicationTransitionRecord(input = {}) {
  const tenantId = String(input.tenantId == null ? "" : input.tenantId).trim();
  const participationId = String(input.participationId == null ? "" : input.participationId).trim();
  if (!TENANT.test(tenantId) || !PARTICIPATION.test(participationId)) invalid();
  if (!isVerifiedTalkApplicationTransition(input.transition)) invalid();
  const core = {
    tenant_id: tenantId,
    participation_id: participationId,
    ...input.transition,
    source_refs: [...input.transition.source_refs],
  };
  const digest = createHash("sha256").update(stableJson(core), "utf8").digest("hex");
  const record = Object.freeze({ transition_id: `talk-transition:${digest}`, ...core, source_refs: Object.freeze(core.source_refs) });
  VERIFIED_RECORDS.add(record);
  return record;
}

function normalizeRow(row) {
  if (!row || typeof row !== "object" || Array.isArray(row)) invalid();
  if (Object.keys(row).sort().join(",") !== [...KEYS].sort().join(",")) invalid();
  if (!TRANSITION_ID.test(row.transition_id) || !TENANT.test(row.tenant_id) || !PARTICIPATION.test(row.participation_id)) invalid();
  if (!STATES.has(row.from_state) || !STATES.has(row.to_state)) invalid();
  if (typeof row.reason !== "string" || row.reason.length < 1 || row.reason.length > 500) invalid();
  if (!Array.isArray(row.source_refs) || row.source_refs.length < 1 || row.source_refs.length > 20) invalid();
  if (new Set(row.source_refs).size !== row.source_refs.length || row.source_refs.some((ref) => !SOURCE_REF.test(ref))) invalid();
  return { ...row, source_refs: [...row.source_refs] };
}

const COLUMNS = `
  transition_id, tenant_id, participation_id, from_state, to_state,
  to_char(observed_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') AS observed_at,
  reason, source_refs
`;

function createTalkApplicationTransitionStore(options = {}) {
  if (typeof options.connect !== "function") throw new Error("talk transition store unavailable");
  return Object.freeze({
    async append(record) {
      if (!VERIFIED_RECORDS.has(record)) invalid();
      const expected = normalizeRow(record);
      let client;
      try {
        client = await options.connect();
        if (!client || typeof client.query !== "function" || typeof client.release !== "function") invalid();
        await client.query("BEGIN");
        let parent = (await client.query(`
          SELECT tenant_id, participation_id, kind, state
          FROM public.lm_event_participations
          WHERE participation_id = $1 AND tenant_id = $2
          FOR UPDATE
        `, [expected.participation_id, expected.tenant_id])).rows;
        if (parent.length !== 1 || parent[0].kind !== "talk_application") invalid();
        let existing = (await client.query(`
          SELECT ${COLUMNS}
          FROM public.lm_talk_application_transitions
          WHERE transition_id = $1 AND tenant_id = $2
        `, [expected.transition_id, expected.tenant_id])).rows;
        if (existing.length > 0) {
          if (existing.length !== 1 || !isDeepStrictEqual(normalizeRow(existing[0]), expected)) invalid();
          await client.query("COMMIT");
          return record;
        }
        if (parent[0].state !== expected.from_state) invalid();
        const inserted = (await client.query(`
          INSERT INTO public.lm_talk_application_transitions (
            transition_id, tenant_id, participation_id, from_state, to_state,
            observed_at, reason, source_refs
          ) VALUES ($1, $2, $3, $4, $5, $6::timestamptz, $7, $8::jsonb)
          ON CONFLICT (transition_id) DO NOTHING
          RETURNING ${COLUMNS}
        `, [
          expected.transition_id, expected.tenant_id, expected.participation_id,
          expected.from_state, expected.to_state, expected.observed_at,
          expected.reason, JSON.stringify(expected.source_refs),
        ])).rows;
        if (inserted.length !== 1 || !isDeepStrictEqual(normalizeRow(inserted[0]), expected)) invalid();
        parent = (await client.query(`
          SELECT tenant_id, participation_id, kind, state
          FROM public.lm_event_participations
          WHERE participation_id = $1 AND tenant_id = $2
        `, [expected.participation_id, expected.tenant_id])).rows;
        if (parent.length !== 1 || parent[0].kind !== "talk_application" || parent[0].state !== expected.to_state) invalid();
        await client.query("COMMIT");
        return record;
      } catch {
        try { if (client) await client.query("ROLLBACK"); } catch { /* preserve generic failure */ }
        throw new Error("talk transition store unavailable");
      } finally {
        if (client) client.release();
      }
    },
  });
}

module.exports = { buildTalkApplicationTransitionRecord, createTalkApplicationTransitionStore };
