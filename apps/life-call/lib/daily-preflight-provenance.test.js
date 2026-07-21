"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const {
  buildPreflightReport,
  collectControlledL3,
  collectTelegramControlled,
  sanitizeEvidence,
} = require("./daily-preflight.js");
const { parseArgs } = require("../scripts/daily-preflight.js");

const NOW = Date.parse("2026-07-21T06:00:00Z");
const good = () => ({
  telegram: {
    attempted: true, verified: true, checkedAt: new Date(NOW).toISOString(),
    requestMessageRef: "sha256:111111111111", replyMessageRef: "sha256:222222222222",
    exactUrl: true, allowedUpdates: ["message", "edited_message", "callback_query"],
    providerError: false, pendingUpdateCount: 0, pendingUpdateSamples: [1, 0],
  },
  email: {
    attempted: true, providerAccepted: true, inboxReceived: true, recipientOwned: true,
    checkedAt: new Date(NOW).toISOString(), providerRef: "sha256:333333333333",
    messageIdRef: "sha256:444444444444",
  },
});

test("public CLI rejects caller supplied --proofs", () => {
  assert.throws(() => parseArgs(["--proofs", "/tmp/forged.json"]), /unknown argument/);
});

test("controlled L3 is collected by the runner and bound into the generated report", async () => {
  const results = good();
  const controlledL3 = await collectControlledL3({
    mode: "controlled-l3", nowMs: NOW,
    collectors: { telegram: async () => results.telegram, email: async () => results.email },
  });
  const report = await buildPreflightReport({
    checks: [{ name: "health", run: async () => ({ ok: true, evidence: { healthy: true } }) }],
    controlledL3, timeoutMs: 100, now: () => NOW,
  });
  assert.equal(report.controlledL3.telegram.checkedAt, new Date(NOW).toISOString());
  assert.equal(report.controlledL3.telegram.request_message_ref, "sha256:111111111111");
  assert.equal(report.controlledL3.email.provider_ref, "sha256:333333333333");
  assert.equal(JSON.parse(JSON.stringify(report)).controlledL3.email.message_id_ref, "sha256:444444444444");
});

test("controlled collectors fail closed for missing, malformed, and stale results", async (t) => {
  for (const [name, mutate] of [
    ["missing", (value) => { delete value.email; }],
    ["malformed", (value) => { value.telegram.attempted = "yes"; }],
    ["stale", (value) => { value.email.checkedAt = new Date(NOW - 900001).toISOString(); }],
  ]) await t.test(name, async () => {
    const value = good(); mutate(value);
    await assert.rejects(() => collectControlledL3({
      mode: "controlled-l3", nowMs: NOW,
      collectors: {
        telegram: async () => value.telegram,
        email: async () => value.email,
      },
    }), /collector/);
  });
});

test("email collector requires every same-run acceptance and receipt field", async (t) => {
  for (const field of ["attempted", "providerAccepted", "inboxReceived", "recipientOwned", "providerRef", "messageIdRef"]) {
    await t.test(field, async () => {
      const value = good(); value.email[field] = field.endsWith("Ref") ? "" : false;
      await assert.rejects(() => collectControlledL3({ mode: "controlled-l3", nowMs: NOW, collectors: {
        telegram: async () => value.telegram, email: async () => value.email,
      } }), /email collector/);
    });
  }
});

test("telegram bounded polling must observe the real webhook backlog drain to exactly zero", async (t) => {
  for (const [name, mutate, classification] of [
    ["pending", (v) => { v.pendingUpdateCount = 1; v.pendingUpdateSamples = [1, 1, 1]; }, "telegram_backlog"],
    ["missing", (v) => { v.allowedUpdates = ["message"]; }, "telegram_allowed_updates"],
  ]) await t.test(name, async () => {
    const value = good(); mutate(value.telegram);
    await assert.rejects(() => collectControlledL3({ mode: "controlled-l3", nowMs: NOW, collectors: {
      telegram: async () => value.telegram, email: async () => value.email,
    } }), new RegExp(classification));
  });
  const value = good();
  const result = await collectControlledL3({ mode: "controlled-l3", nowMs: NOW, collectors: {
    telegram: async () => value.telegram, email: async () => value.email,
  } });
  assert.equal(result.telegram.pendingUpdateCount, 0);
  assert.deepEqual(result.telegram.pendingUpdateSamples, [1, 0]);
});

test("telegram collector performs round trip then bounded-polls getWebhookInfo", async () => {
  const samples = [1, 0];
  let roundTrips = 0;
  const value = await collectTelegramControlled({
    roundTrip: async () => { roundTrips += 1; return good().telegram; },
    getWebhookInfo: async () => ({
      pending_update_count: samples.shift(), exactUrl: true,
      allowed_updates: ["message", "edited_message", "callback_query"], providerError: false,
    }),
    now: () => NOW,
  });
  assert.equal(roundTrips, 1);
  assert.deepEqual(value.pendingUpdateSamples, [1, 0]);
  assert.equal(value.pendingUpdateCount, 0);
});

test("final evidence schema replaces unknown strings, URLs, PII, errors, and nested raw text", () => {
  const output = sanitizeEvidence({
    unknown: "Daisuke Anicca", url: "https://opaque.example/private/path?q=token",
    providerError: "card declined for person@example.com", nested: { rawText: "Bearer secret-token" },
    safe: true, count: 3, hash: "sha256:0123456789ab", status: "pass",
  });
  assert.deepEqual(output, {
    unknown: "[REDACTED]", url: "[REDACTED]", providerError: "[REDACTED]",
    nested: { rawText: "[REDACTED]" }, safe: true, count: 3,
    hash: "sha256:0123456789ab", status: "pass",
  });
});
