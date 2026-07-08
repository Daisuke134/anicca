/**
 * address-classify.mjs — Pure: chain-shape classification for wallet addresses.
 *
 * REQ-002 (franklin-loop-revival): `fetchUsdcBalance` must dispatch by the wallet's actual chain
 * shape instead of hard-validating EVM-only. This module supplies the pure predicate that
 * dispatch reads — no I/O, no network, deterministic string-shape check only
 * (verification-architecture.md Purity Boundary Map / PROP-001).
 *
 * `isSolanaAddress` reuses the SAME base58 alphabet/length window already defined and verified at
 * skills/_shared/lib/solana-verify.mjs's `B58_RE` (32-90 chars) — no new alphabet invented.
 */

// EVM: 0x + exactly 40 hex chars (case-insensitive — checksummed addresses mix case).
const EVM_RE = /^0x[0-9a-fA-F]{40}$/;

// base58 alphabet (no 0 O I l), 32-90 chars — identical window to solana-verify.mjs's B58_RE.
const SOLANA_RE = /^[1-9A-HJ-NP-Za-km-z]{32,90}$/;

/**
 * @param {unknown} address
 * @returns {boolean} true iff address is a well-formed `0x`+40-hex EVM address.
 */
export function isEvmAddress(address) {
  return typeof address === 'string' && EVM_RE.test(address);
}

/**
 * @param {unknown} address
 * @returns {boolean} true iff address is a well-formed base58 Solana-shaped string.
 */
export function isSolanaAddress(address) {
  return typeof address === 'string' && SOLANA_RE.test(address);
}

/**
 * @param {unknown} address
 * @returns {'evm'|'solana'|'invalid'} exactly one classification, never throws.
 */
export function classifyAddress(address) {
  if (isEvmAddress(address)) return 'evm';
  if (isSolanaAddress(address)) return 'solana';
  return 'invalid';
}
