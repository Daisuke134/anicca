// VSDD RED->GREEN: the genome harness must merge/mutate/id EXPLORATION knobs only, and must
// NEVER be able to touch money-safety caps (MAX_BET_SIZE/MAX_PASS_SPEND/POLY_MIN_ORDER), even
// from a maliciously/accidentally crafted file on disk.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";

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

const KNOB_RANGES = Object.freeze({
  MIN_EDGE: [0.05, 0.4],
  MIN_CONF: [4, 10],
  RESOLVE_HORIZON_DAYS: [3, 30],
  MAX_CANDIDATES: [2, 10],
});

function assertInRange(mutated) {
  for (const [key, [min, max]] of Object.entries(KNOB_RANGES)) {
    assert.ok(
      mutated[key] >= min && mutated[key] <= max,
      `${key}=${mutated[key]} out of [${min},${max}]`,
    );
  }
}

test("mutate() stays within the safe clamp range over many draws (single-step, real Math.random)", () => {
  const genome = { ...SAFE_DEFAULT_GENOME };
  for (let i = 0; i < 2000; i++) {
    assertInRange(mutate(genome));
  }
});

// Adversary MUST-FIX 2 regression guard: MIN_EDGE's declared safe floor is 0.05 — mutate() must
// NEVER let it drop below that, even across many CHAINED (compounding) mutations, where each
// generation's output feeds into the next mutate() call as its input. This is the realistic
// worst case for drift (as opposed to a single step off the default), so it is fuzzed hard: 500
// independent lineages x 50 generations each = 25,000 mutate() calls, real Math.random (no fixed
// seed) — deterministically green regardless of RNG outcome because the clamp is enforced on
// every single step, not just checked at the end.
test("mutate() chained across many generations NEVER breaches [min,max] for any knob (25,000 calls, real RNG)", () => {
  for (let lineage = 0; lineage < 500; lineage++) {
    let g = { ...SAFE_DEFAULT_GENOME };
    for (let gen = 0; gen < 50; gen++) {
      g = mutate(g);
      assertInRange(g);
    }
  }
});

// Adversary MUST-FIX 2, exact scenario: MIN_EDGE already AT its floor (0.05) + a mutate() draw
// that happens to move it further down (-step) must clamp back to EXACTLY 0.05, never 0.02.
test("mutate() clamps MIN_EDGE back to exactly 0.05 when already at the floor and stepping down", () => {
  const atFloor = { ...SAFE_DEFAULT_GENOME, MIN_EDGE: 0.05 };
  // count:1 is passed explicitly so no rng() call is spent on the count decision. rng sequence:
  // [0]=index-pick -> floor(0.1*4)=0 -> "MIN_EDGE" (pool[0]); [1]=direction -> 0.05<0.5 -> -1 (down).
  const sequence = [0.1, 0.05];
  let i = 0;
  const rng = () => sequence[i++ % sequence.length];
  const mutated = mutate(atFloor, { rng, count: 1 });
  assert.equal(mutated.MIN_EDGE, 0.05, "MIN_EDGE must clamp at the 0.05 floor, never dip to 0.02");
});

// A genome fed in with an ALREADY out-of-range value for the SELECTED knob (e.g. a malformed
// override file, or a knob left over from before a range was tightened) must not let mutate()
// compound that violation outward — the base is re-clamped before stepping, in EITHER direction.
// (mutate() only ever touches the 1-2 knobs it randomly selects per call — an unselected knob's
// existing value legitimately passes through untouched by design; this test forces MIN_EDGE to
// be the selected knob via a deterministic rng so the re-anchor guarantee is directly exercised.)
test("mutate() re-anchors an already-out-of-range SELECTED knob to the safe range before stepping", () => {
  const poisoned = { ...SAFE_DEFAULT_GENOME, MIN_EDGE: 0.01 }; // already below the 0.05 floor
  // count:1 explicit (no rng() spent on the count decision). sequence[0]=index-pick ->
  // floor(0.1*4)=0 -> "MIN_EDGE". sequence[1]=direction.
  const stepUp = () => {
    const seq = [0.1, 0.9]; // 0.9>=0.5 -> direction +1
    let i = 0;
    return () => seq[i++ % seq.length];
  };
  const stepDown = () => {
    const seq = [0.1, 0.1]; // 0.1<0.5 -> direction -1
    let i = 0;
    return () => seq[i++ % seq.length];
  };
  const up = mutate(poisoned, { rng: stepUp(), count: 1 });
  const down = mutate(poisoned, { rng: stepDown(), count: 1 });
  assert.equal(up.MIN_EDGE, 0.08, "re-anchored to the 0.05 floor first, THEN +0.03 step");
  assert.equal(down.MIN_EDGE, 0.05, "re-anchored to the 0.05 floor first, THEN -0.03 step clamps back to it");
  assertInRange(up);
  assertInRange(down);
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

// Injection regression test (adversary hardening ask): toExportLines()'s output is `eval`'d
// VERBATIM by run.sh (`eval "$GENOME_ENV"`) — this locks the shQuote() invariant so a future
// refactor can never silently reintroduce a shell-injection hole. Every value here carries a
// DIFFERENT shell metacharacter attack (command chaining, command substitution $(...), backtick
// substitution, and a single-quote breakout attempt) and this test proves — by ACTUALLY running
// the generated lines through a real bash `eval`, not just pattern-matching the string shape —
// that none of the payloads execute and every value round-trips as an inert literal string.
test("toExportLines neutralizes shell metacharacters — no injection survives a real bash eval", () => {
  const dir = tmpDir("genome-inject-");
  const m1 = path.join(dir, "PWNED-semicolon");
  const m2 = path.join(dir, "PWNED-dollar-paren");
  const m3 = path.join(dir, "PWNED-backtick");
  const m4 = path.join(dir, "PWNED-quote-breakout");

  const genome = {
    MIN_EDGE: `0.1; touch ${m1}`, // command-chaining attempt
    MIN_CONF: `$(touch ${m2})`, // command-substitution attempt
    RESOLVE_HORIZON_DAYS: `\`touch ${m3}\``, // backtick-substitution attempt
    MAX_CANDIDATES: `5'; touch ${m4}; echo '`, // single-quote breakout attempt
    EARN_CONSENSUS_MODELS: "nvidia/llama-4-maverick,nvidia/qwen3-next-80b-a3b-instruct,nvidia/mistral-nemotron",
  };
  const maliciousId = `abc\`touch ${dir}/PWNED-id\`123`;
  const lines = toExportLines(genome, maliciousId, true);

  const script =
    lines.join("\n") +
    "\n" +
    'printf "MIN_EDGE=[%s]\\n" "$MIN_EDGE"\n' +
    'printf "MIN_CONF=[%s]\\n" "$MIN_CONF"\n' +
    'printf "RESOLVE_HORIZON_DAYS=[%s]\\n" "$RESOLVE_HORIZON_DAYS"\n' +
    'printf "MAX_CANDIDATES=[%s]\\n" "$MAX_CANDIDATES"\n' +
    'printf "EARN_GENOME_ID=[%s]\\n" "$EARN_GENOME_ID"\n';

  const out = execFileSync("bash", ["-c", script], { encoding: "utf8" });

  for (const marker of [m1, m2, m3, `${dir}/PWNED-id`, m4]) {
    assert.ok(!fs.existsSync(marker), `injection payload must NOT have executed: ${marker}`);
  }
  assert.match(out, /MIN_EDGE=\[0\.1; touch /, "value round-trips as an inert literal, semicolon included verbatim");
  assert.match(out, /MIN_CONF=\[\$\(touch /, "$(...) survives only as inert literal text, never expanded");
  assert.match(out, /RESOLVE_HORIZON_DAYS=\[`touch /, "backticks survive only as inert literal text, never expanded");
  assert.match(out, /MAX_CANDIDATES=\[5'; touch /, "embedded single-quote breakout attempt neutralized, value intact");
  assert.match(out, /EARN_GENOME_ID=\[abc`touch /, "genome_id metacharacters also neutralized");
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
