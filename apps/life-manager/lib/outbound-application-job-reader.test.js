"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { buildEventApplicationJob } = require("./outbound-event-job.js");
const { createOutboundApplicationJobReader } = require("./outbound-application-job-reader.js");

function job() {
  return buildEventApplicationJob({
    tenantId: "dais-local",
    eventUrl: "https://luma.com/founder-night",
    eventStartIso: "2026-08-05T19:00:00+09:00",
    identityRef: "identity://dais-local/luma",
    browserProfileRef: "browser-profile://cloakbrowser/daily-driver",
    calendarRef: "calendar://google/primary",
  });
}

test("reads only the exact tenant-bound application job state", async () => {
  const expected = job();
  const calls = [];
  const reader = createOutboundApplicationJobReader({
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [{ ...expected, status: "queued" }] };
    },
  });
  assert.deepEqual(await reader.read(expected), { status: "queued" });
  assert.deepEqual(calls[0].params, [expected.job_id, "dais-local"]);
  assert.match(calls[0].sql, /WHERE job_id = \$1 AND tenant_id = \$2/);
});
test("missing is null while collisions, malformed status, and multiple rows fail closed", async () => {
  const expected = job();
  assert.equal(await createOutboundApplicationJobReader({
    async query() { return { rows: [] }; },
  }).read(expected), null);
  const rows = [
    [{ ...expected, effect_key: "different", status: "queued" }],
    [{ ...expected, status: "retry" }],
    [{ ...expected, status: "queued" }, { ...expected, status: "queued" }],
  ];
  for (const value of rows) {
    const reader = createOutboundApplicationJobReader({ async query() { return { rows: value }; } });
    await assert.rejects(reader.read(expected), /outbound application job reader unavailable/i);
  }
});
