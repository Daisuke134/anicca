"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const {
  buildEventParticipationEntities,
  transitionEventEntity,
} = require("./event-participation-entity.js");
const {
  transitionStoredEventEntity,
  upsertDiscoveredEventEntities,
} = require("./event-participation-store.js");

const SQL = fs.readFileSync(path.join(
  __dirname,
  "../migrations/2026-08-02-lm-event-participation-entities.sql",
), "utf8");

function entities() {
  return buildEventParticipationEntities({
    tenantId: "dais-local",
    eventRef: "luma-event://event/agent-night",
    canonicalUrl: "https://luma.com/agent-night",
    startsAt: "2026-08-10T10:00:00.000Z",
    decision: {
      participation_kind: "both",
      talk_format: "lightning_talk",
      application_status: "open",
      should_create_talk_application: true,
      application_url: "https://forms.example.com/speaker",
    },
  });
}

test("migrationはtenant-bound current entityとappend-only transitionをservice-onlyで作る", () => {
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_event_participation_entities/i);
  assert.match(SQL, /PRIMARY KEY \(tenant_id, entity_id\)/i);
  assert.match(SQL, /entity_kind text NOT NULL CHECK \(entity_kind IN \('audience_registration', 'talk_application'\)\)/i);
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_event_participation_transitions/i);
  assert.match(SQL, /UNIQUE \(tenant_id, entity_id, version\)/i);
  assert.match(SQL, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(SQL, /REVOKE ALL .* FROM PUBLIC/i);
  assert.doesNotMatch(SQL, /GRANT .* TO (?:anon|authenticated)/i);
});

test("discoveryは別entityを同じevent refでidempotent upsertする", async () => {
  const calls = [];
  const saved = await upsertDiscoveredEventEntities(entities(), {
    query: async (sql, params) => {
      calls.push({ sql, params });
      return { rows: [{ entity_id: params[1], inserted: true }] };
    },
  });

  assert.equal(saved.length, 2);
  assert.equal(calls.length, 2);
  assert.equal(calls.every(({ sql }) => /ON CONFLICT \(tenant_id, entity_id\) DO NOTHING/i.test(sql)), true);
  assert.equal(calls[0].params[0], "dais-local");
  assert.equal(calls[0].params[3], "audience_registration");
  assert.equal(calls[1].params[3], "talk_application");
  assert.equal(calls[0].params[2], calls[1].params[2]);
});

test("transition storeはtenant/kind/from/versionのcompare-and-setと履歴insertを一文で行う", async () => {
  const [audience] = entities();
  const change = transitionEventEntity(audience, "queued", {
    at: "2026-08-02T00:00:00.000Z",
  });
  let call;
  const result = await transitionStoredEventEntity(audience, change, {
    query: async (sql, params) => {
      call = { sql, params };
      return { rows: [{ entity_id: audience.entity_id, status: "queued", version: 2 }] };
    },
  });

  assert.equal(result.status, "queued");
  assert.match(call.sql, /WITH updated AS/i);
  assert.match(call.sql, /INSERT INTO public\.lm_event_participation_transitions/i);
  assert.deepEqual(call.params.slice(0, 7), [
    audience.tenant_id,
    audience.entity_id,
    "audience_registration",
    "discovered",
    1,
    "queued",
    2,
  ]);
});

test("compare-and-setが0行なら競合を成功にしない", async () => {
  const [audience] = entities();
  const change = transitionEventEntity(audience, "queued", {
    at: "2026-08-02T00:00:00.000Z",
  });
  await assert.rejects(
    transitionStoredEventEntity(audience, change, {
      query: async () => ({ rows: [] }),
    }),
    /event entity transition conflict/,
  );
});
