#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";

function fail() { process.stderr.write("verification failed\n"); process.exit(1); }
function text(file) { try { return readFileSync(file, "utf8"); } catch { fail(); } }
function json(file) { try { return JSON.parse(text(file)); } catch { fail(); } }
function git(args) { try { return execFileSync("git", args, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim(); } catch { fail(); } }
function snapshot(file) {
  const entries = new Map();
  for (const line of text(file).trim().split(/\r?\n/)) {
    const match = /^([A-Za-z][A-Za-z0-9]*)=(\S+)$/.exec(line);
    if (!match || entries.has(match[1])) fail();
    entries.set(match[1], match[2]);
  }
  for (const key of ["baselineCommit", "baselineTree", "greenCommit", "greenTree"])
    if (!/^[a-f0-9]{40}$/.test(entries.get(key) || "")) fail();
  if (entries.has("contractDigest") && !/^[a-f0-9]{64}$/.test(entries.get("contractDigest"))) fail();
  return entries;
}
function verifyScope(file) {
  const values = snapshot(file);
  if (values.get("greenCommit") !== git(["rev-parse", "HEAD"]) ||
      values.get("greenTree") !== git(["rev-parse", "HEAD:apps/life-call"])) fail();
  return values;
}
function allJsonFiles(root) {
  const out = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const target = path.join(root, entry.name);
    if (entry.isDirectory()) out.push(...allJsonFiles(target));
    else if (entry.name.endsWith(".json")) out.push(target);
  }
  return out;
}

const args = process.argv.slice(2);
const expected = { historical: 5, gates: 3, trace: 5, schemas: 2, scope: 2, coverage: 3 };
if (!Object.hasOwn(expected, args[0]) || args.length !== expected[args[0]]) fail();
if (args.slice(1).some(value => !value)) fail();

if (args[0] === "historical") {
  const lines = text(args[1]).trim().split(/\r?\n/);
  const hashes = lines.filter(line => /^[a-f0-9]{64}\s{2}\S+$/.test(line));
  const modes = lines.filter(line => /^\d{3}\s+\S+$/.test(line));
  if (lines.length !== 4 || hashes.length !== 2 || modes.length !== 2 || args[4] !== "600" ||
      hashes[0].slice(0, 64) !== args[2] || hashes[1].slice(0, 64) !== args[3] ||
      modes.some(line => !line.startsWith(`${args[4]} `))) fail();
} else if (args[0] === "gates") {
  const state = json(args[1]); const contract = text(args[2]);
  if (!["2b", "2c"].includes(state.currentPhase) || state.sprintCount !== 0 || state.mode !== "strict" ||
      state.gates?.["1c"]?.humanApproved !== true || state.gates?.["1c"]?.adversaryVerdict !== "PASS" ||
      !/^status: approved$/m.test(contract)) fail();
} else if (args[0] === "trace") {
  const state = json(args[1]); const spec = text(args[2]); const architecture = text(args[3]); const contract = text(args[4]);
  const required = [...Array(18)].map((_, i) => `REQ-${String(i + 1).padStart(3, "0")}`);
  const props = [...Array(12)].map((_, i) => `PROP-${String(i + 1).padStart(3, "0")}`);
  const criteria = [...Array(5)].map((_, i) => `CRIT-${String(i + 1).padStart(3, "0")}`);
  if (required.some(id => !spec.includes(id) || !architecture.includes(id)) ||
      props.some(id => !architecture.includes(id) || !contract.includes(id)) || criteria.some(id => !contract.includes(id))) fail();
  const beads = state.traceability?.beads;
  if (!Array.isArray(beads)) fail();
  const byId = new Map(beads.map(bead => [bead.beadId, bead]));
  for (const bead of beads) for (const linked of bead.linkedBeads || []) if (!byId.has(linked)) fail();
  if ([...required, ...props, ...criteria].some(id => !beads.some(bead => bead.externalId === id))) fail();
} else if (args[0] === "schemas") {
  const root = args[1];
  if (!existsSync(root) || !statSync(root).isDirectory() || !existsSync(path.join(root, "state.json")) ||
      !existsSync(path.join(root, "contracts/sprint-1.md"))) fail();
  const state = json(path.join(root, "state.json"));
  if (state.featureName !== "life-manager-daily-preflight" || !Array.isArray(state.traceability?.beads)) fail();
  const files = allJsonFiles(root);
  if (files.length < 10) fail();
  for (const file of files) {
    const value = json(file);
    if (file.endsWith("verdict.json") && (!value.overallVerdict || !Array.isArray(value.dimensions))) fail();
    if (/FIND-\d{3}\.json$/.test(file) && (!/^FIND-\d{3}$/.test(value.findingId || "") || !value.routeToPhase)) fail();
  }
} else if (args[0] === "scope") {
  verifyScope(args[1]);
} else if (args[0] === "coverage") {
  verifyScope(args[2]);
  const rows = text(args[1]).split(/\r?\n/).map(line => {
    const match = /^.*?([\w./-]+\.js)\s*\|\s*(\d+(?:\.\d+)?)\s*\|(?:\s*\d+(?:\.\d+)?\s*\|)?\s*(\d+(?:\.\d+)?)\s*(?:\||$)/.exec(line);
    return match && { file: match[1], lines: Number(match[2]), functions: Number(match[3]) };
  }).filter(Boolean);
  const required = ["daily-preflight.js", "daily-preflight-collectors.js", "mail-gog.js"];
  if (required.some(name => !rows.some(row => row.file.endsWith(name))) ||
      rows.some(row => row.lines < 90 || row.functions < 90)) fail();
}
