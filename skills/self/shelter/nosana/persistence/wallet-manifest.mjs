// wallet-manifest.mjs — builds the addresses-only wallet manifest (S4). Never holds or writes the
// secret itself: resolveSolanaSecret's return value lives only inside this module's call stack,
// only long enough to derive the public address via keypair.mjs's deriveAddressFromSecret (bs58
// decode -> last 32 bytes are the public key), then falls out of scope. Nothing here ever
// serializes the secret or the raw secretBytes — the returned object contains only the derived
// address and a timestamp, exactly like the manifest this module builds is meant to be synced.

import { resolveSolanaSecret } from "../../../../earn/lib/resolve-identity.mjs";
import { deriveAddressFromSecret } from "../keypair.mjs";

/**
 * Resolve THIS environment's own Solana secret (same canonical resolution every other earn/spend
 * engine uses) and derive the addresses-only manifest to sync. Fails closed (throws, secret-free
 * message — same convention as keypair.mjs's ensureNosanaKeypair) if this environment cannot
 * resolve a secret: a manifest can only ever be built by an agent that actually holds its own key.
 *
 * @param {{env?: Record<string,string>, home?: string, now?: () => number}} [opts]
 * @returns {{solanaAddress: string, generatedAtTs: number}}
 */
export function buildWalletManifest({ env = process.env, home, now = () => Date.now() } = {}) {
  const secret = resolveSolanaSecret({ home, env });
  if (!secret) {
    throw new Error(
      "buildWalletManifest: no Solana secret resolved for this instance — cannot build an addresses-only manifest without first resolving identity locally",
    );
  }
  const { address } = deriveAddressFromSecret(secret);
  return { solanaAddress: address, generatedAtTs: now() / 1000 };
}

/**
 * Pure read, for cross-checking a RESTORED manifest against this environment's own identity after
 * a rebuild — never compares secrets, only the derived public address. Returns null (never
 * throws) if this environment cannot resolve a secret, mirroring resolveSolanaSecret's own
 * fail-closed-to-null convention.
 *
 * @param {{env?: Record<string,string>, home?: string}} [opts]
 * @returns {string|null}
 */
export function resolveLocalSolanaAddress({ env = process.env, home } = {}) {
  const secret = resolveSolanaSecret({ home, env });
  if (!secret) return null;
  return deriveAddressFromSecret(secret).address;
}
