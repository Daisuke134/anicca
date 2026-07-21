import assert from "node:assert/strict";
import crypto from "node:crypto";
import { chmodSync, cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
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

function run(helper, args, { cwd = root } = {}) {
  const target = path.join(here, helper);
  assert.equal(existsSync(target), true, `missing Phase 2 helper: ${helper}`);
  return spawnSync(process.execPath, [target, ...args], { cwd, encoding: "utf8", env: { PATH: process.env.PATH ?? "" } });
}
function rejected(helper, args, options) {
  const result = run(helper, args, options);
  assert.notEqual(result.status, 0, `${helper} accepted corrupt fixture`);
  assert.doesNotMatch(result.stderr, /fixture-secret-value|person@example\.test|\+15551234567|raw-correlation-value|provider-id-value/);
}
function write(name, value, mode) { const target = path.join(fixtureRoot, name); writeFileSync(target, value, mode ? { mode } : undefined); return target; }
function writeIn(directory, relative, value) {
  const target = path.join(directory, relative);
  mkdirSync(path.dirname(target), { recursive: true });
  writeFileSync(target, value);
  return target;
}
function git(directory, args) {
  const result = spawnSync("git", args, { cwd: directory, encoding: "utf8", env: { PATH: process.env.PATH ?? "" } });
  assert.equal(result.status, 0, result.stderr || `${args.join(" ")} failed`);
  return result.stdout.trim();
}
function gitFixture(name, changes = {}) {
  const directory = path.join(fixtureRoot, name);
  mkdirSync(directory, { recursive: true });
  git(directory, ["init", "-q"]);
  git(directory, ["config", "user.name", "Verifier Fixture"]);
  git(directory, ["config", "user.email", "verifier-fixture@example.invalid"]);
  git(directory, ["config", "commit.gpgsign", "false"]);
  const base = {
    "apps/life-call/lib/daily-preflight.js": "module.exports = {};\n",
    "apps/life-call/lib/daily-preflight-collectors.js": "module.exports = {};\n",
    "apps/life-call/lib/transport/mail-gog.js": "module.exports = {};\n",
    "apps/life-call/scripts/daily-preflight.js": "module.exports = {};\n",
    "docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md": "canonical fixture\n",
    ".vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/historical.json": "{}\n",
  };
  for (const [relative, value] of Object.entries(base)) writeIn(directory, relative, value);
  git(directory, ["add", "."]);
  git(directory, ["commit", "-q", "-m", "baseline"]);
  const baselineCommit = git(directory, ["rev-parse", "HEAD"]);
  const baselineTree = git(directory, ["rev-parse", "HEAD:apps/life-call"]);
  if (Object.keys(changes).length > 0) {
    for (const [relative, value] of Object.entries(changes)) writeIn(directory, relative, value);
    git(directory, ["add", "."]);
    git(directory, ["commit", "-q", "-m", "green"]);
  }
  return {
    directory,
    baselineCommit,
    baselineTree,
    greenCommit: git(directory, ["rev-parse", "HEAD"]),
    greenTree: git(directory, ["rev-parse", "HEAD:apps/life-call"]),
  };
}
function snapshotFor(name, fixture) {
  return write(name, `baselineCommit=${fixture.baselineCommit}\nbaselineTree=${fixture.baselineTree}\ngreenCommit=${fixture.greenCommit}\ngreenTree=${fixture.greenTree}\n`);
}

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
  const coverage = write("coverage.log", "apps/life-call/lib/daily-preflight.js | 92.08 | 95.77\napps/life-call/lib/daily-preflight-collectors.js | 98.52 | 90.63\napps/life-call/lib/transport/mail-gog.js | 100 | 100\napps/life-call/scripts/daily-preflight.js | 95.70 | 100\n");
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

const coverageFixture = gitFixture("coverage-diff", {
  "apps/life-call/scripts/daily-preflight.js": "module.exports = { changed: true };\n",
  "apps/life-call/lib/additional-production.js": "module.exports = { changed: true };\n",
});
const coverageSnapshot = snapshotFor("coverage-diff-snapshot.txt", coverageFixture);
const coverageRows = [
  "apps/life-call/lib/daily-preflight.js | 95 | 95",
  "apps/life-call/lib/daily-preflight-collectors.js | 95 | 95",
  "apps/life-call/lib/transport/mail-gog.js | 95 | 95",
];
test("manager RED: coverage verifier rejects omission of changed scripts/daily-preflight.js", () => {
  const coverage = write("coverage-missing-cli.log", `${[...coverageRows, "apps/life-call/lib/additional-production.js | 95 | 95"].join("\n")}\n`);
  rejected("verify-phase2-process.mjs", ["coverage", coverage, coverageSnapshot], { cwd: coverageFixture.directory });
});
test("manager RED: coverage verifier rejects omission of any additional changed production module", () => {
  const coverage = write("coverage-missing-additional.log", `${[...coverageRows, "apps/life-call/scripts/daily-preflight.js | 95 | 95"].join("\n")}\n`);
  rejected("verify-phase2-process.mjs", ["coverage", coverage, coverageSnapshot], { cwd: coverageFixture.directory });
});

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

test("manager RED: safe scan traverses supplied directories and rejects a secret in production JavaScript without echoing it", () => {
  const directory = path.join(fixtureRoot, "production-js-scan");
  writeIn(directory, "README.txt", "clean fixture\n");
  writeIn(directory, "src/production.js", "const credential = 'api_key=fixture-secret-value';\n");
  rejected("verify-safe-scan.mjs", ["--paths", directory, "--exclude-historical-json", "--allow-utc-timestamps"]);
});

test("manager RED: trace verifier rejects broken REQ to PROP to CRIT and test reachability with every ID token retained", () => {
  const broken = structuredClone(stateObject);
  for (const bead of broken.traceability.beads) bead.linkedBeads = [];
  const brokenState = write("broken-reachability-state.json", `${JSON.stringify(broken)}\n`);
  rejected("verify-phase2-process.mjs", ["trace", brokenState, path.join(feature, "specs/behavioral-spec.md"), path.join(feature, "specs/verification-architecture.md"), contract]);
});

test("manager RED: schemas verifier rejects schema-invalid state retaining superficial helper fields", () => {
  const schemaFeature = path.join(fixtureRoot, "schema-invalid-state-feature");
  cpSync(feature, schemaFeature, { recursive: true });
  const target = path.join(schemaFeature, "state.json");
  const value = JSON.parse(readFileSync(target, "utf8"));
  value.unexpectedSchemaField = true;
  writeFileSync(target, `${JSON.stringify(value)}\n`);
  rejected("verify-phase2-process.mjs", ["schemas", schemaFeature]);
});

test("manager RED: schemas verifier rejects schema-invalid review retaining overallVerdict and dimensions", () => {
  const schemaFeature = path.join(fixtureRoot, "schema-invalid-review-feature");
  cpSync(feature, schemaFeature, { recursive: true });
  const target = path.join(schemaFeature, "reviews/sprint-1/output/verdict.json");
  const value = JSON.parse(readFileSync(target, "utf8"));
  value.unexpectedSchemaField = true;
  writeFileSync(target, `${JSON.stringify(value)}\n`);
  rejected("verify-phase2-process.mjs", ["schemas", schemaFeature]);
});

for (const [name, changedPath] of [
  ["unauthorized changed path", "outside-approved-scope.txt"],
  ["historical evidence mutation", ".vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/historical.json"],
  ["canonical root spec mutation", "docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md"],
]) {
  test(`manager RED: scope verifier rejects ${name}`, () => {
    const fixture = gitFixture(`scope-${name.replaceAll(" ", "-")}`, { [changedPath]: "mutated\n" });
    rejected("verify-phase2-process.mjs", ["scope", snapshotFor(`scope-${name.replaceAll(" ", "-")}.txt`, fixture)], { cwd: fixture.directory });
  });
}

const l3Fixture = gitFixture("controlled-l3-clean");
const l3Modules = {
  "lib/daily-preflight.js": { lines: 95, functions: 95 },
  "lib/daily-preflight-collectors.js": { lines: 95, functions: 95 },
  "lib/transport/mail-gog.js": { lines: 95, functions: 95 },
  "scripts/daily-preflight.js": { lines: 95, functions: 95 },
};
const greenEvidenceObject = { appNew: 63, helper: 12, baselineFocused: 51, baselineFull: 371, eval: 33, schema: 45, poll: 12, purity: 32, coverage: "pass", safeScan: "pass", contractDigest: hash(readFileSync(contract)), outputAbsent: true, modules: l3Modules };
const greenEvidence = write("green-evidence.json", JSON.stringify(greenEvidenceObject));
const l3Snapshot = write("l3-snapshot.txt", `baselineCommit=${l3Fixture.baselineCommit}\nbaselineTree=${l3Fixture.baselineTree}\ngreenCommit=${l3Fixture.greenCommit}\ngreenTree=${l3Fixture.greenTree}\ncontractDigest=${hash(readFileSync(contract))}\ngreenEvidence=${greenEvidence}\nfinalOutput=${path.join(fixtureRoot, "future-final.json")}\n`);
test("verify-controlled-l3-gates.mjs: valid synthetic post-Phase3-PASS snapshot passes", () => { assert.equal(run("verify-controlled-l3-gates.mjs", [state, contract, l3Snapshot], { cwd: l3Fixture.directory }).status, 0); });
test("manager RED: controlled L3 gate rejects evidence with the modules field missing", () => {
  const value = structuredClone(greenEvidenceObject); delete value.modules;
  const evidence = write("green-evidence-missing-modules.json", JSON.stringify(value));
  const candidate = write("l3-missing-modules.txt", readFileSync(l3Snapshot, "utf8").replace(greenEvidence, evidence));
  rejected("verify-controlled-l3-gates.mjs", [state, contract, candidate], { cwd: l3Fixture.directory });
});
test("manager RED: controlled L3 gate rejects an extra production module", () => {
  const value = structuredClone(greenEvidenceObject); value.modules["lib/unbound-production.js"] = { lines: 95, functions: 95 };
  const evidence = write("green-evidence-extra-module.json", JSON.stringify(value));
  const candidate = write("l3-extra-module.txt", readFileSync(l3Snapshot, "utf8").replace(greenEvidence, evidence));
  rejected("verify-controlled-l3-gates.mjs", [state, contract, candidate], { cwd: l3Fixture.directory });
});
test("manager RED: controlled L3 gate rejects non-finite module coverage data", () => {
  const value = structuredClone(greenEvidenceObject); value.modules["scripts/daily-preflight.js"].lines = "NaN";
  const evidence = write("green-evidence-nonfinite-module.json", JSON.stringify(value));
  const candidate = write("l3-nonfinite-module.txt", readFileSync(l3Snapshot, "utf8").replace(greenEvidence, evidence));
  rejected("verify-controlled-l3-gates.mjs", [state, contract, candidate], { cwd: l3Fixture.directory });
});
test("manager audit: controlled L3 gate rejects below-90 module coverage data", () => {
  const value = structuredClone(greenEvidenceObject); value.modules["scripts/daily-preflight.js"].functions = 89.99;
  const evidence = write("green-evidence-low-module.json", JSON.stringify(value));
  const candidate = write("l3-low-module.txt", readFileSync(l3Snapshot, "utf8").replace(greenEvidence, evidence));
  rejected("verify-controlled-l3-gates.mjs", [state, contract, candidate], { cwd: l3Fixture.directory });
});
test("verify-controlled-l3-gates.mjs: HEAD/tree/count/coverage/schema/scan/digest/output mutations all fail", () => {
  for (const [name, mutate] of [["head", v => v.replace(`greenCommit=${l3Fixture.greenCommit}`, `greenCommit=${"0".repeat(40)}`)], ["count", v => v.replace("greenEvidence=", "missingEvidence=")],
    ["digest", v => v.replace(/contractDigest=[a-f0-9]{64}/, `contractDigest=${"0".repeat(64)}`)]]) rejected("verify-controlled-l3-gates.mjs", [state, contract, write(`l3-${name}.txt`, mutate(readFileSync(l3Snapshot, "utf8")))], { cwd: l3Fixture.directory });
  const existing = write("future-final.json", "{}\n"); assert.equal(existsSync(existing), true); rejected("verify-controlled-l3-gates.mjs", [state, contract, l3Snapshot], { cwd: l3Fixture.directory });
});
test("verify-controlled-l3-gates.mjs: malformed argv and pre-Phase3 state fail", () => { rejected("verify-controlled-l3-gates.mjs", [], { cwd: l3Fixture.directory }); const pre = { ...stateObject, currentPhase: "2a" }; rejected("verify-controlled-l3-gates.mjs", [write("pre-state.json", JSON.stringify(pre)), contract, l3Snapshot], { cwd: l3Fixture.directory }); });

test("manager audit: stored f9a35c8d2 controlled-L3 snapshot is rejected against current 05da7b34f HEAD and tree", () => {
  const stored = path.join(feature, "evidence/sprint-1/corrective-green-iteration-1/controlled-l3-gate-snapshot.txt");
  rejected("verify-controlled-l3-gates.mjs", [path.join(feature, "state.json"), contract, stored]);
});
