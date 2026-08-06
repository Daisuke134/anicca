#!/usr/bin/env node
"use strict";

const path = require("node:path");

const { createMinimalProductionOperations } = require(
  "../../apps/life-manager/lib/connector-minimal-operations.js",
);
const { createNativeProductionConfig } = require("./native-pass.js");

function invalid() {
  throw new Error("Connector minimal crash report unavailable");
}

async function reportMinimalCrash(options = {}) {
  const ownerToken = String(options.ownerToken || "").trim();
  if (!/^[A-Za-z0-9._-]{16,200}$/.test(ownerToken)) invalid();
  const stateDir = path.resolve(String(options.stateDir || ""));
  const repoRoot = path.resolve(String(options.repoRoot || ""));
  if (
    !path.isAbsolute(stateDir) || stateDir === path.parse(stateDir).root
    || !path.isAbsolute(repoRoot) || repoRoot === path.parse(repoRoot).root
  ) invalid();
  const config = createNativeProductionConfig({ repoRoot, env: options.env }, stateDir, ownerToken);
  const createOperations = options.createOperations || createMinimalProductionOperations;
  if (typeof createOperations !== "function") invalid();
  const operations = createOperations({
    stateDir,
    wakeId: config.wakeId,
    telegramTarget: config.telegramTarget,
  });
  if (!operations || typeof operations.reportWake !== "function") invalid();
  return operations.reportWake({
    status: "circuit_open",
    safe_reason: "process_crash",
    consecutive_failure_count: 0,
  });
}

function cliArguments(argv = process.argv.slice(2)) {
  if (
    argv.length !== 6 || argv[0] !== "--repo-root"
    || argv[2] !== "--state-dir" || argv[4] !== "--owner-token"
  ) invalid();
  return Object.freeze({ repoRoot: argv[1], stateDir: argv[3], ownerToken: argv[5] });
}

if (require.main === module) {
  reportMinimalCrash(cliArguments()).catch(() => {
    process.stderr.write("Connector minimal crash report unavailable\n", () => process.exit(2));
  });
}

module.exports = { reportMinimalCrash };
