#!/usr/bin/env node
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";

function fail() { process.stderr.write("verification failed\n"); process.exit(1); }
function git(args) { try { return execFileSync("git", args, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim(); } catch { fail(); } }
function digest(value) { return crypto.createHash("sha256").update(value).digest("hex"); }
const args = process.argv.slice(2);
if (args.length !== 3 || args.some(value => !existsSync(value))) fail();
let state; let contract; let rawSnapshot;
try { state = JSON.parse(readFileSync(args[0], "utf8")); contract = readFileSync(args[1], "utf8"); rawSnapshot = readFileSync(args[2], "utf8"); } catch { fail(); }
const snapshot = {};
for (const line of rawSnapshot.trim().split(/\r?\n/)) {
  const match = /^([A-Za-z][A-Za-z0-9]*)=(\S+)$/.exec(line);
  if (!match || Object.hasOwn(snapshot, match[1])) fail();
  snapshot[match[1]] = match[2];
}
if (!["2b", "2c"].includes(state.currentPhase) || state.sprintCount !== 0 || state.mode !== "strict" ||
    state.gates?.["1c"]?.humanApproved !== true || state.gates?.["1c"]?.adversaryVerdict !== "PASS" ||
    !/^status: approved$/m.test(contract) || snapshot.greenCommit !== git(["rev-parse", "HEAD"]) ||
    snapshot.greenTree !== git(["rev-parse", "HEAD:apps/life-call"]) || snapshot.contractDigest !== digest(contract) ||
    !snapshot.greenEvidence || !snapshot.finalOutput || existsSync(snapshot.finalOutput) || !existsSync(snapshot.greenEvidence)) fail();
let evidence;
try { evidence = JSON.parse(readFileSync(snapshot.greenEvidence, "utf8")); } catch { fail(); }
const expected = { appNew: 63, helper: 12, baselineFocused: 51, baselineFull: 371, eval: 33, schema: 45, poll: 12, purity: 32 };
if (Object.entries(expected).some(([key, value]) => evidence[key] !== value) || evidence.coverage !== "pass" ||
    evidence.safeScan !== "pass" || evidence.contractDigest !== snapshot.contractDigest || evidence.outputAbsent !== true) fail();
if (evidence.modules !== undefined) {
  const required = ["lib/daily-preflight.js", "lib/daily-preflight-collectors.js", "lib/transport/mail-gog.js", "scripts/daily-preflight.js"];
  if (required.some(file => !evidence.modules[file] || evidence.modules[file].lines < 90 || evidence.modules[file].functions < 90)) fail();
}
const dirty = git(["status", "--porcelain"]).split(/\r?\n/).filter(Boolean);
if (dirty.some(line => {
  const file = line.slice(3);
  return !file.startsWith(".vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/") &&
    file !== ".vcsdd/features/life-manager-daily-preflight/state.json";
})) fail();
