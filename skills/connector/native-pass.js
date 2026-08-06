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

function readDeliveryReceipts(stateDir) {
  const file = path.join(stateDir, "delivery-receipts.jsonl");
  let source;
  try {
    const stat = fs.statSync(file);
    if (stat.size > 1_000_000) unavailable();
    source = fs.readFileSync(file, "utf8");
  } catch (error) {
    if (error && error.code === "ENOENT") return Object.freeze([]);
    throw error;
  }
  const rows = source.split(/\r?\n/).filter(Boolean).map((line) => {
    let value;
    try { value = JSON.parse(line); } catch { unavailable(); }
    if (
      !value || typeof value !== "object" || Array.isArray(value)
      || Object.keys(value).sort().join(",") !== "calendar_event_ref,event_ref,telegram_provider_id"
      || !/^luma-event:\/\/event\/[A-Za-z0-9_-]+$/.test(String(value.event_ref || ""))
      || !/^calendar-evidence:\/\/google\/event\/[0-9a-f]{64}$/.test(String(value.calendar_event_ref || ""))
      || !/^[^\x00-\x1f\x7f]{1,128}$/.test(String(value.telegram_provider_id || ""))
    ) unavailable();
    return Object.freeze({ ...value });
  });
  if (rows.length > 100 || new Set(rows.map((row) => row.telegram_provider_id)).size !== rows.length) unavailable();
  return Object.freeze(rows);
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
    lumaEmail: requiredText(env.LM_CONNECTOR_LUMA_EMAIL || calendarAccount).toLowerCase(),
    lumaName: requiredText(env.LM_CONNECTOR_LUMA_NAME || "Dais"),
    gogBin: String(env.GOG_BIN || "").trim() || undefined,
    gogKeyring: requiredText(env.GOG_KEYRING_PASSWORD),
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
    deliveredReceipts: readDeliveryReceipts(stateDir),
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
  const write = result.write && typeof result.write === "object" && !Array.isArray(result.write)
    ? {
      status: String(result.write.status || ""),
      outcome: String(result.write.outcome || ""),
      ...(/^[A-Z][A-Z0-9_:-]{0,99}$/.test(String(result.write.error_code || ""))
        ? { error_code: String(result.write.error_code) }
        : {}),
      event_ref: String(result.write.event_ref || ""),
      calendar_event_ref: String(result.write.calendar_sync && result.write.calendar_sync.calendar_event_ref || ""),
      telegram_provider_id: String(result.write.telegram && result.write.telegram.provider_id || ""),
    }
    : null;
  const coverageCounts = Object.freeze({
    open,
    covered_existing: Number(counts.covered_existing || 0),
    covered_new: Number(counts.covered_new || 0),
    unavailable: Number(counts.unavailable || 0),
  });
  if (Object.values(coverageCounts).some((value) => !Number.isSafeInteger(value) || value < 0)) unavailable();
  const candidateAttempts = Array.isArray(result.candidate_attempts)
    ? result.candidate_attempts.map((attempt) => {
      if (
        !attempt || typeof attempt !== "object" || Array.isArray(attempt)
        || Object.keys(attempt).sort().join(",") !== "event_ref,observed_at,outcome,retry_after,safe_reason"
        || !/^luma-event:\/\/event\/[A-Za-z0-9_-]+$/.test(String(attempt.event_ref || ""))
        || !["verified_success", "known_no_effect", "unknown_effect", "recovery_required"].includes(attempt.outcome)
        || !/^[A-Za-z0-9_:-]{1,100}$/.test(String(attempt.safe_reason || ""))
        || new Date(Date.parse(String(attempt.observed_at || ""))).toISOString() !== attempt.observed_at
        || !(attempt.retry_after === null
          || new Date(Date.parse(String(attempt.retry_after || ""))).toISOString() === attempt.retry_after)
      ) unavailable();
      return Object.freeze({ ...attempt });
    })
    : [];
  if (candidateAttempts.length > 100) unavailable();
  return Object.freeze({ status, complete, write, candidateAttempts: Object.freeze(candidateAttempts), coverageCounts });
}

function appendCandidateAttempts(stateDir, attempts) {
  if (!attempts.length) return;
  const historyFile = path.join(stateDir, "candidate-attempts.jsonl");
  try {
    const stat = fs.statSync(historyFile);
    if (stat.size > 10_000_000) unavailable();
  } catch (error) {
    if (!error || error.code !== "ENOENT") throw error;
  }
  fs.appendFileSync(
    historyFile,
    `${attempts.map((attempt) => JSON.stringify(attempt)).join("\n")}\n`,
    { encoding: "utf8", mode: 0o600 },
  );
}

function appendDeliveryReceipt(stateDir, write) {
  if (write && write.telegram_provider_id && write.event_ref && write.calendar_event_ref) {
    const historyFile = path.join(stateDir, "delivery-receipts.jsonl");
    let existing = "";
    try {
      const stat = fs.statSync(historyFile);
      if (stat.size > 1_000_000) unavailable();
      existing = fs.readFileSync(historyFile, "utf8");
    } catch (error) {
      if (!error || error.code !== "ENOENT") throw error;
    }
    const receipt = {
      event_ref: write.event_ref,
      calendar_event_ref: write.calendar_event_ref,
      telegram_provider_id: write.telegram_provider_id,
    };
    const duplicate = existing.split(/\r?\n/).filter(Boolean).some((line) => {
      try { return JSON.parse(line).telegram_provider_id === receipt.telegram_provider_id; }
      catch { unavailable(); }
    });
    if (!duplicate) fs.appendFileSync(historyFile, `${JSON.stringify(receipt)}\n`, { encoding: "utf8", mode: 0o600 });
  }
}

function recordLastResult(stateDir, bounded) {
  const file = path.join(stateDir, "last-result.json");
  fs.mkdirSync(stateDir, { recursive: true, mode: 0o700 });
  fs.writeFileSync(file, `${JSON.stringify({
    status: bounded.status, coverage_counts: bounded.coverageCounts, write: bounded.write,
  })}\n`, {
    encoding: "utf8", mode: 0o600,
  });
  appendDeliveryReceipt(stateDir, bounded.write);
  appendCandidateAttempts(stateDir, bounded.candidateAttempts);
}

function migrateLastResult(stateDir) {
  const file = path.join(stateDir, "last-result.json");
  let value;
  try { value = JSON.parse(fs.readFileSync(file, "utf8")); }
  catch (error) {
    if (error && error.code === "ENOENT") return;
    unavailable();
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) unavailable();
  appendDeliveryReceipt(stateDir, value.write);
}

async function runNativePass(options = {}) {
  absoluteDirectory(options.repoRoot);
  const stateDir = absoluteDirectory(options.stateDir);
  requiredToken(options.ownerToken);
  migrateLastResult(stateDir);

  const runtime = typeof options.runRuntime === "function"
    ? options.runRuntime
    : runNativeConnectorPass;
  try {
    const result = await runtime({
      config: runtimeConfig(options, stateDir),
      deps: options.deps && typeof options.deps === "object" ? options.deps : {},
    });
    const bounded = boundedResult(result);
    recordLastResult(stateDir, bounded);
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
    .then((result) => { process.exit(result.exitCode); })
    .catch(() => {
      process.stderr.write("Connector native pass unavailable\n", () => process.exit(2));
    });
}

module.exports = { runNativePass };
