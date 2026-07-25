// derive-address.mjs — a deliberately SELF-CONTAINED copy of ../keypair.mjs's
// deriveAddressFromSecret, plus the in-job identity resolver built on top of it.
//
// NOT imported from ../keypair.mjs: tenant/'s in-job code (this file + github-contents-store.mjs +
// report-ledger.mjs + proof.mjs + entrypoint.mjs) has ZERO relative imports outside this directory,
// on purpose. A fresh Nosana container fetches exactly these five files (see job.mjs's
// TENANT_BUNDLE_RELATIVE_FILES) from a pinned commit on the public life-manager repo via plain
// `fetch` — no git, no npm workspace, no monorepo checkout. Reaching into ../keypair.mjs would
// drag in that file's OWN static import of ../../earn/lib/resolve-identity.mjs (irrelevant to the
// tenant identity, which never touches Franklin's treasury secret), which would need fetching too,
// and so on transitively. Keeping the in-job bundle to a fixed, small, self-contained file set is
// judged more robust than chasing the monorepo's import graph from inside an ephemeral container.
//
// Solana's secret-key layout (32-byte seed + 32-byte embedded public key, bs58-encoded) is a
// stable wire format defined by solana-keygen/tweetnacl, not application logic that could
// plausibly drift out from under a hand-copied duplicate — see ../keypair.mjs's own header for the
// original.

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
