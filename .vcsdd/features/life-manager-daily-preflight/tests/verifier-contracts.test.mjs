import assert from "node:assert/strict";
import { existsSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../../../..");
const fixtureRoot = mkdtempSync(path.join(tmpdir(), "core8d-verifier-red-"));
const sourceSnapshot = path.join(fixtureRoot, "source-snapshot.txt");
const state = path.join(root, ".vcsdd/features/life-manager-daily-preflight/state.json");
const contract = path.join(root, ".vcsdd/features/life-manager-daily-preflight/contracts/sprint-1.md");
const report = path.join(fixtureRoot, "report.json");
writeFileSync(sourceSnapshot, "baselineCommit=58846034b4505f585bd8b4ea3fbcaa04c38e31bc\nbaselineTree=3432afc948ec99fb3a6b78c5c29586693b561649\ngreenCommit=8bac59bb0e9902fdbd3afdefd5550b9220ffecac\ngreenTree=3432afc948ec99fb3a6b78c5c29586693b561649\n");
writeFileSync(report, "{}\n", { mode: 0o600 });

function run(helper, args) {
  const target = path.join(here, helper);
  assert.equal(existsSync(target), true, `missing Phase 2 helper: ${helper}`);
  return spawnSync(process.execPath, [target, ...args], { cwd: root, encoding: "utf8", env: { PATH: process.env.PATH ?? "" } });
}

const contracts = [
  ["verify-phase2-process.mjs", ["gates", state, contract], ["bogus"], ["gates", state, path.join(fixtureRoot, "stale-contract.md")]],
  ["verify-final-artifact.mjs", [report, sourceSnapshot], [], [report, path.join(fixtureRoot, "wrong-snapshot.txt")]],
  ["verify-safe-scan.mjs", ["--paths", "apps/life-call", ".vcsdd/features/life-manager-daily-preflight", "--exclude-historical-json", "--allow-utc-timestamps"], ["--unknown"], ["--paths", path.join(fixtureRoot, "stale")]],
  ["verify-controlled-l3-gates.mjs", [state, contract, sourceSnapshot], [], [state, contract, path.join(fixtureRoot, "wrong-snapshot.txt")]],
];

for (const [helper, valid, malformed, stale] of contracts) {
  test(`${helper}: accepts one valid explicit input`, () => { const r = run(helper, valid); assert.equal(r.status, 0); assert.equal(r.stdout, ""); });
  test(`${helper}: rejects missing or malformed argv`, () => { const r = run(helper, malformed); assert.notEqual(r.status, 0); assert.doesNotMatch(r.stderr, /token|secret|credential/i); });
  test(`${helper}: rejects stale or wrong-snapshot input`, () => { const r = run(helper, stale); assert.notEqual(r.status, 0); assert.doesNotMatch(r.stderr, /token|secret|credential/i); });
}
