#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { validateDocument } = require("/Users/anicca/.codex/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/scripts/lib/vcsdd-schema.js");
const FEATURE = ".vcsdd/features/life-manager-daily-preflight";
const BASE_MODULES = new Set([
  "lib/daily-preflight.js", "lib/daily-preflight-collectors.js",
  "lib/transport/mail-gog.js", "scripts/daily-preflight.js",
]);

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
      values.get("greenTree") !== git(["rev-parse", "HEAD:apps/life-call"]) ||
      values.get("baselineTree") !== git(["rev-parse", `${values.get("baselineCommit")}:apps/life-call`]) ||
      values.get("greenTree") !== git(["rev-parse", `${values.get("greenCommit")}:apps/life-call`])) fail();
  return values;
}
function changedPaths(values) {
  const output = git(["diff", "--name-only", values.get("baselineCommit"), values.get("greenCommit")]);
  return output ? output.split(/\r?\n/).filter(Boolean) : [];
}
function productionModules(values) {
  const modules = new Set(BASE_MODULES);
  for (const file of changedPaths(values)) {
    if (!/^apps\/life-call\/(?:lib|scripts)\/.+\.js$/.test(file) ||
        /(?:\.test\.|\.test-support\.|\/test-support\/)/.test(file)) continue;
    modules.add(file.slice("apps/life-call/".length));
  }
  return modules;
}
function coverageRows(file) {
  const rows = new Map();
  for (const line of text(file).split(/\r?\n/)) {
    const match = /^\s*(?:apps\/life-call\/)?((?:lib|scripts)\/[\w./-]+\.js)\s*\|\s*([^|]+)\s*\|(?:\s*[^|]+\s*\|)?\s*([^|]+?)\s*(?:\||$)/.exec(line);
    if (!match) continue;
    const lines = Number(match[2]); const functions = Number(match[3]);
    if (rows.has(match[1]) || !Number.isFinite(lines) || !Number.isFinite(functions)) fail();
    rows.set(match[1], { lines, functions });
  }
  return rows;
}
function exactSet(actual, expected) {
  return actual.size === expected.size && [...expected].every(value => actual.has(value));
}
function allowedChangedPath(file) {
  if (file === ".vcsdd/history.jsonl") return true;
  if (file === `${FEATURE}/state.json`) return true;
  if (["verify-phase2-process.mjs", "verify-safe-scan.mjs", "verify-controlled-l3-gates.mjs"]
    .some(name => file === `${FEATURE}/tests/${name}`)) return true;
  if (file.startsWith(`${FEATURE}/evidence/sprint-1/manager-review-green-ba370/`)) return true;
  if (file.startsWith("apps/life-call/") && !/(?:\.test\.|\/test-support\/|\.test-support\.)/.test(file)) return true;
  if (["apps/life-call/test-support/core8d-cli-loader.cjs", "apps/life-call/test-support/core8d-runtime-harness.js"].includes(file)) return true;
  return false;
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
  if (byId.size !== beads.length) fail();
  const requireReciprocal = beads.filter(bead => bead.type === "test-case").every(bead => bead.status === "green");
  for (const bead of beads) for (const linked of bead.linkedBeads || []) {
    const other = byId.get(linked);
    if (!other || (requireReciprocal && !(other.linkedBeads || []).includes(bead.beadId))) fail();
  }
  const byExternal = new Map();
  for (const bead of beads) {
    if (!bead.externalId) continue;
    if (byExternal.has(bead.externalId)) fail();
    byExternal.set(bead.externalId, bead);
  }
  if ([...required, ...props, ...criteria].some(id => !byExternal.has(id))) fail();
  for (const requirement of required.map(id => byExternal.get(id))) {
    const propertyBeads = requirement.linkedBeads.map(id => byId.get(id)).filter(bead => bead?.type === "verification-property");
    const reachable = propertyBeads.some(property => property.linkedBeads.map(id => byId.get(id))
      .filter(bead => bead?.type === "contract-criterion")
      .some(criterion => criterion.linkedBeads.some(id => byId.get(id)?.type === "test-case")));
    if (!reachable) fail();
  }
} else if (args[0] === "schemas") {
  const root = args[1];
  if (!existsSync(root) || !statSync(root).isDirectory() || !existsSync(path.join(root, "state.json")) ||
      !existsSync(path.join(root, "contracts/sprint-1.md"))) fail();
  const state = json(path.join(root, "state.json"));
  const verdict = json(path.join(root, "reviews/sprint-1/output/verdict.json"));
  if (!validateDocument("state", state).valid || !validateDocument("grading", verdict).valid) fail();
  for (let index = 1; index <= 11; index += 1) {
    const finding = json(path.join(root, `reviews/sprint-1/output/findings/FIND-${String(index).padStart(3, "0")}.json`));
    if (!validateDocument("finding", finding).valid) fail();
  }
} else if (args[0] === "scope") {
  const values = verifyScope(args[1]);
  if (changedPaths(values).some(file => !allowedChangedPath(file))) fail();
} else if (args[0] === "coverage") {
  const values = verifyScope(args[2]);
  const expectedModules = productionModules(values);
  const rows = coverageRows(args[1]);
  if (!exactSet(new Set(rows.keys()), expectedModules) ||
      [...rows.values()].some(row => row.lines < 90 || row.functions < 90)) fail();
}
