"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { validateTalkApplicationTransition } = require("./talk-application-transition.js");
const {
  buildTalkApplicationTransitionRecord,
  createTalkApplicationTransitionStore,
} = require("./talk-application-transition-store.js");

const TENANT_ID = "dais-local";
const PARTICIPATION_ID = "event-participation:" + "a".repeat(64);

function verifiedTransition(overrides = {}) {
  return validateTalkApplicationTransition({
    to_state: "accepted",
    evidence_excerpt: "登壇応募を採択しました。",
    reason: "主催者の通知で登壇採択が確認できたため",
    source_refs: ["mail-receipt://connector/talk-decision/receipt-1"],
    ...(overrides.decision || {}),
  }, {
    currentState: "submitted",
    observedAt: "2026-08-02T02:00:00.000Z",
    now: "2026-08-02T02:01:00.000Z",
    sourceText: "登壇応募を採択しました。イベント当日の登壇をお願いします。",
    sourceRefs: ["mail-receipt://connector/talk-decision/receipt-1"],
    ...(overrides.input || {}),
  });
}

test("verified transition becomes one stable reference-only ledger record", () => {
  const transition = verifiedTransition();
  const one = buildTalkApplicationTransitionRecord({ tenantId: TENANT_ID, participationId: PARTICIPATION_ID, transition });
  const two = buildTalkApplicationTransitionRecord({ tenantId: TENANT_ID, participationId: PARTICIPATION_ID, transition });
  assert.deepEqual(one, two);
  assert.match(one.transition_id, /^talk-transition:[0-9a-f]{64}$/);
  assert.deepEqual(one, {
    transition_id: one.transition_id,
    tenant_id: TENANT_ID,
    participation_id: PARTICIPATION_ID,
    from_state: "submitted",
    to_state: "accepted",
    observed_at: "2026-08-02T02:00:00.000Z",
    reason: "主催者の通知で登壇採択が確認できたため",
    source_refs: ["mail-receipt://connector/talk-decision/receipt-1"],
  });
  assert.equal(Object.isFrozen(one), true);
  assert.doesNotMatch(JSON.stringify(one), /登壇応募を採択しました|@|password|cookie|guest.?key/i);
});

test("plain transition copies and malformed scope cannot build records", () => {
  const transition = verifiedTransition();
  for (const input of [
    { tenantId: TENANT_ID, participationId: PARTICIPATION_ID, transition: structuredClone(transition) },
    { tenantId: "dais@example.com", participationId: PARTICIPATION_ID, transition },
    { tenantId: TENANT_ID, participationId: "event-participation:bad", transition },
  ]) assert.throws(() => buildTalkApplicationTransitionRecord(input), /talk transition record invalid/i);
});

test("store locks the same tenant talk row, appends once, and verifies current-state projection", async () => {
  const record = buildTalkApplicationTransitionRecord({ tenantId: TENANT_ID, participationId: PARTICIPATION_ID, transition: verifiedTransition() });
  const calls = [];
  let state = "submitted";
  let released = 0;
  const store = createTalkApplicationTransitionStore({ async connect() { return {
    async query(sql) {
      calls.push(sql);
      if (/FROM public\.lm_event_participations/.test(sql)) return { rows: [{ tenant_id: TENANT_ID, participation_id: PARTICIPATION_ID, kind: "talk_application", state }] };
      if (/FROM public\.lm_talk_application_transitions/.test(sql)) return { rows: [] };
      if (/INSERT INTO public\.lm_talk_application_transitions/.test(sql)) { state = "accepted"; return { rows: [{ ...record }] }; }
      return { rows: [] };
    },
    release() { released += 1; },
  }; } });
  assert.deepEqual(await store.append(record), record);
  assert.match(calls[0], /BEGIN/);
  assert.match(calls[1], /FOR UPDATE/);
  assert.match(calls[2], /lm_talk_application_transitions/);
  assert.match(calls[3], /INSERT INTO/);
  assert.match(calls[4], /lm_event_participations/);
  assert.match(calls.at(-1), /COMMIT/);
  assert.equal(released, 1);
});

test("an exact retry is idempotent even after the application advances further", async () => {
  const record = buildTalkApplicationTransitionRecord({ tenantId: TENANT_ID, participationId: PARTICIPATION_ID, transition: verifiedTransition() });
  let inserts = 0;
  const store = createTalkApplicationTransitionStore({ async connect() { return {
    async query(sql) {
      if (/FROM public\.lm_event_participations/.test(sql)) return { rows: [{ tenant_id: TENANT_ID, participation_id: PARTICIPATION_ID, kind: "talk_application", state: "presented" }] };
      if (/FROM public\.lm_talk_application_transitions/.test(sql)) return { rows: [{ ...record }] };
      if (/INSERT INTO/.test(sql)) inserts += 1;
      return { rows: [] };
    }, release() {},
  }; } });
  assert.deepEqual(await store.append(record), record);
  assert.equal(inserts, 0);
});

test("cross-tenant, stale-state, audience, and transition ID collisions roll back", async () => {
  const record = buildTalkApplicationTransitionRecord({ tenantId: TENANT_ID, participationId: PARTICIPATION_ID, transition: verifiedTransition() });
  for (const scenario of ["missing", "stale", "audience", "collision"]) {
    const calls = [];
    const store = createTalkApplicationTransitionStore({ async connect() { return {
      async query(sql) {
        calls.push(sql);
        if (/FROM public\.lm_event_participations/.test(sql)) {
          if (scenario === "missing") return { rows: [] };
          return { rows: [{ tenant_id: TENANT_ID, participation_id: PARTICIPATION_ID, kind: scenario === "audience" ? "audience_registration" : "talk_application", state: scenario === "stale" ? "discovered" : "submitted" }] };
        }
        if (/FROM public\.lm_talk_application_transitions/.test(sql)) return { rows: scenario === "collision" ? [{ ...record, reason: "different" }] : [] };
        return { rows: [] };
      }, release() {},
    }; } });
    await assert.rejects(store.append(record), /talk transition store unavailable/i);
    assert.match(calls.at(-1), /ROLLBACK/);
  }
});

test("migration enforces the graph, atomic projection, tenant boundary, and immutable rows", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-02-lm-talk-application-transitions.sql"), "utf8");
  for (const required of [
    "lm_talk_application_transitions",
    "FOREIGN KEY \\(participation_id, tenant_id\\)",
    "submission_queued",
    "submitted",
    "accepted",
    "rejected",
    "presented",
    "FOR UPDATE",
    "talk_application",
    "UPDATE public.lm_event_participations",
    "UPDATE OR DELETE",
    "immutable",
    "ENABLE ROW LEVEL SECURITY",
  ]) assert.match(sql, new RegExp(required, "i"));
  assert.doesNotMatch(sql, /email|phone|password|cookie|guest_key|mail_body/i);
});
