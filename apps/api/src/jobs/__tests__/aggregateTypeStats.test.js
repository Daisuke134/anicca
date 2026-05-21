/**
 * AggregateTypeStats ジョブのテスト
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { runAggregateTypeStats } from '../aggregateTypeStats.js';

describe('aggregateTypeStats', () => {
  let mockQuery;

  beforeEach(() => {
    mockQuery = vi.fn();
  });

  it('should aggregate type_stats from nudge_events', async () => {
    // Mock INSERT result
    mockQuery.mockResolvedValueOnce({ rowCount: 8 });

    // Mock SELECT result for logging
    mockQuery.mockResolvedValueOnce({
      rows: [
        { type_id: 'T1', tone: 'gentle', sample_size: 100, tap_rate: 0.45, thumbs_up_rate: 0.80 },
        { type_id: 'T2', tone: 'logical', sample_size: 80, tap_rate: 0.38, thumbs_up_rate: 0.75 },
      ],
    });

    const result = await runAggregateTypeStats(mockQuery);

    expect(result.success).toBe(true);
    expect(result.rowCount).toBe(8);

    // Verify INSERT query was called
    expect(mockQuery).toHaveBeenCalledTimes(2);
    const insertCall = mockQuery.mock.calls[0][0];
    expect(insertCall).toContain('INSERT INTO type_stats');
    expect(insertCall).toContain('ON CONFLICT (type_id, tone) DO UPDATE');
  });

  it('should handle empty results gracefully', async () => {
    mockQuery.mockResolvedValueOnce({ rowCount: 0 });
    mockQuery.mockResolvedValueOnce({ rows: [] });

    const result = await runAggregateTypeStats(mockQuery);

    expect(result.success).toBe(true);
    expect(result.rowCount).toBe(0);
  });

  it('should throw on database error', async () => {
    mockQuery.mockRejectedValueOnce(new Error('Connection failed'));

    await expect(runAggregateTypeStats(mockQuery)).rejects.toThrow('Connection failed');
  });

  it('should filter only valid user types (T1-T4)', async () => {
    mockQuery.mockResolvedValueOnce({ rowCount: 4 });
    mockQuery.mockResolvedValueOnce({ rows: [] });

    await runAggregateTypeStats(mockQuery);

    const insertCall = mockQuery.mock.calls[0][0];
    expect(insertCall).toContain("IN ('T1', 'T2', 'T3', 'T4')");
  });

  it('should normalize invalid tones to logical', async () => {
    mockQuery.mockResolvedValueOnce({ rowCount: 4 });
    mockQuery.mockResolvedValueOnce({ rows: [] });

    await runAggregateTypeStats(mockQuery);

    const insertCall = mockQuery.mock.calls[0][0];
    expect(insertCall).toContain("ELSE 'logical'");
  });
});
