#!/usr/bin/env node
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import { existsSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

function fail() { process.stderr.write("verification failed\n"); process.exit(1); }
const args = process.argv.slice(2);
if (args.length !== 2 || args.some(value => !existsSync(value))) fail();
let report; let snapshot;
try { report = JSON.parse(readFileSync(args[0], "utf8")); snapshot = readFileSync(args[1], "utf8"); } catch { fail(); }
if ((statSync(args[0]).mode & 0o777) !== 0o600) fail();
const values = Object.fromEntries(snapshot.trim().split(/\r?\n/).map(line => {
  const match = /^([A-Za-z][A-Za-z0-9]*)=(\S+)$/.exec(line);
  if (!match) fail();
  return [match[1], match[2]];
}));
if (!/^[a-f0-9]{40}$/.test(values.greenCommit || "") || !/^[a-f0-9]{40}$/.test(values.greenTree || "")) fail();
let head; let tree;
try {
  head = execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  tree = execFileSync("git", ["rev-parse", "HEAD:apps/life-call"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
} catch { fail(); }
if (head !== values.greenCommit || tree !== values.greenTree) fail();
const expectedSource = `sha256:${crypto.createHash("sha256").update(values.greenTree).digest("hex")}`;
if (report.sourceSnapshotRef !== expectedSource || /^sha256:0{64}$/.test(String(report.runRef || ""))) fail();
try {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const require = createRequire(import.meta.url);
  const { validateAndBuildFinalReport } = require(path.resolve(here, "../../../../apps/life-call/lib/daily-preflight.js"));
  validateAndBuildFinalReport(report);
} catch { fail(); }
