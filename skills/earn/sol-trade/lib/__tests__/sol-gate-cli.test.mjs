// VCSDD RED->GREEN: FIND-001 (impl-review iteration-1) wiring proof. mutate()/shouldMutateThisPass
// are correct, well-tested PURE functions (see sol-genome.test.mjs) but the original blocking
// finding was that NOTHING in production wiring ever CALLED them, so the pre-gate's genome_id was
// frozen at baseline forever. This file proves the WIRING itself: sol-gate-cli.mjs (the ONLY
// entrypoint sol-trade/run.sh invokes each pass) actually mutates on the cadence and PERSISTS the
// mutant as the active per-instance override, so genomeId() actually changes across passes.
//
// Hermetic: no real network (SOL_GATE_PRICE_ENDPOINT points at an unreachable local port with a
// short timeout so the fetch fails fast/deterministically -- ECONNREFUSED, never a real HTTP call),
// no real ANICCA_HOME (a fresh tmp dir every test), no real trace files (SOL_GATE_TRACE_PATH /
// SOL_TRADE_TRACE_PATH / SOL_GATE_CACHE_DIR all redirected into the tmp dir).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { instanceOverridePath, genomeId, SAFE_DEFAULT_GENOME } from "../sol-genome.mjs";

const CLI_PATH = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "sol-gate-cli.mjs");
const BASELINE_ID = genomeId(SAFE_DEFAULT_GENOME);

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function runGateOnce(home, extraEnv = {}) {
  const out = execFileSync(process.execPath, [CLI_PATH], {
    encoding: "utf8",
    env: {
      ...process.env,
      ANICCA_HOME: home,
      SOL_GATE_PRICE_ENDPOINT: "http://127.0.0.1:1", // connection-refused, deterministic, no real network
      SOL_GATE_FETCH_TIMEOUT_MS: "200",
      SOL_GATE_TRACE_PATH: path.join(home, "sol-gate.trace.jsonl"),
      SOL_TRADE_TRACE_PATH: path.join(home, "sol-trade.trace.jsonl"),
      SOL_GATE_CACHE_DIR: path.join(home, "sol-gate-cache"),
      ...extraEnv,
    },
  });
  return JSON.parse(out);
}

test("FIND-001: with cadence=1, sol-gate-cli.mjs mutates EVERY pass -- genome_id differs from the frozen baseline id", () => {
  const home = tmpDir("sol-gate-cli-mutate-every-");
  const result = runGateOnce(home, { SOL_GATE_GENOME_MUTATE_EVERY: "1" });
  assert.notEqual(
    result.genome_id,
    BASELINE_ID,
    "FIND-001's exact complaint: genomeId(genome) must NOT be identical to baseline forever once mutation cadence fires",
  );
});

test("FIND-001: mutation is persisted as the active per-instance override -- the override file's own genomeId matches the pass's reported genome_id", () => {
  const home = tmpDir("sol-gate-cli-persist-");
  const result = runGateOnce(home, { SOL_GATE_GENOME_MUTATE_EVERY: "1" });
  const overridePath = instanceOverridePath(home);
  assert.ok(fs.existsSync(overridePath), "a mutation this pass must be persisted to the instance override file");
  const persisted = JSON.parse(fs.readFileSync(overridePath, "utf8"));
  assert.equal(genomeId(persisted), result.genome_id, "the persisted override's content-hash id must match this pass's reported genome_id");
});

test("FIND-001: with a cadence that will NOT fire on pass 1, sol-gate-cli.mjs does NOT mutate -- genome_id stays at baseline, no override file written", () => {
  const home = tmpDir("sol-gate-cli-no-mutate-");
  const result = runGateOnce(home, { SOL_GATE_GENOME_MUTATE_EVERY: "1000000" });
  assert.equal(result.genome_id, BASELINE_ID, "cadence not yet due -- must run the UNMUTATED baseline genome this pass");
  assert.ok(!fs.existsSync(instanceOverridePath(home)), "no mutation this pass -- no override file should be written");
});

test("FIND-001: fail-soft -- sol-gate-cli.mjs never crashes/exits-nonzero even with mutation wiring engaged", () => {
  const home = tmpDir("sol-gate-cli-failsoft-");
  // exits 0 by construction of execFileSync not throwing; assert exact output shape too.
  const result = runGateOnce(home, { SOL_GATE_GENOME_MUTATE_EVERY: "1" });
  assert.equal(typeof result.genome_id, "string");
  assert.ok(["paper", "live"].includes(result.mode));
  assert.ok(["engage", "skip"].includes(result.decision));
});
