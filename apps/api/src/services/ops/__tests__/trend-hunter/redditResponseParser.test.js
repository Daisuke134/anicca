import { describe, it, expect } from 'vitest';
import { parseRedditResponse } from '../../trend-hunter/redditResponseParser.js';

const MOCK_REDDIT_RESPONSE = JSON.stringify({
  success: true,
  data: {
    results: [
      {
        id: '1a2b3c4d',
        title: 'I literally cannot stop staying up until 3am',
        content: 'I have tried everything...',
        subreddit: 'r/selfimprovement',
        upvotes: 4523,
        comments: 342,
        created: '2026-02-05T22:15:00Z',
        url: 'https://reddit.com/r/selfimprovement/comments/1a2b3c4d',
      },
      {
        id: '5e6f7g8h',
        title: 'The real reason you can\'t sleep on time',
        content: 'Sleep psychologist here...',
        subreddit: 'r/getdisciplined',
        upvotes: 8901,
        comments: 567,
        created: '2026-02-04T15:30:00Z',
        url: 'https://reddit.com/r/getdisciplined/comments/5e6f7g8h',
      },
      {
        id: '9i0j1k2l',
        title: '6 years of trying to fix my sleep schedule',
        content: 'I am not selling anything...',
        subreddit: 'r/DecidingToBeBetter',
        upvotes: 2156,
        comments: 189,
        created: '2026-02-03T08:45:00Z',
        url: 'https://reddit.com/r/DecidingToBeBetter/comments/9i0j1k2l',
      },
    ],
    total: 20,
  },
});

const META = { problemType: 'staying_up_late', type: 'empathy', minScore: 100 };

describe('redditResponseParser', () => {
  // #15
  it('parses valid response into NormalizedTrend array', () => {
    const result = parseRedditResponse(MOCK_REDDIT_RESPONSE, META);
    expect(result).toHaveLength(3);
    expect(result[0].source).toBe('reddit');
    expect(result[0].metrics.engagement).toBe(4523);
    expect(result[0].problemType).toBe('staying_up_late');
    expect(result[0].contentType).toBe('empathy');
  });

  // #16
  it('returns empty array for empty results', () => {
    const result = parseRedditResponse(
      JSON.stringify({ success: true, data: { results: [] } }),
      META
    );
    expect(result).toEqual([]);
  });

  // #17
  it('throws on API error response', () => {
    expect(() =>
      parseRedditResponse(
        JSON.stringify({ success: false, error: 'Rate limited' }),
        META
      )
    ).toThrow();
  });
});
