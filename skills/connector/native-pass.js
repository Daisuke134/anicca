#!/usr/bin/env node
"use strict";

const path = require("node:path");

const { runNativeConnectorPass } = require("../../apps/life-manager/lib/connector-native-runtime.js");
const { recordContinuation } = require("./lib/native-state.js");

function unavailable() {
  throw new Error("Connector native pass unavailable");
}

function absoluteDirectory(value) {
  const directory = path.resolve(String(value == null ? "" : value));
  if (!path.isAbsolute(directory) || directory === path.parse(directory).root) unavailable();
  return directory;
}

function requiredToken(value) {
  const token = String(value == null ? "" : value).trim();
  if (!/^[A-Za-z0-9._-]{16,200}$/.test(token)) unavailable();
  return token;
}

function runtimeConfig(options, stateDir) {
  if (options.config && typeof options.config === "object" && !Array.isArray(options.config)) {
    return options.config;
  }
  const env = options.env || process.env;
  const calendarAccount = String(
    env.LM_CONNECTOR_CALENDAR_ACCOUNT
      || env.GOG_ACCOUNT
      || env.DAIS_EMAIL
      || env.LM_CONNECTOR_LUMA_EMAIL
      || "",
  ).trim();
  if (!calendarAccount) unavailable();
  const evidenceDir = String(env.LM_CONNECTOR_EVIDENCE_DIR || path.join(stateDir, "evidence")).trim();
  return Object.freeze({
    tenantId: String(env.LM_CONNECTOR_TENANT_ID || "dais-local").trim(),
    timeZone: String(env.LM_CONNECTOR_TIME_ZONE || "Asia/Tokyo").trim(),
    now: new Date().toISOString(),
    evidenceDir: absoluteDirectory(evidenceDir),
    calendarAccount,
    gogBin: String(env.GOG_BIN || "").trim() || undefined,
  });
}

function boundedResult(result) {
  if (!result || typeof result !== "object" || Array.isArray(result)) unavailable();
  const status = String(result.status || "").trim();
  const counts = result.coverage && result.coverage.counts;
  const open = counts && counts.open;
  const continuation = result.continuation;
  if (
    !["complete", "incomplete"].includes(status)
    || !counts || !Number.isSafeInteger(open) || open < 0 || open > 21
    || !continuation || typeof continuation !== "object"
    || !["complete", "continue"].includes(String(continuation.status || ""))
  ) unavailable();
  const complete = status === "complete"
    && open === 0
    && continuation.status === "complete";
  if (status === "complete" && !complete) unavailable();
  if (status === "incomplete" && complete) unavailable();
  return Object.freeze({ status, complete });
}

async function runNativePass(options = {}) {
  absoluteDirectory(options.repoRoot);
  const stateDir = absoluteDirectory(options.stateDir);
  requiredToken(options.ownerToken);

  const runtime = typeof options.runRuntime === "function"
    ? options.runRuntime
    : runNativeConnectorPass;
  try {
    const result = await runtime({
      config: runtimeConfig(options, stateDir),
      deps: options.deps && typeof options.deps === "object" ? options.deps : {},
    });
    const bounded = boundedResult(result);
    if (bounded.complete) {
      return Object.freeze({ exitCode: 0, status: "complete" });
    }
    recordContinuation({ stateDir, reason: "runtime_incomplete" });
    return Object.freeze({ exitCode: 1, status: "incomplete" });
  } catch {
    recordContinuation({ stateDir, reason: "runtime_failed" });
    return Object.freeze({ exitCode: 1, status: "failed" });
  }
}

function cliArguments(argv = process.argv.slice(2)) {
  if (argv.length !== 6 || argv[0] !== "--repo-root" || argv[2] !== "--state-dir" || argv[4] !== "--owner-token") {
    unavailable();
  }
  return Object.freeze({ repoRoot: argv[1], stateDir: argv[3], ownerToken: argv[5], env: process.env });
}

if (require.main === module) {
  runNativePass(cliArguments())
    .then((result) => { process.exitCode = result.exitCode; })
    .catch(() => {
      process.stderr.write("Connector native pass unavailable\n");
      process.exitCode = 2;
    });
}

module.exports = { runNativePass };
