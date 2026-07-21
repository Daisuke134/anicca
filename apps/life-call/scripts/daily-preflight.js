#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const crypto = require("node:crypto");
const { execFileSync } = require("node:child_process");
const path = require("node:path");
const {
  buildFinalPreflightReport,
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

function currentSourceSnapshotRef() {
  const root = path.resolve(__dirname, "../../..");
  const tree = execFileSync("git", ["rev-parse", "HEAD:apps/life-call"], {
    cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"],
  }).trim();
  if (!/^[a-f0-9]{40}$/.test(tree)) throw new Error("source snapshot unavailable");
  return `sha256:${crypto.createHash("sha256").update(tree).digest("hex")}`;
}

async function main(options) {
  if (options && Object.prototype.hasOwnProperty.call(options, "transport")) {
    throw new Error("caller transport injection rejected");
  }
  const { argv = process.argv.slice(2), env = process.env, fetchImpl = fetch } = options || {};
  const args = parseArgs(argv);
  const nowMs = Date.now();
  const controlledL3 = args.mode === "controlled-l3"
    ? await collectControlledL3({ mode: args.mode })
    : undefined;
  const checks = createDependencyChecks({ env, fetchImpl, nowMs, controlledL3 });
  const report = args.mode === "controlled-l3"
    ? await buildFinalPreflightReport({ checks, controlledL3, timeoutMs: args.timeoutMs,
      sourceSnapshotRef: currentSourceSnapshotRef() })
    : await buildPreflightReport({ checks, timeoutMs: args.timeoutMs });
  if (args.output) {
    const output = path.resolve(args.output);
    fs.mkdirSync(path.dirname(output), { recursive: true });
    const temporary = `${output}.${process.pid}.${Date.now()}.tmp`;
    let handle;
    try {
      handle = fs.openSync(temporary, "wx", 0o600);
      fs.writeFileSync(handle, `${JSON.stringify(report, null, 2)}\n`);
      fs.fsyncSync(handle);
      fs.closeSync(handle); handle = undefined;
      fs.renameSync(temporary, output);
    } catch (error) {
      if (handle !== undefined) try { fs.closeSync(handle); } catch {}
      try { fs.unlinkSync(temporary); } catch {}
      throw error;
    }
  }
  process.stdout.write(`${JSON.stringify({
    artifact: args.output || null,
    overallStatus: report.runStatus || report.overallStatus,
    exitCode: report.runStatus === "pass" ? 0 : report.exitCode,
    summary: report.runStatus === "pass" ? {
      required: report.requiredDependencyCount,
      passed: report.passedDependencyCount,
      failed: report.failedDependencyCount,
    } : report.summary,
    dependencies: report.dependencies.map(({ dependency, status, latencyMs, failureClass }) =>
      report.runStatus === "pass" ? { dependency, status } : { dependency, status, latencyMs, failureClass }),
  })}\n`);
  return report.runStatus === "pass" ? 0 : report.exitCode;
}

async function runCli(runMain = main) {
  try { process.exitCode = await runMain(); } catch {
    process.stderr.write("daily preflight failed before report generation\n");
    process.exitCode = 1;
  }
}

if (require.main === module) runCli();

module.exports = { main, parseArgs, runCli };
