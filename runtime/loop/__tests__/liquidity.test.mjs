// VCSDD RED→GREEN: an agent must never strand itself at ~$0 liquid (the root of "zero balance, cannot
// act, begs for a seed"). When liquid USDC is below its OWN compute buffer, the wake prompt must steer it
// to REPLENISH first (close a profitable HL / withdraw idle yield) and NOT deploy more. The numbers are
// the instance's own (its liquid + its COMPUTE_RESERVE_USDC) — nothing hardcoded per agent.
import { test } from "node:test";
import assert from "node:assert/strict";
import { liquidityDirective } from "../liquidity.mjs";

test("healthy: liquid at/above buffer → no directive", () => {
  assert.equal(liquidityDirective(5.0, 5), "");
  assert.equal(liquidityDirective(12.3, 5), "");
});

test("below buffer → REPLENISH-FIRST, offers BOTH close-HL and withdraw-yield, forbids deploying", () => {
  const d = liquidityDirective(0.06, 5);
  assert.match(d, /BELOW COMPUTE BUFFER/);
  assert.match(d, /\$0\.06/);
  assert.match(d, /close/i);
  assert.match(d, /withdraw/i);
  assert.match(d, /do NOT deploy more/i);
});

test("uses the instance's OWN reserve (not a hardcoded 5)", () => {
  assert.notEqual(liquidityDirective(8, 10), ""); // bigger buffer → 8 is below
  assert.equal(liquidityDirective(8, 2), "");      // smaller buffer → 8 is healthy
});

test("EDGE: reserve <= 0 (buffer disabled) → no directive", () => {
  assert.equal(liquidityDirective(0, 0), "");
  assert.equal(liquidityDirective(0, -1), "");
});

test("EDGE: negative balance is still 'below buffer' (urgent), never throws", () => {
  const d = liquidityDirective(-3, 5);
  assert.match(d, /BELOW COMPUTE BUFFER/);
  assert.match(d, /\$-3\.0000/);
});

test("EDGE: NaN/undefined inputs → '' (never throws)", () => {
  assert.equal(liquidityDirective(undefined, undefined), "");
  assert.equal(liquidityDirective(NaN, 5), "");
  assert.equal(typeof liquidityDirective("x", "y"), "string");
});
