import baseLogger from '../utils/logger.js';

const logger = baseLogger.withContext('HookSelector');

/**
 * C5: Hook Selection via Thompson Sampling
 *
 * Strategy:
 * - 80% EXPLOIT: Pick from top performers using Thompson Sampling (Beta distribution)
 * - 20% EXPLORE: Pick hook with highest exploration_weight (least tested)
 */

const EXPLORE_PROBABILITY = 0.20;

/**
 * Sample from Beta(alpha, beta) distribution using gamma variates.
 * @param {number} alpha - shape parameter (successes + 1)
 * @param {number} beta - shape parameter (failures + 1)
 * @returns {number} sample in [0, 1]
 */
function betaSample(alpha, beta) {
  const x = gammaSample(alpha);
  const y = gammaSample(beta);
  if (x + y === 0) return 0.5;
  return x / (x + y);
}

/**
 * Sample from Gamma(shape, 1) using Marsaglia and Tsang's method.
 * @param {number} shape - shape parameter > 0
 * @returns {number}
 */
function gammaSample(shape) {
  if (shape < 1) {
    // Boost for shape < 1: Gamma(shape) = Gamma(shape+1) * U^(1/shape)
    return gammaSample(shape + 1) * Math.pow(Math.random(), 1 / shape);
  }

  const d = shape - 1 / 3;
  const c = 1 / Math.sqrt(9 * d);

  while (true) {
    let x, v;
    do {
      x = normalSample();
      v = 1 + c * x;
    } while (v <= 0);

    v = v * v * v;
    const u = Math.random();

    if (u < 1 - 0.0331 * (x * x) * (x * x)) return d * v;
    if (Math.log(u) < 0.5 * x * x + d * (1 - v + Math.log(v))) return d * v;
  }
}

/**
 * Sample from standard normal distribution using Box-Muller transform.
 * @returns {number}
 */
function normalSample() {
  const u1 = Math.random();
  const u2 = Math.random();
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

/**
 * Select a hook candidate using Thompson Sampling.
 *
 * @param {Array<{id: string, text: string, tone: string, appTapRate: number, appSampleSize: number, tiktokLikeRate: number, tiktokSampleSize: number, explorationWeight: number, isWisdom: boolean, tiktokHighPerformer: boolean}>} candidates
 * @returns {{ hook: object, strategy: 'exploit' | 'explore', score: number } | null}
 */
export function selectHook(candidates) {
  if (!candidates || candidates.length === 0) return null;

  const isExplore = Math.random() < EXPLORE_PROBABILITY;

  if (isExplore) {
    // Explore: pick highest exploration_weight (least tested)
    const sorted = [...candidates].sort(
      (a, b) => Number(b.explorationWeight) - Number(a.explorationWeight),
    );
    logger.info(`Explore mode: selected "${sorted[0].text}" (weight: ${sorted[0].explorationWeight})`);
    return { hook: sorted[0], strategy: 'explore', score: Number(sorted[0].explorationWeight) };
  }

  // Exploit: Thompson Sampling with Beta distribution
  // Combine app + TikTok performance for scoring
  const scored = candidates.map((c) => {
    const appRate = Number(c.appTapRate);
    const appN = c.appSampleSize;
    const tiktokRate = Number(c.tiktokLikeRate);
    const tiktokN = c.tiktokSampleSize;

    // App Beta sample (weighted more heavily since it's the primary channel)
    const appAlpha = Math.max(appN * appRate, 0) + 1;
    const appBeta = Math.max(appN * (1 - appRate), 0) + 1;
    const appScore = betaSample(appAlpha, appBeta);

    // TikTok Beta sample
    const tikAlpha = Math.max(tiktokN * tiktokRate, 0) + 1;
    const tikBeta = Math.max(tiktokN * (1 - tiktokRate), 0) + 1;
    const tikScore = betaSample(tikAlpha, tikBeta);

    // Combined score: 60% app + 40% tiktok (app is primary)
    const combinedScore = 0.6 * appScore + 0.4 * tikScore;

    // Bonus for wisdom hooks
    const wisdomBonus = c.isWisdom ? 0.05 : 0;

    return { hook: c, score: combinedScore + wisdomBonus };
  });

  scored.sort((a, b) => b.score - a.score);
  const selected = scored[0];

  logger.info(`Exploit mode: selected "${selected.hook.text}" (score: ${selected.score.toFixed(4)})`);
  return { hook: selected.hook, strategy: 'exploit', score: selected.score };
}

/**
 * Platform-aware Thompson Sampling for closed-loop ops.
 * Uses pre-computed successCount/failureCount per candidate.
 *
 * @param {Array<{id: string, text: string, successCount: number, failureCount: number}>} candidates
 * @returns {object} selected candidate (raw object, not wrapped)
 */
export function selectHookThompson(candidates) {
  if (!candidates || candidates.length === 0) return null;

  const scored = candidates.map(c => {
    const alpha = (c.successCount || 0) + 1;
    const beta = (c.failureCount || 0) + 1;
    const score = betaSample(alpha, beta);
    return { candidate: c, score };
  });

  scored.sort((a, b) => b.score - a.score);
  return scored[0].candidate;
}

export { EXPLORE_PROBABILITY, betaSample, gammaSample };
