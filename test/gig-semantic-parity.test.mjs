import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { cpSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const GIG = join(REPO_ROOT, "skills", "earn", "gig");
const VERIFIER = join(GIG, "scripts", "verify_cutover_parity.py");

test("cutover verifier compares four-lane, funnel, report, and experiment semantics", () => {
  const root = mkdtempSync(join(tmpdir(), "gig-semantic-parity-"));
  const legacy = join(root, "legacy-gig");
  const output = join(root, "parity.json");
  cpSync(GIG, legacy, { recursive: true });

  const result = spawnSync(
    "python3",
    [
      VERIFIER,
      "--legacy-source",
      legacy,
      "--canonical-source",
      GIG,
      "--output",
      output,
    ],
    { encoding: "utf8", timeout: 60_000 },
  );
  assert.equal(
    result.status,
    0,
    `parity verifier failed\nstdout=${result.stdout}\nstderr=${result.stderr}`,
  );
  const report = JSON.parse(readFileSync(output, "utf8"));
  assert.equal(report.status, "PASS");
  assert.equal(report.semantic_equal, true);
  assert.equal(report.four_lane.legacy_exit, 0);
  assert.equal(report.four_lane.canonical_exit, 0);
  assert.equal(report.four_lane.canonical_success_exit, 0);
  assert.equal(report.four_lane.checks_equal, true);
  assert.equal(report.four_lane.path_normalized_pass_body_equal, true);
  assert.equal(report.funnel.equal, true);
  assert.equal(report.funnel.ledger_delta_each, 1);
  assert.equal(report.telegram_envelope.equal, true);
  assert.equal(report.experiment_verdict.equal, true);
  assert.equal(report.duplicate_customer_side_effects, 0);
});
