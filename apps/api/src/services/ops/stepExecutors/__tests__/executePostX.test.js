import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../../test/setup.js';

describe('executePostX', () => {
  // T44: test_executePostX_createsXPost
  it('T44: creates XPost record and emits tweet_posted event', async () => {
    prismaMock.xPost.create.mockResolvedValue({
      id: 'xpost-1',
      text: 'test post',
      hookCandidateId: 'hook-1'
    });

    const { executePostX } = await import('../executePostX.js');
    const result = await executePostX({
      input: { content: 'test post', hookId: 'hook-1', verificationScore: 4 },
      missionId: 'mission-1'
    });

    expect(result.output.postId).toBe('xpost-1');
    expect(result.output.platform).toBe('x');
    expect(result.events).toHaveLength(1);
    expect(result.events[0].kind).toBe('tweet_posted');
    expect(result.events[0].payload.postId).toBe('xpost-1');
  });

  it('throws when content is missing', async () => {
    const { executePostX } = await import('../executePostX.js');

    await expect(executePostX({
      input: {},
      missionId: 'mission-1'
    })).rejects.toThrow('post_x requires input.content');
  });
});
