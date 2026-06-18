/**
 * ledger.mjs — Effectful: append-only writes to $ANICCA_HOME/state/ledger.jsonl
 *
 * REQ-007: Only ever appends (O_APPEND). Never rewrites or truncates.
 * Creates parent dir on first write.
 * Disk-full errors logged to stderr; caller sleeps SLEEP_ERROR_S.
 */

import { promises as fs, constants as fsConst } from 'node:fs';
import path from 'node:path';

/**
 * Append a single line to the loop's ledger file.
 * Silently creates the parent directory if absent.
 *
 * @param {string} ledgerPath - absolute path to ledger.jsonl
 * @param {string} line - formatted JSON line (must end with \n)
 * @returns {Promise<void>}
 * @throws {Error} on disk-full or permission errors
 */
export async function appendLedgerLine(ledgerPath, line) {
  await fs.mkdir(path.dirname(ledgerPath), { recursive: true });
  // O_APPEND ensures atomic appends under Linux (writes < PIPE_BUF = 4096 bytes)
  const fh = await fs.open(ledgerPath, 'a');
  try {
    await fh.write(line);
  } finally {
    await fh.close();
  }
}

/**
 * Read the loop's ledger file, returning parsed JSON objects.
 * Missing file → []. Blank/malformed lines skipped.
 *
 * @param {string} ledgerPath
 * @returns {Promise<object[]>}
 */
export async function readLedgerLines(ledgerPath) {
  let raw;
  try {
    raw = await fs.readFile(ledgerPath, 'utf8');
  } catch (err) {
    if (err.code === 'ENOENT') return [];
    throw err;
  }
  return raw
    .split('\n')
    .filter(l => l.trim().length > 0)
    .map(l => { try { return JSON.parse(l); } catch { return null; } })
    .filter(Boolean);
}
