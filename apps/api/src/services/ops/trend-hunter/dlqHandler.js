/**
 * dlqHandler — Dead Letter Queue for failed hook saves
 * Pure functions for DLQ entry creation, filtering, cleanup, and state updates.
 * File I/O is handled by the caller (orchestrator or VPS exec).
 */
import { DLQ_CONFIG } from './config.js';

/**
 * Create a DLQ entry for a failed hook save.
 *
 * @param {Object} hook - Hook candidate that failed to save
 * @param {string} endpoint - Railway API endpoint URL
 * @param {{message: string, code?: string}} error - Error details
 * @param {number} [attemptsMade=0] - Previous attempt count
 * @returns {DLQEntry} New DLQ entry
 */
export function createDLQEntry(hook, endpoint, error, attemptsMade = 0) {
  const newAttempts = attemptsMade + 1;
  return {
    jobId: `hook-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    data: { hook, endpoint },
    attemptsMade: newAttempts,
    maxAttempts: DLQ_CONFIG.maxAttempts,
    timestamp: Date.now(),
    nextRetry: Date.now() + calcDelay(newAttempts),
    error: {
      message: error.message || String(error),
      code: error.code || null,
    },
    state: newAttempts >= DLQ_CONFIG.maxAttempts ? 'exhausted' : 'pending',
  };
}

/**
 * Calculate exponential backoff delay with optional jitter.
 *
 * @param {number} attempt - Current attempt number (1-based)
 * @param {number} [jitterOverride] - Override jitter for deterministic testing (0 = no jitter)
 * @returns {number} Delay in milliseconds
 */
export function calcDelay(attempt, jitterOverride) {
  const base = DLQ_CONFIG.baseDelayMs * Math.pow(2, attempt - 1);
  const jitter = jitterOverride !== undefined
    ? jitterOverride
    : (Math.random() * 2 - 1) * DLQ_CONFIG.jitterMs;
  return Math.min(base + jitter, DLQ_CONFIG.maxDelayMs);
}

/**
 * Filter DLQ entries that are ready for retry.
 *
 * @param {DLQEntry[]} entries - All DLQ entries
 * @param {number} [now=Date.now()] - Current timestamp
 * @returns {DLQEntry[]} Entries ready for retry
 */
export function filterRetryable(entries, now = Date.now()) {
  return entries.filter(entry =>
    entry.state === 'pending' &&
    entry.attemptsMade < entry.maxAttempts &&
    now >= entry.nextRetry
  );
}

/**
 * Update the state of a specific DLQ entry.
 *
 * @param {DLQEntry[]} entries - All DLQ entries
 * @param {string} jobId - Target job ID
 * @param {string} newState - New state ('resolved', 'exhausted', etc.)
 * @returns {DLQEntry[]} Updated entries (new array, immutable)
 */
export function updateEntryState(entries, jobId, newState) {
  return entries.map(entry => {
    if (entry.jobId === jobId) {
      return {
        ...entry,
        state: newState,
        resolvedAt: newState === 'resolved' ? Date.now() : undefined,
      };
    }
    return entry;
  });
}

/**
 * Clean up old DLQ entries.
 * - resolved entries > 24h old are removed
 * - exhausted entries > 7 days old are removed
 * - pending entries are never removed
 *
 * @param {DLQEntry[]} entries - All DLQ entries
 * @param {number} [now=Date.now()] - Current timestamp
 * @returns {DLQEntry[]} Kept entries
 */
export function cleanupEntries(entries, now = Date.now()) {
  const DAY_MS = 86400000;
  return entries.filter(entry => {
    if (entry.state === 'resolved' && now - entry.timestamp > DAY_MS) return false;
    if (entry.state === 'exhausted' && now - entry.timestamp > 7 * DAY_MS) return false;
    return true;
  });
}
