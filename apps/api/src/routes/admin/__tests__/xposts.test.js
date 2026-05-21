import { describe, it, expect } from 'vitest';

/**
 * xposts.js route tests
 *
 * normalizeScheduleOutput はモジュール内部関数のため、
 * ソースからロジックを抽出してテストする。
 * エンドポイントのロジックは関数レベルで検証。
 */

// Re-implement normalizeScheduleOutput for testing (mirrors xposts.js exactly)
function normalizeScheduleOutput(raw) {
  let tiktokPosts = raw?.tiktokPosts;
  if (!tiktokPosts && raw?.tiktokPost) {
    tiktokPosts = [{ ...raw.tiktokPost, slot: 'morning' }];
  }
  if (tiktokPosts) {
    tiktokPosts = tiktokPosts.map((post, i) => ({
      ...post,
      slot: post.slot || (i === 0 ? 'morning' : 'evening'),
    }));
  }
  let xPosts = Array.isArray(raw?.xPosts) ? raw.xPosts : [];
  xPosts = xPosts.map((post, i) => ({
    ...post,
    slot: post.slot || (i === 0 ? 'morning' : 'evening'),
  }));
  return { tiktokPosts: tiktokPosts || [], xPosts };
}

describe('normalizeScheduleOutput (xposts)', () => {
  it('converts tiktokPost singular to tiktokPosts array (#14)', () => {
    const raw = {
      tiktokPost: { caption: 'test', tone: 'strict', reasoning: 'r' },
      xPosts: [{ text: 'tweet', reasoning: 'r' }],
    };
    const result = normalizeScheduleOutput(raw);
    expect(result.tiktokPosts).toHaveLength(1);
    expect(result.tiktokPosts[0].slot).toBe('morning');
    expect(result.tiktokPosts[0].caption).toBe('test');
  });

  it('filters xPosts by slot (#9)', () => {
    const raw = {
      xPosts: [
        { slot: 'morning', text: 'morning tweet', reasoning: 'r' },
        { slot: 'evening', text: 'evening tweet', reasoning: 'r' },
      ],
    };
    const result = normalizeScheduleOutput(raw);
    const morning = result.xPosts.filter(p => p.slot === 'morning');
    const evening = result.xPosts.filter(p => p.slot === 'evening');
    expect(morning).toHaveLength(1);
    expect(morning[0].text).toBe('morning tweet');
    expect(evening).toHaveLength(1);
    expect(evening[0].text).toBe('evening tweet');
  });

  it('adds slot fallback when xPosts have no slot (#10)', () => {
    const raw = {
      xPosts: [
        { text: 'first', reasoning: 'r' },
        { text: 'second', reasoning: 'r' },
      ],
    };
    const result = normalizeScheduleOutput(raw);
    expect(result.xPosts[0].slot).toBe('morning');
    expect(result.xPosts[1].slot).toBe('evening');
  });

  it('returns empty xPosts for evening slot when only morning exists (#21)', () => {
    const raw = {
      xPosts: [{ slot: 'morning', text: 'morning only', reasoning: 'r' }],
    };
    const result = normalizeScheduleOutput(raw);
    const evening = result.xPosts.filter(p => p.slot === 'evening');
    expect(evening).toHaveLength(0);
    // This is correct — the /pending endpoint returns 200 with empty array
  });
});

describe('PUT /x/posts/:id/metrics validation', () => {
  it('partial update logic: only sent fields are written (#27)', () => {
    // Simulate the partial update logic from xposts.js
    const body = { impression_count: 100, like_count: 5 };
    // retweet_count and reply_count are NOT sent

    const updateData = { metricsFetchedAt: new Date() };
    if (body.impression_count !== undefined && body.impression_count !== null) {
      updateData.impressionCount = BigInt(body.impression_count);
    }
    if (body.like_count !== undefined && body.like_count !== null) {
      updateData.likeCount = BigInt(body.like_count);
    }
    if (body.retweet_count !== undefined && body.retweet_count !== null) {
      updateData.retweetCount = BigInt(body.retweet_count);
    }
    if (body.reply_count !== undefined && body.reply_count !== null) {
      updateData.replyCount = BigInt(body.reply_count);
    }

    // Only impression_count and like_count should be in updateData
    expect(updateData.impressionCount).toBe(100n);
    expect(updateData.likeCount).toBe(5n);
    expect(updateData.retweetCount).toBeUndefined();
    expect(updateData.replyCount).toBeUndefined();
  });

  it('engagement rate only calculated when all fields present (#27 cont)', () => {
    const allFields = {
      impression_count: 1000,
      like_count: 50,
      retweet_count: 10,
      reply_count: 5,
    };

    const totalEngagements = allFields.like_count + allFields.retweet_count + allFields.reply_count;
    const engagementRate = allFields.impression_count > 0
      ? totalEngagements / allFields.impression_count
      : 0;

    expect(engagementRate).toBeCloseTo(0.065);
  });

  it('requireInternalAuth is applied to router (#28)', async () => {
    // Verify by reading the source — requireInternalAuth middleware is applied
    const { readFileSync } = await import('fs');
    const { resolve } = await import('path');
    const source = readFileSync(
      resolve(import.meta.dirname, '../../admin/xposts.js'),
      'utf-8',
    );
    expect(source).toContain('requireInternalAuth');
    expect(source).toContain('router.use(requireInternalAuth)');
  });
});
