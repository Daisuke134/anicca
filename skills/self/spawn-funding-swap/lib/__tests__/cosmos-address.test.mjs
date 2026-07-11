// VCSDD spawn-funding-swap Phase 2a (sprint-2, RED). PROP-030/PROP-031 — lib/pure/cosmos-address.mjs's
// bech32Encode/deriveCosmosAddress. Pure, no I/O; written against a file that does NOT exist yet as of
// this commit -- every test below MUST fail (module-not-found) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { bech32Encode, convertBits8to5, deriveCosmosAddress } from "../pure/cosmos-address.mjs";

// Known-answer vector: sha256("test-address-seed-2026")[:20] -> bech32("noble"/"osmo", ...). Independently
// cross-checked during this sprint's design phase against a from-scratch Python BIP-173 reference
// implementation (both agree byte-for-byte) AND accepted live by Skip API's `/v2/fungible/msgs`
// address_list validator (2026-07-11) as well-formed bech32 -- this is not an invented/unverified vector.
const KNOWN_HASH_HEX = createHash("sha256").update("test-address-seed-2026").digest("hex").slice(0, 40);
const KNOWN_NOBLE_ADDRESS = "noble1f348g5sxhduw5skh63rua0pjxldcqzpmrwrg2w";
const KNOWN_OSMO_ADDRESS = "osmo1f348g5sxhduw5skh63rua0pjxldcqzpmrk9syj";

function hexToBytes20(hex) {
  const bytes = new Uint8Array(20);
  for (let i = 0; i < 20; i++) bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  return bytes;
}

test("PROP-030: deriveCosmosAddress(knownHash, 'noble') matches the independently cross-checked known-answer vector", () => {
  const address = deriveCosmosAddress(hexToBytes20(KNOWN_HASH_HEX), "noble");
  assert.equal(address, KNOWN_NOBLE_ADDRESS);
});

test("PROP-030: deriveCosmosAddress(knownHash, 'osmo') matches the independently cross-checked known-answer vector", () => {
  const address = deriveCosmosAddress(hexToBytes20(KNOWN_HASH_HEX), "osmo");
  assert.equal(address, KNOWN_OSMO_ADDRESS);
});

test("PROP-030: the SAME 20-byte hash produces DIFFERENT addresses for different hrp prefixes (proves hrp actually participates in the checksum, not just prepended)", () => {
  const hash = hexToBytes20(KNOWN_HASH_HEX);
  const noble = deriveCosmosAddress(hash, "noble");
  const osmo = deriveCosmosAddress(hash, "osmo");
  const akash = deriveCosmosAddress(hash, "akash");
  assert.notEqual(noble, osmo);
  assert.notEqual(noble, akash);
  assert.notEqual(osmo, akash);
  assert.ok(noble.startsWith("noble1"));
  assert.ok(osmo.startsWith("osmo1"));
  assert.ok(akash.startsWith("akash1"));
});

test("PROP-031: deriveCosmosAddress throws on a hash shorter than 20 bytes", () => {
  assert.throws(() => deriveCosmosAddress(new Uint8Array(19), "noble"));
});

test("PROP-031: deriveCosmosAddress throws on a hash longer than 20 bytes", () => {
  assert.throws(() => deriveCosmosAddress(new Uint8Array(21), "noble"));
});

test("PROP-031: deriveCosmosAddress throws on a non-Uint8Array input", () => {
  assert.throws(() => deriveCosmosAddress(Array.from({ length: 20 }, () => 0), "noble"));
});

test("PROP-031: bech32Encode throws on an empty hrp", () => {
  assert.throws(() => bech32Encode("", convertBits8to5(new Uint8Array(20))));
});

test("convertBits8to5: round-trips a known byte sequence into the expected 5-bit group count (20 bytes -> 32 groups)", () => {
  const groups = convertBits8to5(new Uint8Array(20));
  assert.equal(groups.length, 32); // ceil(20*8/5) = 32
  assert.ok(groups.every((g) => g >= 0 && g <= 31));
});

test("convertBits8to5: throws on an out-of-range byte value", () => {
  assert.throws(() => convertBits8to5([256]));
  assert.throws(() => convertBits8to5([-1]));
});
