// keypair.mjs (tenant, Mac-side ONLY, KEPT-FOR-LATER — see tenant/README.md's "A path not taken"
// section) — generates and persists a SEPARATE, disposable Solana keypair for a PERSISTENT tenant
// identity. This was part of the first pass's in-job design (a funded tenant secret in the job's
// env); the current job (entrypoint.mjs) uses a fresh EPHEMERAL keypair generated inside the
// container instead and does not call this file at all. Kept, tested, and unused: a future
// delegated/capped-spend design would need exactly this — a stable address the treasury can
// `approve` a spending allowance for — see tenant/fund-tenant.mjs's header for the SPL Token
// delegate primitive this would build on.
//
// This is deliberately NOT Franklin's treasury identity (../keypair.mjs's ensureNosanaKeypair /
// skills/earn/lib/resolve-identity.mjs's resolveSolanaSecret). The treasury secret
// ($HOME/.blockrun/.solana-session) is never read, imported, or referenced anywhere in this file —
// structurally impossible to leak here, because this module has no code path that can reach it.
//
// Only ever runs on this Mac, from bin/citizen-tenant-fund. The persistent design this supports
// needs a STABLE address across job lives, which is why this generates a keypair ONCE and persists
// it, rather than minting a fresh one on every deploy (contrast entrypoint.mjs's ephemeral identity,
// which is deliberately re-generated every run).

import fs from "node:fs";
import path from "node:path";

export const TENANT_KEYPAIR_FILE_NAME = "tenant-solana.json";

/**
 * Pure(ish) — no filesystem I/O, but calls the injected keypair constructor, which by default
 * touches real randomness: generate a brand-new tenant keypair. Returns the secret bs58-encoded,
 * matching the encoding Franklin's own treasury secret uses (../keypair.mjs's
 * deriveAddressFromSecret expects this exact format), so the SAME decode path works for both.
 *
 * @param {{keypairCtor?: Function}} [opts]
 * @returns {Promise<{address: string, secretBase58: string}>}
 */
export async function generateTenantKeypair({ keypairCtor } = {}) {
  const Keypair = keypairCtor || (await import("@solana/web3.js")).Keypair;
  const bs58 = (await import("bs58")).default;
  const kp = Keypair.generate();
  const secretBase58 = bs58.encode(kp.secretKey);
  return { address: kp.publicKey.toBase58(), secretBase58 };
}

/**
 * I/O: resolve THIS Mac's persisted tenant keypair, generating + persisting one the first time.
 * Idempotent — a second call against the same ANICCA_HOME returns the SAME address every time
 * (never regenerates over an existing file). Mirrors ../keypair.mjs's materializeKeypairFile
 * discipline: 0700 parent dir, 0600 file, never logs secret material.
 *
 * @param {{env?: Record<string,string>, home?: string, keypairCtor?: Function,
 *          readFileImpl?: Function, writeFileImpl?: Function, existsImpl?: Function}} [opts]
 * @returns {Promise<{address: string, secretBase58: string, keypairPath: string, created: boolean}>}
 */
export async function ensureLocalTenantKeypair({
  env = process.env,
  home,
  keypairCtor,
  readFileImpl = fs.readFileSync,
  writeFileImpl,
  existsImpl = fs.existsSync,
} = {}) {
  const effectiveHome = home ?? env.ANICCA_HOME;
  if (!effectiveHome) {
    throw new Error("ensureLocalTenantKeypair: ANICCA_HOME (or an explicit home) is required to place the tenant keypair file");
  }
  const keypairPath = path.join(effectiveHome, ".automaton", TENANT_KEYPAIR_FILE_NAME);

  if (existsImpl(keypairPath)) {
    let parsed;
    try {
      parsed = JSON.parse(readFileImpl(keypairPath, "utf8"));
    } catch (err) {
      throw new Error(`ensureLocalTenantKeypair: ${keypairPath} exists but could not be parsed: ${err.message}`);
    }
    if (!parsed || typeof parsed.secretBase58 !== "string" || typeof parsed.address !== "string") {
      throw new Error(`ensureLocalTenantKeypair: ${keypairPath} exists but is missing address/secretBase58`);
    }
    return { address: parsed.address, secretBase58: parsed.secretBase58, keypairPath, created: false };
  }

  const generated = await generateTenantKeypair({ keypairCtor });
  const payload = JSON.stringify(
    { address: generated.address, secretBase58: generated.secretBase58, createdAtTs: Date.now() / 1000 },
    null,
    2,
  );
  if (writeFileImpl) {
    writeFileImpl(keypairPath, payload);
  } else {
    const dir = path.dirname(keypairPath);
    fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
    fs.chmodSync(dir, 0o700); // mkdirSync's mode is subject to umask; enforce explicitly.
    fs.writeFileSync(keypairPath, payload, { mode: 0o600 });
    fs.chmodSync(keypairPath, 0o600);
  }
  return { address: generated.address, secretBase58: generated.secretBase58, keypairPath, created: true };
}
