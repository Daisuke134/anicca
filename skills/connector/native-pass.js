#!/usr/bin/env node
"use strict";

const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const { createMinimalProductionDependencies } = require(
  "../../apps/life-manager/lib/connector-minimal-production.js",
);
const { runMinimalConnectorWake } = require(
  "../../apps/life-manager/lib/connector-minimal-runner.js",
);
const { loadConnectorEnv } = require("./lib/load-connector-env.js");

const DEFAULT_PROVIDERS = Object.freeze(["luma", "connpass"]);

function unavailable() {
  throw new Error("Connector minimal pass unavailable");
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

function requiredText(value, fallback) {
  const text = String(value == null || value === "" ? fallback || "" : value).trim();
  if (!text || text.length > 2_000 || /[\x00-\x1f\x7f]/.test(text)) unavailable();
  return text;
}

function resolvedTelegramTarget(env) {
  const configured = String(env.LM_CONNECTOR_TELEGRAM_TARGET || "").trim();
  if (configured) return requiredText(configured);
  const home = absoluteDirectory(env.HOME);
  const file = path.join(home, ".openclaw", "credentials", "telegram-default-allowFrom.json");
  let value;
  try {
    const stat = fs.statSync(file);
    if (!stat.isFile() || stat.size < 2 || stat.size > 64 * 1024 || (stat.mode & 0o077) !== 0) unavailable();
    value = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch { unavailable(); }
  const candidates = Array.isArray(value) ? value : value && value.allowFrom;
  const target = Array.isArray(candidates) ? String(candidates[0] || "").trim() : "";
  if (!/^-?[0-9]{5,20}$/.test(target)) unavailable();
  return target;
}

function productionConfig(options, stateDir, ownerToken) {
  const supplied = options.env && typeof options.env === "object" && !Array.isArray(options.env)
    ? options.env : process.env;
  const sharedFile = String(supplied.LM_CONNECTOR_SHARED_ENV_FILE || "").trim();
  const loaded = sharedFile && fs.existsSync(sharedFile) ? loadConnectorEnv(sharedFile) : {};
  const env = { ...loaded, ...supplied };
  const calendarAccount = requiredText(env.GOG_ACCOUNT || env.LM_CONNECTOR_LUMA_EMAIL);
  return Object.freeze({
    repoRoot: absoluteDirectory(options.repoRoot),
    stateDir,
    wakeId: `wake-${createHash("sha256").update(ownerToken).digest("hex").slice(0, 24)}`,
    calendarAccount,
    gogKeyring: requiredText(env.GOG_KEYRING_PASSWORD),
    gogBin: String(env.GOG_BIN || "").trim() || undefined,
    telegramTarget: resolvedTelegramTarget(env),
    tenantId: requiredText(env.LM_CONNECTOR_TENANT_ID, "dais-local"),
    calendarId: requiredText(env.LM_CONNECTOR_CALENDAR_ID, "primary"),
    lumaFormProfilePath: path.join(path.dirname(stateDir), "private", "connector-luma-form-profile.json"),
    lunaEvidenceDir: path.join(stateDir, "luna"),
  });
}

async function runNativePass(options = {}) {
  absoluteDirectory(options.repoRoot);
  const stateDir = absoluteDirectory(options.stateDir);
  const ownerToken = requiredToken(options.ownerToken);
  const runWake = typeof options.runWake === "function"
    ? options.runWake
    : runMinimalConnectorWake;
  const createDependencies = typeof options.createDependencies === "function"
    ? options.createDependencies : createMinimalProductionDependencies;
  const dependencies = options.dependencies || createDependencies(
    productionConfig(options, stateDir, ownerToken),
  );
  if (!dependencies || typeof dependencies !== "object" || Array.isArray(dependencies)) unavailable();

  return runWake(Object.freeze({
    ownerToken,
    stateDir,
    providers: DEFAULT_PROVIDERS,
    maxConsecutiveFailures: 3,
    maxWakeMs: 600_000,
    maxAgentSteps: 10,
  }), dependencies);
}

function cliArguments(argv = process.argv.slice(2)) {
  if (
    argv.length !== 6
    || argv[0] !== "--repo-root"
    || argv[2] !== "--state-dir"
    || argv[4] !== "--owner-token"
  ) unavailable();
  return Object.freeze({
    repoRoot: argv[1],
    stateDir: argv[3],
    ownerToken: argv[5],
  });
}

if (require.main === module) {
  runNativePass(cliArguments())
    .then((result) => {
      const exitCode = result && result.status === "applied_bundle" ? 0 : 1;
      process.exit(exitCode);
    })
    .catch(() => {
      process.stderr.write("Connector minimal pass unavailable\n", () => process.exit(2));
    });
}

module.exports = { runNativePass };
