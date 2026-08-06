#!/usr/bin/env node
"use strict";

const path = require("node:path");

const { runMinimalConnectorWake } = require(
  "../../apps/life-manager/lib/connector-minimal-runner.js",
);

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

async function runNativePass(options = {}) {
  absoluteDirectory(options.repoRoot);
  const stateDir = absoluteDirectory(options.stateDir);
  const ownerToken = requiredToken(options.ownerToken);
  const runWake = typeof options.runWake === "function"
    ? options.runWake
    : runMinimalConnectorWake;
  const dependencies = options.dependencies;
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
