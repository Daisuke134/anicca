"use strict";
// FIN-a — the Life Manager agent's own wallet.
//
// Spec 10.1 U7 is explicit: the agent generates a NEW wallet and never reuses an existing one, so this
// module only ever mints. Two things are treated as safety-critical rather than stylistic. First,
// derivation is pinned to published Ethereum vectors in the tests, because a subtly wrong address does
// not fail — it silently sends money nowhere. Second, the private key must be unable to escape through a
// log line, so anything we might print goes through redactWallet first.
//
// Node ships SHA3-256, which is NOT the keccak256 Ethereum uses; they differ in padding. The hash and
// the curve therefore come from audited libraries rather than a hand-rolled permutation.
const crypto = require("node:crypto");
const { keccak_256 } = require("@noble/hashes/sha3.js");
const { secp256k1 } = require("@noble/curves/secp256k1.js");

// secp256k1 group order. A key must be in [1, n-1]: zero has no public key, and anything at or above
// the order wraps around to a different, weaker key.
const CURVE_ORDER = BigInt("0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141");
const SECRET_FIELDS = Object.freeze(["privateKey", "private_key", "privatekey", "mnemonic", "seed"]);

function normalise(keyHex) {
  const raw = String(keyHex == null ? "" : keyHex).trim().replace(/^0x/i, "");
  return /^[0-9a-fA-F]{64}$/.test(raw) ? raw.toLowerCase() : null;
}

function isValidPrivateKey(keyHex) {
  const raw = normalise(keyHex);
  if (!raw) return false;
  const value = BigInt(`0x${raw}`);
  return value > 0n && value < CURVE_ORDER;
}

// EIP-55: the address carries its own checksum in the casing of its hex letters, so a typo in a pasted
// address is detectable rather than silently accepted.
function toChecksumAddress(lowercaseHex) {
  const digest = Buffer.from(keccak_256(Buffer.from(lowercaseHex, "ascii"))).toString("hex");
  let out = "";
  for (let index = 0; index < lowercaseHex.length; index++) {
    const character = lowercaseHex[index];
    out += parseInt(digest[index], 16) >= 8 ? character.toUpperCase() : character;
  }
  return `0x${out}`;
}

function deriveAddress(keyHex) {
  if (!isValidPrivateKey(keyHex)) throw new Error("private key is not a usable secp256k1 scalar");
  const raw = normalise(keyHex);
  // Uncompressed public key minus its 0x04 tag; the address is the last 20 bytes of its keccak hash.
  const publicKey = secp256k1.getPublicKey(Buffer.from(raw, "hex"), false).slice(1);
  const hashed = Buffer.from(keccak_256(publicKey)).subarray(-20).toString("hex");
  return toChecksumAddress(hashed);
}

function generateAgentWallet(entropySource) {
  const source = typeof entropySource === "function" ? entropySource : (size) => crypto.randomBytes(size);
  const bytes = Buffer.from(source(32));
  const privateKey = bytes.toString("hex");
  // Refuse rather than reroll: silently retrying would hide a broken entropy source, and a broken
  // source is exactly the failure that produces a guessable key.
  if (bytes.length !== 32 || !isValidPrivateKey(privateKey)) {
    throw new Error("entropy did not yield a usable private key");
  }
  return { address: deriveAddress(privateKey), privateKey };
}

// Strip anything secret before a value can reach a log, a ledger, or an error report. Applied deeply,
// because a key nested inside a wrapper object leaks just as completely as a top-level one.
function redactWallet(value) {
  if (Array.isArray(value)) return value.map(redactWallet);
  if (!value || typeof value !== "object") return value;
  const out = {};
  for (const [key, nested] of Object.entries(value)) {
    if (SECRET_FIELDS.includes(key)) continue;
    out[key] = redactWallet(nested);
  }
  return out;
}

module.exports = { CURVE_ORDER, isValidPrivateKey, deriveAddress, generateAgentWallet, redactWallet, toChecksumAddress };
