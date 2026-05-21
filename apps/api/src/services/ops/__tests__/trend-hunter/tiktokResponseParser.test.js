import { describe, it, expect } from 'vitest';
import { parseTikTokResponse } from '../../trend-hunter/tiktokResponseParser.js';

const MOCK_TIKTOK_RESPONSE = JSON.stringify([
  {
    id: '1686858772679682',
    name: '#sleepschedule',
    url: 'https://www.tiktok.com/tag/sleepschedule',
    countryCode: 'JP',
    rank: 12,
    industryName: 'Education',
    videoCount: 4523,
    viewCount: 15800000,
    rankDiff: 8,
    markedAsNew: true,
    isPromoted: false,
  },
  {
    id: '1686858772679999',
    name: '#夜更かし',
    url: 'https://www.tiktok.com/tag/夜更かし',
    countryCode: 'JP',
    rank: 45,
    industryName: 'Life',
    videoCount: 890,
    viewCount: 3200000,
    rankDiff: 15,
    markedAsNew: false,
    isPromoted: false,
  },
]);

describe('tiktokResponseParser', () => {
  // #18
  it('parses valid response into NormalizedTrend array', () => {
    const result = parseTikTokResponse(MOCK_TIKTOK_RESPONSE);
    expect(result).toHaveLength(2);
    expect(result[0].source).toBe('tiktok');
    expect(result[0].metrics.engagement).toBe(15800000);
    expect(result[0].text).toBe('#sleepschedule');
  });

  // #19
  it('filters out promoted hashtags', () => {
    const withPromoted = JSON.stringify([
      {
        id: '1',
        name: '#sleepschedule',
        viewCount: 15800000,
        isPromoted: false,
        countryCode: 'JP',
        rank: 12,
        industryName: 'Education',
      },
      {
        id: '2',
        name: '#promoted_wellness',
        viewCount: 50000000,
        isPromoted: true,
        countryCode: 'JP',
        rank: 3,
        industryName: 'Life',
      },
    ]);
    const result = parseTikTokResponse(withPromoted);
    expect(result).toHaveLength(1);
    expect(result[0].text).toBe('#sleepschedule');
  });

  // #20
  it('returns empty array for empty input', () => {
    const result = parseTikTokResponse(JSON.stringify([]));
    expect(result).toEqual([]);
  });
});
