"use strict";

const STATUS_FROM = Object.freeze({ submitted: "drafted", accepted: "submitted", rejected: "submitted", presented: "accepted" });

function valid(entry) {
  return entry && entry.schema_version === 1
    && /^talk-ledger:[0-9a-f]{64}$/.test(String(entry.ledger_id || ""))
    && /^event-entity:[0-9a-f]{64}$/.test(String(entry.talk_entity_id || ""))
    && typeof entry.tenant_id === "string" && entry.tenant_id.length > 0
    && typeof entry.event_ref === "string" && entry.event_ref.length > 2
    && STATUS_FROM[entry.status] === entry.from_status
    && Number.isInteger(entry.entity_version) && entry.entity_version >= 2
    && Number.isFinite(Date.parse(entry.occurred_at))
    && /^[a-z][a-z0-9+.-]*:\/\/[^\s]+$/i.test(String(entry.receipt_ref || ""));
}

async function appendTalkApplicationLedgerEntry(entry, options = {}) {
  if (!valid(entry) || typeof options.query !== "function") throw new Error("talk application ledger store invalid");
  const result = await options.query(`
    WITH inserted AS (
      INSERT INTO public.lm_event_talk_application_ledger (
        tenant_id, ledger_id, talk_entity_id, event_ref, from_status,
        status, receipt_ref, entity_version, occurred_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::timestamptz)
      ON CONFLICT DO NOTHING
      RETURNING ledger_id, true AS inserted
    ), replay AS (
      SELECT ledger_id, false AS inserted
      FROM public.lm_event_talk_application_ledger
      WHERE tenant_id = $1 AND ledger_id = $2 AND talk_entity_id = $3
        AND event_ref = $4 AND from_status = $5 AND status = $6
        AND receipt_ref = $7 AND entity_version = $8 AND occurred_at = $9::timestamptz
    )
    SELECT * FROM inserted
    UNION ALL
    SELECT * FROM replay WHERE NOT EXISTS (SELECT 1 FROM inserted)
  `, [
    entry.tenant_id, entry.ledger_id, entry.talk_entity_id, entry.event_ref,
    entry.from_status, entry.status, entry.receipt_ref, entry.entity_version, entry.occurred_at,
  ]);
  if (!result || !Array.isArray(result.rows) || result.rows.length !== 1) throw new Error("talk application ledger store conflict");
  return Object.freeze({ ...result.rows[0] });
}

module.exports = { appendTalkApplicationLedgerEntry };
