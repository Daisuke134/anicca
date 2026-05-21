/**
 * Roundtable debate resolver.
 *
 * Deterministic rule: safety wins over growth.
 */

export function resolveDebate({ anicca, growth } = {}) {
  if (!anicca || !growth) throw new Error('anicca and growth proposals required');

  // If growth proposes something that violates safety constraints, reject it.
  if (growth.riskLevel === 'high' || growth.violatesSafety === true) {
    return {
      decision: 'reject_growth',
      reason: 'safety_priority',
      accepted: anicca,
      rejected: growth,
    };
  }

  // Default: accept anicca when conflict is ambiguous.
  if (anicca.priority === 'safety') {
    return {
      decision: 'accept_anicca',
      reason: 'safety_priority',
      accepted: anicca,
      rejected: growth,
    };
  }

  return {
    decision: 'accept_growth',
    reason: 'no_safety_conflict',
    accepted: growth,
    rejected: anicca,
  };
}

export default {
  resolveDebate,
};
