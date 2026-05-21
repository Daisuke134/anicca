/**
 * twitterResponseParser — TwitterAPI.io raw JSON → NormalizedTrend[]
 */

/**
 * Parse TwitterAPI.io response into normalized trend objects.
 *
 * @param {string} rawJson - Raw JSON string from TwitterAPI.io
 * @param {Object} meta
 * @param {string} meta.problemType - ProblemType used for the search
 * @param {'empathy'|'solution'} meta.type - Content type
 * @param {'ja'|'en'} meta.lang - Language
 * @returns {NormalizedTrend[]} Normalized trends
 * @throws {Error} On JSON parse failure or API error
 */
export function parseTwitterResponse(rawJson, meta) {
  let data;
  try {
    data = JSON.parse(rawJson);
  } catch (parseErr) {
    throw new Error(`Twitter JSON parse failed: ${parseErr.message}`);
  }

  if (data.error || data.errors) {
    throw new Error(`Twitter API error: ${JSON.stringify(data.error || data.errors)}`);
  }

  const tweets = data.tweets || [];

  return tweets.map(tweet => ({
    id: tweet.id,
    source: 'x',
    problemType: meta.problemType,
    contentType: meta.type,
    lang: meta.lang,
    text: tweet.text,
    url: tweet.author?.userName
      ? `https://x.com/${tweet.author.userName}/status/${tweet.id}`
      : null,
    metrics: {
      engagement: tweet.likeCount || 0,
    },
    author: tweet.author?.userName || null,
    raw: {
      retweetCount: tweet.retweetCount,
      replyCount: tweet.replyCount,
      viewCount: tweet.viewCount,
      hashtags: tweet.entities?.hashtags?.map(h => h.text) || [],
    },
  }));
}
