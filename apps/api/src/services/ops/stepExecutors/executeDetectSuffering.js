import { logger } from '../../../lib/logger.js';

/**
 * Web検索で苦しみに関するトレンド・投稿を検出
 * VPS Worker の web_search ツールで実行
 *
 * Input: {}
 * Output: { note: string }
 * Events: [] (actual events emitted by step/complete handler based on detections)
 */
export async function executeDetectSuffering({ skillName }) {
  logger.info('detect_suffering: VPS Worker が web_search で検出を実行');

  return {
    output: {
      note: 'VPS Worker executes web_search and returns detections in step/complete output'
    },
    events: []
  };
}
