import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../../test/setup.js';

// Mock callLLM
const mockCallLLM = vi.fn();
vi.mock('../../../../lib/llm.js', () => ({
  callLLM: mockCallLLM
}));

// Mock hookSelector
const mockSelectHookThompson = vi.fn();
vi.mock('../../../hookSelector.js', () => ({
  selectHookThompson: mockSelectHookThompson
}));

beforeEach(() => {
  mockCallLLM.mockReset();
  mockSelectHookThompson.mockReset();
});

describe('executeDraftContent', () => {
  // T34: test_executeDraftContent_returnsContent
  it('T34: returns content with hookId from LLM generation', async () => {
    const mockHooks = [
      {
        id: 'hook-1',
        text: '6年間、何も変われなかった',
        targetProblemTypes: ['procrastination'],
        xEngagementRate: 0.05,
        xSampleSize: 10,
        tiktokLikeRate: 0.03,
        tiktokSampleSize: 5
      }
    ];

    prismaMock.hookCandidate.findMany.mockResolvedValue(mockHooks);
    mockSelectHookThompson.mockReturnValue(mockHooks[0]);
    mockCallLLM.mockResolvedValue('挫折は恥じゃない。6年間の苦しみが、今日の一歩に変わる。');

    const { executeDraftContent } = await import('../executeDraftContent.js');
    const result = await executeDraftContent({
      input: { slot: 'morning' },
      proposalPayload: {},
      skillName: 'x-poster'
    });

    expect(result.output.content).not.toBeNull();
    expect(result.output.content).toContain('挫折');
    expect(result.output.hookId).toBe('hook-1');
    expect(result.output.platform).toBe('x');
    expect(result.events).toEqual([]);
  });

  it('throws when no hook candidates available', async () => {
    prismaMock.hookCandidate.findMany.mockResolvedValue([]);

    const { executeDraftContent } = await import('../executeDraftContent.js');

    await expect(executeDraftContent({
      input: {},
      proposalPayload: {},
      skillName: 'x-poster'
    })).rejects.toThrow('No hook candidates available');
  });
});
