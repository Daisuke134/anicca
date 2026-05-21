import { logger } from '../../../lib/logger.js';

/**
 * trend-hunter のフルパイプラインを単一ステップとして実行
 * VPS SKILL.md が内部で4ソース収集→LLMフィルタ→hook生成→Railway保存→イベント発行を全て行う
 *
 * Input: {}
 * Output: { savedCount: number, sources: string[], errors: string[] }
 */
export async function executeRunTrendScan({ input, proposalPayload }) {
  logger.info('run_trend_scan: Interface definition only — execution is on VPS SKILL.md');

  return {
    output: {
      savedCount: 0,
      sources: [],
      errors: [],
      empathyCount: 0,
      solutionCount: 0
    },
    events: []
  };
}
