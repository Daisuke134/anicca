"use strict";

const { createHash } = require("node:crypto");
const { isDeepStrictEqual } = require("node:util");

const { canonicalEventUrl } = require("./canonical-event-url.js");
const { isVerifiedEventTalkOpportunity } = require("./event-talk-opportunity.js");

const KINDS = Object.freeze(["audience_registration", "talk_application"]);
const AUDIENCE_STATES = Object.freeze([
  "discovered", "registration_queued", "registered", "waitlist", "cancelled",
]);
const TALK_STATES = Object.freeze([
  "discovered", "submission_queued", "submitted", "accepted", "rejected", "withdrawn", "presented",
]);
const LUMA_HOSTS = new Set(["lu.ma", "luma.com", "www.luma.com"]);
const TENANT = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const EVIDENCE_REF = /^evidence:\/\/event\/[a-z0-9._~:/?#@!$&'()*+,;=%-]{1,900}$/i;
const TALK_PACK_REF = /^artifact:\/\/connector-talk-pack\/sha256\/[0-9a-f]{64}$/;
const ENTITY_KEYS = Object.freeze([
  "action_ref", "availability", "event_ref", "event_start_at", "evidence_ref", "kind",
  "participation_id", "state", "talk_format", "tenant_id",
]);

function invalid() {
  throw new Error("event participation invalid");
}

function eventReference(value) {
  const canonical = canonicalEventUrl(value);
  let url;
  try { url = new URL(canonical); } catch { invalid(); }
  if (!LUMA_HOSTS.has(url.hostname.toLowerCase())) invalid();
  return canonical;
}

function exactTime(value) {
  const text = String(value == null ? "" : value).trim();
  const ms = Date.parse(text);
  if (!Number.isFinite(ms) || !/[zZ]|[+-]\d\d:\d\d$/.test(text)) invalid();
  return new Date(ms).toISOString();
}

function stableId(tenantId, eventRef, startsAt, kind) {
  const digest = createHash("sha256")
    .update(`${tenantId}\n${eventRef}\n${startsAt}\n${kind}`, "utf8")
    .digest("hex");
  return `event-participation:${digest}`;
}

function entity(base, kind, fields) {
  return Object.freeze({
    participation_id: stableId(base.tenantId, base.eventRef, base.startsAt, kind),
    tenant_id: base.tenantId,
    event_ref: base.eventRef,
    event_start_at: base.startsAt,
    kind,
    state: "discovered",
    availability: fields.availability,
    talk_format: fields.talkFormat,
    action_ref: fields.actionRef,
    evidence_ref: base.evidenceRef,
  });
}

function buildEventParticipationEntities(input = {}) {
  const tenantId = String(input.tenantId == null ? "" : input.tenantId).trim();
  if (!TENANT.test(tenantId)) invalid();
  const eventRef = eventReference(input.eventUrl);
  const startsAt = exactTime(input.eventStartIso);
  const evidenceRef = String(input.evidenceRef == null ? "" : input.evidenceRef).trim();
  if (!EVIDENCE_REF.test(evidenceRef)) invalid();
  const opportunity = input.opportunity;
  if (!isVerifiedEventTalkOpportunity(opportunity)) {
    throw new Error("event participation verified opportunity required");
  }

  const base = { tenantId, eventRef, startsAt, evidenceRef };
  const rows = [];
  if (["audience_only", "both"].includes(opportunity.participation_kind)) {
    rows.push(entity(base, "audience_registration", {
      availability: null,
      talkFormat: null,
      actionRef: eventRef,
    }));
  }
  if (["talk_application", "both"].includes(opportunity.participation_kind)) {
    rows.push(entity(base, "talk_application", {
      availability: opportunity.application_status,
      talkFormat: opportunity.talk_format,
      actionRef: opportunity.application_status === "open" ? opportunity.application_url : null,
    }));
  }
  if (rows.length === 0) invalid();
  return Object.freeze(rows);
}

function normalizeEntity(value, tenantId) {
  if (!value || typeof value !== "object" || Array.isArray(value)) invalid();
  if (Object.keys(value).sort().join(",") !== [...ENTITY_KEYS].sort().join(",")) invalid();
  if (value.tenant_id !== tenantId || !TENANT.test(value.tenant_id)) invalid();
  if (!/^event-participation:[0-9a-f]{64}$/.test(value.participation_id)) invalid();
  if (!KINDS.includes(value.kind) || value.state !== "discovered") invalid();
  if (eventReference(value.event_ref) !== value.event_ref) invalid();
  if (exactTime(value.event_start_at) !== value.event_start_at) invalid();
  if (!EVIDENCE_REF.test(value.evidence_ref)) invalid();
  if (value.kind === "audience_registration") {
    if (value.availability !== null || value.talk_format !== null || value.action_ref !== value.event_ref) invalid();
  } else {
    if (!["open", "closed", "invite_only", "not_offered", "unknown"].includes(value.availability)) invalid();
    if (!value.talk_format) invalid();
    if ((value.availability === "open") !== (typeof value.action_ref === "string")) invalid();
    if (value.action_ref != null) {
      let url;
      try { url = new URL(value.action_ref); } catch { invalid(); }
      if (url.protocol !== "https:" || url.username || url.password) invalid();
    }
  }
  return { ...value };
}

function sameEntities(actual, expected) {
  const byId = new Map(actual.map((row) => [row.participation_id, row]));
  return expected.every((row) => isDeepStrictEqual(byId.get(row.participation_id), row));
}

function createEventParticipationStore(options = {}) {
  const query = options.query;
  const connect = options.connect || (typeof query === "function" ? async () => ({
    query,
    release() {},
  }) : null);
  if (typeof connect !== "function") throw new Error("event participation store unavailable");
  return Object.freeze({
    async saveDiscovered(values) {
      if (!Array.isArray(values) || values.length < 1 || values.length > 2) invalid();
      const tenantId = values[0] && values[0].tenant_id;
      const expected = values.map((value) => normalizeEntity(value, tenantId));
      if (new Set(expected.map((row) => row.kind)).size !== expected.length) invalid();
      let client;
      try {
        client = await connect();
        if (!client || typeof client.query !== "function" || typeof client.release !== "function") invalid();
        await client.query("BEGIN");
        let rows = (await client.query(`
          INSERT INTO public.lm_event_participations (
            participation_id, tenant_id, event_ref, event_start_at, kind, state,
            availability, talk_format, action_ref, evidence_ref
          )
          SELECT participation_id, tenant_id, event_ref, event_start_at::timestamptz, kind, state,
                 availability, talk_format, action_ref, evidence_ref
          FROM jsonb_to_recordset($1::jsonb) AS x(
            participation_id text, tenant_id text, event_ref text, event_start_at text,
            kind text, state text, availability text, talk_format text, action_ref text, evidence_ref text
          )
          WHERE tenant_id = $2
          ON CONFLICT (participation_id) DO NOTHING
          RETURNING participation_id, tenant_id, event_ref,
                    to_char(event_start_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') AS event_start_at,
                    kind, state, availability, talk_format, action_ref, evidence_ref
        `, [JSON.stringify(expected), tenantId])).rows;
        if (rows.length !== expected.length) {
          rows = (await client.query(`
            SELECT participation_id, tenant_id, event_ref,
                   to_char(event_start_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') AS event_start_at,
                   kind, state, availability, talk_format, action_ref, evidence_ref
            FROM public.lm_event_participations
            WHERE tenant_id = $1 AND participation_id = ANY($2::text[])
            ORDER BY kind
          `, [tenantId, expected.map((row) => row.participation_id)])).rows;
        }
        if (rows.length !== expected.length || !sameEntities(rows, expected)) invalid();
        await client.query("COMMIT");
        return Object.freeze(expected.map((row) => Object.freeze(row)));
      } catch {
        try { if (client) await client.query("ROLLBACK"); } catch { /* preserve generic failure */ }
        throw new Error("event participation store unavailable");
      } finally {
        if (client) client.release();
      }
    },
    async attachTalkPack(input = {}) {
      const tenantId = String(input.tenantId == null ? "" : input.tenantId).trim();
      const participationId = String(input.participationId == null ? "" : input.participationId).trim();
      const artifactRef = String(input.artifactRef == null ? "" : input.artifactRef).trim();
      if (!TENANT.test(tenantId) || !/^event-participation:[0-9a-f]{64}$/.test(participationId) || !TALK_PACK_REF.test(artifactRef)) invalid();
      let client;
      try {
        client = await connect();
        if (!client || typeof client.query !== "function" || typeof client.release !== "function") invalid();
        const rows = (await client.query(`
          UPDATE public.lm_event_participations
          SET talk_pack_ref = $3, updated_at = clock_timestamp()
          WHERE tenant_id = $1 AND participation_id = $2 AND kind = 'talk_application'
            AND (talk_pack_ref IS NULL OR talk_pack_ref = $3)
          RETURNING participation_id, tenant_id, kind, talk_pack_ref
        `, [tenantId, participationId, artifactRef])).rows;
        if (rows.length !== 1 || rows[0].kind !== "talk_application" || rows[0].talk_pack_ref !== artifactRef) invalid();
        return Object.freeze({ ...rows[0] });
      } catch {
        throw new Error("event participation store unavailable");
      } finally {
        if (client) client.release();
      }
    },
  });
}

module.exports = {
  AUDIENCE_STATES,
  KINDS,
  TALK_STATES,
  buildEventParticipationEntities,
  createEventParticipationStore,
};
