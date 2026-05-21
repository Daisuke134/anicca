import { describe, it, expect } from 'vitest';
import { parseTwitterResponse } from '../../trend-hunter/twitterResponseParser.js';

const MOCK_TWITTER_RESPONSE = JSON.stringify({
  tweets: [
    {
      type: 'tweet',
      id: '1846987139428634858',
      text: '毎日「今日は早く寝よう」って決めてるのに気づいたら2時半でスマホ握りしめてる人、いいねしてくれ',
      likeCount: 50000,
      retweetCount: 12000,
      replyCount: 3400,
      viewCount: 2500000,
      createdAt: '2026-02-07T18:30:00.000Z',
      lang: 'ja',
      author: {
        userName: 'testuser',
        name: 'テストユーザー',
      },
      entities: {
        hashtags: [{ text: '夜更かし' }, { text: '寝れない' }],
      },
    },
    {
      type: 'tweet',
      id: '1846987139428634999',
      text: 'How to fix your sleep schedule in 7 days',
      likeCount: 35000,
      retweetCount: 8000,
      replyCount: 1200,
      viewCount: 5000000,
      createdAt: '2026-02-06T14:00:00.000Z',
      lang: 'en',
      author: {
        userName: 'sleepexpert',
        name: 'Dr. Sleep',
      },
      entities: { hashtags: [] },
    },
  ],
  has_next_page: true,
  next_cursor: 'DAACCgACGdy1XF2xbk8KAAIZw',
});

const META = { problemType: 'staying_up_late', type: 'empathy', lang: 'ja' };

describe('twitterResponseParser', () => {
  // #11
  it('parses valid response into NormalizedTrend array', () => {
    const result = parseTwitterResponse(MOCK_TWITTER_RESPONSE, META);
    expect(result).toHaveLength(2);
    expect(result[0].source).toBe('x');
    expect(result[0].metrics.engagement).toBe(50000);
    expect(result[0].problemType).toBe('staying_up_late');
    expect(result[0].contentType).toBe('empathy');
    expect(result[0].text).toContain('毎日');
    expect(result[0].url).toBe('https://x.com/testuser/status/1846987139428634858');
  });

  // #12
  it('returns empty array for empty tweets', () => {
    const result = parseTwitterResponse(
      JSON.stringify({ tweets: [], has_next_page: false }),
      META
    );
    expect(result).toEqual([]);
  });

  // #13
  it('handles missing author gracefully', () => {
    const response = JSON.stringify({
      tweets: [
        {
          id: '123',
          text: 'test',
          likeCount: 100,
          retweetCount: 10,
          replyCount: 5,
          author: null,
        },
      ],
    });
    const result = parseTwitterResponse(response, META);
    expect(result).toHaveLength(1);
    expect(result[0].author).toBeNull();
    expect(result[0].url).toBeNull();
  });

  // #14
  it('throws on malformed JSON', () => {
    expect(() => parseTwitterResponse('not json', META)).toThrow();
  });
});
