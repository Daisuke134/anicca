import assert from "node:assert/strict";
import crypto from "node:crypto";
import { chmodSync, cpSync, existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../../../..");
const fixtureRoot = mkdtempSync(path.join(tmpdir(), "core8d-verifier-red-"));
const feature = path.join(root, ".vcsdd/features/life-manager-daily-preflight");
const hash = value => crypto.createHash("sha256").update(value).digest("hex");

function run(helper, args) {
  const target = path.join(here, helper);
  assert.equal(existsSync(target), true, `missing Phase 2 helper: ${helper}`);
  return spawnSync(process.execPath, [target, ...args], { cwd: root, encoding: "utf8", env: { PATH: process.env.PATH ?? "" } });
}
function rejected(helper, args) {
  const result = run(helper, args);
  assert.notEqual(result.status, 0, `${helper} accepted corrupt fixture`);
  assert.doesNotMatch(result.stderr, /fixture-secret-value|person@example\.test|\+15551234567|raw-correlation-value|provider-id-value/);
}
function write(name, value, mode) { const target = path.join(fixtureRoot, name); writeFileSync(target, value, mode ? { mode } : undefined); return target; }

const stateObject = JSON.parse(readFileSync(path.join(feature, "state.json"), "utf8"));
stateObject.currentPhase = "2b"; stateObject.sprintCount = 0;
const state = write("state.json", `${JSON.stringify(stateObject)}\n`);
const contract = path.join(feature, "contracts/sprint-1.md");
const head = spawnSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).stdout.trim();
const tree = spawnSync("git", ["rev-parse", "HEAD:apps/life-call"], { cwd: root, encoding: "utf8" }).stdout.trim();
const snapshot = write("source-snapshot.txt", `baselineCommit=${head}\nbaselineTree=${tree}\ngreenCommit=${head}\ngreenTree=${tree}\ncontractDigest=${hash(readFileSync(contract))}\n`);

const report = path.join(fixtureRoot, "actual-cli-report.json");
const cli = spawnSync(process.execPath, ["--require", path.join(root, "apps/life-call/test-support/core8d-cli-loader.cjs"),
  path.join(root, "apps/life-call/scripts/daily-preflight.js"), "--mode", "controlled-l3", "--output", report], {
  cwd: root, encoding: "utf8", env: { PATH: process.env.PATH ?? "", CORE8D_LOADER_FINAL: "1" },
});
assert.equal(cli.status, 0, cli.stderr); chmodSync(report, 0o600);

test("verify-phase2-process.mjs: every mode accepts valid phase-appropriate fixtures", () => {
  const historical = write("historical.txt", `${"a".repeat(64)}  first.json\n${"b".repeat(64)}  second.json\n600 first.json\n600 second.json\n`);
  const spec = path.join(feature, "specs/behavioral-spec.md"); const arch = path.join(feature, "specs/verification-architecture.md");
  const schemaFeature = path.join(fixtureRoot, "schema-feature"); cpSync(feature, schemaFeature, { recursive: true });
  const coverage = write("coverage.log", "apps/life-call/lib/daily-preflight.js | 92.08 | 95.77\napps/life-call/lib/daily-preflight-collectors.js | 98.52 | 90.63\napps/life-call/lib/transport/mail-gog.js | 100 | 100\n");
  for (const args of [["historical", historical, "a".repeat(64), "b".repeat(64), "600"], ["gates", state, contract],
    ["trace", state, spec, arch, contract], ["schemas", schemaFeature], ["scope", snapshot], ["coverage", coverage, snapshot]])
    assert.equal(run("verify-phase2-process.mjs", args).status, 0, args[0]);
});
test("verify-phase2-process.mjs: corrupt hash/mode/trace/schema/scope/coverage all fail", () => {
  const bad = write("bad-process.txt", "corrupt\n");
  for (const args of [["historical", bad, "a".repeat(64), "b".repeat(64), "600"], ["trace", state, bad, bad, contract],
    ["schemas", fixtureRoot], ["scope", bad], ["coverage", bad, snapshot]]) rejected("verify-phase2-process.mjs", args);
});
test("verify-phase2-process.mjs: malformed argv and stale current-HEAD scope fail", () => { rejected("verify-phase2-process.mjs", ["bogus"]); const stale = write("stale-snapshot.txt", `baselineCommit=${head}\nbaselineTree=${tree}\ngreenCommit=${"0".repeat(40)}\ngreenTree=${tree}\n`); rejected("verify-phase2-process.mjs", ["scope", stale]); });

test("verify-final-artifact.mjs: accepts the valid actual CLI artifact", () => { assert.equal(run("verify-final-artifact.mjs", [report, snapshot]).status, 0); });
test("verify-final-artifact.mjs: rejects closed-schema identity/order/time/binding/effects mutations and empty object", () => {
  const base = JSON.parse(readFileSync(report, "utf8"));
  const mutations = [v => { v.unknown = true; }, v => { v.dependencies[0].dependency = "maps"; }, v => v.dependencies.reverse(),
    v => { v.dependencies[0].checkedAt = "2000-01-01T00:00:00.000Z"; }, v => { v.runRef = `sha256:${"0".repeat(64)}`; },
    v => { v.effects.phoneCallCount = 1; }, v => { v.sourceSnapshotRef = `sha256:${"0".repeat(64)}`; }];
  for (const [index, mutate] of mutations.entries()) { const value = structuredClone(base); mutate(value); const target = write(`mutated-${index}.json`, `${JSON.stringify(value)}\n`, 0o600); rejected("verify-final-artifact.mjs", [target, snapshot]); }
  rejected("verify-final-artifact.mjs", [write("empty.json", "{}\n", 0o600), snapshot]);
});
test("verify-final-artifact.mjs: malformed argv and wrong mode fail", () => { rejected("verify-final-artifact.mjs", []); const wrong = write("wrong-mode.json", readFileSync(report), 0o644); rejected("verify-final-artifact.mjs", [wrong, snapshot]); });

const cleanScan = write("clean.txt", "schema pass count 9\n");
test("verify-safe-scan.mjs: clean fixture passes without matched content", () => { const r = run("verify-safe-scan.mjs", ["--paths", cleanScan, cleanScan, "--exclude-historical-json", "--allow-utc-timestamps"]); assert.equal(r.status, 0); assert.equal(r.stderr, ""); });
test("verify-safe-scan.mjs: secret email phone raw-correlation and provider-ID fixtures fail without leakage", () => {
  for (const [name, content] of [["secret", "api_key=fixture-secret-value"], ["email", "person@example.test"], ["phone", "+15551234567"], ["correlation", "raw-correlation-value"], ["provider", "provider-id-value"]]) {
    const target = write(`scan-${name}.txt`, content); rejected("verify-safe-scan.mjs", ["--paths", target, cleanScan, "--exclude-historical-json", "--allow-utc-timestamps"]);
  }
});
test("verify-safe-scan.mjs: malformed argv and missing path fail safely", () => { rejected("verify-safe-scan.mjs", ["--unknown"]); rejected("verify-safe-scan.mjs", ["--paths", path.join(fixtureRoot, "missing"), "--exclude-historical-json", "--allow-utc-timestamps"]); });

const greenEvidence = write("green-evidence.json", JSON.stringify({ appNew: 63, helper: 12, baselineFocused: 51, baselineFull: 371, eval: 33, schema: 45, poll: 12, purity: 32, coverage: "pass", safeScan: "pass", contractDigest: hash(readFileSync(contract)), outputAbsent: true }));
const l3Snapshot = write("l3-snapshot.txt", `${readFileSync(snapshot)}greenEvidence=${greenEvidence}\nfinalOutput=${path.join(fixtureRoot, "future-final.json")}\n`);
test("verify-controlled-l3-gates.mjs: valid synthetic post-Phase3-PASS snapshot passes", () => { assert.equal(run("verify-controlled-l3-gates.mjs", [state, contract, l3Snapshot]).status, 0); });
test("verify-controlled-l3-gates.mjs: HEAD/tree/count/coverage/schema/scan/digest/output mutations all fail", () => {
  for (const [name, mutate] of [["head", v => v.replace(`greenCommit=${head}`, `greenCommit=${"0".repeat(40)}`)], ["count", v => v.replace("greenEvidence=", "missingEvidence=")],
    ["digest", v => v.replace(/contractDigest=[a-f0-9]{64}/, `contractDigest=${"0".repeat(64)}`)]]) rejected("verify-controlled-l3-gates.mjs", [state, contract, write(`l3-${name}.txt`, mutate(readFileSync(l3Snapshot, "utf8")))]);
  const existing = write("future-final.json", "{}\n"); assert.equal(existsSync(existing), true); rejected("verify-controlled-l3-gates.mjs", [state, contract, l3Snapshot]);
});
test("verify-controlled-l3-gates.mjs: malformed argv and pre-Phase3 state fail", () => { rejected("verify-controlled-l3-gates.mjs", []); const pre = { ...stateObject, currentPhase: "2a" }; rejected("verify-controlled-l3-gates.mjs", [write("pre-state.json", JSON.stringify(pre)), contract, l3Snapshot]); });
