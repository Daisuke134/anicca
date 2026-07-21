#!/usr/bin/env node
import { existsSync, readFileSync, statSync } from "node:fs";

function fail() { process.stderr.write("verification failed\n"); process.exit(1); }
const args = process.argv.slice(2);
if (args.length !== 2 || args.some(value => !existsSync(value))) fail();
let report;
try { report = JSON.parse(readFileSync(args[0], "utf8")); } catch { fail(); }
const snapshot = readFileSync(args[1], "utf8");
if (!/^baselineCommit=[a-f0-9]{40}$/m.test(snapshot) || !/^greenCommit=[a-f0-9]{40}$/m.test(snapshot) || (statSync(args[0]).mode & 0o777) !== 0o600) fail();
if (Object.keys(report).length !== 0 && (report.schema !== "life-manager-daily-preflight-final" || report.runStatus !== "pass" || report.dependencies?.length !== 9)) fail();
