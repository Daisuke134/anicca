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

describe('executeEvaluateHook', () => {
  // T53: test_executeEvaluateHook_shouldPostDecision
  it('T53: returns shouldPost=true with approved event when LLM says true', async () => {
    prismaMock.opsEvent.findUnique.mockResolvedValue({
      id: 'evt-1',
      payload: { hookId: 'hook-1' }
    });

    prismaMock.hookCandidate.findUnique.mockResolvedValue({
      id: 'hook-1',
      text: '6年間何も変われなかった',
      targetProblemTypes: ['procrastination'],
      xEngagementRate: 0.05
    });

    mockCallLLM.mockResolvedValue('shouldPost: true. This hook resonates with our target persona.');

    const { executeEvaluateHook } = await import('../executeEvaluateHook.js');
    const result = await executeEvaluateHook({
      input: { eventId: 'evt-1' },
      proposalPayload: {}
    });

    expect(result.output.shouldPost).toBe(true);
    expect(result.events).toHaveLength(1);
    expect(result.events[0].kind).toBe('hook:approved_for_post');
  });

  it('returns shouldPost=false when hook not found', async () => {
    prismaMock.opsEvent.findUnique.mockResolvedValue({
      id: 'evt-1',
      payload: { hookId: 'nonexistent' }
    });

    prismaMock.hookCandidate.findUnique.mockResolvedValue(null);

    const { executeEvaluateHook } = await import('../executeEvaluateHook.js');
    const result = await executeEvaluateHook({
      input: { eventId: 'evt-1' },
      proposalPayload: {}
    });

    expect(result.output.shouldPost).toBe(false);
  });
});
