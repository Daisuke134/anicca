/**
 * env-filter.mjs — Pure: scrubPrivateKeys(env) → filteredEnv
 *
 * REQ-004: Private-key isolation.
 * Strips every variable matching: .*_WALLET_KEY | .*_PRIVATE_KEY | .*_PRIV_KEY
 * Returns a new object; never mutates the original.
 *
 * Also exports: redactPrivateKeyPatterns(str) → string
 * Redacts 64-hex private key patterns (0x[0-9a-fA-F]{64}) from strings.
 * A 40-hex wallet address is NOT redacted.
 *
 * PROP-005, PROP-006, PROP-018, PROP-020
 */

const PRIVATE_KEY_REGEX = /(_WALLET_KEY|_PRIVATE_KEY|_PRIV_KEY)$/;

// Matches a full 64-hex private key: 0x followed by exactly 64 hex chars.
// A wallet address (0x + 40 hex) must NOT match this pattern.
const PRIVKEY_PATTERN = /0x[0-9a-fA-F]{64}/g;

/**
 * Returns a new env object with all private-key variables removed.
 * Idempotent: calling twice returns the same filtered result.
 *
 * @param {Record<string, unknown>} env
 * @returns {Record<string, unknown>}
 */
export function scrubPrivateKeys(env) {
  if (!env || typeof env !== 'object') return {};
  const filtered = {};
  for (const [key, value] of Object.entries(env)) {
    if (!PRIVATE_KEY_REGEX.test(key)) {
      filtered[key] = value;
    }
  }
  return filtered;
}

/**
 * Redacts 64-hex private-key patterns from a string.
 * Wallet addresses (40 hex) are untouched.
 *
 * @param {string} str
 * @returns {string}
 */
export function redactPrivateKeyPatterns(str) {
  if (typeof str !== 'string') return String(str ?? '');
  return str.replace(PRIVKEY_PATTERN, '[REDACTED]');
}
