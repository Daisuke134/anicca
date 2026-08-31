"use strict";

const { createHash } = require("node:crypto");
const { isDeepStrictEqual } = require("node:util");
const { isVerifiedAcceptedTalkTimeline } = require("./accepted-talk-timeline.js");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const PARTICIPATION = /^event-participation:[0-9a-f]{64}$/;
const SNAPSHOT = /^talk-timeline:[0-9a-f]{64}$/;
const SOURCE_REF = /^(?:evidence|provider-receipt|mail-receipt|object):\/\/[a-z0-9._~:/?#@!$&'()*+,;=%-]{1,950}$/i;
const TICKET_REF = /^object:\/\/sha256\/[0-9a-f]{64}$/;
const VERIFIED_SNAPSHOTS = new WeakSet();
const KEYS = Object.freeze([
  "accepted_at", "appearance_end_at", "appearance_start_at", "follow_up_at", "follow_up_purpose",
  "follow_up_reason", "participation_id", "slide_due_at", "slide_status", "snapshot_id", "source_refs",
  "tenant_id", "ticket_ref", "ticket_status", "venue_address", "venue_name", "venue_status",
]);

function invalid() { throw new Error("talk timeline snapshot invalid"); }

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function buildTalkTimelineSnapshot(input = {}) {
  const tenantId = String(input.tenantId == null ? "" : input.tenantId).trim();
  const participationId = String(input.participationId == null ? "" : input.participationId).trim();
  if (!TENANT.test(tenantId) || !PARTICIPATION.test(participationId)) invalid();
  if (!isVerifiedAcceptedTalkTimeline(input.timeline)) invalid();
  const core = {
    tenant_id: tenantId,
    participation_id: participationId,
    ...input.timeline,
    source_refs: [...input.timeline.source_refs],
  };
  const digest = createHash("sha256").update(stableJson(core), "utf8").digest("hex");
  const snapshot = Object.freeze({ snapshot_id: `talk-timeline:${digest}`, ...core, source_refs: Object.freeze(core.source_refs) });
  VERIFIED_SNAPSHOTS.add(snapshot);
  return snapshot;
}

function normalizeRow(row) {
  if (!row || typeof row !== "object" || Array.isArray(row)) invalid();
  const value = {};
  for (const key of KEYS) value[key] = row[key];
  if (Object.keys(row).sort().join(",") !== [...KEYS].sort().join(",")) invalid();
  if (!SNAPSHOT.test(value.snapshot_id) || !TENANT.test(value.tenant_id) || !PARTICIPATION.test(value.participation_id)) invalid();
  if (!Array.isArray(value.source_refs) || value.source_refs.length < 1 || value.source_refs.some((ref) => !SOURCE_REF.test(ref))) invalid();
  if (value.ticket_ref !== null && !TICKET_REF.test(value.ticket_ref)) invalid();
  return value;
}

const RETURNING = `
  snapshot_id, tenant_id, participation_id,
  to_char(accepted_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') AS accepted_at,
  slide_status,
  CASE WHEN slide_due_at IS NULL THEN NULL ELSE to_char(slide_due_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') END AS slide_due_at,
  to_char(appearance_start_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') AS appearance_start_at,
  to_char(appearance_end_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') AS appearance_end_at,
  venue_status, venue_name, venue_address, ticket_status, ticket_ref,
  to_char(follow_up_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') AS follow_up_at,
  follow_up_purpose, follow_up_reason, source_refs
`;

function createAcceptedTalkTimelineStore(options = {}) {
  if (typeof options.connect !== "function") throw new Error("talk timeline store unavailable");
  return Object.freeze({
    async save(snapshot) {
      if (!VERIFIED_SNAPSHOTS.has(snapshot)) invalid();
      const expected = normalizeRow(snapshot);
      let client;
      try {
        client = await options.connect();
        if (!client || typeof client.query !== "function" || typeof client.release !== "function") invalid();
        await client.query("BEGIN");
        const parent = (await client.query(`
          SELECT participation_id, tenant_id, kind, state
          FROM public.lm_event_participations
          WHERE participation_id = $1 AND tenant_id = $2
          FOR SHARE
        `, [expected.participation_id, expected.tenant_id])).rows;
        if (parent.length !== 1 || parent[0].kind !== "talk_application" || parent[0].state !== "accepted") invalid();
        let rows = (await client.query(`
          INSERT INTO public.lm_talk_timeline_snapshots (
            snapshot_id, tenant_id, participation_id, accepted_at, slide_status, slide_due_at,
            appearance_start_at, appearance_end_at, venue_status, venue_name, venue_address,
            ticket_status, ticket_ref, follow_up_at, follow_up_purpose, follow_up_reason, source_refs
          ) VALUES (
            $1, $2, $3, $4::timestamptz, $5, $6::timestamptz, $7::timestamptz, $8::timestamptz,
            $9, $10, $11, $12, $13, $14::timestamptz, $15, $16, $17::jsonb
          )
          ON CONFLICT (snapshot_id) DO NOTHING
          RETURNING ${RETURNING}
        `, [
          expected.snapshot_id, expected.tenant_id, expected.participation_id, expected.accepted_at,
          expected.slide_status, expected.slide_due_at, expected.appearance_start_at, expected.appearance_end_at,
          expected.venue_status, expected.venue_name, expected.venue_address, expected.ticket_status,
          expected.ticket_ref, expected.follow_up_at, expected.follow_up_purpose, expected.follow_up_reason,
          JSON.stringify(expected.source_refs),
        ])).rows;
        if (rows.length === 0) {
          rows = (await client.query(`SELECT ${RETURNING} FROM public.lm_talk_timeline_snapshots WHERE snapshot_id = $1 AND tenant_id = $2`, [expected.snapshot_id, expected.tenant_id])).rows;
        }
        if (rows.length !== 1 || !isDeepStrictEqual(normalizeRow(rows[0]), expected)) invalid();
        await client.query("COMMIT");
        return snapshot;
      } catch {
        try { if (client) await client.query("ROLLBACK"); } catch { /* preserve generic failure */ }
        throw new Error("talk timeline store unavailable");
      } finally {
        if (client) client.release();
      }
    },
  });
}

module.exports = { buildTalkTimelineSnapshot, createAcceptedTalkTimelineStore };
