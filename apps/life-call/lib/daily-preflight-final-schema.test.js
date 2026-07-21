"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const test = require("node:test");
const support = require("./daily-preflight.test-support.js");

const GENERATED_MS = Date.parse("2026-07-21T06:00:00.000Z");
const RUN_STARTED_MS = GENERATED_MS - 900000;
const RUN_CORRELATION = "current-run-correlation";
const DEPENDENCIES = ["health", "telegram", "calendar", "call", "location", "email", "discovery", "gemini", "maps"];
const hash = value => `sha256:${crypto.createHash("sha256").update(value).digest("hex")}`;

function validInput() {
  return {
    sourceSnapshotRef: hash("source"), runCorrelation: RUN_CORRELATION,
    runStartedAtMs: RUN_STARTED_MS, generatedAtMs: GENERATED_MS,
    dependencies: DEPENDENCIES.map((dependency, index) => ({
      dependency, status: "pass", fresh: true,
      checkedAt: new Date(GENERATED_MS - index).toISOString(),
      checkedAtMs: GENERATED_MS - index, evidenceRef: hash(dependency),
      runCorrelation: RUN_CORRELATION,
    })),
    effects: {
      telegramSendCount: 1, emailSendCount: 1, phoneCallCount: 0,
      telegramReplyReadCount: 1, telegramWebhookReadCount: 1, emailInboxReadCount: 1,
      telegramCorrelated: true, telegramWebhookDrained: true, emailCorrelated: true, recipientOwned: true,
    },
  };
}

function validator() {
  assert.equal(typeof support.validateAndBuildFinalReportForTest, "function", "missing closed final-report validator");
  return support.validateAndBuildFinalReportForTest;
}

function accepts(name, mutate = () => {}) {
  test(name, () => { const input = validInput(); mutate(input); assert.doesNotThrow(() => validator()(input)); });
}

function rejects(name, mutate) {
  test(name, () => { const input = validInput(); mutate(input); const validate = validator(); assert.throws(() => validate(input)); });
}

accepts("schema positive: closed 9/9 current-run report is accepted");
accepts("schema positive: exact 900000 ms checkedAt lower boundary is accepted", v => { v.dependencies[0].checkedAtMs = RUN_STARTED_MS; v.dependencies[0].checkedAt = new Date(RUN_STARTED_MS).toISOString(); });

const closedFieldCases = [
  ["root unknown key", v => { v.unknown = true; }], ["wrong schema enum", v => { v.schema = "other"; }],
  ["wrong version enum", v => { v.version = 2; }], ["wrong runStatus enum", v => { v.runStatus = "fail"; }],
  ["invalid sourceSnapshotRef", v => { v.sourceSnapshotRef = "source"; }], ["caller supplied runRef", v => { v.runRef = hash("forged"); }],
  ["generatedAt after freshUntil", v => { v.freshUntil = "2026-07-21T05:59:59.999Z"; }], ["fresh window over 15 minutes", v => { v.freshUntil = "2026-07-21T06:15:00.001Z"; }],
  ["required count not 9", v => { v.requiredDependencyCount = 8; }], ["passed count not 9", v => { v.passedDependencyCount = 8; }],
  ["failed count not 0", v => { v.failedDependencyCount = 1; }], ["dependency unknown key", v => { v.dependencies[0].raw = "x"; }],
  ["dependency status not pass", v => { v.dependencies[0].status = "fail"; }], ["dependency fresh not true", v => { v.dependencies[0].fresh = false; }],
  ["invalid evidenceRef", v => { v.dependencies[0].evidenceRef = "id"; }], ["effects unknown key", v => { v.effects.raw = true; }],
  ["telegram send count not 1", v => { v.effects.telegramSendCount = 2; }], ["email send count not 1", v => { v.effects.emailSendCount = 0; }],
  ["phone call count not 0", v => { v.effects.phoneCallCount = 1; }], ["reply reads outside 1..6", v => { v.effects.telegramReplyReadCount = 7; }],
  ["webhook reads outside 1..3", v => { v.effects.telegramWebhookReadCount = 4; }], ["inbox reads outside 1..6", v => { v.effects.emailInboxReadCount = 7; }],
  ["correlation boolean false", v => { v.effects.telegramCorrelated = false; }], ["recipient ownership false", v => { v.effects.recipientOwned = false; }],
];
for (const [name, mutate] of closedFieldCases) rejects(`schema closed field: ${name}`, mutate);

const checkedAtCases = [
  ["checkedAt: one millisecond stale is rejected", v => { v.dependencies[0].checkedAtMs = RUN_STARTED_MS - 1; v.dependencies[0].checkedAt = new Date(RUN_STARTED_MS - 1).toISOString(); }],
  ["checkedAt: one millisecond future is rejected", v => { v.dependencies[0].checkedAtMs = GENERATED_MS + 1; v.dependencies[0].checkedAt = new Date(GENERATED_MS + 1).toISOString(); }],
  ["checkedAt: malformed strict timestamp is rejected", v => { v.dependencies[0].checkedAt = "2026-07-21 06:00"; }],
  ["checkedAt: non-finite internal millisecond is rejected", v => { v.dependencies[0].checkedAtMs = NaN; }],
  ["checkedAt: before current run start is rejected", v => { v.runStartedAtMs = GENERATED_MS - 100; v.dependencies[0].checkedAtMs = GENERATED_MS - 101; v.dependencies[0].checkedAt = new Date(GENERATED_MS - 101).toISOString(); }],
  ["checkedAt: mixed-run observation is rejected", v => { v.dependencies[0].runCorrelation = "old-run"; }],
  ["checkedAt: fresh true without time proof is rejected", v => { delete v.dependencies[0].checkedAtMs; }],
  ["checkedAt: non-round-trip UTC timestamp is rejected", v => { v.dependencies[0].checkedAt = "2026-07-21T06:00:00Z"; }],
];
for (const [name, mutate] of checkedAtCases) rejects(name, mutate);

rejects("dependency set: duplicate dependency is rejected", v => { v.dependencies[8].dependency = "health"; });
rejects("dependency set: missing dependency is rejected", v => { v.dependencies.pop(); });
rejects("dependency set: extra dependency is rejected", v => { v.dependencies.push({ ...v.dependencies[0], dependency: "extra" }); });
rejects("failure channel: failure diagnostics cannot enter a successful artifact", v => { v.failure = { failureCode: "timeout" }; });

const securityCases = [
  ["security: raw run correlation is never serialized", v => { v.dependencies[0].rawCorrelation = RUN_CORRELATION; }],
  ["security: runRef must hash current correlation", v => { v.runCorrelation = "different-current-run"; }],
  ["security: provider response is forbidden", v => { v.dependencies[0].providerResponse = {}; }],
  ["security: provider ID is forbidden", v => { v.dependencies[0].messageId = "provider-id"; }],
  ["security: address is forbidden", v => { v.dependencies[0].address = "redacted-address"; }],
  ["security: arbitrary nested string is forbidden", v => { v.effects.detail = "raw detail"; }],
  ["security: previous-run observation is rejected despite fresh true", v => { for (const d of v.dependencies) d.runCorrelation = "previous-run"; }],
];
for (const [name, mutate] of securityCases) rejects(name, mutate);
