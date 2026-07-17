const { test } = require("node:test");
const assert = require("node:assert");
const { FIXED_IDENTITIES, expectedHost } = require("../fixed-identities");

test("claude-p's dedicated signing identity (any case) resolves to host 'claude-p'", () => {
  // NOT the funded Polymarket proxy (0x904B…) — that's an ERC-1167 smart-contract wallet with no
  // private key, so it can't sign EIP-191. This is the dedicated signing-only identity generated for
  // claude-p's telemetry reports (2026-07-05 finding, see the comment above FIXED_IDENTITIES).
  const addr = "0x02Bb6b2aF70DBf2c367C1B69aCA9858BF3525502";
  assert.strictEqual(expectedHost(addr), "claude-p");
  assert.strictEqual(expectedHost(addr.toLowerCase()), "claude-p");
});

test("Franklin's Solana address resolves to host 'Franklin' — exact case only (base58 is case-sensitive)", () => {
  const addr = "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T";
  assert.strictEqual(expectedHost(addr), "Franklin");
  // flipping case must NOT match — base58 is a different address if lowercased/uppercased, and
  // FIXED_IDENTITIES lookup must never .toLowerCase() a Solana id (would corrupt/misroute it).
  assert.notStrictEqual(expectedHost(addr.toLowerCase()), "Franklin");
});

test("franklin2's Solana address resolves to host 'Franklin2' — exact case only (base58 is case-sensitive)", () => {
  // FIX-1 (2026-07-17): franklin2's own wallet, derived from ~/.franklin2-home/.blockrun/.solana-session
  // the same way telemetry-post-franklin.mjs derives it (last 32 bytes of the secret key, base58).
  const addr = "HyJHSfTkLjpmqeY4FEbnSjM4DfUh9ELGchHqgFDBkrcX";
  assert.strictEqual(expectedHost(addr), "Franklin2");
  assert.notStrictEqual(expectedHost(addr.toLowerCase()), "Franklin2");
});

test("an unregistered EVM address falls back to the auto-derived anicca-<hex> scheme", () => {
  const addr = "0x000000000000000000000000000000DEADBEEF".toLowerCase();
  assert.strictEqual(expectedHost(addr), "anicca-" + addr.slice(2, 8));
});

test("FIXED_IDENTITIES contains no private keys — only the three known public addresses", () => {
  const keys = Object.keys(FIXED_IDENTITIES);
  assert.strictEqual(keys.length, 3);
  for (const k of keys) assert.ok(/^0x[a-fA-F0-9]{40}$/.test(k) || /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(k));
});
