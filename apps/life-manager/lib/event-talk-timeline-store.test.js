"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const { upsertAcceptedTalkTimeline } = require("./event-talk-timeline-store.js");
const { buildAcceptedTalkTimeline } = require("./event-talk-timeline.js");

const migration = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-02-lm-event-talk-timelines.sql"), "utf8");
const timeline = buildAcceptedTalkTimeline({
  entity: { schema_version: 1, entity_id: `event-entity:${"b".repeat(64)}`, tenant_id: "tenant-a", kind: "talk_application", event_ref: "luma-event://event/proof", canonical_url: "https://luma.com/proof", status: "accepted", payload: { starts_at: "2026-08-20T10:00:00Z" }, version: 4 },
  acceptedAt: "2026-08-01T00:00:00Z", acceptedReceiptRef: "receipt://accepted/proof",
  slideDeadline: "2026-08-18T00:00:00Z", arrivalAt: "2026-08-20T09:30:00Z",
  venue: "Tokyo", qrArtifactRef: "object://sha256/ticket-proof", followUpAt: "2026-08-21T00:00:00Z",
});

test("migrationはtenant-bound one timelineとservice-only RLSを作る", () => {
  assert.match(migration, /CREATE TABLE IF NOT EXISTS public\.lm_event_talk_timelines/i);
  assert.match(migration, /PRIMARY KEY \(tenant_id, timeline_id\)/i);
  assert.match(migration, /UNIQUE \(tenant_id, talk_entity_id\)/i);
  assert.match(migration, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(migration, /REVOKE ALL.*authenticated/is);
  assert.match(migration, /jsonb_array_length\(items\) = 5/i);
});

test("stable timelineをidempotent upsertしaccepted receiptを保持する", async () => {
  let seen;
  const actual = await upsertAcceptedTalkTimeline(timeline, { query: async (sql, params) => {
    seen = { sql, params };
    return { rows: [{ timeline_id: timeline.timeline_id, inserted: true }] };
  }});
  assert.equal(actual.timeline_id, timeline.timeline_id);
  assert.match(seen.sql, /ON CONFLICT \(tenant_id, talk_entity_id\)/i);
  assert.match(seen.sql, /accepted_receipt_ref/i);
  assert.equal(JSON.parse(seen.params[6]).length, 5);
});

test("cross-field不整合やDB 0行を成功にしない", async () => {
  await assert.rejects(upsertAcceptedTalkTimeline({ ...timeline, tenant_id: "tenant-b" }, { query: async () => ({ rows: [] }) }), /invalid/i);
  await assert.rejects(upsertAcceptedTalkTimeline(timeline, { query: async () => ({ rows: [] }) }), /conflict/i);
});
