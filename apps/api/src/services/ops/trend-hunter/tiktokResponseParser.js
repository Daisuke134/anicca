/**
 * tiktokResponseParser — Apify TikTok Trends Scraper raw JSON → NormalizedTrend[]
 */

/**
 * Parse Apify TikTok Trends Scraper response into normalized trend objects.
 * Filters out promoted hashtags.
 *
 * @param {string} rawJson - Raw JSON string from Apify dataset
 * @returns {NormalizedTrend[]} Normalized trends
 */
export function parseTikTokResponse(rawJson) {
  let items;
  try {
    items = JSON.parse(rawJson);
  } catch (parseErr) {
    throw new Error(`TikTok JSON parse failed: ${parseErr.message}`);
  }

  if (!Array.isArray(items)) {
    return [];
  }

  return items
    .filter(item => !item.isPromoted)
    .map(item => ({
      id: item.id,
      source: 'tiktok',
      problemType: null, // TikTok trends are not ProblemType-specific initially
      contentType: null,
      lang: null,
      text: item.name,
      url: item.url || null,
      metrics: {
        engagement: item.viewCount || 0,
      },
      author: null,
      raw: {
        rank: item.rank,
        rankDiff: item.rankDiff,
        videoCount: item.videoCount,
        countryCode: item.countryCode,
        industryName: item.industryName,
        markedAsNew: item.markedAsNew,
      },
    }));
}
