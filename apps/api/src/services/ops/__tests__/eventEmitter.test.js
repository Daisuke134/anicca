import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../test/setup.js';

// Mock reactionProcessor
const mockEvaluateReactionMatrix = vi.fn();
vi.mock('../reactionProcessor.js', () => ({
  evaluateReactionMatrix: mockEvaluateReactionMatrix
}));

beforeEach(() => {
  mockEvaluateReactionMatrix.mockReset();
});

describe('emitEvent', () => {
  // T38: test_emitEvent_triggersReactionMatrix
  it('T38: creates event and triggers reaction matrix evaluation', async () => {
    const mockEvent = {
      id: 'evt-1',
      source: 'x-poster',
      kind: 'tweet_posted',
      tags: ['tweet', 'posted'],
      payload: { postId: 'xpost-1' },
      missionId: 'mission-1'
    };

    prismaMock.opsEvent.create.mockResolvedValue(mockEvent);
    mockEvaluateReactionMatrix.mockResolvedValue(undefined);

    const { emitEvent } = await import('../eventEmitter.js');
    const result = await emitEvent('x-poster', 'tweet_posted', ['tweet', 'posted'], { postId: 'xpost-1' }, 'mission-1');

    expect(result.id).toBe('evt-1');
    expect(prismaMock.opsEvent.create).toHaveBeenCalledWith({
      data: {
        source: 'x-poster',
        kind: 'tweet_posted',
        tags: ['tweet', 'posted'],
        payload: { postId: 'xpost-1' },
        missionId: 'mission-1'
      }
    });
    expect(mockEvaluateReactionMatrix).toHaveBeenCalledWith(mockEvent);
  });

  it('still returns event even if reaction matrix fails', async () => {
    prismaMock.opsEvent.create.mockResolvedValue({ id: 'evt-2' });
    mockEvaluateReactionMatrix.mockRejectedValue(new Error('matrix error'));

    const { emitEvent } = await import('../eventEmitter.js');
    const result = await emitEvent('test', 'test_event', [], {});

    expect(result.id).toBe('evt-2');
  });
});
