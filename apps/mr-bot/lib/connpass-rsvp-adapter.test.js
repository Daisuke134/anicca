"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildConnpassEventApplicationJob, executeConnpassRsvpJob,
} = require("./connpass-rsvp-adapter.js");

const INPUT = {
  tenantId: "dais-local",
  eventUrl: "https://tokyo-builders.connpass.com/event/101/",
  eventStartIso: "2026-08-05T19:00:00+09:00",
  identityRef: "identity://dais-local/connpass",
  browserProfileRef: "browser-profile://cloakbrowser/daily-driver",
  calendarRef: "calendar://google/primary",
};

test("builds one deterministic Connpass-only publish job", () => {
  const job = buildConnpassEventApplicationJob(INPUT);
  assert.match(job.job_id, /^outbound-event:[0-9a-f]{64}$/);
  assert.match(job.effect_key, /^event-application:connpass:101:[0-9a-f]{64}$/);
  assert.equal(job.input_refs.event_ref.startsWith("connpass-event://event/101?starts_at="), true);
  assert.equal(job.input_refs.canonical_url_ref, INPUT.eventUrl);
  assert.equal(JSON.stringify(job).includes("cookie"), false);
});

test("executes parent provider readback then returns only verifier-produced evidence", async () => {
  const job = { ...buildConnpassEventApplicationJob(INPUT), attempt: 1 };
  const calls = [];
  const png = Buffer.alloc(5_000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const crypto = require("node:crypto");
  const sha = crypto.createHash("sha256").update(png).digest("hex");
  const result = await executeConnpassRsvpJob(job, {
    provider: {
      async inspectRegistration(contract) { calls.push(["inspect", contract]); return { state: "absent" }; },
      async submitRegistration(contract) {
        calls.push(["submit", contract]);
        return {
          state: "registered", registration_status: "registered",
          external_receipt_ref: "provider-receipt://connpass/proof-101",
          artifact_ref: `object://sha256/${sha}`, canonical_url: INPUT.eventUrl,
        };
      },
    },
    async readExternalReceipt() {
      return { kind: "provider_response", provider_id: "proof-101", observed_at: "2026-08-06T01:02:03.000Z" };
    },
    async readArtifact() { return png; },
    async fetchImpl() { return { status: 200 }; },
    now: () => "2026-08-06T01:02:03.000Z",
  });
  assert.equal(result.receipt.status, "verified");
  assert.equal(result.receipt.canonical_url, INPUT.eventUrl);
  assert.deepEqual(calls.map(([name]) => name), ["inspect", "submit"]);
});

test("unknown parent readback never submits and click uncertainty propagates", async () => {
  const job = { ...buildConnpassEventApplicationJob(INPUT), attempt: 1 };
  let submits = 0;
  await assert.rejects(executeConnpassRsvpJob(job, {
    provider: {
      async inspectRegistration() { return { state: "unknown" }; },
      async submitRegistration() { submits += 1; },
    },
  }), (error) => { assert.equal(error.unknownEffect, true); return true; });
  assert.equal(submits, 0);
});
