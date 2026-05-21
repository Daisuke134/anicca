/**
 * viralityFilter — Filter trends by source-specific engagement thresholds
 */

/**
 * Filter trends by their source-specific virality thresholds.
 *
 * @param {NormalizedTrend[]} trends - Trends to filter
 * @param {Record<string, number>} thresholds - Source-specific thresholds
 * @returns {NormalizedTrend[]} Filtered trends with engagement >= threshold
 */
export function filterByVirality(trends, thresholds) {
  return trends.filter(trend => {
    const threshold = thresholds[trend.source];
    if (threshold === undefined) return true; // unknown source passes by default
    return trend.metrics.engagement >= threshold;
  });
}
