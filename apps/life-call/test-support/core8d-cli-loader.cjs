"use strict";

const Module = require("node:module");
const path = require("node:path");

const productionModule = path.resolve(__dirname, "../lib/daily-preflight.js");
const { buildFinalPreflightReport } = require(productionModule);
const originalLoad = Module._load;

Module._load = function core8dTestProvider(request, parent, isMain) {
  let resolved;
  try { resolved = Module._resolveFilename(request, parent, isMain); } catch {}
  if (resolved === productionModule) {
    const dependencies = ["health", "telegram", "calendar", "call", "location", "email", "discovery", "gemini", "maps"];
    return {
      collectControlledL3: async () => ({
        telegram: { attempted: true, verified: true, checkedAt: new Date().toISOString(),
          requestMessageRef: "sha256:111111111111", replyMessageRef: "sha256:222222222222",
          exactUrl: true, allowedUpdates: ["message", "edited_message", "callback_query"], providerError: false,
          pendingUpdateCount: 0, pendingUpdateSamples: [0], replyReadCount: 1, webhookReadCount: 1 },
        email: { attempted: true, providerAccepted: true, inboxReceived: true, recipientOwned: true,
          checkedAt: new Date().toISOString(), providerRef: "sha256:333333333333",
          messageIdRef: "sha256:444444444444", inboxReadCount: 1 },
      }),
      createDependencyChecks: () => dependencies.map(dependency => ({
        name: dependency, run: async () => ({ ok: true, evidence: { status: "pass" } }),
      })),
      buildFinalPreflightReport,
      buildPreflightReport: async () => ({
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
