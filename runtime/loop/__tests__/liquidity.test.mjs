// VCSDD RED→GREEN: an agent must never strand itself at ~$0 liquid (the root of "zero balance, cannot
// act, begs for a seed"). When liquid USDC is below its OWN compute buffer, the wake prompt must steer it
// to REPLENISH first (close a profitable HL position / withdraw idle yield) and NOT deploy more. The
// numbers are the instance's own (its liquid + its COMPUTE_RESERVE_USDC) — nothing hardcoded per agent.
import { test } from "node:test";
import assert from "node:assert/strict";
import { liquidityDirective } from "../liquidity.mjs";

test("healthy: liquid at/above buffer → no directive", () => {
  assert.equal(liquidityDirective(5.0, 5, true), "");
  assert.equal(liquidityDirective(12.3, 5, false), "");
});

test("below buffer WITH an HL position → steer to CLOSE to realise into liquid", () => {
  const d = liquidityDirective(0.06, 5, true);
  assert.match(d, /BELOW.*BUFFER/i);
  assert.match(d, /close/i);
  assert.match(d, /\$0\.06/);
});

test("below buffer with NO position → steer to withdraw idle yield", () => {
  const d = liquidityDirective(0.5, 5, false);
  assert.match(d, /withdraw/i);
  assert.doesNotMatch(d, /close a profitable HL/i);
});

test("below buffer ALWAYS forbids deploying more", () => {
  assert.match(liquidityDirective(0.06, 5, true), /do not deploy more|don't deploy/i);
});

test("uses the instance's OWN reserve (not a hardcoded 5)", () => {
  // a bigger buffer makes a mid balance 'below'; a smaller one makes it healthy
  assert.notEqual(liquidityDirective(8, 10, true), "");
  assert.equal(liquidityDirective(8, 2, true), "");
});

test("never throws on weird input", () => {
  assert.equal(typeof liquidityDirective(undefined, undefined, undefined), "string");
});
