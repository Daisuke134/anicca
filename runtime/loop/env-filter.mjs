/**
 * env-filter.mjs — Pure: scrubPrivateKeys(env) → filteredEnv
 *
 * REQ-004: Private-key isolation.
 * Strips every variable matching: .*_WALLET_KEY | .*_PRIVATE_KEY | .*_PRIV_KEY
 * Returns a new object; never mutates the original.
 *
 * Also exports: scrubUserPIIEnv(env) → filteredEnv
 * Strips user-identity PII vars (mirrors identity-guard.mjs USER_PII_ENV_PATTERNS)
 * so the earn skill subprocess never sees them even when the gateway process exports them.
 *
 * Also exports: redactPrivateKeyPatterns(str) → string
 * Redacts 64-hex private key patterns (0x[0-9a-fA-F]{64}) from strings.
 * A 40-hex wallet address is NOT redacted.
 *
 * PROP-005, PROP-006, PROP-018, PROP-020
 */

const PRIVATE_KEY_REGEX = /(_WALLET_KEY|_PRIVATE_KEY|_PRIV_KEY)$/;

// Mirrors skills/_shared/lib/identity-guard.mjs USER_PII_ENV_PATTERNS.
// Any var matching these must never reach an earn skill subprocess (spec 28 §3).
const USER_PII_ENV_PATTERNS = [
  /^USER_/i,
  /GOOGLE_LOGIN/i,
  /COMPOSIO/i,
  /GCAL|GOOGLE_CALENDAR/i,
  /USER.?GMAIL|GMAIL_REFRESH|GMAIL_TOKEN/i,
  /TELEGRAM/i,
  /USER.?PHONE|USER.?CONTACT/i,
];

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
export function scrubUserPIIEnv(env) {
  if (!env || typeof env !== 'object') return {};
  const filtered = {};
  for (const [key, value] of Object.entries(env)) {
    if (!USER_PII_ENV_PATTERNS.some((re) => re.test(key))) {
      filtered[key] = value;
    }
  }
  return filtered;
}

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
