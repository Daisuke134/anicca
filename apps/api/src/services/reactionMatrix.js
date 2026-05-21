/**
 * Reaction Matrix (C2)
 *
 * Deterministic, platform-agnostic scoring used for learning and initiatives.
 * This is intentionally simpler than Z-score normalization (crossPlatformLearning).
 */

const WEIGHTS = {
  app: {
    notification_tap: 3,
    thumbs_up: 2,
    thumbs_down: -2,
    ignore: -1,
  },
  moltbook: {
    upvote: 2,
    reply: 1,
  },
  x: {
    like: 1,
    retweet: 2,
    reply: 1,
  },
  tiktok: {
    like: 1,
    comment: 2,
    share: 3,
  },
};

export function scoreReaction(platform, signals = {}) {
  const p = String(platform || '').toLowerCase();
  const w = WEIGHTS[p];
  if (!w) return 0;

  let score = 0;

  for (const [key, weight] of Object.entries(w)) {
    const val = signals[key];
    if (val === undefined || val === null) continue;
    const n = typeof val === 'boolean' ? (val ? 1 : 0) : Number(val);
    if (!Number.isFinite(n)) continue;
    score += weight * n;
  }

  return score;
}

export function getReactionWeights() {
  return WEIGHTS;
}

export default {
  scoreReaction,
  getReactionWeights,
};
