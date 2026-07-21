"use strict";

const Module = require("node:module");
const path = require("node:path");

const productionModule = path.resolve(__dirname, "../lib/daily-preflight.js");
const { validateAndBuildFinalReport } = require(productionModule);
const originalLoad = Module._load;

function closedReport() {
  const crypto = require("node:crypto");
  const hash = value => `sha256:${crypto.createHash("sha256").update(value).digest("hex")}`;
  const generatedAtMs = Date.parse("2026-07-21T06:00:00.000Z");
  const runCorrelation = "loader-current-run";
  return validateAndBuildFinalReport({
    sourceSnapshotRef: hash("source"), runCorrelation, runStartedAtMs: generatedAtMs - 1000, generatedAtMs,
    dependencies: ["health", "telegram", "calendar", "call", "location", "email", "discovery", "gemini", "maps"].map((dependency, index) => ({
      dependency, status: "pass", fresh: true, checkedAt: new Date(generatedAtMs - index).toISOString(), checkedAtMs: generatedAtMs - index,
      evidenceRef: hash(dependency), runCorrelation,
    })),
    effects: { telegramSendCount: 1, emailSendCount: 1, phoneCallCount: 0, telegramReplyReadCount: 1,
      telegramWebhookReadCount: 1, emailInboxReadCount: 1, telegramCorrelated: true, telegramWebhookDrained: true,
      emailCorrelated: true, recipientOwned: true },
  });
}

Module._load = function core8dTestProvider(request, parent, isMain) {
  let resolved;
  try { resolved = Module._resolveFilename(request, parent, isMain); } catch {}
  if (resolved === productionModule) {
    const dependencies = ["health", "telegram", "calendar", "call", "location", "email", "discovery", "gemini", "maps"];
    return {
      collectControlledL3: async () => ({ telegram: {}, email: {} }),
      createDependencyChecks: () => dependencies.map(dependency => ({ name: dependency, run: async () => ({ ok: true }) })),
      buildPreflightReport: async () => process.env.CORE8D_LOADER_FINAL === "1" ? closedReport() : ({
        schemaVersion: 1,
        kind: "life-manager-daily-preflight",
        overallStatus: "pass",
        exitCode: 0,
        summary: { required: 9, passed: 9, failed: 0 },
        dependencies: dependencies.map(dependency => ({ dependency, status: "pass", latencyMs: 0, failureClass: null })),
      }),
    };
  }
  return originalLoad.apply(this, arguments);
};
