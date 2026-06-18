/**
 * dotenv.mjs — Effectful: reads $ANICCA_HOME/.env from disk.
 *
 * REQ-009: .env path always derived from ANICCA_HOME env var.
 * Never hard-codes ~/.anicca or any literal path.
 * Returns empty string if file is absent (not an error).
 */

import { promises as fs } from 'node:fs';
import path from 'node:path';

/**
 * Read the .env file from $ANICCA_HOME/.env.
 *
 * @param {string} anicca_home - value of ANICCA_HOME env var
 * @returns {Promise<string>} - raw file contents (or '' if absent)
 */
export async function readDotenvFile(anicca_home) {
  if (!anicca_home) return '';
  const envPath = path.join(anicca_home, '.env');
  try {
    return await fs.readFile(envPath, 'utf8');
  } catch (err) {
    if (err.code === 'ENOENT') return '';
    // Other errors (permissions etc.) — log to stderr, return empty
    process.stderr.write(`[loop] dotenv read error: ${err.message}\n`);
    return '';
  }
}
