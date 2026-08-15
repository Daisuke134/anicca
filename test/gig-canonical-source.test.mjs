import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const GIG = join(ROOT, "skills/earn/gig");

const REQUIRED_RUNTIME = [
  "SKILL.md",
  "README.md",
  "GIG_PASS_RUNBOOK.md",
  "gig_pass.sh",
  "passprep.py",
  "scripts/experiment_evaluator.py",
  "scripts/gig_healer.py",
  "scripts/telegram_report.py",
  "schemas/gig_b2_result.schema.json",
  "launchd/ai.anicca.hf-gig-pass.plist",
  "tests/test_experiment_evaluator.py",
];

test("Life Manager contains the complete active Gig runtime instead of a tombstone", () => {
  const missing = REQUIRED_RUNTIME.filter((relative) => !existsSync(join(GIG, relative)));

  assert.deepEqual(missing, []);
  assert.equal(existsSync(join(GIG, "MOVED.md")), false);
});

test("runtime-only artifacts and retired archives are not tracked as canonical source", () => {
  assert.equal(existsSync(join(GIG, "artifacts")), false);
  assert.equal(existsSync(join(GIG, "archive")), false);
});
