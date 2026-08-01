"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { validateEventTalkOpportunity } = require("./event-talk-opportunity.js");
const {
  buildEventParticipationEntities,
  createEventParticipationStore,
} = require("./event-participation-entities.js");

const SOURCE = Object.freeze({
  canonicalUrl: "https://lu.ma/tokyo-builders-night",
  title: "Tokyo Builders Night",
  body: "一般参加を受付中です。5分LTもこちらのフォームから募集中: https://forms.example.com/talk",
  now: "2026-08-01T16:00:00.000Z",
});

const BASE = Object.freeze({
  tenantId: "dais",
  eventUrl: SOURCE.canonicalUrl,
  eventStartIso: "2026-08-08T10:00:00.000Z",
  evidenceRef: "evidence://event/luma/tokyo-builders-night/inspection-1",
});

function decision(overrides = {}) {
  return validateEventTalkOpportunity({
    participation_kind: "both",
    talk_format: "lightning_talk",
    application_status: "open",
    should_create_talk_application: true,
    application_url: "https://forms.example.com/talk",
    evidence_excerpt: "5分LTもこちらのフォームから募集中: https://forms.example.com/talk",
    reason: "一般参加と公開LT応募の両方がある",
    ...overrides,
  }, SOURCE);
}

test("both event becomes two immutable entities with distinct IDs, actions, and state machines", () => {
  const entities = buildEventParticipationEntities({ ...BASE, opportunity: decision() });
  assert.equal(entities.length, 2);
  const audience = entities.find((row) => row.kind === "audience_registration");
  const talk = entities.find((row) => row.kind === "talk_application");
  assert.ok(audience);
  assert.ok(talk);
  assert.notEqual(audience.participation_id, talk.participation_id);
  assert.equal(audience.action_ref, "https://lu.ma/tokyo-builders-night");
  assert.equal(audience.state, "discovered");
  assert.equal(audience.availability, null);
  assert.equal(audience.talk_format, null);
  assert.equal(talk.action_ref, "https://forms.example.com/talk");
  assert.equal(talk.state, "discovered");
  assert.equal(talk.availability, "open");
  assert.equal(talk.talk_format, "lightning_talk");
  assert.equal(Object.isFrozen(audience), true);
  assert.equal(Object.isFrozen(talk), true);
  assert.doesNotMatch(JSON.stringify(entities), /@|gmail|cookie|password|080-\d/i);
});

test("audience-only and talk-only discoveries never invent the other entity", () => {
  const audienceDecision = validateEventTalkOpportunity({
    participation_kind: "audience_only",
    talk_format: null,
    application_status: "not_offered",
    should_create_talk_application: false,
    application_url: null,
    evidence_excerpt: "一般参加を受付中です。",
    reason: "一般参加だけ",
  }, SOURCE);
  assert.deepEqual(
    buildEventParticipationEntities({ ...BASE, opportunity: audienceDecision }).map((x) => x.kind),
    ["audience_registration"],
  );

  const talkSource = { ...SOURCE, body: "登壇者限定。LT公募は終了しました。" };
  const talkDecision = validateEventTalkOpportunity({
    participation_kind: "talk_application",
    talk_format: "lightning_talk",
    application_status: "closed",
    should_create_talk_application: false,
    application_url: null,
    evidence_excerpt: "LT公募は終了しました。",
    reason: "登壇枠は存在するが締切済み",
  }, talkSource);
  const rows = buildEventParticipationEntities({ ...BASE, opportunity: talkDecision });
  assert.equal(rows.length, 1);
  assert.equal(rows[0].kind, "talk_application");
  assert.equal(rows[0].availability, "closed");
  assert.equal(rows[0].action_ref, null);
});

test("only classifier-verified decisions and reference-only inputs can create entities", () => {
  const plain = {
    participation_kind: "both",
    talk_format: "lightning_talk",
    application_status: "open",
    should_create_talk_application: true,
    application_url: "https://forms.example.com/talk",
  };
  assert.throws(
    () => buildEventParticipationEntities({ ...BASE, opportunity: plain }),
    /verified opportunity/i,
  );
  for (const override of [
    { tenantId: "dais@example.com" },
    { eventUrl: "https://example.com/not-an-event" },
    { eventStartIso: "next week" },
    { evidenceRef: "/Users/anicca/raw-page.html" },
  ]) {
    assert.throws(
      () => buildEventParticipationEntities({ ...BASE, ...override, opportunity: decision() }),
      /participation/i,
    );
  }
});

test("store inserts both entities atomically and returns tenant-scoped rows", async () => {
  const calls = [];
  const entities = buildEventParticipationEntities({ ...BASE, opportunity: decision() });
  const store = createEventParticipationStore({
    async query(sql, params = []) {
      calls.push({ sql, params });
      if (/INSERT INTO/.test(sql)) return { rows: JSON.parse(params[0]) };
      return { rows: [] };
    },
  });
  const saved = await store.saveDiscovered(entities);
  assert.deepEqual(saved, entities);
  assert.match(calls[0].sql, /BEGIN/);
  assert.match(calls[1].sql, /INSERT INTO public\.lm_event_participations/);
  assert.match(calls.at(-1).sql, /COMMIT/);
  assert.equal(calls[1].params[1], "dais");
});

test("store rolls back a cross-tenant or partial insert instead of splitting a both event", async () => {
  const calls = [];
  const entities = buildEventParticipationEntities({ ...BASE, opportunity: decision() });
  const store = createEventParticipationStore({
    async query(sql) {
      calls.push(sql);
      if (/INSERT INTO/.test(sql)) throw new Error("tenant collision");
      return { rows: [] };
    },
  });
  await assert.rejects(store.saveDiscovered(entities), /participation store unavailable/i);
  assert.match(calls.at(-1), /ROLLBACK/);
});

test("production transaction leases one database client through commit and releases it", async () => {
  const calls = [];
  let released = 0;
  const entities = buildEventParticipationEntities({ ...BASE, opportunity: decision() });
  const store = createEventParticipationStore({
    async connect() {
      return {
        async query(sql, params = []) {
          calls.push(sql);
          if (/INSERT INTO/.test(sql)) return { rows: JSON.parse(params[0]) };
          return { rows: [] };
        },
        release() { released += 1; },
      };
    },
  });
  await store.saveDiscovered(entities);
  assert.deepEqual(calls.map((sql) => sql.trim().split(/\s+/)[0]), ["BEGIN", "INSERT", "COMMIT"]);
  assert.equal(released, 1);
});

test("migration enforces the two disjoint state machines without raw identity columns", () => {
  const sql = fs.readFileSync(
    path.join(__dirname, "../migrations/2026-08-01-lm-event-participations.sql"),
    "utf8",
  );
  for (const required of [
    "audience_registration",
    "talk_application",
    "registration_queued",
    "submission_queued",
    "registered",
    "submitted",
    "accepted",
    "rejected",
    "presented",
    "ENABLE ROW LEVEL SECURITY",
  ]) assert.match(sql, new RegExp(required));
  assert.doesNotMatch(sql, /email|phone|password|cookie|form_answer/i);
});
