#!/usr/bin/env node
"use strict";

const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

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

function workerTimeout(value) {
  const milliseconds = Number(value == null || value === "" ? 900_000 : value);
  if (!Number.isSafeInteger(milliseconds) || milliseconds < 1_000 || milliseconds > 900_000) unavailable();
  return milliseconds;
}

function resolveWorker(repoRoot, value) {
  const worker = String(value == null ? "" : value).trim()
    || path.join(repoRoot, "skills", "earn", "marketing-engine", "run_agent.sh");
  if (!path.isAbsolute(worker) || !fs.statSync(worker).isFile()) unavailable();
  return worker;
}

function nativeWorkerArguments(repoRoot, stateDir) {
  const evidenceDir = path.join(stateDir, "worker-evidence", `${Date.now()}-${process.pid}`);
  fs.mkdirSync(evidenceDir, { recursive: true, mode: 0o700 });
  return Object.freeze({
    evidenceDir,
    args: Object.freeze([
      "--task-class", "browser-lane-agent",
      "--evidence-dir", evidenceDir,
      "--task-label", "connector-native-pass",
      "--loop", "connector",
      "--workdir", repoRoot,
    ]),
  });
}

function runNativePass(options = {}) {
  const repoRoot = absoluteDirectory(options.repoRoot);
  const stateDir = absoluteDirectory(options.stateDir);
  const ownerToken = requiredToken(options.ownerToken);
  const worker = resolveWorker(repoRoot, options.env?.CONNECTOR_NATIVE_WORKER_BIN);
  const contractPath = path.join(repoRoot, "skills", "connector", "WORKER-CONTRACT.md");
  if (!fs.statSync(contractPath).isFile()) unavailable();
  const contract = fs.readFileSync(contractPath, "utf8");
  if (contract.trim().length < 16) unavailable();

  const invocation = nativeWorkerArguments(repoRoot, stateDir);
  const result = (options.spawnSync || spawnSync)(worker, invocation.args, {
    cwd: repoRoot,
    env: {
      ...process.env,
      ...(options.env || {}),
      CONNECTOR_NATIVE_OWNER_TOKEN: ownerToken,
      CONNECTOR_NATIVE_REPO_ROOT: repoRoot,
      CONNECTOR_NATIVE_STATE_DIR: stateDir,
    },
    input: contract,
    stdio: ["pipe", "ignore", "ignore"],
    timeout: workerTimeout(options.env?.CONNECTOR_NATIVE_WORKER_TIMEOUT_MS),
  });
  const exitCode = Number.isSafeInteger(result?.status) && result.status >= 0 && result.status <= 125
    ? result.status
    : 1;
  recordContinuation({
    stateDir,
    reason: exitCode === 0 ? "worker_finished_unverified" : "worker_failed",
  });
  return Object.freeze({ exitCode });
}

function cliArguments(argv = process.argv.slice(2)) {
  if (argv.length !== 6 || argv[0] !== "--repo-root" || argv[2] !== "--state-dir" || argv[4] !== "--owner-token") {
    unavailable();
  }
  return Object.freeze({ repoRoot: argv[1], stateDir: argv[3], ownerToken: argv[5], env: process.env });
}

if (require.main === module) {
  try {
    process.exitCode = runNativePass(cliArguments()).exitCode;
  } catch {
    process.stderr.write("Connector native pass unavailable\n");
    process.exitCode = 2;
  }
}

module.exports = { runNativePass };
