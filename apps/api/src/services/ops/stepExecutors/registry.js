import { executeDraftContent } from './executeDraftContent.js';
import { executeVerifyContent } from './executeVerifyContent.js';
import { executePostX } from './executePostX.js';
import { executePostTiktok } from './executePostTiktok.js';
import { executeFetchMetrics } from './executeFetchMetrics.js';
import { executeAnalyzeEngagement } from './executeAnalyzeEngagement.js';
import { executeDiagnose } from './executeDiagnose.js';
import { executeDetectSuffering } from './executeDetectSuffering.js';
import { executeDraftNudge } from './executeDraftNudge.js';
import { executeSendNudge } from './executeSendNudge.js';
import { executeEvaluateHook } from './executeEvaluateHook.js';
import { executeRunTrendScan } from './executeRunTrendScan.js';

/**
 * step_kind → executor 関数のマッピング
 * 新しい step_kind の追加はここに1行追加するだけ
 */
const EXECUTOR_MAP = new Map([
  ['draft_content',       executeDraftContent],
  ['verify_content',      executeVerifyContent],
  ['post_x',              executePostX],
  ['post_tiktok',         executePostTiktok],
  ['fetch_metrics',       executeFetchMetrics],
  ['analyze_engagement',  executeAnalyzeEngagement],
  ['diagnose',            executeDiagnose],
  ['detect_suffering',    executeDetectSuffering],
  ['draft_nudge',         executeDraftNudge],
  ['send_nudge',          executeSendNudge],
  ['evaluate_hook',       executeEvaluateHook],
  ['run_trend_scan',      executeRunTrendScan],
]);

/**
 * step_kind に対応する executor を取得
 * @param {string} stepKind
 * @returns {Function} executor 関数
 * @throws {Error} 未知の step_kind
 */
export function getExecutor(stepKind) {
  const executor = EXECUTOR_MAP.get(stepKind);
  if (!executor) {
    throw new Error(`Unknown step_kind: ${stepKind}. Available: ${[...EXECUTOR_MAP.keys()].join(', ')}`);
  }
  return executor;
}
