"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { buildAcceptedTalkTimeline } = require("./event-talk-timeline.js");

const ENTITY = Object.freeze({
  schema_version: 1,
  entity_id: `event-entity:${"a".repeat(64)}`,
  tenant_id: "tenant-a",
  kind: "talk_application",
  event_ref: "luma-event://event/ai-night",
  canonical_url: "https://luma.com/ai-night",
  status: "accepted",
  payload: Object.freeze({ starts_at: "2026-08-20T10:00:00.000Z", talk_format: "lightning_talk" }),
  version: 4,
});

const INPUT = Object.freeze({
  entity: ENTITY,
  acceptedAt: "2026-08-05T01:00:00+09:00",
  acceptedReceiptRef: "gmail-message://tenant-a/accepted-proof",
  slideDeadline: "2026-08-18T18:00:00+09:00",
  arrivalAt: "2026-08-20T18:30:00+09:00",
  venue: "Tokyo Innovation Base",
  qrArtifactRef: "object://sha256/official-ticket-qr",
  followUpAt: "2026-08-21T10:00:00+09:00",
});

test("accepted後の5 milestoneを一つのstable timelineにする", () => {
  const actual = buildAcceptedTalkTimeline(INPUT);
  assert.match(actual.timeline_id, /^talk-timeline:[0-9a-f]{64}$/);
  assert.deepEqual(actual.items.map((item) => item.kind), [
    "accepted", "slide_deadline", "ticket_qr", "talk_start", "follow_up",
  ]);
  assert.deepEqual(actual.items.map((item) => item.status), ["completed", "pending", "pending", "pending", "pending"]);
  assert.equal(actual.items[2].artifact_ref, INPUT.qrArtifactRef);
  assert.equal(actual.items[2].venue, INPUT.venue);
  assert.equal(actual.items[3].scheduled_at, "2026-08-20T10:00:00.000Z");
  assert.equal(buildAcceptedTalkTimeline(INPUT).timeline_id, actual.timeline_id);
  assert.equal(Object.isFrozen(actual.items), true);
});

test("accepted以外、receiptなし、順序矛盾、非opaque QRを拒否する", () => {
  assert.throws(() => buildAcceptedTalkTimeline({ ...INPUT, entity: { ...ENTITY, status: "submitted" } }), /accepted/i);
  assert.throws(() => buildAcceptedTalkTimeline({ ...INPUT, acceptedReceiptRef: null }), /receipt/i);
  assert.throws(() => buildAcceptedTalkTimeline({ ...INPUT, slideDeadline: "2026-08-21T00:00:00Z" }), /order/i);
  assert.throws(() => buildAcceptedTalkTimeline({ ...INPUT, qrArtifactRef: "/tmp/ticket.png" }), /QR/i);
});

test("audience entityや別tenantを示すartifactを受理しない", () => {
  assert.throws(() => buildAcceptedTalkTimeline({ ...INPUT, entity: { ...ENTITY, kind: "audience_registration" } }), /accepted/i);
  assert.throws(() => buildAcceptedTalkTimeline({ ...INPUT, qrArtifactRef: "object://tenant-b/ticket" }), /QR/i);
});
