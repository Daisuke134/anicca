// keypair.mjs — materializes Franklin's own Solana secret as the `nosana` CLI's expected
// 64-byte JSON-array keypair file. Wallet-rail-only (spec constraint 1): this file IS the
// identity Franklin pays Nosana with — never a second/new wallet (constraint 2). It is derived
// at runtime from the SAME canonical secret skills/earn/lib/resolve-identity.mjs already
// resolves for every other earn/spend engine in this repo, never generated fresh.
//
// Money-safety discipline (constraint 6): this module NEVER logs, echoes, or embeds the raw
// secret (or anything decoded from it) in a thrown Error's message. Every throw site below is
// a static string with no interpolation of secret-derived data — mirrors the existing
// runtime/wallet-address-solana.mjs convention in this monorepo.

import fs from "node:fs";
import path from "node:path";
import bs58 from "bs58";
import { resolveSolanaSecret } from "../../../earn/lib/resolve-identity.mjs";

// Standard Solana secretKey layout (solana-keygen / tweetnacl sign.keyPair): 32-byte seed
// followed by the 32-byte public key. No elliptic-curve derivation needed — the public key is
// already embedded in the last 32 bytes of a valid 64-byte secret key.
const SECRET_KEY_BYTE_LENGTH = 64;
const PUBLIC_KEY_BYTE_LENGTH = 32;

/**
 * Pure: decode a base58 Solana secret key and split out its embedded public key.
 * Never throws with the input echoed back — callers may safely log the thrown message.
 *
 * @param {string} secretBase58
 * @returns {{address: string, secretBytes: Uint8Array}}
 */
export function deriveAddressFromSecret(secretBase58) {
  if (typeof secretBase58 !== "string" || secretBase58.length === 0) {
    throw new Error("deriveAddressFromSecret: secret must be a non-empty string");
  }
  let decoded;
  try {
    decoded = bs58.decode(secretBase58);
  } catch {
    // Deliberately does not interpolate the caught error — bs58 error messages can echo back
    // the offending input.
    throw new Error("deriveAddressFromSecret: secret is not valid base58");
  }
  if (decoded.length !== SECRET_KEY_BYTE_LENGTH) {
    throw new Error(
      `deriveAddressFromSecret: expected a ${SECRET_KEY_BYTE_LENGTH}-byte secret key, got ${decoded.length} bytes`,
    );
  }
  const publicKeyBytes = decoded.subarray(SECRET_KEY_BYTE_LENGTH - PUBLIC_KEY_BYTE_LENGTH);
  return { address: bs58.encode(publicKeyBytes), secretBytes: decoded };
}

/**
 * Materialize the nosana CLI's expected keypair file: a JSON array of the 64 raw secret-key
 * bytes, written 0600 into a 0700 parent dir. Idempotent — overwrites in place on every call
 * for the same secret rather than accumulating stale keypair files. Never logs secretBytes.
 *
 * @param {{secretBytes: Uint8Array, keypairPath: string}} opts
 */
export function materializeKeypairFile({ secretBytes, keypairPath }) {
  if (!(secretBytes && secretBytes.length === SECRET_KEY_BYTE_LENGTH)) {
    throw new Error(`materializeKeypairFile: secretBytes must be ${SECRET_KEY_BYTE_LENGTH} bytes`);
  }
  if (typeof keypairPath !== "string" || keypairPath.length === 0) {
    throw new Error("materializeKeypairFile: keypairPath is required");
  }
  const dir = path.dirname(keypairPath);
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  // mkdirSync's `mode` is subject to umask; enforce the exact bit pattern explicitly so the
  // directory holding the keypair file is never group/world readable regardless of umask.
  fs.chmodSync(dir, 0o700);
  const json = JSON.stringify(Array.from(secretBytes));
  fs.writeFileSync(keypairPath, json, { mode: 0o600 });
  // Same umask concern as above, enforced explicitly for the keypair file itself.
  fs.chmodSync(keypairPath, 0o600);
  return keypairPath;
}

/**
 * Resolve Franklin's own Solana secret (via the canonical resolve-identity.mjs), derive its
 * address, and materialize the CLI keypair file at $ANICCA_HOME/.automaton/nosana_key.json.
 * Fails closed (throws a secret-free error) if the secret cannot be resolved or is malformed —
 * NEVER falls back to generating a new wallet.
 *
 * @param {{env?: Record<string,string>, home?: string}} [opts]
 * @returns {{address: string, keypairPath: string}}
 */
export function ensureNosanaKeypair({ env = process.env, home } = {}) {
  const secret = resolveSolanaSecret({ home, env });
  if (!secret) {
    throw new Error(
      "ensureNosanaKeypair: no Solana secret resolved for this instance — ANICCA_HOME must point at Franklin's home (e.g. $HOME/.blockrun)",
    );
  }
  const effectiveHome = home ?? env.ANICCA_HOME;
  if (!effectiveHome) {
    throw new Error("ensureNosanaKeypair: ANICCA_HOME (or an explicit home) is required to place the keypair file");
  }
  const { address, secretBytes } = deriveAddressFromSecret(secret);
  const keypairPath = path.join(effectiveHome, ".automaton", "nosana_key.json");
  materializeKeypairFile({ secretBytes, keypairPath });
  return { address, keypairPath };
}
