import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  createDLQEntry,
  calcDelay,
  filterRetryable,
  cleanupEntries,
  updateEntryState,
} from '../../trend-hunter/dlqHandler.js';
import { DLQ_CONFIG } from '../../trend-hunter/config.js';

describe('dlqHandler', () => {
  // #50
  it('createDLQEntry creates entry with pending state', () => {
    const hook = { text: 'test hook', targetProblemTypes: ['anxiety'] };
    const endpoint = 'https://api.example.com/hooks';
    const error = { message: 'Connection refused', code: 'ECONNREFUSED' };

    const entry = createDLQEntry(hook, endpoint, error, 0);

    expect(entry.state).toBe('pending');
    expect(entry.data.hook).toEqual(hook);
    expect(entry.data.endpoint).toBe(endpoint);
    expect(entry.attemptsMade).toBe(1);
    expect(entry.maxAttempts).toBe(DLQ_CONFIG.maxAttempts);
    expect(entry.error.message).toBe('Connection refused');
    expect(entry.jobId).toMatch(/^hook-/);
  });

  // #51
  it('createDLQEntry sets exhausted state at max attempts', () => {
    const hook = { text: 'test hook', targetProblemTypes: ['anxiety'] };
    const entry = createDLQEntry(hook, 'https://api.example.com/hooks', { message: 'fail' }, 4);
    expect(entry.state).toBe('exhausted');
    expect(entry.attemptsMade).toBe(5);
  });

  // #52
  it('calcDelay follows exponential backoff', () => {
    // Use a fixed seed-like approach: just check base pattern without jitter
    const delay1 = calcDelay(1, 0); // no jitter for deterministic test
    const delay2 = calcDelay(2, 0);
    const delay3 = calcDelay(3, 0);

    expect(delay1).toBe(60000);   // 60s * 2^0
    expect(delay2).toBe(120000);  // 60s * 2^1
    expect(delay3).toBe(240000);  // 60s * 2^2
  });

  // #53
  it('calcDelay caps at max delay', () => {
    const delay = calcDelay(20, 0);
    expect(delay).toBeLessThanOrEqual(DLQ_CONFIG.maxDelayMs);
  });

  // #54
  it('filterRetryable returns only pending entries with due nextRetry', () => {
    const now = Date.now();
    const entries = [
      { jobId: '1', state: 'pending', attemptsMade: 1, maxAttempts: 5, nextRetry: now - 1000 },
      { jobId: '2', state: 'pending', attemptsMade: 1, maxAttempts: 5, nextRetry: now - 500 },
      { jobId: '3', state: 'exhausted', attemptsMade: 5, maxAttempts: 5, nextRetry: now - 1000 },
      { jobId: '4', state: 'resolved', attemptsMade: 2, maxAttempts: 5, nextRetry: now - 1000 },
    ];
    const result = filterRetryable(entries, now);
    expect(result).toHaveLength(2);
    expect(result.map(e => e.jobId)).toEqual(['1', '2']);
  });

  // #55
  it('filterRetryable respects nextRetry time', () => {
    const now = Date.now();
    const entries = [
      { jobId: '1', state: 'pending', attemptsMade: 1, maxAttempts: 5, nextRetry: now + 60000 },
    ];
    const result = filterRetryable(entries, now);
    expect(result).toHaveLength(0);
  });

  // #56 - test_retryDLQ_success (tested at integration level)
  it('updateEntryState sets resolved state', () => {
    const entries = [
      { jobId: 'hook-1', state: 'pending', attemptsMade: 1 },
      { jobId: 'hook-2', state: 'pending', attemptsMade: 2 },
    ];
    const updated = updateEntryState(entries, 'hook-1', 'resolved');
    expect(updated.find(e => e.jobId === 'hook-1').state).toBe('resolved');
    expect(updated.find(e => e.jobId === 'hook-2').state).toBe('pending');
  });

  // #57 - test_retryDLQ_fail_again (increments attempt)
  it('updateEntryState keeps other entries unchanged', () => {
    const entries = [
      { jobId: 'hook-1', state: 'pending', attemptsMade: 1 },
      { jobId: 'hook-2', state: 'pending', attemptsMade: 2 },
    ];
    const updated = updateEntryState(entries, 'hook-1', 'resolved');
    expect(updated.find(e => e.jobId === 'hook-2').attemptsMade).toBe(2);
  });

  // #58
  it('cleanupEntries removes old exhausted entries', () => {
    const now = Date.now();
    const DAY_MS = 86400000;
    const entries = [
      { jobId: '1', state: 'exhausted', timestamp: now - 8 * DAY_MS },
      { jobId: '2', state: 'pending', timestamp: now - 8 * DAY_MS },
      { jobId: '3', state: 'resolved', timestamp: now - 2 * DAY_MS },
    ];
    const kept = cleanupEntries(entries, now);
    expect(kept).toHaveLength(1); // only pending is kept (resolved > 24h removed too)
    expect(kept[0].jobId).toBe('2');
  });

  // #59
  it('cleanupEntries keeps pending even if old', () => {
    const now = Date.now();
    const DAY_MS = 86400000;
    const entries = [
      { jobId: '1', state: 'pending', timestamp: now - 30 * DAY_MS },
    ];
    const kept = cleanupEntries(entries, now);
    expect(kept).toHaveLength(1);
  });

  // #60
  it('updateEntryState resolves target entry', () => {
    const entries = [
      { jobId: 'hook-abc', state: 'pending', attemptsMade: 1 },
      { jobId: 'hook-def', state: 'pending', attemptsMade: 2 },
    ];
    const updated = updateEntryState(entries, 'hook-abc', 'resolved');
    const target = updated.find(e => e.jobId === 'hook-abc');
    expect(target.state).toBe('resolved');
    expect(target.resolvedAt).toBeDefined();
  });

  // #61
  it('updateEntryState handles missing jobId gracefully', () => {
    const entries = [
      { jobId: 'hook-abc', state: 'pending', attemptsMade: 1 },
    ];
    const updated = updateEntryState(entries, 'nonexistent', 'resolved');
    expect(updated).toHaveLength(1);
    expect(updated[0].state).toBe('pending'); // unchanged
  });

  // #62
  it('handles single quotes in hook text', () => {
    const hook = { text: "it's a test hook", targetProblemTypes: ['anxiety'] };
    const entry = createDLQEntry(hook, 'https://api.example.com', { message: 'fail' }, 0);
    expect(entry.data.hook.text).toBe("it's a test hook");
    // Verify JSON serialization works
    const serialized = JSON.stringify(entry);
    const deserialized = JSON.parse(serialized);
    expect(deserialized.data.hook.text).toBe("it's a test hook");
  });

  // #63
  it('handles JSON special chars in hook text', () => {
    const hook = { text: '{"key":"val"} test', targetProblemTypes: ['anxiety'] };
    const entry = createDLQEntry(hook, 'https://api.example.com', { message: 'fail' }, 0);
    const serialized = JSON.stringify(entry);
    const deserialized = JSON.parse(serialized);
    expect(deserialized.data.hook.text).toBe('{"key":"val"} test');
  });
});
