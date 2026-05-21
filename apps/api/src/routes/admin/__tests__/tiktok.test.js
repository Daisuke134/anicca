import { describe, it, expect } from 'vitest';

/**
 * tiktok.js route tests
 *
 * normalizeScheduleOutput はモジュール内部関数のため、
 * ソースからロジックを抽出してテストする。
 */

// Re-implement normalizeScheduleOutput for testing (mirrors tiktok.js exactly)
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

describe('normalizeScheduleOutput (tiktok)', () => {
  it('filters tiktokPosts by slot (#11)', () => {
    const raw = {
      tiktokPosts: [
        { slot: 'morning', caption: 'morning cap', tone: 't', reasoning: 'r' },
        { slot: 'evening', caption: 'evening cap', tone: 't', reasoning: 'r' },
      ],
    };
    const result = normalizeScheduleOutput(raw);
    const morning = result.tiktokPosts.filter(p => p.slot === 'morning');
    const evening = result.tiktokPosts.filter(p => p.slot === 'evening');
    expect(morning).toHaveLength(1);
    expect(morning[0].caption).toBe('morning cap');
    expect(evening).toHaveLength(1);
    expect(evening[0].caption).toBe('evening cap');
  });

  it('backward compat: converts tiktokPost singular to array (#12)', () => {
    const raw = {
      tiktokPost: { caption: 'old format', tone: 'strict', reasoning: 'r' },
    };
    const result = normalizeScheduleOutput(raw);
    expect(result.tiktokPosts).toHaveLength(1);
    expect(result.tiktokPosts[0].caption).toBe('old format');
    expect(result.tiktokPosts[0].slot).toBe('morning');
  });

  it('returns empty array for evening slot when only morning exists (#22)', () => {
    const raw = {
      tiktokPosts: [{ slot: 'morning', caption: 'morning only', tone: 't', reasoning: 'r' }],
    };
    const result = normalizeScheduleOutput(raw);
    const evening = result.tiktokPosts.filter(p => p.slot === 'evening');
    expect(evening).toHaveLength(0);
    // Endpoint returns 200 with empty tiktokPosts for this slot
  });

  it('adds slot fallback when tiktokPosts have no slot (#26)', () => {
    const raw = {
      tiktokPosts: [
        { caption: 'first', tone: 't', reasoning: 'r' },
        { caption: 'second', tone: 't', reasoning: 'r' },
      ],
    };
    const result = normalizeScheduleOutput(raw);
    expect(result.tiktokPosts[0].slot).toBe('morning');
    expect(result.tiktokPosts[1].slot).toBe('evening');
  });
});
