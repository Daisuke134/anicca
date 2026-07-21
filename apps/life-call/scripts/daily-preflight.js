#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { createDependencyChecks, runPreflight } = require("../lib/daily-preflight.js");

function parseArgs(argv) {
  const args = { output: "", proofs: "", timeoutMs: 15000 };
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === "--output") args.output = argv[++index] || "";
    else if (argv[index] === "--proofs") args.proofs = argv[++index] || "";
    else if (argv[index] === "--timeout-ms") args.timeoutMs = Number(argv[++index]);
    else throw new Error(`unknown argument: ${argv[index]}`);
  }
  if (!Number.isFinite(args.timeoutMs) || args.timeoutMs < 1) throw new Error("--timeout-ms must be positive");
  return args;
}

async function main({ argv = process.argv.slice(2), env = process.env, fetchImpl = fetch } = {}) {
  const args = parseArgs(argv);
  let proofs = {};
  if (args.proofs) {
    const parsed = JSON.parse(fs.readFileSync(path.resolve(args.proofs), "utf8"));
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") throw new Error("--proofs must contain an object");
    proofs = parsed;
  }
  const checks = createDependencyChecks({ env, fetchImpl, nowMs: Date.now(), proofs });
  const report = await runPreflight({ checks, timeoutMs: args.timeoutMs });
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

if (require.main === module) {
  main().then((exitCode) => { process.exitCode = exitCode; }).catch(() => {
    process.stderr.write("daily preflight failed before report generation\n");
    process.exitCode = 1;
  });
}

module.exports = { main, parseArgs };
