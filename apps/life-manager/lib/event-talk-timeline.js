"use strict";

const { createHash } = require("node:crypto");

const ENTITY_ID = /^event-entity:[0-9a-f]{64}$/;
const REF = /^[a-z][a-z0-9+.-]*:\/\/[^\s]{3,500}$/i;

function invalid(label) { throw new Error(`accepted talk timeline ${label} invalid`); }
function text(value, max, label) {
  const result = String(value == null ? "" : value).trim();
  if (!result || result.length > max) invalid(label);
  return result;
}
function instant(value, label) {
  const raw = text(value, 80, label);
  const ms = Date.parse(raw);
  if (!Number.isFinite(ms) || !/[zZ]|[+-]\d\d:\d\d$/.test(raw)) invalid(label);
  return Object.freeze({ iso: new Date(ms).toISOString(), ms });
}
function timelineId(tenantId, entityId) {
  return `talk-timeline:${createHash("sha256").update(`${tenantId}\n${entityId}`).digest("hex")}`;
}

function buildAcceptedTalkTimeline(input = {}) {
  const entity = input.entity;
  if (!entity || entity.schema_version !== 1 || entity.kind !== "talk_application" || entity.status !== "accepted"
    || !ENTITY_ID.test(String(entity.entity_id || "")) || !entity.payload || typeof entity.payload !== "object") {
    invalid("accepted entity");
  }
  const tenantId = text(entity.tenant_id, 128, "tenant");
  const eventRef = text(entity.event_ref, 500, "event ref");
  const canonicalUrl = text(entity.canonical_url, 500, "canonical URL");
  if (!canonicalUrl.startsWith("https://")) invalid("canonical URL");
  const acceptedReceiptRef = text(input.acceptedReceiptRef, 500, "receipt");
  if (!REF.test(acceptedReceiptRef)) invalid("receipt");
  const qrArtifactRef = text(input.qrArtifactRef, 500, "QR");
  if (!/^object:\/\/sha256\/[a-zA-Z0-9._-]{3,200}$/.test(qrArtifactRef)) invalid("QR");
  const venue = text(input.venue, 300, "venue");
  const accepted = instant(input.acceptedAt, "accepted time");
  const slide = instant(input.slideDeadline, "slide deadline");
  const arrival = instant(input.arrivalAt, "arrival time");
  const start = instant(entity.payload.starts_at, "talk start");
  const followUp = instant(input.followUpAt, "follow-up time");
  if (!(accepted.ms < slide.ms && slide.ms <= arrival.ms && arrival.ms < start.ms && start.ms < followUp.ms)) invalid("order");

  const item = (kind, scheduledAt, status, extra = {}) => Object.freeze({ kind, scheduled_at: scheduledAt, status, ...extra });
  const items = Object.freeze([
    item("accepted", accepted.iso, "completed", { receipt_ref: acceptedReceiptRef }),
    item("slide_deadline", slide.iso, "pending"),
    item("ticket_qr", arrival.iso, "pending", { venue, artifact_ref: qrArtifactRef }),
    item("talk_start", start.iso, "pending", { venue }),
    item("follow_up", followUp.iso, "pending"),
  ]);
  return Object.freeze({
    schema_version: 1,
    timeline_id: timelineId(tenantId, entity.entity_id),
    tenant_id: tenantId,
    talk_entity_id: entity.entity_id,
    event_ref: eventRef,
    canonical_url: canonicalUrl,
    accepted_receipt_ref: acceptedReceiptRef,
    items,
  });
}

module.exports = { buildAcceptedTalkTimeline, timelineId };
