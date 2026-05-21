const CRISIS_PATTERNS = [
  /死にたい/i,
  /自殺/i,
  /消えたい/i,
  /kill\s*myself/i,
  /want\s*to\s*die/i,
  /end\s*my\s*life/i,
  /suicid/i,
];

const SUFFERING_PATTERNS = [
  /つらい/i,
  /苦しい/i,
  /しんどい/i,
  /もう無理/i,
  /i\s+can't\s+take\s+it/i,
  /i\s+am\s+not\s+okay/i,
  /hopeless/i,
  /overwhelmed/i,
];

function normalizeScore(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return null;
  if (value < 0 || value > 1) return null;
  return value;
}

function estimateSeverityScore(context, providedScore = null, providedSeverity = null) {
  const score = normalizeScore(providedScore);
  if (score !== null) return score;

  if (providedSeverity === 'crisis') {
    return 0.95;
  }

  const text = String(context || '');
  if (CRISIS_PATTERNS.some((pattern) => pattern.test(text))) {
    return 0.95;
  }

  if (SUFFERING_PATTERNS.some((pattern) => pattern.test(text))) {
    return 0.7;
  }

  return 0;
}

function detectSuffering({
  context,
  severityScore = null,
  severity = null,
  source = 'heuristic',
} = {}) {
  const score = estimateSeverityScore(context, severityScore, severity);
  const detections = [];

  if (score >= 0.9) {
    detections.push({
      type: 'crisis',
      score,
      eventType: 'crisis:detected',
      source,
      recommendedAction: 'safe_t_interrupt',
    });
  } else if (score >= 0.6) {
    detections.push({
      type: 'suffering',
      score,
      eventType: 'suffering_detected',
      source,
      recommendedAction: 'route_app_nudge',
    });
  }

  return {
    severityScore: score,
    severity: score >= 0.9 ? 'crisis' : null,
    detections,
    safeTTriggered: score >= 0.9,
    eventTypes: detections.map((d) => d.eventType),
  };
}

export {
  detectSuffering,
  estimateSeverityScore,
};

export default {
  detectSuffering,
  estimateSeverityScore,
};
