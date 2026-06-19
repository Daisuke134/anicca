/**
 * config.mjs — Pure: loadConfig(processEnv, dotenvText) → Config
 *
 * REQ-009: Config via env / .env file.
 * - Minimal dotenv parser (KEY=VALUE lines; # comments; blank lines skipped; malformed lines skipped)
 * - Process env wins over .env values (never overwrite)
 * - All paths derive from ANICCA_HOME (never hard-coded literals)
 * - Returns a Config object with all known knobs, typed where relevant
 *
 * PROP-011, PROP-012
 */

const DEFAULTS = {
  OPENAI_BASE_URL:      'http://127.0.0.1:8402/v1',
  // Best FREE model (verified available on BlockRun free tier 2026-06-19). gpt-oss-120b = OpenAI's
  // open model, strong agentic tool-use — the cost-free brain so an Anicca earns with $0 compute.
  // This is the long-run default: prepared skills (yield/invest/x402) + a free model = pure profit.
  ANICCA_FREE_MODEL:    'blockrun/free/gpt-oss-120b',
  ANICCA_LEAN_MODEL:    'blockrun/free/mistral-large-3-675b', // fallback free heavyweight (675B)
  ANICCA_FUNDED_MODEL:  'anthropic/claude-opus-4.8',          // only when surplus funds a frontier decision
  SLEEP_BASE_S:         120,
  SLEEP_ERROR_S:        60,
  SLEEP_LOOP_DETECT_S:  300,
  SKILL_TIMEOUT_S:      120,
  LOOP_DETECT_WINDOW:   3,
  BALANCE_CACHE_TTL_S:  300,
  LEAN_TIER_THRESHOLD:  1.00,
  ANICCA_BRAIN:         'proxy',
  ANICCA_BRAIN_MODEL:   'claude-sonnet-4-6',
};

const INTEGER_KEYS = new Set([
  'SLEEP_BASE_S', 'SLEEP_ERROR_S', 'SLEEP_LOOP_DETECT_S',
  'SKILL_TIMEOUT_S', 'LOOP_DETECT_WINDOW', 'BALANCE_CACHE_TTL_S',
]);

const FLOAT_KEYS = new Set(['LEAN_TIER_THRESHOLD']);

/**
 * Parse a minimal dotenv text.
 * - Lines starting with # are comments
 * - Blank lines are skipped
 * - KEY=VALUE format only; malformed lines are silently skipped
 *
 * @param {string} dotenvText
 * @returns {Record<string, string>}
 */
function parseDotenv(dotenvText) {
  if (!dotenvText || typeof dotenvText !== 'string') return {};
  const result = {};
  for (const rawLine of dotenvText.split('\n')) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const eqIdx = line.indexOf('=');
    if (eqIdx <= 0) continue; // malformed: no key or no `=`
    const key = line.slice(0, eqIdx).trim();
    if (!key || !/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) continue; // invalid key syntax
    const value = line.slice(eqIdx + 1); // value may contain = itself
    result[key] = value;
  }
  return result;
}

/**
 * Build the final config object.
 * Precedence: processEnv > dotenv > DEFAULTS
 *
 * @param {Record<string, string|undefined>} processEnv - typically process.env
 * @param {string} [dotenvText] - contents of $ANICCA_HOME/.env (may be undefined/empty)
 * @returns {Record<string, string|number|undefined>}
 */
export function loadConfig(processEnv, dotenvText) {
  const dotenvValues = parseDotenv(dotenvText || '');
  const config = {};

  // Merge all known keys with precedence: processEnv > dotenvValues > DEFAULTS
  for (const [key, defaultValue] of Object.entries(DEFAULTS)) {
    const raw = processEnv[key] ?? dotenvValues[key] ?? String(defaultValue);
    config[key] = coerce(key, raw);
  }

  // Pass through ANICCA_HOME (required; no default)
  if (processEnv.ANICCA_HOME) {
    config.ANICCA_HOME = processEnv.ANICCA_HOME;
  } else if (dotenvValues.ANICCA_HOME) {
    config.ANICCA_HOME = dotenvValues.ANICCA_HOME;
  } else {
    config.ANICCA_HOME = undefined;
  }

  // Pass through any other env vars the caller may need
  config.ANICCA_WALLET_ADDRESS = processEnv.ANICCA_WALLET_ADDRESS
    ?? dotenvValues.ANICCA_WALLET_ADDRESS
    ?? undefined;

  config.ANICCA_BALANCE_OVERRIDE = processEnv.ANICCA_BALANCE_OVERRIDE
    ?? dotenvValues.ANICCA_BALANCE_OVERRIDE
    ?? undefined;

  config.ANICCA_EARN_SKILL = processEnv.ANICCA_EARN_SKILL
    ?? dotenvValues.ANICCA_EARN_SKILL
    ?? undefined;

  config.EARN_LEDGER = processEnv.EARN_LEDGER
    ?? dotenvValues.EARN_LEDGER
    ?? undefined;

  config.CLAUDE_BIN = processEnv.CLAUDE_BIN
    ?? dotenvValues.CLAUDE_BIN
    ?? undefined;

  return config;
}

function coerce(key, raw) {
  if (raw == null) return undefined;
  const str = String(raw);
  if (INTEGER_KEYS.has(key)) {
    const n = parseInt(str, 10);
    return Number.isNaN(n) ? DEFAULTS[key] : n;
  }
  if (FLOAT_KEYS.has(key)) {
    const n = parseFloat(str);
    return Number.isNaN(n) ? DEFAULTS[key] : n;
  }
  return str;
}
