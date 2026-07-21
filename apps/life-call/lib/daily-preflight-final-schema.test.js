"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const test = require("node:test");
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const support = require("./daily-preflight.test-support.js");
const { buildFinalPreflightReport, validateAndBuildFinalReport } = require("./daily-preflight.js");

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

test("schema positive: actual offline CLI artifact is the closed 9/9 current-run report", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "core8d-cli-red-"));
  const output = path.join(directory, "report.json");
  try {
    const result = spawnSync(process.execPath, ["--require", path.join(__dirname, "../test-support/core8d-cli-loader.cjs"),
      path.join(__dirname, "../scripts/daily-preflight.js"), "--mode", "controlled-l3", "--output", output], {
      cwd: path.join(__dirname, ".."), encoding: "utf8", env: { PATH: process.env.PATH || "" },
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(fs.existsSync(output), true);
    const emitted = JSON.parse(fs.readFileSync(output, "utf8"));
    assert.doesNotThrow(() => validator()(emitted));
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});
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

function controlledProof(checkedAt) {
  return {
    telegram: {
      attempted: true, verified: true, checkedAt,
      requestMessageRef: "sha256:111111111111", replyMessageRef: "sha256:222222222222",
      exactUrl: true, allowedUpdates: ["message", "edited_message", "callback_query"],
      providerError: false, pendingUpdateCount: 0, pendingUpdateSamples: [0],
      replyReadCount: 1, webhookReadCount: 1,
    },
    email: {
      attempted: true, providerAccepted: true, inboxReceived: true, recipientOwned: true, checkedAt,
      providerRef: "sha256:333333333333", messageIdRef: "sha256:444444444444", inboxReadCount: 1,
    },
  };
}

async function boundReport(mutateResult = () => {}) {
  const base = Date.parse("2026-07-21T06:00:00.000Z");
  let tick = 0;
  const now = () => base + tick++;
  const contexts = [];
  const observations = [];
  const checks = DEPENDENCIES.map((dependency, index) => ({
    name: dependency,
    secrets: [],
    run: async context => {
      contexts.push(context);
      const checkedAtMs = now();
      observations.push(checkedAtMs);
      const result = {
        ok: true,
        evidence: { status: "pass" },
        checkedAtMs,
        runCorrelation: context.runCorrelation,
      };
      mutateResult(result, index, context);
      return result;
    },
  }));
  const report = await buildFinalPreflightReport({
    checks,
    controlledL3: controlledProof(new Date(base).toISOString()),
    timeoutMs: 100,
    sourceSnapshotRef: hash("source"),
    now,
  });
  return { report, contexts, observations };
}

test("manager RED: current-run binding: correlation and run start exist before the first dependency collection", async () => {
  const { contexts } = await boundReport();
  assert.equal(contexts.length, DEPENDENCIES.length);
  assert.equal(contexts.every(context => typeof context.runCorrelation === "string" && context.runCorrelation.length > 0), true);
  assert.equal(contexts.every(context => Number.isFinite(context.runStartedAtMs)), true);
  assert.equal(new Set(contexts.map(context => context.runCorrelation)).size, 1);
  assert.equal(new Set(contexts.map(context => context.runStartedAtMs)).size, 1);
});

test("manager RED: current-run binding: final report preserves each distinct actual observation time", async () => {
  const { report, observations } = await boundReport();
  assert.equal(new Set(observations).size, DEPENDENCIES.length);
  assert.deepEqual(report.dependencies.map(item => Date.parse(item.checkedAt)), observations);
});

test("manager RED: current-run binding: missing checkedAtMs is rejected", async () => {
  await assert.rejects(boundReport((result, index) => { if (index === 0) delete result.checkedAtMs; }));
});

test("manager RED: current-run binding: mismatched dependency correlation is rejected", async () => {
  await assert.rejects(boundReport((result, index) => { if (index === 0) result.runCorrelation = "previous-run"; }));
});

test("manager RED: current-run binding: one-millisecond pre-run observation is rejected", async () => {
  await assert.rejects(boundReport((result, index, context) => {
    if (index === 0) result.checkedAtMs = context.runStartedAtMs - 1;
  }));
});

test("manager RED: current-run binding: future observation is rejected", async () => {
  await assert.rejects(boundReport((result, index) => { if (index === 0) result.checkedAtMs = Number.MAX_SAFE_INTEGER; }));
});

test("manager RED: current-run binding: arbitrary nonzero serialized runRef is rejected", async () => {
  const { report } = await boundReport();
  const forged = structuredClone(report);
  forged.runRef = `sha256:${"f".repeat(64)}`;
  assert.throws(() => validateAndBuildFinalReport(forged), /final_report_invalid/);
});

test("review6 RED: serialized validation requires explicit same-invocation provenance in current and fresh processes", async () => {
  const first = (await boundReport()).report;
  await boundReport();
  let firstReplayAcceptedAfterSecond = false;
  try { validateAndBuildFinalReport(first); firstReplayAcceptedAfterSecond = true; } catch {}

  const arbitrary = { ...first, runRef: `sha256:${"a".repeat(64)}` };
  const child = spawnSync(process.execPath, ["-e", [
    "const {validateAndBuildFinalReport}=require(process.argv[1]);",
    "const report=JSON.parse(Buffer.from(process.argv[2],'base64').toString('utf8'));",
    "try{validateAndBuildFinalReport(report);process.exit(0)}catch{process.exit(1)}",
  ].join(""), path.join(__dirname, "daily-preflight.js"), Buffer.from(JSON.stringify(arbitrary)).toString("base64")], {
    cwd: __dirname, encoding: "utf8", env: { PATH: process.env.PATH || "" },
  });
  assert.deepEqual({ firstReplayAcceptedAfterSecond, freshProcessArbitraryRunRefAccepted: child.status === 0 }, {
    firstReplayAcceptedAfterSecond: false,
    freshProcessArbitraryRunRefAccepted: false,
  });
});
