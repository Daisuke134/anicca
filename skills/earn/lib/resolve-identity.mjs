// resolve-identity.mjs — per-instance multi-chain identity resolution (#26 EQUALIZE).
//
// The real unequalizer was never identity GENERATION (every instance already gets its own
// EVM + Solana keypair — runtime/compute-proxy/start-local.sh + ensure-solana-wallet.mjs) or
// SLOT access (every instance sees the same live pm/sol/hl slots — earn-slot.mjs). It is that
// each trading engine hardcodes a fixed wallet source (pm-trade → claude-p's agent .env,
// sol-trade → Franklin's ~/.blockrun/.solana-session). This module gives every engine ONE
// place to ask "what is THIS instance's own key" so a fresh spawn can trade with its OWN
// identity, while an existing instance's current resolution path is preserved unchanged.
//
// Priority order (spec 2026-07-05-equalize-multichain-identity-design.md R1/R2):
//   EVM:    ① env.ANICCA_EVM_PRIVATE_KEY  ② $ANICCA_HOME/.automaton/wallet.json (privateKey)
//           ③ $HOME/.automaton/wallet.json (back-compat, legacy shared path)  ④ null
//   Solana: ① env.ANICCA_SOLANA_PRIVATE_KEY  ② $ANICCA_HOME/.automaton/solana.json (secretKey)
//           ③ $HOME/.blockrun/.solana-session (back-compat, Franklin's legacy path)  ④ null
//
// Fail-closed (R5, money-safety): any missing file/field or parse error returns null — this
// module NEVER throws. Callers (run.sh wrappers) must treat null as "skip this engine, warn".
// This module never logs/echoes the key material it reads or returns — that discipline stays
// with the caller (see env-filter.mjs's scrubPrivateKeys / redactPrivateKeyPatterns).

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Reads `field` out of a JSON file. Returns null (never throws) on any read/parse/shape issue.
function readJsonField(filePath, field) {
  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    const value = parsed && parsed[field];
    return typeof value === 'string' && value.length > 0 ? value : null;
  } catch {
    return null;
  }
}

// Reads a raw single-value secret file (e.g. Franklin's `.solana-session`: a bare base58
// string, no JSON wrapper). Returns null (never throws) on any read issue or empty content.
function readRawSecretFile(filePath) {
  try {
    const raw = fs.readFileSync(filePath, 'utf8').trim();
    return raw.length > 0 ? raw : null;
  } catch {
    return null;
  }
}

// viem's generatePrivateKey() already returns a `0x`-prefixed key, but normalize defensively
// (matches the existing convention in skills/earn/ensure-gas.mjs's loadKey()).
function normalizeEvmKey(key) {
  if (typeof key !== 'string' || key.length === 0) return null;
  return key.startsWith('0x') ? key : `0x${key}`;
}

/**
 * Resolve THIS instance's own EVM signing key (immutable, pure read — no mutation, no throw).
 *
 * @param {{home?: string, env?: Record<string, string>}} [opts]
 *   home: explicit ANICCA_HOME override (mainly for tests); defaults to opts.env.ANICCA_HOME.
 *   env:  environment map to read overrides/back-compat HOME from; defaults to process.env.
 * @returns {string|null} `0x`-prefixed private key, or null if unresolvable (fail-closed).
 */
export function resolveEvmPrivateKey({ home, env } = {}) {
  const e = env || process.env;

  const override = normalizeEvmKey(e.ANICCA_EVM_PRIVATE_KEY);
  if (override) return override;

  const aniccaHome = home ?? e.ANICCA_HOME;
  if (aniccaHome) {
    const fromAnicca = readJsonField(path.join(aniccaHome, '.automaton', 'wallet.json'), 'privateKey');
    if (fromAnicca) return normalizeEvmKey(fromAnicca);
  }

  const legacyHome = e.HOME;
  if (legacyHome) {
    const fromLegacy = readJsonField(path.join(legacyHome, '.automaton', 'wallet.json'), 'privateKey');
    if (fromLegacy) return normalizeEvmKey(fromLegacy);
  }

  return null;
}

/**
 * Resolve THIS instance's own Solana signing secret (base58, immutable, pure read — no throw).
 *
 * @param {{home?: string, env?: Record<string, string>}} [opts]
 *   home: explicit ANICCA_HOME override (mainly for tests); defaults to opts.env.ANICCA_HOME.
 *   env:  environment map to read overrides/back-compat HOME from; defaults to process.env.
 * @returns {string|null} base58 secret key, or null if unresolvable (fail-closed).
 */
export function resolveSolanaSecret({ home, env } = {}) {
  const e = env || process.env;

  if (typeof e.ANICCA_SOLANA_PRIVATE_KEY === 'string' && e.ANICCA_SOLANA_PRIVATE_KEY.length > 0) {
    return e.ANICCA_SOLANA_PRIVATE_KEY;
  }

  const aniccaHome = home ?? e.ANICCA_HOME;
  if (aniccaHome) {
    const fromAnicca = readJsonField(path.join(aniccaHome, '.automaton', 'solana.json'), 'secretKey');
    if (fromAnicca) return fromAnicca;
  }

  const legacyHome = e.HOME;
  if (legacyHome) {
    const fromSession = readRawSecretFile(path.join(legacyHome, '.blockrun', '.solana-session'));
    if (fromSession) return fromSession;
  }

  return null;
}

// --- CLI entrypoint: `node resolve-identity.mjs <evm|solana>` prints the resolved key to
// stdout (nothing if unresolved) so bash run.sh wrappers can capture it via command
// substitution — this module itself never logs the key (R5 + env-filter discipline).
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const which = process.argv[2];
  if (which !== 'evm' && which !== 'solana') {
    process.stderr.write('usage: resolve-identity.mjs <evm|solana>\n');
    process.exitCode = 2;
  } else {
    const resolved = which === 'evm' ? resolveEvmPrivateKey({}) : resolveSolanaSecret({});
    if (resolved) process.stdout.write(resolved + '\n');
  }
}
