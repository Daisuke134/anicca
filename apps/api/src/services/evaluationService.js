/**
 * Evaluate task execution result and normalize metrics.
 *
 * @param {string} taskId
 * @param {{
 *   success: boolean,
 *   verificationScore?: number,
 *   latencyMs?: number,
 *   metadata?: object
 * }} result
 * @returns {Promise<{ taskId: string, score: number, metrics: object }>}
 */
export async function evaluateTask(taskId, result = {}) {
  const verificationScore = Number.isFinite(result.verificationScore)
    ? Math.max(0, Math.min(result.verificationScore, 5))
    : 0;
  const success = Boolean(result.success);
  const score = success ? verificationScore / 5 : 0;

  return {
    taskId,
    score,
    metrics: {
      success,
      verificationScore,
      latencyMs: Number.isFinite(result.latencyMs) ? Math.max(0, result.latencyMs) : null,
      metadata: result.metadata || {},
      timestamp: new Date().toISOString(),
    },
  };
}

export default {
  evaluateTask,
};
