"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  CAPABILITY,
  LOOP_ID,
  buildEventApplicationJob,
  enqueueEventApplication,
} = require("./outbound-event-job.js");

const BASE = Object.freeze({
  tenantId: "dais",
  eventUrl: "https://lu.ma/tokyo-founders-2026",
  eventStartIso: "2026-08-04T10:00:00.000Z",
  identityRef: "identity://dais/default",
  browserProfileRef: "browser-profile://cloakbrowser/daily-driver",
  calendarRef: "calendar://google/primary",
});

test("builds one reference-only durable job for a Luma registration", () => {
  const job = buildEventApplicationJob(BASE);

  assert.equal(CAPABILITY, "outbound.event.apply");
  assert.equal(LOOP_ID, "outbound.events");
  assert.equal(job.tenant_id, "dais");
  assert.equal(job.loop_id, LOOP_ID);
  assert.equal(job.capability, CAPABILITY);
  assert.equal(job.effect_class, "publish");
  assert.match(job.job_id, /^outbound-event:[0-9a-f]{64}$/);
  assert.match(
    job.effect_key,
    /^event-application:luma:tokyo-founders-2026:[0-9a-f]{64}$/,
  );
  assert.deepEqual(job.input_refs, {
    event_ref: "luma-event://event/tokyo-founders-2026?starts_at=2026-08-04T10%3A00%3A00.000Z",
    identity_ref: "identity://dais/default",
    browser_profile_ref: "browser-profile://cloakbrowser/daily-driver",
    calendar_ref: "calendar://google/primary",
  });
  assert.equal(job.max_attempts, 5);
  assert.doesNotMatch(JSON.stringify(job), /keiodaisuke|password|cookie|@gmail/i);
});

test("same tenant, event, identity, and start time produce the same idempotency keys", () => {
  const first = buildEventApplicationJob(BASE);
  const second = buildEventApplicationJob({
    ...BASE,
    eventUrl: "https://luma.com/tokyo-founders-2026?utm_source=test",
  });
  assert.equal(first.job_id, second.job_id);
  assert.equal(first.effect_key, second.effect_key);

  const differentEvent = buildEventApplicationJob({
    ...BASE,
    eventUrl: "https://luma.com/web3-builders-tokyo",
  });
  assert.notEqual(first.job_id, differentEvent.job_id);
  assert.notEqual(first.effect_key, differentEvent.effect_key);
});

test("rejects non-Luma targets, malformed times, and raw identity data", () => {
  assert.throws(
    () => buildEventApplicationJob({ ...BASE, eventUrl: "https://example.com/event" }),
    /Luma event URL/i,
  );
  assert.throws(
    () => buildEventApplicationJob({ ...BASE, eventStartIso: "next Tuesday" }),
    /event start/i,
  );
  assert.throws(
    () => buildEventApplicationJob({ ...BASE, identityRef: "keiodaisuke@gmail.com" }),
    /identity reference/i,
  );
  assert.throws(
    () => buildEventApplicationJob({ ...BASE, browserProfileRef: "/Users/anicca/profile" }),
    /browser profile reference/i,
  );
});

test("enqueue delegates the exact built job to the existing runtime store", async () => {
  const calls = [];
  const result = await enqueueEventApplication(BASE, { query: async () => ({ rows: [] }) }, {
    enqueueJob: async (job, storeOptions) => {
      calls.push({ job, storeOptions });
      return { created: true, job: { ...job, status: "queued" } };
    },
  });

  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].job, buildEventApplicationJob(BASE));
  assert.equal(typeof calls[0].storeOptions.query, "function");
  assert.equal(result.created, true);
  assert.equal(result.job.status, "queued");
});
