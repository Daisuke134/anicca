// VSDD RED->GREEN: the genome harness must merge/mutate/id EXPLORATION knobs only, and must
// NEVER be able to touch money-safety caps (MAX_BET_SIZE/MAX_PASS_SPEND/POLY_MIN_ORDER), even
// from a maliciously/accidentally crafted file on disk.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  loadGenome,
  mutate,
  genomeId,
  toExportLines,
  shouldMutateThisPass,
  SAFE_DEFAULT_GENOME,
  KNOB_KEYS,
  FORBIDDEN_CAP_KEYS,
} from "../genome.mjs";

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

test("loadGenome falls back to SAFE_DEFAULT_GENOME when canonical file is missing and no override exists", () => {
  const home = tmpDir("genome-load-");
  const canonicalPath = path.join(home, "does-not-exist-baseline-genome.json");
  const genome = loadGenome({ home, canonicalPath });
  assert.deepEqual(genome, SAFE_DEFAULT_GENOME);
});

test("loadGenome merges canonical baseline + instance override (override wins per-key)", () => {
  const home = tmpDir("genome-merge-");
  const canonicalPath = path.join(home, "baseline-genome.json");
  fs.writeFileSync(canonicalPath, JSON.stringify({ ...SAFE_DEFAULT_GENOME, MIN_EDGE: 0.2 }));

  const stateDir = path.join(home, "skills", "earn", "state");
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, "genome-override.json"), JSON.stringify({ MAX_CANDIDATES: 8 }));

  const genome = loadGenome({ home, canonicalPath });
  assert.equal(genome.MIN_EDGE, 0.2, "canonical baseline value used when override doesn't touch it");
  assert.equal(genome.MAX_CANDIDATES, 8, "instance override wins for the key it sets");
  assert.equal(genome.MIN_CONF, SAFE_DEFAULT_GENOME.MIN_CONF, "untouched knobs keep the safe default");
});

test("loadGenome strips forbidden cap keys even if a malformed file smuggles them in", () => {
  const home = tmpDir("genome-forbidden-");
  const canonicalPath = path.join(home, "baseline-genome.json");
  fs.writeFileSync(
    canonicalPath,
    JSON.stringify({ ...SAFE_DEFAULT_GENOME, MAX_BET_SIZE: 999999, MAX_PASS_SPEND: 999999 }),
  );
  const genome = loadGenome({ home, canonicalPath });
  for (const cap of FORBIDDEN_CAP_KEYS) {
    assert.equal(genome[cap], undefined, `${cap} must never survive loadGenome`);
  }
});

test("mutate() never introduces a forbidden cap key", () => {
  const genome = loadGenome({ home: tmpDir("genome-mutate-caps-"), canonicalPath: "/no/such/file.json" });
  for (let i = 0; i < 50; i++) {
    const mutated = mutate(genome);
    for (const cap of FORBIDDEN_CAP_KEYS) {
      assert.equal(mutated[cap], undefined, `mutate() must never emit ${cap}`);
    }
  }
});

test("mutate() never touches EARN_CONSENSUS_MODELS (categorical, not a numeric knob)", () => {
  const genome = { ...SAFE_DEFAULT_GENOME };
  for (let i = 0; i < 50; i++) {
    const mutated = mutate(genome);
    assert.equal(mutated.EARN_CONSENSUS_MODELS, SAFE_DEFAULT_GENOME.EARN_CONSENSUS_MODELS);
  }
});

test("mutate() stays within the safe clamp range over many draws", () => {
  const genome = { ...SAFE_DEFAULT_GENOME };
  const ranges = {
    MIN_EDGE: [0.05, 0.4],
    MIN_CONF: [4, 10],
    RESOLVE_HORIZON_DAYS: [3, 30],
    MAX_CANDIDATES: [2, 10],
  };
  for (let i = 0; i < 500; i++) {
    const mutated = mutate(genome);
    for (const [key, [min, max]] of Object.entries(ranges)) {
      assert.ok(mutated[key] >= min && mutated[key] <= max, `${key}=${mutated[key]} out of [${min},${max}]`);
    }
  }
});

test("mutate() changes only 1-2 knobs per call (deterministic rng)", () => {
  // rng sequence: first call picks count via (rng()<0.5?1:2) -> feed 0.9 -> count=2;
  // then index draws + direction draws use the remaining sequence.
  const sequence = [0.9, 0.1, 0.4, 0.1, 0.4, 0.1];
  let i = 0;
  const rng = () => sequence[i++ % sequence.length];
  const genome = { ...SAFE_DEFAULT_GENOME };
  const mutated = mutate(genome, { rng });
  let changed = 0;
  for (const key of Object.keys(SAFE_DEFAULT_GENOME)) {
    if (mutated[key] !== genome[key]) changed += 1;
  }
  assert.ok(changed >= 1 && changed <= 2, `expected 1-2 changed knobs, got ${changed}`);
});

test("mutate() returns a NEW object, never mutates its argument (immutability)", () => {
  const genome = { ...SAFE_DEFAULT_GENOME };
  const snapshot = { ...genome };
  mutate(genome);
  assert.deepEqual(genome, snapshot, "input genome object must be untouched");
});

test("genomeId is deterministic regardless of key order", () => {
  const a = { MIN_EDGE: 0.15, MIN_CONF: 7, RESOLVE_HORIZON_DAYS: 14, MAX_CANDIDATES: 5 };
  const b = { MAX_CANDIDATES: 5, RESOLVE_HORIZON_DAYS: 14, MIN_CONF: 7, MIN_EDGE: 0.15 };
  assert.equal(genomeId(a), genomeId(b));
});

test("genomeId differs for different knob values", () => {
  const a = { ...SAFE_DEFAULT_GENOME };
  const b = { ...SAFE_DEFAULT_GENOME, MIN_EDGE: 0.18 };
  assert.notEqual(genomeId(a), genomeId(b));
});

test("genomeId ignores a smuggled forbidden cap key (identity depends only on real knobs)", () => {
  const a = { ...SAFE_DEFAULT_GENOME };
  const b = { ...SAFE_DEFAULT_GENOME, MAX_BET_SIZE: 99999 };
  assert.equal(genomeId(a), genomeId(b));
});

test("toExportLines only ever emits KNOB_KEYS + EARN_GENOME_ID/EARN_GENOME_MUTATED", () => {
  const genome = { ...SAFE_DEFAULT_GENOME, MAX_BET_SIZE: 99999 }; // simulate a bad merge upstream
  const lines = toExportLines(genome, "abc123", true).join("\n");
  assert.match(lines, /export EARN_GENOME_ID='abc123'/);
  assert.match(lines, /export EARN_GENOME_MUTATED='1'/);
  for (const key of KNOB_KEYS) {
    assert.match(lines, new RegExp(`export ${key}=`));
  }
  assert.doesNotMatch(lines, /MAX_BET_SIZE/, "forbidden cap must never be exported by genome.mjs");
  assert.doesNotMatch(lines, /MAX_PASS_SPEND/);
  assert.doesNotMatch(lines, /POLY_MIN_ORDER/);
});

test("shouldMutateThisPass fires exactly every Mth pass", () => {
  const counterFile = path.join(tmpDir("genome-cadence-"), "counter.json");
  const fires = [];
  for (let i = 1; i <= 10; i++) fires.push(shouldMutateThisPass(counterFile, 5));
  assert.deepEqual(fires, [false, false, false, false, true, false, false, false, false, true]);
});

test("shouldMutateThisPass fail-closed: garbage counter file restarts cleanly instead of throwing", () => {
  const dir = tmpDir("genome-cadence-garbage-");
  const counterFile = path.join(dir, "counter.json");
  fs.writeFileSync(counterFile, "{not json");
  assert.doesNotThrow(() => shouldMutateThisPass(counterFile, 3));
});
