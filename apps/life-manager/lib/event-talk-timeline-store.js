"use strict";

const { timelineId } = require("./event-talk-timeline.js");

function valid(value) {
  return value && value.schema_version === 1
    && value.timeline_id === timelineId(value.tenant_id, value.talk_entity_id)
    && /^event-entity:[0-9a-f]{64}$/.test(value.talk_entity_id)
    && typeof value.event_ref === "string" && value.event_ref.length > 2
    && typeof value.canonical_url === "string" && value.canonical_url.startsWith("https://")
    && /^[a-z][a-z0-9+.-]*:\/\/[^\s]+$/i.test(value.accepted_receipt_ref)
    && Array.isArray(value.items) && value.items.length === 5;
}

async function upsertAcceptedTalkTimeline(value, options = {}) {
  if (!valid(value) || typeof options.query !== "function") throw new Error("accepted talk timeline store invalid");
  const result = await options.query(`
    INSERT INTO public.lm_event_talk_timelines (
      tenant_id, timeline_id, talk_entity_id, event_ref, canonical_url,
      accepted_receipt_ref, items
    ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
    ON CONFLICT (tenant_id, talk_entity_id) DO UPDATE SET
      canonical_url = EXCLUDED.canonical_url,
      accepted_receipt_ref = EXCLUDED.accepted_receipt_ref,
      items = EXCLUDED.items,
      updated_at = clock_timestamp()
    WHERE public.lm_event_talk_timelines.timeline_id = EXCLUDED.timeline_id
    RETURNING timeline_id, (xmax = 0) AS inserted
  `, [
    value.tenant_id, value.timeline_id, value.talk_entity_id, value.event_ref,
    value.canonical_url, value.accepted_receipt_ref, JSON.stringify(value.items),
  ]);
  if (!result || !Array.isArray(result.rows) || result.rows.length !== 1) throw new Error("accepted talk timeline store conflict");
  return Object.freeze({ ...result.rows[0] });
}

module.exports = { upsertAcceptedTalkTimeline };
