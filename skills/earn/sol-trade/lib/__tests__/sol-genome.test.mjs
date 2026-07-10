// VCSDD RED->GREEN: SOL genome harness for the pre-gate (franklin-sol-evolvable-edge,
// REQ-001..006, REQ-016). Mirrors skills/earn/lib/genome.mjs's proven shape/tests; SOL-specific
// knob names, mutation ranges, and the SOL_TRADE_MAX_SPEND forbidden cap.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import fc from "fast-check";

import {
  loadGenome,
  mutate,
  genomeId,
  stripForbidden,
  instanceOverridePath,
  SAFE_DEFAULT_GENOME,
  KNOB_KEYS,
  FORBIDDEN_CAP_KEYS,
} from "../sol-genome.mjs";

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

// --- PROP-001 ------------------------------------------------------------------------------
test("PROP-001: SAFE_DEFAULT_GENOME has exactly 5 keys with stated defaults; disjoint from FORBIDDEN_CAP_KEYS", () => {
  assert.deepEqual(Object.keys(SAFE_DEFAULT_GENOME).sort(), [
    "SOL_GATE_MAX_STALENESS_SEC",
    "SOL_GATE_MIN_CONVICTION",
    "SOL_GATE_MIN_LIQUIDITY_USD",
    "SOL_GATE_MIN_MOMENTUM_PCT",
    "SOL_GATE_WATCHLIST",
  ]);
  assert.equal(SAFE_DEFAULT_GENOME.SOL_GATE_MIN_MOMENTUM_PCT, 2.0);
  assert.equal(SAFE_DEFAULT_GENOME.SOL_GATE_MIN_LIQUIDITY_USD, 1000000);
  assert.equal(SAFE_DEFAULT_GENOME.SOL_GATE_MIN_CONVICTION, 6);
  assert.equal(SAFE_DEFAULT_GENOME.SOL_GATE_MAX_STALENESS_SEC, 300);
  assert.equal(SAFE_DEFAULT_GENOME.SOL_GATE_WATCHLIST, "So11111111111111111111111111111111111111112");
  assert.deepEqual([...KNOB_KEYS].sort(), Object.keys(SAFE_DEFAULT_GENOME).sort());
  for (const key of KNOB_KEYS) {
    assert.ok(!FORBIDDEN_CAP_KEYS.includes(key), `${key} must not collide with FORBIDDEN_CAP_KEYS`);
  }
  assert.deepEqual([...FORBIDDEN_CAP_KEYS], ["SOL_TRADE_MAX_SPEND"]);
});

// --- PROP-004 (Tier 2, fast-check) ---------------------------------------------------------
test("PROP-004: stripForbidden() removes SOL_TRADE_MAX_SPEND from every input, incl. adversarially crafted objects", () => {
  fc.assert(
    fc.property(
      fc.dictionary(fc.string(), fc.oneof(fc.integer(), fc.string(), fc.boolean(), fc.constant(null))),
      (obj) => {
        const withCap = { ...obj, SOL_TRADE_MAX_SPEND: 999999 };
        const stripped = stripForbidden(withCap);
        assert.equal(stripped.SOL_TRADE_MAX_SPEND, undefined);
      },
    ),
  );
});

test("PROP-004: stripForbidden() never mutates its input argument (immutability)", () => {
  const input = { ...SAFE_DEFAULT_GENOME, SOL_TRADE_MAX_SPEND: 5 };
  const before = JSON.stringify(input);
  stripForbidden(input);
  assert.equal(JSON.stringify(input), before);
});

// --- PROP-005 --------------------------------------------------------------------------------
test("PROP-005: genomeId is order-independent and cap-presence-independent; differing values -> different ids", () => {
  const g1 = { ...SAFE_DEFAULT_GENOME };
  const g2reordered = Object.fromEntries(Object.entries(SAFE_DEFAULT_GENOME).reverse());
  assert.equal(genomeId(g1), genomeId(g2reordered));

  const withCap = { ...SAFE_DEFAULT_GENOME, SOL_TRADE_MAX_SPEND: 42 };
  assert.equal(genomeId(g1), genomeId(withCap));

  const different = { ...SAFE_DEFAULT_GENOME, SOL_GATE_MIN_MOMENTUM_PCT: 3.5 };
  assert.notEqual(genomeId(g1), genomeId(different));
});

// --- PROP-006 --------------------------------------------------------------------------------
test("PROP-006: loadGenome falls back to SAFE_DEFAULT_GENOME when canonical missing and no override", () => {
  const home = tmpDir("sol-genome-load-");
  const canonicalPath = path.join(home, "does-not-exist-baseline-genome.json");
  const genome = loadGenome({ home, canonicalPath });
  assert.deepEqual(genome, SAFE_DEFAULT_GENOME);
});

test("PROP-006: loadGenome merges canonical + instance override (override wins per-key)", () => {
  const home = tmpDir("sol-genome-merge-");
  const canonicalPath = path.join(home, "baseline-genome.json");
  fs.writeFileSync(canonicalPath, JSON.stringify({ ...SAFE_DEFAULT_GENOME, SOL_GATE_MIN_MOMENTUM_PCT: 3.0 }));

  const stateDir = path.join(home, "skills", "earn", "state");
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, "sol-gate-genome-override.json"), JSON.stringify({ SOL_GATE_MIN_CONVICTION: 8 }));

  const genome = loadGenome({ home, canonicalPath });
  assert.equal(genome.SOL_GATE_MIN_MOMENTUM_PCT, 3.0, "canonical baseline value used when override doesn't touch it");
  assert.equal(genome.SOL_GATE_MIN_CONVICTION, 8, "instance override wins for the key it sets");
  assert.equal(genome.SOL_GATE_MIN_LIQUIDITY_USD, SAFE_DEFAULT_GENOME.SOL_GATE_MIN_LIQUIDITY_USD, "untouched knobs keep the safe default");
});

test("PROP-006: loadGenome strips forbidden cap keys even from a malformed canonical file", () => {
  const home = tmpDir("sol-genome-forbidden-");
  const canonicalPath = path.join(home, "baseline-genome.json");
  fs.writeFileSync(canonicalPath, JSON.stringify({ ...SAFE_DEFAULT_GENOME, SOL_TRADE_MAX_SPEND: 999 }));
  const genome = loadGenome({ home, canonicalPath });
  assert.equal(genome.SOL_TRADE_MAX_SPEND, undefined);
});

test("PROP-006: loadGenome never throws for malformed JSON canonical/override files (fails closed to SAFE_DEFAULT)", () => {
  const home = tmpDir("sol-genome-malformed-");
  const canonicalPath = path.join(home, "baseline-genome.json");
  fs.writeFileSync(canonicalPath, "{not valid json");
  const stateDir = path.join(home, "skills", "earn", "state");
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, "sol-gate-genome-override.json"), "{also not valid");
  assert.doesNotThrow(() => loadGenome({ home, canonicalPath }));
  assert.deepEqual(loadGenome({ home, canonicalPath }), SAFE_DEFAULT_GENOME);
});

test("PROP-006: loadGenome with a missing override file uses baseline alone", () => {
  const home = tmpDir("sol-genome-no-override-");
  const canonicalPath = path.join(home, "baseline-genome.json");
  fs.writeFileSync(canonicalPath, JSON.stringify({ ...SAFE_DEFAULT_GENOME, SOL_GATE_MIN_CONVICTION: 9 }));
  const genome = loadGenome({ home, canonicalPath });
  assert.equal(genome.SOL_GATE_MIN_CONVICTION, 9);
});

test("REQ-006 edge case: ANICCA_HOME unset resolves instanceOverridePath to $HOME/.anicca convention", () => {
  const saved = process.env.ANICCA_HOME;
  delete process.env.ANICCA_HOME;
  try {
    const expected = path.join(process.env.HOME || "", ".anicca", "skills", "earn", "state", "sol-gate-genome-override.json");
    assert.equal(instanceOverridePath(), expected);
  } finally {
    if (saved !== undefined) process.env.ANICCA_HOME = saved;
  }
});

// --- REQ-003 (categorical watchlist knob) ---------------------------------------------------
test("REQ-003 edge case: malformed/empty SOL_GATE_WATCHLIST override fails closed to SAFE_DEFAULT watchlist", () => {
  const home = tmpDir("sol-genome-watchlist-empty-");
  const canonicalPath = path.join(home, "does-not-exist.json");
  const stateDir = path.join(home, "skills", "earn", "state");
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, "sol-gate-genome-override.json"), JSON.stringify({ SOL_GATE_WATCHLIST: "" }));
  const genome = loadGenome({ home, canonicalPath });
  assert.equal(genome.SOL_GATE_WATCHLIST, SAFE_DEFAULT_GENOME.SOL_GATE_WATCHLIST);
});

test("REQ-003 edge case: malformed mint list (non-base58 junk) fails closed to SAFE_DEFAULT watchlist", () => {
  const home = tmpDir("sol-genome-watchlist-malformed-");
  const canonicalPath = path.join(home, "does-not-exist.json");
  const stateDir = path.join(home, "skills", "earn", "state");
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, "sol-gate-genome-override.json"), JSON.stringify({ SOL_GATE_WATCHLIST: "not-a-mint!!" }));
  const genome = loadGenome({ home, canonicalPath });
  assert.equal(genome.SOL_GATE_WATCHLIST, SAFE_DEFAULT_GENOME.SOL_GATE_WATCHLIST);
});

test("REQ-003 acceptance: mutate() output's SOL_GATE_WATCHLIST is byte-identical to its input's, every call", () => {
  const genome = {
    ...SAFE_DEFAULT_GENOME,
    SOL_GATE_WATCHLIST: "So11111111111111111111111111111111111111112,EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  };
  for (let i = 0; i < 50; i++) {
    const mutated = mutate(genome);
    assert.equal(mutated.SOL_GATE_WATCHLIST, genome.SOL_GATE_WATCHLIST);
  }
});

// --- PROP-003 --------------------------------------------------------------------------------
test("PROP-003: mutate() never introduces a forbidden cap key", () => {
  const genome = { ...SAFE_DEFAULT_GENOME };
  for (let i = 0; i < 50; i++) {
    const mutated = mutate(genome);
    for (const cap of FORBIDDEN_CAP_KEYS) {
      assert.equal(mutated[cap], undefined, `mutate() must never emit ${cap}`);
    }
  }
});

test("PROP-003: mutate()'s mutation pool never selects SOL_GATE_WATCHLIST or any FORBIDDEN_CAP_KEYS", () => {
  // repeated single-key mutation draws; the watchlist value (and any forbidden key) must never move.
  const genome = { ...SAFE_DEFAULT_GENOME };
  for (let i = 0; i < 100; i++) {
    const mutated = mutate(genome, { count: 1 });
    assert.equal(mutated.SOL_GATE_WATCHLIST, genome.SOL_GATE_WATCHLIST);
  }
});

// --- PROP-002 (Tier 2, fast-check) -----------------------------------------------------------
const KNOB_RANGES = Object.freeze({
  SOL_GATE_MIN_MOMENTUM_PCT: [0.5, 8.0],
  SOL_GATE_MIN_LIQUIDITY_USD: [100000, 5000000],
  SOL_GATE_MIN_CONVICTION: [3, 10],
  SOL_GATE_MAX_STALENESS_SEC: [60, 900],
});

function assertInRange(mutated) {
  for (const [key, [min, max]] of Object.entries(KNOB_RANGES)) {
    assert.ok(mutated[key] >= min && mutated[key] <= max, `${key}=${mutated[key]} out of [${min},${max}]`);
  }
}

test("PROP-002: mutate() output always within [min,max] for every numeric knob, randomized seeds (property-based)", () => {
  fc.assert(
    fc.property(fc.integer({ min: 0, max: 2 ** 31 - 1 }), (seed) => {
      let state = seed || 1;
      const rng = () => {
        state = (state * 1103515245 + 12345) & 0x7fffffff;
        return state / 0x7fffffff;
      };
      assertInRange(mutate(SAFE_DEFAULT_GENOME, { rng }));
    }),
  );
});

test("PROP-002 edge case: mutate() re-anchors an out-of-range input BEFORE stepping (no outward compounding)", () => {
  // mutate() only ever touches 1-2 of the 4 numeric knobs per call (mirrors genome.mjs exactly --
  // NEVER all 4 at once), so an out-of-range knob is only re-anchored WHEN it is one of the
  // knobs selected this round. This test verifies that per-knob guarantee: set exactly one knob
  // out of range, draw mutate() many times (virtually certain to select it at least once over 200
  // draws from a 4-key, 1-2-per-draw pool), and assert that whenever it IS selected (its value
  // changed from the out-of-range seed), the result lands back in range.
  const oobValues = {
    SOL_GATE_MIN_MOMENTUM_PCT: 999,
    SOL_GATE_MIN_LIQUIDITY_USD: -50,
    SOL_GATE_MIN_CONVICTION: -5,
    SOL_GATE_MAX_STALENESS_SEC: 99999,
  };
  for (const [key, [min, max]] of Object.entries(KNOB_RANGES)) {
    const genome = { ...SAFE_DEFAULT_GENOME, [key]: oobValues[key] };
    let sawMutationOfKey = false;
    for (let i = 0; i < 200; i++) {
      const mutated = mutate(genome);
      if (mutated[key] !== oobValues[key]) {
        sawMutationOfKey = true;
        assert.ok(mutated[key] >= min && mutated[key] <= max, `${key}=${mutated[key]} out of [${min},${max}]`);
      }
    }
    assert.ok(sawMutationOfKey, `expected ${key} to be selected for mutation at least once over 200 draws`);
  }
});

test("PROP-002 edge case: mutate() returns a NEW object; never mutates its input argument", () => {
  const genome = { ...SAFE_DEFAULT_GENOME };
  const before = JSON.stringify(genome);
  mutate(genome);
  assert.equal(JSON.stringify(genome), before);
});

// --- PROP-016 (cross-instance isolation) ------------------------------------------------------
test("PROP-016: instanceOverridePath differs per ANICCA_HOME for arbitrary distinct homes (property-based)", () => {
  fc.assert(
    fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.integer({ min: 0, max: 1_000_000 }), (a, b) => {
      fc.pre(a !== b);
      const homeA = path.join(os.tmpdir(), `sol-gate-home-${a}`);
      const homeB = path.join(os.tmpdir(), `sol-gate-home-${b}`);
      assert.notEqual(instanceOverridePath(homeA), instanceOverridePath(homeB));
    }),
  );
});

test("PROP-016: writing instance A's override file never appears when loading under instance B's home", () => {
  const homeA = tmpDir("sol-gate-isolation-a-");
  const homeB = tmpDir("sol-gate-isolation-b-");
  const overrideA = instanceOverridePath(homeA);
  fs.mkdirSync(path.dirname(overrideA), { recursive: true });
  fs.writeFileSync(overrideA, JSON.stringify({ SOL_GATE_MIN_CONVICTION: 9 }));

  const genomeB = loadGenome({ home: homeB, canonicalPath: path.join(homeB, "no-such-file.json") });
  assert.equal(genomeB.SOL_GATE_MIN_CONVICTION, SAFE_DEFAULT_GENOME.SOL_GATE_MIN_CONVICTION);
});
