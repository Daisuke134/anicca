import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../../test/setup.js';

describe('executePostTiktok', () => {
  beforeEach(() => {
    delete process.env.BLOTATO_API_KEY;
    delete process.env.BLOTATO_TIKTOK_ACCOUNT_ID;
    delete process.env.BLOTATO_ACCOUNT_ID_EN;
    global.fetch = vi.fn();
  });

  // T45: test_executePostTiktok_createsTiktokPost
  it('T45: creates TiktokPost record and emits tiktok_posted event', async () => {
    prismaMock.tiktokPost.create.mockResolvedValue({
      id: 'tiktok-1',
      caption: 'test tiktok post',
      hookCandidateId: 'hook-1'
    });

    const { executePostTiktok } = await import('../executePostTiktok.js');
    const result = await executePostTiktok({
      input: { content: 'test tiktok post', hookId: 'hook-1', verificationScore: 4 },
      missionId: 'mission-1'
    });

    expect(result.output.postId).toBe('tiktok-1');
    expect(result.output.platform).toBe('tiktok');
    expect(result.events).toHaveLength(1);
    expect(result.events[0].kind).toBe('tiktok_posted');
  });

  it('posts to Blotato when TikTok credentials are set and includes required target fields', async () => {
    process.env.BLOTATO_API_KEY = 'blt_test';
    process.env.BLOTATO_TIKTOK_ACCOUNT_ID = 'tt_123';
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ postSubmissionId: 'sub_1' })
    });

    prismaMock.tiktokPost.create.mockResolvedValue({
      id: 'tiktok-2',
      caption: 'hello',
      blotatoPostId: 'sub_1'
    });

    const { executePostTiktok } = await import('../executePostTiktok.js');
    const result = await executePostTiktok({
      input: {
        content: 'hello',
        verificationScore: 5,
        mediaUrls: ['https://cdn.example.com/post.jpg']
      },
      missionId: 'mission-2'
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [, req] = global.fetch.mock.calls[0];
    const body = JSON.parse(req.body);
    expect(body.post.accountId).toBe('tt_123');
    expect(body.post.content.mediaUrls).toEqual(['https://cdn.example.com/post.jpg']);
    expect(body.post.target.privacyLevel).toBe('PUBLIC_TO_EVERYONE');
    expect(body.post.target.disabledComments).toBe(false);
    expect(body.post.target.disabledDuet).toBe(false);
    expect(body.post.target.disabledStitch).toBe(false);
    expect(body.post.target.isBrandedContent).toBe(false);
    expect(body.post.target.isYourBrand).toBe(false);
    expect(body.post.target.isAiGenerated).toBe(false);
    expect(result.events[0].payload.blotatoPostId).toBe('sub_1');
  });

  it('throws when credentials are set but mediaUrls are missing', async () => {
    process.env.BLOTATO_API_KEY = 'blt_test';
    process.env.BLOTATO_TIKTOK_ACCOUNT_ID = 'tt_123';
    const { executePostTiktok } = await import('../executePostTiktok.js');

    await expect(executePostTiktok({
      input: { content: 'hello' },
      missionId: 'mission-3'
    })).rejects.toThrow('post_tiktok requires at least one media URL');
  });

  it('throws when content is missing', async () => {
    const { executePostTiktok } = await import('../executePostTiktok.js');

    await expect(executePostTiktok({
      input: {},
      missionId: 'mission-1'
    })).rejects.toThrow('post_tiktok requires input.content');
  });
});
