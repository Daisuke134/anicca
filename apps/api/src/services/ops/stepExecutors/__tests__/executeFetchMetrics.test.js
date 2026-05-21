import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../../test/setup.js';

describe('executeFetchMetrics', () => {
  // T46: test_executeFetchMetrics_xBigIntConversion
  it('T46: converts BigInt fields to Number for X posts', async () => {
    prismaMock.opsEvent.findUnique.mockResolvedValue({
      id: 'evt-1',
      kind: 'tweet_posted',
      payload: { postId: 'xpost-1' }
    });

    prismaMock.xPost.findUnique.mockResolvedValue({
      id: 'xpost-1',
      impressionCount: 1000n,
      likeCount: 50n,
      retweetCount: 10n,
      replyCount: 5n,
      engagementRate: 0.065
    });

    const { executeFetchMetrics } = await import('../executeFetchMetrics.js');
    const result = await executeFetchMetrics({
      input: { eventId: 'evt-1' },
      proposalPayload: {}
    });

    expect(result.output.metrics.impressions).toBe(1000);
    expect(typeof result.output.metrics.impressions).toBe('number');
    expect(result.output.metrics.likes).toBe(50);
    expect(result.output.platform).toBe('x');
  });

  // T47: test_executeFetchMetrics_tiktokMetrics
  it('T47: returns tiktok metrics with engagement rate', async () => {
    prismaMock.opsEvent.findUnique.mockResolvedValue({
      id: 'evt-2',
      kind: 'tiktok_posted',
      payload: { postId: 'tiktok-1' }
    });

    prismaMock.tiktokPost.findUnique.mockResolvedValue({
      id: 'tiktok-1',
      viewCount: 5000n,
      likeCount: 250n,
      commentCount: 30n,
      shareCount: 10n
    });

    const { executeFetchMetrics } = await import('../executeFetchMetrics.js');
    const result = await executeFetchMetrics({
      input: { eventId: 'evt-2' },
      proposalPayload: {}
    });

    expect(typeof result.output.metrics.engagementRate).toBe('string');
    expect(parseFloat(result.output.metrics.engagementRate)).toBe(5.00);
    expect(result.output.platform).toBe('tiktok');
  });
});
