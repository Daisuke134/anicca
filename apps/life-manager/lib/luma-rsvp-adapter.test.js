"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const test = require("node:test");

const { buildEventApplicationJob } = require("./outbound-event-job.js");
const { assertVerifiedOutboundReceipt } = require("./outbound-success.js");
const {
  createLumaRsvpLoopAdapter,
} = require("./luma-rsvp-adapter.js");

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function claimedJob(overrides = {}) {
  return {
    ...buildEventApplicationJob({
      tenantId: "dais-local",
      eventUrl: "https://luma.com/tokyo-agent-night",
      eventStartIso: "2026-08-04T19:00:00+09:00",
      identityRef: "identity://dais-local/luma",
      browserProfileRef: "browser-profile://cloakbrowser/daily-driver",
      calendarRef: "calendar://google/primary",
    }),
    attempt: 1,
    ...overrides,
  };
}

function evidenceFixture() {
  const bytes = Buffer.alloc(5000, 0x61);
  PNG_SIGNATURE.copy(bytes, 0);
  const hash = createHash("sha256").update(bytes).digest("hex");
  return {
    result: {
      external_receipt_ref: "provider-receipt://luma/guest-123",
      artifact_ref: `object://sha256/${hash}`,
      canonical_url: "https://luma.com/tokyo-agent-night",
    },
    services: {
      async readExternalReceipt(tenantId, ref) {
        assert.equal(tenantId, "dais-local");
        assert.equal(ref, "provider-receipt://luma/guest-123");
        return {
          kind: "provider_response",
          provider_id: "guest-123",
          observed_at: "2026-08-01T10:00:00.000Z",
        };
      },
      async readArtifact(tenantId, ref) {
        assert.equal(tenantId, "dais-local");
        assert.equal(ref, `object://sha256/${hash}`);
        return bytes;
      },
      async fetchImpl(url, options) {
        assert.equal(url, "https://luma.com/tokyo-agent-night");
        assert.equal(options.method, "HEAD");
        assert.equal(options.redirect, "manual");
        return { status: 200 };
      },
    },
  };
}

test("checks the effect fence before one submit and returns verifier-bound receipt", async () => {
  const job = claimedJob();
  const evidence = evidenceFixture();
  const calls = [];
  const adapter = createLumaRsvpLoopAdapter({
    provider: {
      async inspectRegistration(input) {
        calls.push(["inspect", input.event_ref]);
        return { state: "absent" };
      },
      async submitRegistration(input) {
        calls.push(["submit", input.event_ref]);
        return evidence.result;
      },
    },
    ...evidence.services,
    now: () => "2026-08-01T10:00:01.000Z",
  });

  const execution = await adapter.execute(job);

  assert.deepEqual(calls, [
    ["inspect", "luma-event://event/tokyo-agent-night"],
    ["submit", "luma-event://event/tokyo-agent-night"],
  ]);
  assert.equal(execution.effect_started, true);
  assert.equal(execution.receipt.status, "verified");
  assert.equal(assertVerifiedOutboundReceipt(execution.receipt, job), execution.receipt);
});

test("a pre-existing provider registration is verified without submitting again", async () => {
  const job = claimedJob();
  const evidence = evidenceFixture();
  let submits = 0;
  const adapter = createLumaRsvpLoopAdapter({
    provider: {
      async inspectRegistration() {
        return { state: "registered", ...evidence.result };
      },
      async submitRegistration() {
        submits += 1;
      },
    },
    ...evidence.services,
  });

  const execution = await adapter.execute(job);
  assert.equal(submits, 0);
  assert.equal(execution.effect_started, false);
  assert.equal(assertVerifiedOutboundReceipt(execution.receipt, job), execution.receipt);
});

test("login_required stops before submit and is not mislabeled as success", async () => {
  let submits = 0;
  const adapter = createLumaRsvpLoopAdapter({
    provider: {
      async inspectRegistration() {
        return { state: "login_required" };
      },
      async submitRegistration() {
        submits += 1;
      },
    },
  });

  await assert.rejects(
    adapter.execute(claimedJob()),
    (error) => {
      assert.equal(error.code, "LUMA_LOGIN_REQUIRED");
      assert.equal(error.unknownEffect, false);
      return true;
    },
  );
  assert.equal(submits, 0);
});

test("provider unavailability and known pre-submit failure remain retryable without a false effect", async () => {
  const unavailable = createLumaRsvpLoopAdapter({
    provider: {
      async inspectRegistration() { return { state: "unavailable", reason: "full" }; },
      async submitRegistration() { throw new Error("must not submit"); },
    },
  });
  await assert.rejects(unavailable.execute(claimedJob()), (error) => {
    assert.equal(error.code, "LUMA_RSVP_UNAVAILABLE");
    assert.equal(error.unknownEffect, false);
    return true;
  });

  const known = createLumaRsvpLoopAdapter({
    provider: {
      async inspectRegistration() { return { state: "absent" }; },
      async submitRegistration() {
        const error = new Error("form needs agent input");
        error.unknownEffect = false;
        throw error;
      },
    },
  });
  await assert.rejects(known.execute(claimedJob()), (error) => {
    assert.equal(error.unknownEffect, false);
    return true;
  });
});

test("submit errors and post-submit evidence gaps become unknown effects", async () => {
  const thrown = createLumaRsvpLoopAdapter({
    provider: {
      async inspectRegistration() { return { state: "absent" }; },
      async submitRegistration() { throw new Error("provider disconnected"); },
    },
  });
  await assert.rejects(thrown.execute(claimedJob()), (error) => {
    assert.equal(error.unknownEffect, true);
    return true;
  });

  const evidence = evidenceFixture();
  const missingArtifact = createLumaRsvpLoopAdapter({
    provider: {
      async inspectRegistration() { return { state: "absent" }; },
      async submitRegistration() { return evidence.result; },
    },
    ...evidence.services,
    readArtifact: async () => null,
  });
  await assert.rejects(missingArtifact.execute(claimedJob()), (error) => {
    assert.equal(error.unknownEffect, true);
    return true;
  });
});

test("adapter exposes the full runtime contract and plans the existing durable job", async () => {
  const adapter = createLumaRsvpLoopAdapter({});
  for (const method of ["plan", "execute", "reconcile", "verify", "report"]) {
    assert.equal(typeof adapter[method], "function");
  }
  const jobs = await adapter.plan({
    tenantId: "dais-local",
    eventUrl: "https://luma.com/tokyo-agent-night",
    eventStartIso: "2026-08-04T19:00:00+09:00",
    identityRef: "identity://dais-local/luma",
    browserProfileRef: "browser-profile://cloakbrowser/daily-driver",
    calendarRef: "calendar://google/primary",
  });
  assert.equal(jobs.length, 1);
  assert.equal(jobs[0].capability, "outbound.event.apply");
});
