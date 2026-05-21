/**
 * trend-hunter module exports
 */
export { buildQuery } from './queryBuilder.js';
export { selectRotationGroup } from './rotationSelector.js';
export { parseTwitterResponse } from './twitterResponseParser.js';
export { parseRedditResponse } from './redditResponseParser.js';
export { parseTikTokResponse } from './tiktokResponseParser.js';
export { filterByVirality } from './viralityFilter.js';
export { jaccardBigram, isDuplicate } from './textSimilarity.js';
export { formatSlackMessage } from './slackFormatter.js';
export { runTrendHunter } from './orchestrator.js';
export {
  betaSample,
  selectTopN,
  updateBandit,
  decayAll,
  createDefaultBanditState,
  syncBanditFromDB,
} from './thompsonSampling.js';
export {
  createDLQEntry,
  calcDelay,
  filterRetryable,
  updateEntryState,
  cleanupEntries,
} from './dlqHandler.js';
export {
  PROBLEM_TYPES,
  ROTATION_GROUPS,
  VIRALITY_THRESHOLDS,
  SIMILARITY_THRESHOLD,
  WARMUP_THRESHOLD,
  QUERY_DICT,
  LLM_CHAIN,
  DLQ_CONFIG,
} from './config.js';
