#!/usr/bin/env node
"use strict";

const path = require("node:path");
const fs = require("node:fs");

const { runNativeConnectorPass } = require("../../apps/life-manager/lib/connector-native-runtime.js");
const { recordContinuation } = require("./lib/native-state.js");
const { loadConnectorEnv } = require("./lib/load-connector-env.js");

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

function requiredText(value) {
  const text = String(value == null ? "" : value).trim();
  if (!text || text.length > 2_000 || /[\x00-\x1f\x7f]/.test(text)) unavailable();
  return text;
}

function runtimeConfig(options, stateDir) {
  if (options.config && typeof options.config === "object" && !Array.isArray(options.config)) {
    return options.config;
  }
  const suppliedEnv = options.env || process.env;
  const sharedFile = suppliedEnv.LM_CONNECTOR_SHARED_ENV_FILE
    || path.join(suppliedEnv.HOME || process.env.HOME || "", ".openclaw/.env");
  const env = { ...(fs.existsSync(sharedFile) ? loadConnectorEnv(sharedFile) : {}), ...suppliedEnv };
  const calendarAccount = String(
    env.LM_CONNECTOR_CALENDAR_ACCOUNT
      || env.GOG_ACCOUNT
      || env.DAIS_EMAIL
      || env.LM_CONNECTOR_LUMA_EMAIL
      || "",
  ).trim();
  if (!calendarAccount) unavailable();
  const evidenceDir = String(env.LM_CONNECTOR_EVIDENCE_DIR || path.join(stateDir, "evidence")).trim();
  const profilePath = path.resolve(String(
    env.LM_CONNECTOR_PROFILE_PATH
      || path.join(options.repoRoot, "apps/life-manager/config/connector/dais-local.json"),
  ));
  return Object.freeze({
    tenantId: String(env.LM_CONNECTOR_TENANT_ID || "dais-local").trim(),
    timeZone: String(env.LM_CONNECTOR_TIME_ZONE || "Asia/Tokyo").trim(),
    now: new Date().toISOString(),
    evidenceDir: absoluteDirectory(evidenceDir),
    calendarAccount,
    gogBin: String(env.GOG_BIN || "").trim() || undefined,
    profilePath,
    lunaEvidenceDir: absoluteDirectory(env.LM_CONNECTOR_LUNA_EVIDENCE_DIR || path.join(stateDir, "luna")),
    telegramTarget: requiredText(env.LM_CONNECTOR_TELEGRAM_TARGET),
    calendarId: requiredText(env.LM_CONNECTOR_CALENDAR_ID || "primary"),
    calendarCoverageUrl: requiredText(
      env.LM_CONNECTOR_CALENDAR_COVERAGE_URL || "https://calendar.google.com/calendar/u/0/r",
    ),
    homeLocation: requiredText(env.LIFE_HOME_ADDRESS),
    mapsKey: requiredText(env.GOOGLE_API_KEY_DIRECTIONS),
    repoRoot: absoluteDirectory(options.repoRoot),
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
  } catch (error) {
    const code = String(error && error.code || "");
    const reason = /^CONNECTOR_NATIVE_(?:CONFIG|AUTH|INVENTORY|CALENDAR_READ|PROFILE|LUNA|CALENDAR_GATE|SPEND_GATE|WRITE)_FAILED$/.test(code)
      ? code.toLowerCase()
      : "runtime_failed";
    recordContinuation({ stateDir, reason });
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
