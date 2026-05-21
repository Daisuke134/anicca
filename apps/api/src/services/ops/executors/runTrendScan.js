/**
 * runTrendScan — Step executor entry point for closed-loop-ops
 *
 * Called by the VPS worker when a run_trend_scan step is dispatched.
 * Wraps the trend-hunter orchestrator and returns events for the step/complete endpoint.
 */
import { runTrendHunter } from '../trend-hunter/orchestrator.js';

/**
 * Execute a trend scan step.
 *
 * @param {Object} params
 * @param {Object} params.stepParams - Parameters from the mission step
 * @param {Object} params.clients - API clients (twitter, reddit, tiktok, llm, railway)
 * @param {number} [params.executionCount=0] - Current execution count for rotation
 * @returns {Promise<{status: string, output: Object, events: Array}>}
 */
export async function runTrendScan({ stepParams = {}, clients, executionCount = 0 }) {
  const config = {
    executionCount,
    targetTypes: stepParams.targetTypes || undefined,
    enabledSources: {
      x: stepParams.enableX !== false,
      tiktok: stepParams.enableTiktok !== false,
      reddit: stepParams.enableReddit !== false,
      github: stepParams.enableGithub === true,
    },
    llmChain: stepParams.llmChain || [
      { model: 'gpt-4o', timeout: 30000 },
      { model: 'gpt-4o-mini', timeout: 20000 },
    ],
    dryRun: stepParams.dryRun || false,
    similarityThreshold: stepParams.similarityThreshold || 0.7,
    clients,
  };

  const result = await runTrendHunter(config);

  const hasAllSourcesDown = result.errors.length >= 3 && result.scannedCount === 0;
  const status = hasAllSourcesDown ? 'failed' : 'completed';

  return {
    status,
    output: {
      scannedCount: result.scannedCount,
      filteredCount: result.filteredCount,
      savedCount: result.savedCount,
      skippedDuplicates: result.skippedDuplicates,
      targetTypes: result.targetTypes,
      duration: result.duration,
      errors: result.errors,
    },
    events: result.events || [],
  };
}
