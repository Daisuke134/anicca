"use strict";

const ENTITY_ID = /^event-entity:[0-9a-f]{64}$/;
const KINDS = new Set(["audience_registration", "talk_application"]);

function validEntity(entity) {
  return entity
    && entity.schema_version === 1
    && ENTITY_ID.test(String(entity.entity_id || ""))
    && typeof entity.tenant_id === "string"
    && entity.tenant_id.length > 0
    && KINDS.has(entity.kind)
    && typeof entity.event_ref === "string"
    && entity.event_ref.length > 0
    && typeof entity.canonical_url === "string"
    && entity.canonical_url.startsWith("https://")
    && typeof entity.status === "string"
    && entity.payload
    && typeof entity.payload === "object"
    && !Array.isArray(entity.payload)
    && Number.isInteger(entity.version)
    && entity.version >= 1;
}

async function upsertDiscoveredEventEntities(entities, options = {}) {
  const query = options.query;
  if (!Array.isArray(entities) || entities.some((entity) => !validEntity(entity))) {
    throw new Error("event entity discovery invalid");
  }
  if (typeof query !== "function") throw new Error("event entity store unavailable");
  const results = [];
  for (const entity of entities) {
    if (entity.status !== "discovered" || entity.version !== 1) {
      throw new Error("event entity discovery invalid");
    }
    const result = await query(`
      INSERT INTO public.lm_event_participation_entities (
        tenant_id, entity_id, event_ref, entity_kind, canonical_url, status, payload, version
      ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
      ON CONFLICT (tenant_id, entity_id) DO NOTHING
      RETURNING entity_id
    `, [
      entity.tenant_id,
      entity.entity_id,
      entity.event_ref,
      entity.kind,
      entity.canonical_url,
      entity.status,
      JSON.stringify(entity.payload),
      entity.version,
    ]);
    results.push(Object.freeze({
      entity_id: entity.entity_id,
      inserted: Boolean(result && Array.isArray(result.rows) && result.rows.length === 1),
    }));
  }
  return Object.freeze(results);
}

async function transitionStoredEventEntity(before, change, options = {}) {
  const query = options.query;
  const after = change && change.entity;
  const transition = change && change.transition;
  if (
    !validEntity(before)
    || !validEntity(after)
    || !transition
    || typeof query !== "function"
    || before.entity_id !== after.entity_id
    || before.tenant_id !== after.tenant_id
    || before.kind !== after.kind
    || before.version + 1 !== after.version
    || transition.entity_id !== before.entity_id
    || transition.tenant_id !== before.tenant_id
    || transition.kind !== before.kind
    || transition.from_status !== before.status
    || transition.to_status !== after.status
    || transition.version !== after.version
  ) throw new Error("event entity transition invalid");

  const result = await query(`
    WITH updated AS (
      UPDATE public.lm_event_participation_entities
      SET status = $6, version = $7, updated_at = $8::timestamptz
      WHERE tenant_id = $1
        AND entity_id = $2
        AND entity_kind = $3
        AND status = $4
        AND version = $5
      RETURNING tenant_id, entity_id, entity_kind, status, version
    ), inserted AS (
      INSERT INTO public.lm_event_participation_transitions (
        tenant_id, entity_id, entity_kind, from_status, to_status,
        version, occurred_at, receipt_ref
      )
      SELECT tenant_id, entity_id, entity_kind, $4, $6, version, $8::timestamptz, $9
      FROM updated
      RETURNING entity_id
    )
    SELECT updated.entity_id, updated.status, updated.version
    FROM updated JOIN inserted USING (entity_id)
  `, [
    before.tenant_id,
    before.entity_id,
    before.kind,
    before.status,
    before.version,
    after.status,
    after.version,
    transition.occurred_at,
    transition.receipt_ref,
  ]);
  if (!result || !Array.isArray(result.rows) || result.rows.length !== 1) {
    throw new Error("event entity transition conflict");
  }
  return Object.freeze({ ...result.rows[0] });
}

module.exports = {
  transitionStoredEventEntity,
  upsertDiscoveredEventEntities,
};
