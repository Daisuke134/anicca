// heartbeat.mjs — pure signing/verification core of the S9 steward loop (no I/O, no clock).
//
// A heartbeat entry is third-party-verifiable evidence that the tenant process holding
// Franklin's key was alive at a specific moment: the signed message embeds a fresh Solana
// blockhash + slot (a value that cannot be known before that slot existed on-chain), and the
// ed25519 signature binds it to Franklin's own address (entry.payer). A verifier needs only
// this module (pure check) plus, optionally, an RPC `getBlock(slot)` call to confirm the
// blockhash really belongs to that slot — see bin/citizen-steward --verify.
//
// Money-safety (same convention as keypair.mjs): this module NEVER logs, echoes, or embeds
// secret material in a thrown Error's message. Every throw below names only the offending
// public field.

import nacl from "tweetnacl";
import bs58 from "bs58";

const MESSAGE_KEYS = ["blockhash", "cycle", "jobAddress", "payer", "slot", "ts"];

function isNonEmptyString(v) {
  return typeof v === "string" && v.length > 0;
}

/**
 * Pure: canonical message string for signing — JSON with a FIXED sorted key order so the same
 * fields always produce byte-identical messages regardless of caller property order.
 * Throws (field name only, never values of secret-adjacent data) on any missing/invalid field.
 */
export function buildHeartbeatMessage({ jobAddress, payer, blockhash, slot, ts, cycle } = {}) {
  if (!isNonEmptyString(jobAddress)) throw new Error("buildHeartbeatMessage: jobAddress is required (non-empty string)");
  if (!isNonEmptyString(payer)) throw new Error("buildHeartbeatMessage: payer is required (non-empty string)");
  if (!isNonEmptyString(blockhash)) throw new Error("buildHeartbeatMessage: blockhash is required (non-empty string)");
  if (!Number.isInteger(slot) || slot < 0) throw new Error("buildHeartbeatMessage: slot must be a non-negative integer");
  if (typeof ts !== "number" || !Number.isFinite(ts) || ts <= 0) throw new Error("buildHeartbeatMessage: ts must be a positive number");
  if (!Number.isInteger(cycle) || cycle < 0) throw new Error("buildHeartbeatMessage: cycle must be a non-negative integer");
  // Fixed key order (MESSAGE_KEYS) — do NOT rely on object property insertion order.
  const values = { blockhash, cycle, jobAddress, payer, slot, ts };
  const ordered = {};
  for (const key of MESSAGE_KEYS) ordered[key] = values[key];
  return JSON.stringify(ordered);
}

/**
 * Pure: ed25519 detached signature over the canonical message, base58-encoded.
 * secretBytes = the standard 64-byte Solana secret key (seed + embedded public key).
 */
export function signHeartbeat({ message, secretBytes }) {
  if (!isNonEmptyString(message)) throw new Error("signHeartbeat: message is required (non-empty string)");
  if (!(secretBytes && secretBytes.length === 64)) throw new Error("signHeartbeat: secretBytes must be 64 bytes");
  const sig = nacl.sign.detached(new TextEncoder().encode(message), secretBytes);
  return bs58.encode(sig);
}

/**
 * Pure: build one complete, self-verifying ledger entry. The message itself is NOT stored —
 * verifyHeartbeatEntry rebuilds it from the entry's own public fields, so a tampered field
 * automatically breaks the signature.
 */
export function makeHeartbeatEntry({ jobAddress, payer, blockhash, slot, ts, cycle, secretBytes } = {}) {
  const message = buildHeartbeatMessage({ jobAddress, payer, blockhash, slot, ts, cycle });
  const sig = signHeartbeat({ message, secretBytes });
  return { v: 1, kind: "shelter-heartbeat", ts, cycle, jobAddress, payer, slot, blockhash, sig };
}

/**
 * Pure: verify one entry against its own claimed payer address. Never throws — any structural
 * problem, bad encoding, or signature mismatch returns {valid:false, reason}. Suitable for
 * running over an untrusted jsonl file row by row.
 */
export function verifyHeartbeatEntry(entry) {
  try {
    if (!entry || typeof entry !== "object") return { valid: false, reason: "entry is not an object" };
    if (entry.v !== 1 || entry.kind !== "shelter-heartbeat") {
      return { valid: false, reason: "not a v1 shelter-heartbeat entry" };
    }
    const { jobAddress, payer, blockhash, slot, ts, cycle, sig } = entry;
    const message = buildHeartbeatMessage({ jobAddress, payer, blockhash, slot, ts, cycle });
    if (!isNonEmptyString(sig)) return { valid: false, reason: "sig is missing" };
    let sigBytes;
    let pubkeyBytes;
    try {
      sigBytes = bs58.decode(sig);
      pubkeyBytes = bs58.decode(payer);
    } catch {
      return { valid: false, reason: "sig or payer is not valid base58" };
    }
    if (pubkeyBytes.length !== 32) return { valid: false, reason: "payer does not decode to a 32-byte public key" };
    const ok = nacl.sign.detached.verify(new TextEncoder().encode(message), sigBytes, pubkeyBytes);
    return ok
      ? { valid: true, reason: "signature verifies against entry.payer" }
      : { valid: false, reason: "signature does not verify against entry.payer" };
  } catch (err) {
    return { valid: false, reason: `structurally invalid entry: ${String((err && err.message) || err)}` };
  }
}
