// dashboard-wallet-legs.js unit tests — pure data lookups, no I/O.
const { test } = require("node:test");
const assert = require("node:assert");
const { legsFor, polymarketAccountFor, polymarketRevenueEnabledFor } = require("../dashboard-wallet-legs");

const CLAUDE_P_ID = "0x02bb6b2af70dbf2c367c1b69aca9858bf3525502";
const FRANKLIN_ID = "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9";

test("claude-p: legs include the base+polygon+hyperliquid treasury (PM deposit read separately via /value)", () => {
  const legs = legsFor(CLAUDE_P_ID);
  const chains = legs.map((l) => l.chain).sort();
  assert.deepStrictEqual(chains, ["base", "hyperliquid", "polygon"]);
  // the PM deposit wallet must NOT appear as a plain balanceOf leg (would double-count against /value)
  assert.ok(!legs.some((l) => l.address.toLowerCase() === "0x904b50d2e214da947d83d6a2d32c4e3ffc17eb74"));
});

test("claude-p: lookup is case-insensitive (EVM id)", () => {
  const legs = legsFor(CLAUDE_P_ID.toUpperCase().replace("0X", "0x"));
  assert.ok(legs.length > 0);
});

test("claude-p: has a Polymarket account configured, WITH revenue override enabled", () => {
  assert.strictEqual(polymarketAccountFor(CLAUDE_P_ID).toLowerCase(), "0x904b50d2e214da947d83d6a2d32c4e3ffc17eb74");
  assert.strictEqual(polymarketRevenueEnabledFor(CLAUDE_P_ID), true);
});

test("Franklin: legs include its own solana wallet PLUS base + hyperliquid (PM deposit read separately via /value)", () => {
  const legs = legsFor(FRANKLIN_ID);
  const chains = legs.map((l) => l.chain).sort();
  assert.deepStrictEqual(chains, ["base", "hyperliquid", "solana"]);
  assert.ok(legs.some((l) => l.chain === "solana" && l.address === FRANKLIN_ID));
});

test("Franklin: has a Polymarket account configured for net worth, but revenue override is OFF (its earn rail is SOL trading, not PM)", () => {
  assert.strictEqual(polymarketAccountFor(FRANKLIN_ID).toLowerCase(), "0xda4b6e34a25fa70a901f30161f1fd6a3ec68219b");
  assert.strictEqual(polymarketRevenueEnabledFor(FRANKLIN_ID), false);
});

test("Franklin: lookup is case-SENSITIVE (base58/solana id) — a lowercased id must NOT match", () => {
  const legs = legsFor(FRANKLIN_ID.toLowerCase());
  assert.deepStrictEqual(legs, []);
});

test("an unknown id has no legs, no Polymarket account, and revenue is not enabled", () => {
  assert.deepStrictEqual(legsFor("0xunknownunknownunknownunknownunknown0000"), []);
  assert.strictEqual(polymarketAccountFor("0xunknownunknownunknownunknownunknown0000"), null);
  assert.strictEqual(polymarketRevenueEnabledFor("0xunknownunknownunknownunknownunknown0000"), false);
});
