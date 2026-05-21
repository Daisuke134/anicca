/**
 * thompsonSampling — Beta distribution sampling for ProblemType selection (v2)
 */
import { PROBLEM_TYPES } from './config.js';

/**
 * Create default bandit state with Beta(1,1) for all ProblemTypes.
 * @returns {Record<string, {alpha: number, beta: number}>}
 */
export function createDefaultBanditState() {
  const state = {};
  for (const pt of PROBLEM_TYPES) {
    state[pt] = { alpha: 1, beta: 1 };
  }
  return state;
}

/**
 * Sample from Beta distribution using Jöhnk's algorithm.
 *
 * @param {number} alpha - Alpha parameter (> 0)
 * @param {number} beta - Beta parameter (> 0)
 * @returns {number} Sample in [0, 1]
 */
export function betaSample(alpha, beta) {
  // Jöhnk's algorithm for Beta distribution sampling
  let x, y;
  do {
    x = Math.pow(Math.random(), 1 / alpha);
    y = Math.pow(Math.random(), 1 / beta);
  } while (x + y > 1);
  return x / (x + y);
}

/**
 * Select top N ProblemTypes by Thompson Sampling.
 *
 * @param {Record<string, {alpha: number, beta: number}>} banditState
 * @param {number} [n=4] - Number of ProblemTypes to select
 * @returns {string[]} Selected ProblemType names
 */
export function selectTopN(banditState, n = 4) {
  const samples = Object.entries(banditState).map(([type, { alpha, beta }]) => ({
    type,
    sample: betaSample(alpha, beta),
  }));

  return samples
    .sort((a, b) => b.sample - a.sample)
    .slice(0, n)
    .map(s => s.type);
}

/**
 * Update bandit state with feedback.
 *
 * @param {Record<string, {alpha: number, beta: number}>} banditState - Mutated in place
 * @param {string} problemType - ProblemType to update
 * @param {boolean} engaged - True if engagement was above threshold
 */
export function updateBandit(banditState, problemType, engaged) {
  if (!banditState[problemType]) return;
  if (engaged) {
    banditState[problemType].alpha += 1;
  } else {
    banditState[problemType].beta += 1;
  }
}

/**
 * Apply monthly decay to all bandit states.
 *
 * @param {Record<string, {alpha: number, beta: number}>} banditState - Mutated in place
 * @param {number} [factor=0.9] - Decay factor
 */
export function decayAll(banditState, factor = 0.9) {
  for (const state of Object.values(banditState)) {
    state.alpha = Math.max(1, Math.round(state.alpha * factor));
    state.beta = Math.max(1, Math.round(state.beta * factor));
  }
}

/**
 * Sync bandit state from Railway DB hook data.
 *
 * @param {Record<string, {alpha: number, beta: number}>} banditState - Mutated in place
 * @param {{hooks: Array}} hooksResponse - Railway API response
 * @returns {Record<string, {alpha: number, beta: number}>} Updated state
 */
export function syncBanditFromDB(banditState, hooksResponse) {
  for (const hook of hooksResponse.hooks) {
    for (const pt of hook.targetProblemTypes) {
      if (!banditState[pt]) continue;
      const xN = hook.xSampleSize || 0;
      const tN = hook.tiktokSampleSize || 0;
      const totalSamples = xN + tN;
      if (totalSamples > 0) {
        const xRate = hook.xEngagementRate || 0;
        const tRate = hook.tiktokLikeRate || 0;
        const weightedRate = (xRate * xN + tRate * tN) / totalSamples;
        const engaged = weightedRate > 0.05; // 0-1 ratio; 5% threshold
        updateBandit(banditState, pt, engaged);
      }
    }
  }
  return banditState;
}
