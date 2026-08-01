"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildEventParticipationEntities,
  transitionEventEntity,
} = require("./event-participation-entity.js");

const EVENT = Object.freeze({
  tenantId: "dais-local",
  eventRef: "luma-event://event/agent-night",
  canonicalUrl: "https://luma.com/agent-night",
  startsAt: "2026-08-10T10:00:00.000Z",
});

function decision(overrides = {}) {
  return {
    participation_kind: "both",
    talk_format: "lightning_talk",
    application_status: "open",
    should_create_talk_application: true,
    application_url: "https://forms.example.com/speaker",
    evidence_excerpt: "5分LT登壇者を募集中です。",
    reason: "一般参加と公開LT枠があります。",
    ...overrides,
  };
}

test("bothは同じevent refを共有する別IDのaudienceとtalk entityになる", () => {
  const entities = buildEventParticipationEntities({ ...EVENT, decision: decision() });

  assert.equal(entities.length, 2);
  assert.deepEqual(entities.map(({ kind }) => kind), [
    "audience_registration",
    "talk_application",
  ]);
  assert.equal(new Set(entities.map(({ entity_id }) => entity_id)).size, 2);
  assert.equal(entities.every(({ event_ref }) => event_ref === EVENT.eventRef), true);
  assert.equal(entities.every(({ status }) => status === "discovered"), true);
  assert.equal(entities[1].payload.application_url, "https://forms.example.com/speaker");
  assert.equal(JSON.stringify(entities).includes("5分LT"), false);
});

test("audience-onlyとtalk-onlyは該当entityだけを作り再実行でもstable IDになる", () => {
  const audience = buildEventParticipationEntities({
    ...EVENT,
    decision: decision({
      participation_kind: "audience_only",
      talk_format: null,
      application_status: "not_offered",
      should_create_talk_application: false,
      application_url: null,
    }),
  });
  const talk = buildEventParticipationEntities({
    ...EVENT,
    decision: decision({ participation_kind: "talk_application" }),
  });

  assert.deepEqual(audience.map(({ kind }) => kind), ["audience_registration"]);
  assert.deepEqual(talk.map(({ kind }) => kind), ["talk_application"]);
  assert.equal(
    talk[0].entity_id,
    buildEventParticipationEntities({
      ...EVENT,
      decision: decision({ participation_kind: "talk_application" }),
    })[0].entity_id,
  );
});

test("closed・invite-only・unknownはtalk application entityを作らない", () => {
  for (const patch of [
    { application_status: "closed", should_create_talk_application: false, application_url: null },
    { application_status: "invite_only", should_create_talk_application: false, application_url: null },
    {
      participation_kind: "unknown", talk_format: null, application_status: "unknown",
      should_create_talk_application: false, application_url: null,
    },
  ]) {
    const entities = buildEventParticipationEntities({ ...EVENT, decision: decision(patch) });
    assert.equal(entities.some(({ kind }) => kind === "talk_application"), false);
  }
});

test("kind別status machineはcross-kind遷移とreceiptなし外部成果を拒否する", () => {
  const [audience, talk] = buildEventParticipationEntities({ ...EVENT, decision: decision() });
  const queued = transitionEventEntity(audience, "queued", {
    at: "2026-08-02T00:00:00.000Z",
  });
  assert.equal(queued.entity.status, "queued");
  assert.equal(queued.entity.version, 2);
  assert.throws(
    () => transitionEventEntity(queued.entity, "registered", { at: "2026-08-02T00:01:00.000Z" }),
    /event entity transition invalid/,
  );
  const registered = transitionEventEntity(queued.entity, "registered", {
    at: "2026-08-02T00:01:00.000Z",
    receiptRef: "provider-receipt://luma/guest-1",
  });
  assert.equal(registered.entity.status, "registered");
  assert.equal(registered.transition.receipt_ref, "provider-receipt://luma/guest-1");
  assert.throws(
    () => transitionEventEntity(audience, "submitted", {
      at: "2026-08-02T00:01:00.000Z",
      receiptRef: "provider-receipt://talk/1",
    }),
    /event entity transition invalid/,
  );

  const drafted = transitionEventEntity(talk, "drafted", { at: "2026-08-02T00:00:00.000Z" });
  assert.throws(
    () => transitionEventEntity(drafted.entity, "submitted", { at: "2026-08-02T00:01:00.000Z" }),
    /event entity transition invalid/,
  );
  const submitted = transitionEventEntity(drafted.entity, "submitted", {
    at: "2026-08-02T00:01:00.000Z",
    receiptRef: "provider-receipt://talk/submitted-1",
  });
  assert.throws(
    () => transitionEventEntity(submitted.entity, "rejected", { at: "2026-08-03T00:01:00.000Z" }),
    /event entity transition invalid/,
  );
});
