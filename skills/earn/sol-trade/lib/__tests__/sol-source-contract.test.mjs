// VCSDD RED->GREEN: REQ-018 no-evolved-CODE source contract. Mirrors the existing
// execute-yield.mjs deposit-guard wiring test pattern: a static/source-text check that the
// pre-gate's decision/invocation code path never dynamically executes genome-supplied content.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const LIB_DIR = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const FILES = ["sol-genome.mjs", "sol-gate.mjs", "sol-trace.mjs", "sol-evolve.mjs", "sol-gate-cli.mjs"];

test("PROP-018: no eval(/new Function(/genome-value-derived dynamic import anywhere in the pre-gate's decision/invocation code path", () => {
  for (const file of FILES) {
    const filePath = path.join(LIB_DIR, file);
    const src = fs.readFileSync(filePath, "utf8");
    assert.doesNotMatch(src, /\beval\s*\(/, `${file} must not call eval(`);
    assert.doesNotMatch(src, /new\s+Function\s*\(/, `${file} must not use new Function(`);
    // dynamic import() of a bare identifier (a variable) is the genome-value-derived-import smell;
    // static string-literal imports (import("./x.mjs")) are fine and excluded by this pattern.
    assert.doesNotMatch(src, /import\s*\(\s*[a-zA-Z_$][\w$]*\s*\)/, `${file} must not dynamic-import(a variable)`);
  }
});

test("PROP-018 edge case: a malformed genome value never reaches a code-execution sink (decideEngagement fails closed instead)", async () => {
  const { decideEngagement } = await import("../sol-gate.mjs");
  const { SAFE_DEFAULT_GENOME } = await import("../sol-genome.mjs");
  const malformedGenome = { ...SAFE_DEFAULT_GENOME, SOL_GATE_MIN_MOMENTUM_PCT: "eval('1')" };
  const result = decideEngagement({ momentumPct: 5, liquidityUsd: 5_000_000, ageSec: 0, genome: malformedGenome, liveEnabled: true });
  assert.equal(result.wouldEngage, false);
  assert.equal(result.engage, false);
});
