// VCSDD RED->GREEN: REQ-017 money-safety hard-override choke point. The value actually passed to
// `franklin-trading start --max-spend` MUST be a hard-coded cap that NO env var (genome-derived or
// attacker-preset) can ever override.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const SCRIPT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "resolve-max-spend.sh");

test("PROP-017: attacker-preset SOL_TRADE_MAX_SPEND env has ZERO effect on the resolved --max-spend value", () => {
  const out = execFileSync("bash", [SCRIPT], {
    env: { ...process.env, SOL_TRADE_MAX_SPEND: "999999" },
    encoding: "utf8",
  }).trim();
  assert.equal(out, "0.25");
});

test("PROP-017: resolved value with NO env var set is the SAME hard-coded cap", () => {
  const env = { ...process.env };
  delete env.SOL_TRADE_MAX_SPEND;
  const out = execFileSync("bash", [SCRIPT], { env, encoding: "utf8" }).trim();
  assert.equal(out, "0.25");
});

test("PROP-017 edge case: a genome-shaped env var (SOL_GATE_*) present alongside the attack has zero effect either", () => {
  const out = execFileSync("bash", [SCRIPT], {
    env: { ...process.env, SOL_TRADE_MAX_SPEND: "50", SOL_GATE_MIN_MOMENTUM_PCT: "0.01" },
    encoding: "utf8",
  }).trim();
  assert.equal(out, "0.25");
});
