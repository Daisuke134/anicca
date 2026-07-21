"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");
const {
  buildPreflightReport,
  sanitizeEvidence,
} = require("./daily-preflight.js");
const {
  collectControlledL3ForTest,
  collectTelegramControlledForTest,
} = require("./daily-preflight.test-support.js");
const { main, parseArgs, runCli } = require("../scripts/daily-preflight.js");

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

test("production main has no collector or transport injection parameters", () => {
  const parameters = main.toString().match(/^async function main\(([^)]*)\)/)?.[1] || "";
  assert.doesNotMatch(parameters, /\b(?:collectors?|botCall|mtprotoSend|mtprotoRead|execFileImpl|send|findReceipt|mailFactory|now|randomNonce|sleep|maxPolls)\b/);
});

test("read-only production main invokes zero caller or controlled sends", async () => {
  let invoked = 0;
  const forged = { telegram: async () => { invoked += 1; }, email: async () => { invoked += 1; } };
  const originalWrite = process.stdout.write; let exitCode;
  process.stdout.write = () => true;
  try {
    exitCode = await main({ argv: ["--mode", "read-only", "--timeout-ms", "5"], env: {},
      fetchImpl: async () => { throw new Error("offline fixture"); }, collectors: forged });
  } finally { process.stdout.write = originalWrite; }
  assert.equal(exitCode, 1);
  assert.equal(invoked, 0);
});

test("test-only controlled runner invokes each collector exactly once", async () => {
  const value = good(); let telegramCalls = 0; let emailCalls = 0;
  await collectControlledL3ForTest({ mode: "controlled-l3", nowMs: NOW, collectors: {
    telegram: async () => { telegramCalls += 1; return value.telegram; },
    email: async () => { emailCalls += 1; return value.email; },
  } });
  assert.deepEqual({ telegramCalls, emailCalls }, { telegramCalls: 1, emailCalls: 1 });
});

test("production entrypoint cannot import or activate test-only collector DI", () => {
  const source = fs.readFileSync(path.join(__dirname, "../scripts/daily-preflight.js"), "utf8");
  assert.doesNotMatch(source, /test-support|collectors|proof(?:s|File|_file)/i);
});

test("production controlled collectors expose no factory or transport injection surface", () => {
  const collectorPath = path.join(__dirname, "daily-preflight-collectors.js");
  const collectorSource = fs.readFileSync(collectorPath, "utf8");
  const controlledSource = fs.readFileSync(path.join(__dirname, "daily-preflight.js"), "utf8");
  const cliSource = fs.readFileSync(path.join(__dirname, "../scripts/daily-preflight.js"), "utf8");
  const exports = Object.keys(require(collectorPath)).sort();
  const exported = require(collectorPath);
  const forbiddenParameters = /\b(?:env|fetch|fetchImpl|botCall|mtprotoSend|mtprotoRead|execFileImpl|send|findReceipt|mailFactory|now|randomNonce|sleep|maxPolls|maxReplyPolls|maxWebhookPolls)\b/;

  assert.deepEqual(exports, ["collectProductionControlledL3", "validateEmailObservation", "validateTelegramObservation"]);
  assert.equal(exported.collectProductionControlledL3.length, 0);
  assert.doesNotMatch(exported.collectProductionControlledL3.toString().match(/^async function [^(]+\(([^)]*)\)/)?.[1] || "", forbiddenParameters);
  for (const name of exports) assert.doesNotMatch(name, /^(?:create|make)/);
  assert.doesNotMatch(collectorSource, /function\s+create(?:Telegram|Email|ProductionCollector)/);
  assert.doesNotMatch(collectorSource, /collectProductionControlledL3\s*\([^)]/);
  assert.doesNotMatch(`${collectorSource}\n${controlledSource}`, /\.test-support\.js/);
  assert.match(collectorSource, /async function collectProductionControlledL3\(\)/);
  assert.match(controlledSource, /async function collectControlledL3\(\{ mode \} = \{\}\)/);
  assert.doesNotMatch(cliSource, /collectControlledL3\([^)]*(?:env|fetch|collector)/);
});

test("controlled CLI prerequisite errors exit nonzero with sanitized output", () => {
  const result = spawnSync(process.execPath, [path.join(__dirname, "../scripts/daily-preflight.js"), "--mode", "controlled-l3"], {
    encoding: "utf8", env: { PATH: process.env.PATH || "" }, timeout: 5000,
  });
  assert.equal(result.status, 1);
  assert.equal(result.stderr, "daily preflight failed before report generation\n");
  assert.doesNotMatch(`${result.stdout}${result.stderr}`, /@|Bearer|token|provider.*error|https?:/i);
});

test("CLI exit wrapper maps completion and sanitized pre-report failure", async () => {
  const originalWrite = process.stderr.write; const errors = [];
  process.stderr.write = value => { errors.push(value); return true; };
  try {
    await runCli(async () => 7);
    assert.equal(process.exitCode, 7);
    await runCli(async () => { throw new Error("raw provider secret"); });
    assert.equal(process.exitCode, 1);
    assert.deepEqual(errors, ["daily preflight failed before report generation\n"]);
  } finally { process.stderr.write = originalWrite; process.exitCode = 0; }
});

test("controlled L3 is collected by the runner and bound into the generated report", async () => {
  const results = good();
  const controlledL3 = await collectControlledL3ForTest({
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
    await assert.rejects(() => collectControlledL3ForTest({
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
      await assert.rejects(() => collectControlledL3ForTest({ mode: "controlled-l3", nowMs: NOW, collectors: {
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
    await assert.rejects(() => collectControlledL3ForTest({ mode: "controlled-l3", nowMs: NOW, collectors: {
      telegram: async () => value.telegram, email: async () => value.email,
    } }), new RegExp(classification));
  });
  const value = good();
  const result = await collectControlledL3ForTest({ mode: "controlled-l3", nowMs: NOW, collectors: {
    telegram: async () => value.telegram, email: async () => value.email,
  } });
  assert.equal(result.telegram.pendingUpdateCount, 0);
  assert.deepEqual(result.telegram.pendingUpdateSamples, [1, 0]);
});

test("telegram collector performs round trip then bounded-polls getWebhookInfo", async () => {
  const samples = [1, 0];
  let roundTrips = 0;
  const value = await collectTelegramControlledForTest({
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
