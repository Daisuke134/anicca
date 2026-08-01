"use strict";

const { createHash } = require("node:crypto");

const ENTITY_ID = /^event-entity:[0-9a-f]{64}$/;
const RECEIPT = /^[a-z][a-z0-9+.-]*:\/\/[^\s]{3,500}$/i;
const VALID = Object.freeze({
  submitted: "drafted",
  accepted: "submitted",
  rejected: "submitted",
  presented: "accepted",
});

function invalid(label) { throw new Error(`talk application ledger ${label} invalid`); }

function buildTalkApplicationLedgerEntry(change = {}) {
  const entity = change.entity;
  const transition = change.transition;
  if (!entity || !transition || entity.schema_version !== 1 || entity.kind !== "talk_application"
    || transition.kind !== "talk_application" || !ENTITY_ID.test(String(entity.entity_id || ""))
    || entity.entity_id !== transition.entity_id || entity.tenant_id !== transition.tenant_id
    || entity.kind !== transition.kind || entity.status !== transition.to_status
    || entity.version !== transition.version || !Number.isInteger(entity.version)
    || VALID[transition.to_status] !== transition.from_status) invalid("transition");
  const receiptRef = String(transition.receipt_ref == null ? "" : transition.receipt_ref).trim();
  if (!RECEIPT.test(receiptRef)) invalid("receipt");
  const occurredMs = Date.parse(String(transition.occurred_at || ""));
  if (!Number.isFinite(occurredMs) || !/[zZ]|[+-]\d\d:\d\d$/.test(String(transition.occurred_at))) invalid("time");
  const status = transition.to_status;
  const occurredAt = new Date(occurredMs).toISOString();
  const ledgerId = `talk-ledger:${createHash("sha256").update([
    entity.tenant_id, entity.entity_id, entity.version, status, receiptRef,
  ].join("\n")).digest("hex")}`;
  return Object.freeze({
    schema_version: 1,
    ledger_id: ledgerId,
    tenant_id: entity.tenant_id,
    talk_entity_id: entity.entity_id,
    event_ref: entity.event_ref,
    from_status: transition.from_status,
    status,
    entity_version: entity.version,
    occurred_at: occurredAt,
    receipt_ref: receiptRef,
  });
}

module.exports = { buildTalkApplicationLedgerEntry };
