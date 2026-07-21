#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const {
  buildPreflightReport,
  collectControlledL3,
  createDependencyChecks,
} = require("../lib/daily-preflight.js");

function parseArgs(argv) {
  const args = { output: "", mode: "read-only", timeoutMs: 15000 };
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === "--output") args.output = argv[++index] || "";
    else if (argv[index] === "--mode") args.mode = argv[++index] || "";
    else if (argv[index] === "--timeout-ms") args.timeoutMs = Number(argv[++index]);
    else throw new Error(`unknown argument: ${argv[index]}`);
  }
  if (!Number.isFinite(args.timeoutMs) || args.timeoutMs < 1) throw new Error("--timeout-ms must be positive");
  if (!["read-only", "controlled-l3"].includes(args.mode)) throw new Error("--mode must be read-only or controlled-l3");
  return args;
}

async function main({ argv = process.argv.slice(2), env = process.env, fetchImpl = fetch } = {}) {
  const args = parseArgs(argv);
  const nowMs = Date.now();
  const controlledL3 = args.mode === "controlled-l3"
    ? await collectControlledL3({ mode: args.mode, nowMs, env, fetchImpl })
    : undefined;
  const checks = createDependencyChecks({ env, fetchImpl, nowMs, controlledL3 });
  const report = await buildPreflightReport({ checks, controlledL3, timeoutMs: args.timeoutMs });
  if (args.output) {
    const output = path.resolve(args.output);
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`, { mode: 0o600 });
  }
  process.stdout.write(`${JSON.stringify({
    artifact: args.output || null,
    overallStatus: report.overallStatus,
    exitCode: report.exitCode,
    summary: report.summary,
    dependencies: report.dependencies.map(({ dependency, status, latencyMs, failureClass }) => ({
      dependency, status, latencyMs, failureClass,
    })),
  })}\n`);
  return report.exitCode;
}

async function runCli(runMain = main) {
  try { process.exitCode = await runMain(); } catch {
    process.stderr.write("daily preflight failed before report generation\n");
    process.exitCode = 1;
  }
}

if (require.main === module) runCli();

module.exports = { main, parseArgs, runCli };
