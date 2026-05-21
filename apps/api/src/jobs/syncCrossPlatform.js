import {
  refreshBaselines,
  syncXMetricsToHookCandidates,
  identifyPromotions,
  executePromotions,
} from '../agents/crossPlatformLearning.js';

/**
 * Cross-Platform Learning Pipeline（generateNudges 起動時 / 05:00 JST）
 *
 * 実行順序（依存関係あり、並列化不可）:
 * 1. refreshBaselines() — Z-Score 基準値を DB から更新
 * 2. syncXMetricsToHookCandidates() — x_posts → hook_candidates の X フィールド
 * 3. identifyPromotions() — X→TikTok, TikTok→App 候補抽出
 * 4. executePromotions() — 候補の hook_candidates.promoted = true に更新
 *
 * @param {Function} query - DB query function
 */
export async function runCrossPlatformSync(query) {
  await refreshBaselines(query);
  await syncXMetricsToHookCandidates(query);

  const { xToTiktok, tiktokToApp } = await identifyPromotions(query);

  const xIds = xToTiktok.map(h => h.id);
  const tikIds = tiktokToApp.map(h => h.id);

  await executePromotions(query, xIds, 'x_promoted');
  await executePromotions(query, tikIds, 'tiktok_promoted');
}
