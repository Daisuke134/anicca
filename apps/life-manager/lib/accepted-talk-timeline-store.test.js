"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { validateAcceptedTalkTimeline } = require("./accepted-talk-timeline.js");
const { buildTalkTimelineSnapshot, createAcceptedTalkTimelineStore } = require("./accepted-talk-timeline-store.js");

const TENANT_ID = "dais-local";
const PARTICIPATION_ID = "event-participation:" + "a".repeat(64);

function verifiedTimeline() {
  const sourceRefs = ["evidence://connector/acceptance", "object://sha256/" + "b".repeat(64)];
  return validateAcceptedTalkTimeline({
    slide_status: "known", slide_due_at: "2026-08-05T09:00:00.000Z",
    slide_evidence_excerpt: "スライドは8月5日18時まで",
    venue_status: "known", venue_name: "Tokyo Hall", venue_address: "東京都港区1-2-3",
    venue_evidence_excerpt: "会場はTokyo Hall、東京都港区1-2-3です",
    ticket_requirement: "required", follow_up_at: "2026-08-05T10:00:00.000Z",
    follow_up_purpose: "スライド受領確認", follow_up_reason: "提出後の受領状態を確認するため",
    follow_up_evidence_excerpt: "スライドは8月5日18時まで", source_refs: sourceRefs,
  }, {
    acceptedAt: "2026-08-02T00:30:00.000Z", eventStartAt: "2026-08-07T10:00:00.000Z",
    eventEndAt: "2026-08-07T13:00:00.000Z", ticketRef: "object://sha256/" + "b".repeat(64),
    sourceRefs, sourceText: "登壇採択です。スライドは8月5日18時まで。会場はTokyo Hall、東京都港区1-2-3です。",
    now: "2026-08-02T01:00:00.000Z",
  });
}

test("verified timeline becomes one stable reference-only snapshot", () => {
  const timeline = verifiedTimeline();
  const one = buildTalkTimelineSnapshot({ tenantId: TENANT_ID, participationId: PARTICIPATION_ID, timeline });
  const two = buildTalkTimelineSnapshot({ tenantId: TENANT_ID, participationId: PARTICIPATION_ID, timeline });
  assert.deepEqual(one, two);
  assert.match(one.snapshot_id, /^talk-timeline:[0-9a-f]{64}$/);
  assert.equal(one.tenant_id, TENANT_ID);
  assert.equal(one.participation_id, PARTICIPATION_ID);
  assert.equal(one.ticket_ref, "object://sha256/" + "b".repeat(64));
  assert.equal(Object.isFrozen(one), true);
  assert.doesNotMatch(JSON.stringify(one), /登壇採択|@|password|cookie|guest.?key/i);
});

test("plain copied timeline, invalid tenant, and invalid participation fail closed", () => {
  const timeline = verifiedTimeline();
  for (const input of [
    { tenantId: TENANT_ID, participationId: PARTICIPATION_ID, timeline: structuredClone(timeline) },
    { tenantId: "dais@example.com", participationId: PARTICIPATION_ID, timeline },
    { tenantId: TENANT_ID, participationId: "event-participation:bad", timeline },
  ]) assert.throws(() => buildTalkTimelineSnapshot(input), /talk timeline snapshot/i);
});

test("store gates on the same tenant accepted talk row and commits one snapshot", async () => {
  const snapshot = buildTalkTimelineSnapshot({ tenantId: TENANT_ID, participationId: PARTICIPATION_ID, timeline: verifiedTimeline() });
  const calls = [];
  let released = 0;
  const store = createAcceptedTalkTimelineStore({ async connect() { return {
    async query(sql, params = []) {
      calls.push({ sql, params });
      if (/FROM public\.lm_event_participations/.test(sql)) return { rows: [{ participation_id: PARTICIPATION_ID, tenant_id: TENANT_ID, kind: "talk_application", state: "accepted" }] };
      if (/INSERT INTO public\.lm_talk_timeline_snapshots/.test(sql)) return { rows: [{ ...snapshot }] };
      return { rows: [] };
    }, release() { released += 1; },
  }; } });
  assert.deepEqual(await store.save(snapshot), snapshot);
  assert.match(calls[0].sql, /BEGIN/);
  assert.match(calls[1].sql, /FOR SHARE/);
  assert.match(calls[2].sql, /ON CONFLICT \(snapshot_id\) DO NOTHING/);
  assert.match(calls.at(-1).sql, /COMMIT/);
  assert.equal(released, 1);
});

test("idempotent retry reads the identical row but collisions and non-accepted entities roll back", async () => {
  const snapshot = buildTalkTimelineSnapshot({ tenantId: TENANT_ID, participationId: PARTICIPATION_ID, timeline: verifiedTimeline() });
  for (const scenario of ["wrong-state", "collision"]) {
    const calls = [];
    const store = createAcceptedTalkTimelineStore({ async connect() { return {
      async query(sql) {
        calls.push(sql);
        if (/FROM public\.lm_event_participations/.test(sql)) return { rows: [{ participation_id: PARTICIPATION_ID, tenant_id: TENANT_ID, kind: "talk_application", state: scenario === "wrong-state" ? "submitted" : "accepted" }] };
        if (/INSERT INTO public\.lm_talk_timeline_snapshots/.test(sql)) return { rows: [] };
        if (/FROM public\.lm_talk_timeline_snapshots/.test(sql)) return { rows: [{ ...snapshot, venue_name: "invented" }] };
        return { rows: [] };
      }, release() {},
    }; } });
    await assert.rejects(store.save(snapshot), /talk timeline store unavailable/i);
    assert.match(calls.at(-1), /ROLLBACK/);
  }
  const store = createAcceptedTalkTimelineStore({ async connect() { return {
    async query(sql) {
      if (/FROM public\.lm_event_participations/.test(sql)) return { rows: [{ participation_id: PARTICIPATION_ID, tenant_id: TENANT_ID, kind: "talk_application", state: "accepted" }] };
      if (/INSERT INTO public\.lm_talk_timeline_snapshots/.test(sql)) return { rows: [] };
      if (/FROM public\.lm_talk_timeline_snapshots/.test(sql)) return { rows: [{ ...snapshot }] };
      return { rows: [] };
    }, release() {},
  }; } });
  assert.deepEqual(await store.save(snapshot), snapshot);
});

test("migration enforces immutable tenant-bound snapshots and exposes a current view", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-02-lm-talk-timeline-snapshots.sql"), "utf8");
  for (const required of ["lm_talk_timeline_snapshots", "lm_talk_timeline_current", "FOREIGN KEY (participation_id, tenant_id)", "talk_application", "accepted", "UPDATE OR DELETE", "immutable", "ENABLE ROW LEVEL SECURITY"]) assert.match(sql, new RegExp(required, "i"));
  assert.doesNotMatch(sql, /email|phone|password|cookie|guest_key|mail_body/i);
});
