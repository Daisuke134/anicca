/**
 * redditResponseParser — reddapi.dev raw JSON → NormalizedTrend[]
 */

/**
 * Parse reddapi.dev semantic search response into normalized trend objects.
 *
 * @param {string} rawJson - Raw JSON string from reddapi.dev
 * @param {Object} meta
 * @param {string} meta.problemType - ProblemType used for the search
 * @param {'empathy'|'solution'} meta.type - Content type
 * @param {number} meta.minScore - Minimum upvote count (local filter)
 * @returns {NormalizedTrend[]} Normalized trends
 * @throws {Error} On JSON parse failure or API error (success=false)
 */
export function parseRedditResponse(rawJson, meta) {
  let data;
  try {
    data = JSON.parse(rawJson);
  } catch (parseErr) {
    throw new Error(`Reddit JSON parse failed: ${parseErr.message}`);
  }

  if (!data.success) {
    throw new Error(`Reddit API error: ${data.error || 'Unknown error'}`);
  }

  const results = data.data?.results || [];

  return results
    .filter(r => (r.upvotes || 0) >= (meta.minScore || 0))
    .map(r => ({
      id: r.id,
      source: 'reddit',
      problemType: meta.problemType,
      contentType: meta.type,
      lang: 'en', // reddapi primarily returns English content
      text: r.title || '',
      url: r.url || null,
      metrics: {
        engagement: r.upvotes || 0,
      },
      author: null,
      raw: {
        content: r.content,
        subreddit: r.subreddit,
        comments: r.comments,
        relevance: r.relevance,
        sentiment: r.sentiment,
      },
    }));
}
