// derive-address.mjs (Mac-side / kept-for-later — NOT part of the current job's in-job bundle) —
// a deliberately SELF-CONTAINED copy of ../keypair.mjs's deriveAddressFromSecret, plus
// resolveTenantSecretForJob, an in-job-shaped identity resolver built on top of it.
//
// HISTORY: this file WAS part of the first pass's in-job bundle (a funded, persistent tenant
// identity whose secret was resolved here from a job env var). That design was replaced — see
// tenant/README.md's "The finding that forced the redesign" — with an EPHEMERAL identity
// (`Keypair.generate()`, no secret at all) generated directly in entrypoint.mjs. This file is no
// longer imported by anything except its own tests; it is kept because `resolveTenantSecretForJob`
// and `deriveAddressFromSecret` are exactly the building blocks a future persistent/funded/
// delegated-spend in-job identity would need again (see tenant/README.md's "A path not taken"
// section) — not resurrected speculatively, but not deleted either.
//
// NOT imported from ../keypair.mjs: Solana's secret-key layout (32-byte seed + 32-byte embedded
// public key, bs58-encoded) is a stable wire format defined by solana-keygen/tweetnacl, not
// application logic that could plausibly drift out from under a hand-copied duplicate — see
// ../keypair.mjs's own header for the original. Keeping this self-contained (zero imports beyond
// bs58) means it could be dropped back into a future in-job bundle without dragging in
// ../keypair.mjs's own static import of ../../earn/lib/resolve-identity.mjs.

import bs58 from "bs58";

const SECRET_KEY_BYTE_LENGTH = 64;
const PUBLIC_KEY_BYTE_LENGTH = 32;

/**
 * Pure: decode a base58 Solana secret key and split out its embedded public key. Never throws
 * with the input echoed back — callers may safely log the thrown message.
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
    // Deliberately does not interpolate the caught error — bs58 error messages can echo back the
    // offending input.
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
 * Fail-closed, in-job identity resolution: reads ONLY env.NOSANA_TENANT_SECRET_KEY (the disposable
 * tenant secret injected as this job's own env var at post time — see job.mjs's
 * buildTenantJobDefinition). Never touches disk, never falls back to generating a new identity — a
 * job that cannot resolve its own tenant secret must fail loudly rather than silently mint a new,
 * unrecognized address that would break continuity with the tenant's prior incarnations.
 *
 * @param {{env?: Record<string,string>}} [opts]
 * @returns {{address: string, secretBytes: Uint8Array}}
 */
export function resolveTenantSecretForJob({ env = process.env } = {}) {
  const secret = env.NOSANA_TENANT_SECRET_KEY;
  if (typeof secret !== "string" || secret.length === 0) {
    throw new Error("resolveTenantSecretForJob: NOSANA_TENANT_SECRET_KEY is not set — this job cannot identify itself");
  }
  return deriveAddressFromSecret(secret);
}
