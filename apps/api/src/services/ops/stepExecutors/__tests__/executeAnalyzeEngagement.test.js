import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../../test/setup.js';

// Mock callLLM
const mockCallLLM = vi.fn();
vi.mock('../../../../lib/llm.js', () => ({
  callLLM: mockCallLLM
}));

beforeEach(() => {
  mockCallLLM.mockReset();
});

describe('executeAnalyzeEngagement', () => {
  // T48: test_executeAnalyzeEngagement_highThreshold
  it('T48: identifies high engagement and updates hook scores', async () => {
    mockCallLLM.mockResolvedValue('1. Good hook\n2. Resonated with audience\n3. Timing was right');

    // Mock finding the post's hookCandidateId
    prismaMock.xPost.findUnique.mockResolvedValue({
      id: 'xpost-1',
      hookCandidateId: 'hook-1'
    });

    // Mock finding the hook candidate
    prismaMock.hookCandidate.findUnique.mockResolvedValue({
      id: 'hook-1',
      xSampleSize: 5,
      xEngagementRate: 0.04,
      tiktokSampleSize: 0,
      tiktokLikeRate: 0
    });

    prismaMock.hookCandidate.update.mockResolvedValue({});

    const { executeAnalyzeEngagement } = await import('../executeAnalyzeEngagement.js');
    const result = await executeAnalyzeEngagement({
      input: {
        metrics: { engagementRate: '6.00', impressions: 1000, likes: 60 },
        postId: 'xpost-1',
        platform: 'x'
      },
      missionId: 'mission-1'
    });

    expect(result.output.isHighEngagement).toBe(true);
    expect(result.events[0].kind).toBe('engagement:high');

    // Verify hook score update was called
    expect(prismaMock.hookCandidate.update).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { id: 'hook-1' }
      })
    );
  });

  it('throws when metrics are missing', async () => {
    const { executeAnalyzeEngagement } = await import('../executeAnalyzeEngagement.js');

    await expect(executeAnalyzeEngagement({
      input: { postId: 'xpost-1', platform: 'x' },
      missionId: 'mission-1'
    })).rejects.toThrow('analyze_engagement requires input.metrics');
  });
});
