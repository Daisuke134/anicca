/**
 * slackFormatter — Format scan results into Slack message
 */

/**
 * Format trend scan results into a Slack message string.
 *
 * @param {Object} results
 * @param {string[]} results.targetTypes - ProblemTypes scanned
 * @param {Object} results.sourceCounts - { tiktok, reddit, x, github }
 * @param {number} results.filteredCount - LLM filter pass count
 * @param {number} results.savedCount - Hooks saved to DB
 * @param {number} results.empathyCount - Empathy hooks
 * @param {number} results.solutionCount - Solution hooks
 * @param {Array<{source: string, error: string}>} results.errors - Source errors
 * @returns {string} Formatted Slack message
 */
export function formatSlackMessage(results) {
  const {
    targetTypes,
    sourceCounts,
    filteredCount,
    savedCount,
    empathyCount,
    solutionCount,
    errors,
  } = results;

  const lines = [
    `トレンドスキャン完了`,
    `対象: ${targetTypes.join(', ')}`,
    '',
    `TikTok: ${sourceCounts.tiktok}件 | Reddit: ${sourceCounts.reddit}件 | X: ${sourceCounts.x}件`,
    `→ フィルタ通過: ${filteredCount}件 → 新規hook: ${savedCount}件`,
    `共感系: ${empathyCount} | 問題解決系: ${solutionCount}`,
  ];

  if (errors.length > 0) {
    lines.push('');
    lines.push('エラー:');
    for (const err of errors) {
      lines.push(`  ${err.source}: エラー — ${err.error}`);
    }
  }

  return lines.join('\n');
}
