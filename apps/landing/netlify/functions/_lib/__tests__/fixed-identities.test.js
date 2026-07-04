const { test } = require("node:test");
const assert = require("node:assert");
const { FIXED_IDENTITIES, expectedHost } = require("../fixed-identities");

test("claude-p's EVM address (any case) resolves to host 'claude-p'", () => {
  const addr = "0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74"; // mixed-case, as it appears in CLAUDE.md/SSOT
  assert.strictEqual(expectedHost(addr), "claude-p");
  assert.strictEqual(expectedHost(addr.toLowerCase()), "claude-p");
});

test("Franklin's Solana address resolves to host 'Franklin' — exact case only (base58 is case-sensitive)", () => {
  const addr = "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9";
  assert.strictEqual(expectedHost(addr), "Franklin");
  // flipping case must NOT match — base58 is a different address if lowercased/uppercased, and
  // FIXED_IDENTITIES lookup must never .toLowerCase() a Solana id (would corrupt/misroute it).
  assert.notStrictEqual(expectedHost(addr.toLowerCase()), "Franklin");
});

test("an unregistered EVM address falls back to the auto-derived anicca-<hex> scheme", () => {
  const addr = "0x000000000000000000000000000000DEADBEEF".toLowerCase();
  assert.strictEqual(expectedHost(addr), "anicca-" + addr.slice(2, 8));
});

test("FIXED_IDENTITIES contains no private keys — only the two known public addresses", () => {
  const keys = Object.keys(FIXED_IDENTITIES);
  assert.strictEqual(keys.length, 2);
  for (const k of keys) assert.ok(/^0x[a-fA-F0-9]{40}$/.test(k) || /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(k));
});
