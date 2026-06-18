/**
 * ledger-record.mjs — Pure: formatRecord(fields) → string
 *
 * REQ-007: Ledger immutability — produces one JSON line + newline.
 * No I/O. Deterministic. PROP-007.
 */

/**
 * @param {Record<string, unknown>} fields - must include ts, wake_id, kind, sleep_s
 * @returns {string} - JSON-serialised line ending with \n
 */
export function formatRecord(fields) {
  return JSON.stringify(fields) + '\n';
}
