"use strict";
// AE-ZERO-START-1 §4.2 — the tenant agent's own Solana wallet.
//
// The EVM sibling (`agent-wallet.js`) states the two rules this file inherits, for the same reasons: a
// subtly wrong derivation does not fail, it silently sends money nowhere, so derivation is pinned to
// published RFC 8032 vectors in the tests; and the secret must be unable to escape through a log line,
// so nothing printable carries it.
//
// Two things are specific to this rail.
//
// A Solana "secret key" is the 64-byte seed||publicKey pair, base58-encoded — the exact shape
// `Keypair.fromSecretKey(bs58.decode(secret))` consumes (see `runtime/wallet-address-solana.mjs:24-26`).
// Storing that shape rather than a bare seed means the key file this repo writes is directly usable by
// standard Solana tooling later, without a second, divergent representation to keep in sync. The two
// halves are checked against each other on every read: if they disagree, one of them is a lie, and
// signing with it would produce receipts nobody can verify against the stated address.
//
// Every failure message is static. `runtime/wallet-address-solana.mjs:27-31` makes the same choice and
// says why: interpolating either the input or a caught library error's message can echo raw secret
// material straight back into a log line.
const crypto = require("node:crypto");
const { ed25519 } = require("@noble/curves/ed25519.js");
const { base58 } = require("@scure/base");

// The shape the earnings ledger already accepts for a Solana address
// (`lib/earnings-ledger.js` SOLANA_ADDRESS_RE): base58 has no 0, O, I or l.
const SOLANA_ADDRESS_RE = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
const BASE58_RE = /^[1-9A-HJ-NP-Za-km-z]+$/;
const SEED_BYTES = 32;
const SECRET_KEY_BYTES = SEED_BYTES + 32;

// Every spelling a secret has ever reached this codebase under, matched case-insensitively. The set is
// deliberately wider than this module mints, because redaction runs over whole receipts and payloads,
// not just over wallets this file produced.
const SECRET_FIELDS = Object.freeze([
  "privatekey",
  "private_key",
  "secretkey",
  "secret_key",
  "secret",
  "mnemonic",
  "seed",
]);

function decodeBase58(value) {
  if (typeof value !== "string") return null;
  const raw = value.trim();
  if (!raw || !BASE58_RE.test(raw)) return null;
  try {
    return Buffer.from(base58.decode(raw));
  } catch {
    // Swallowed on purpose: the thrown message can quote the malformed input, which may be a secret.
    return null;
  }
}

function publicKeyFromSeed(seed) {
  return Buffer.from(ed25519.getPublicKey(seed));
}

// Pure encoder: turns a 32-byte seed into the canonical base58 64-byte Solana secret key. Kept separate
// from generation so tests can build a key from a published vector without going through entropy.
function encodeSolanaSecretKey(seed) {
  const bytes = Buffer.from(seed || []);
  if (bytes.length !== SEED_BYTES) {
    throw new Error("a Solana secret key seed must be exactly 32 bytes");
  }
  return base58.encode(Buffer.concat([bytes, publicKeyFromSeed(bytes)]));
}

function inspectSolanaSecretKey(value) {
  const decoded = decodeBase58(value);
  if (!decoded || decoded.length !== SECRET_KEY_BYTES) return { ok: false, reason: "shape" };
  const seed = decoded.subarray(0, SEED_BYTES);
  const claimed = Buffer.from(decoded.subarray(SEED_BYTES));
  let derived;
  try {
    derived = publicKeyFromSeed(seed);
  } catch {
    return { ok: false, reason: "shape" };
  }
  if (claimed.length !== derived.length || !crypto.timingSafeEqual(claimed, derived)) {
    return { ok: false, reason: "public-key" };
  }
  return { ok: true, publicKey: derived };
}

function isValidSolanaSecretKey(value) {
  return inspectSolanaSecretKey(value).ok === true;
}

function isSolanaAddress(value) {
  const raw = String(value == null ? "" : value).trim();
  if (!SOLANA_ADDRESS_RE.test(raw)) return false;
  const decoded = decodeBase58(raw);
  return decoded != null && decoded.length === 32;
}

function deriveSolanaAddress(secretKey) {
  const inspected = inspectSolanaSecretKey(secretKey);
  if (inspected.ok) return base58.encode(inspected.publicKey);
  if (inspected.reason === "public-key") {
    throw new Error("Solana secret key does not derive its own embedded public key");
  }
  throw new Error("Solana secret key is not 64 base58-decoded bytes");
}

// The secret is present but non-enumerable, so `JSON.stringify(wallet)` cannot leak it even if a caller
// forgets redactSolanaWallet. The custody writer that genuinely needs it still reads `wallet.secretKey`.
function sealWallet(address, secretKey) {
  const wallet = { address };
  Object.defineProperty(wallet, "secretKey", {
    value: secretKey,
    enumerable: false,
    writable: false,
    configurable: false,
  });
  return Object.freeze(wallet);
}

function generateSolanaAgentWallet(entropySource) {
  const source = typeof entropySource === "function"
    ? entropySource
    : (size) => crypto.randomBytes(size);
  const bytes = Buffer.from(source(SEED_BYTES));
  // Refuse rather than reroll, pad, or truncate. Unlike secp256k1, every 32-byte string is a usable
  // ed25519 seed, so there is no curve check to hide behind: a wrong length or an all-zero draw means
  // the entropy source is broken, and a broken source is exactly the failure that yields a guessable key.
  if (bytes.length !== SEED_BYTES || bytes.every((byte) => byte === 0)) {
    throw new Error("entropy did not yield a usable Solana secret key");
  }
  return sealWallet(base58.encode(publicKeyFromSeed(bytes)), encodeSolanaSecretKey(bytes));
}

// Strip anything secret before a value can reach a log, a ledger, a receipt, or a Telegram payload.
// Applied deeply and through arrays, because a key nested inside a wrapper leaks just as completely as
// a top-level one.
function redactSolanaWallet(value) {
  if (Array.isArray(value)) return value.map(redactSolanaWallet);
  if (!value || typeof value !== "object") return value;
  const out = {};
  for (const [key, nested] of Object.entries(value)) {
    if (SECRET_FIELDS.includes(String(key).toLowerCase())) continue;
    out[key] = redactSolanaWallet(nested);
  }
  return out;
}

module.exports = {
  SECRET_FIELDS,
  SOLANA_ADDRESS_RE,
  deriveSolanaAddress,
  encodeSolanaSecretKey,
  generateSolanaAgentWallet,
  isSolanaAddress,
  isValidSolanaSecretKey,
  redactSolanaWallet,
};
