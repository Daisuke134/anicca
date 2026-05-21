/**
 * Reasoning Logger (Phase 6)
 *
 * Structured logging for Commander Agent decisions.
 * PII protection: hook/content text hidden by default, shown with LOG_NUDGE_CONTENT=true.
 */

import baseLogger from '../utils/logger.js';

const logger = baseLogger.withContext('CommanderReasoning');
const SHOW_CONTENT = process.env.LOG_NUDGE_CONTENT === 'true';

/**
 * Format a user's daily timetable for structured logging.
 *
 * @param {string} userId
 * @param {object} decision - CommanderDecision (normalized)
 * @param {string} mode - 'rule' | 'llm'
 * @param {string} language - 'ja' | 'en'
 * @returns {string} Formatted timetable string
 */
export function formatDailyTimetable(userId, decision, mode, language) {
  const nudges = decision.appNudges || [];
  const enabled = nudges.filter((n) => n.enabled);

  const lines = [];
  lines.push('══════════════════════════════════════════════');
  lines.push(`User: ${userId.slice(0, 8)}... (Day ${decision.dayNumber || '?'}, ${mode}, ${language})`);
  lines.push('══════════════════════════════════════════════');
  
  // RootCause at top for better visibility
  if (decision.rootCauseHypothesis) {
    lines.push(`RootCause: ${decision.rootCauseHypothesis.slice(0, 100)}`);
  }
  
  lines.push('──────────────────────────────────────────────');

  for (const n of nudges) {
    const time = n.scheduledTime || '??:??';
    const pt = (n.problemType || 'unknown').padEnd(18);
    const tone = `(${n.tone || '?'})`;

    // OFFの場合は理由も表示（guardrailタグから抽出）
    let flag = '';
    if (!n.enabled) {
      const guardrailMatch = (n.reasoning || '').match(/\[guardrail:\s*([^\]]+)\]/i);
      const reason = guardrailMatch ? guardrailMatch[1].trim() : 'unknown';
      flag = ` [OFF: ${reason}]`;
    }

    // Base line (always shown)
    lines.push(`${time} [${pt}] ${tone}${flag}`);
    
    // Detailed content only if SHOW_CONTENT=true
    if (SHOW_CONTENT) {
      lines.push(`    Hook: "${n.hook || ''}"`);
      lines.push(`    Body: "${n.content || ''}"`);
      if (n.reasoning) {
        lines.push(`    Why: ${n.reasoning.slice(0, 100)}`);
      }
    }
  }

  lines.push('──────────────────────────────────────────────');
  lines.push(`Total: ${enabled.length} nudges (enabled) / ${nudges.length} slots`);

  if (decision.overallStrategy) {
    lines.push(`Strategy: ${decision.overallStrategy.slice(0, 100)}`);
  }
  if (decision.frequencyDecision) {
    lines.push(`Frequency: ${decision.frequencyDecision.count} (${decision.frequencyDecision.reasoning?.slice(0, 80) || 'N/A'})`);
  }

  lines.push('══════════════════════════════════════════════');

  return lines.join('\n');
}

/**
 * Log the full Commander decision to Railway logs.
 *
 * @param {string} userId
 * @param {object} decision - CommanderDecision (normalized)
 * @param {string} mode - 'rule' | 'llm'
 * @param {string} language
 */
export function logCommanderDecision(userId, decision, mode, language) {
  // Structured JSON log (machine-readable)
  const safeDecision = SHOW_CONTENT ? decision : sanitizeDecision(decision);
  logger.info(JSON.stringify({
    type: 'commander_decision',
    userId: userId.slice(0, 8),
    mode,
    language,
    nudgeCount: decision.appNudges?.length || 0,
    enabledCount: decision.appNudges?.filter((n) => n.enabled).length || 0,
    overallStrategy: decision.overallStrategy?.slice(0, 200),
  }));

  // Human-readable timetable
  const timetable = formatDailyTimetable(userId, decision, mode, language);
  for (const line of timetable.split('\n')) {
    logger.info(line);
  }
}

/**
 * Strip PII from decision for logging.
 * Replaces hook/content with character counts.
 */
function sanitizeDecision(decision) {
  return {
    ...decision,
    appNudges: (decision.appNudges || []).map((n) => ({
      ...n,
      hook: `[${(n.hook || '').length} chars]`,
      content: `[${(n.content || '').length} chars]`,
    })),
  };
}

/**
 * Build Slack notification payload for daily nudge summary.
 *
 * @param {Array<{ userId: string, decision: object, mode: string }>} results
 * @returns {object} Slack webhook payload
 */
export function buildSlackNudgeSummary(results) {
  const totalUsers = results.length;
  const llmUsers = results.filter((r) => r.mode === 'llm').length;
  const ruleUsers = results.filter((r) => r.mode === 'rule').length;
  const totalNudges = results.reduce((sum, r) => sum + (r.decision.appNudges?.filter((n) => n.enabled).length || 0), 0);

  const lines = [
    ':bell: *Daily Nudge Generation Summary*',
    '',
    `Users processed: ${totalUsers} (LLM: ${llmUsers}, Rule: ${ruleUsers})`,
    `Total nudges scheduled: ${totalNudges}`,
    `Avg nudges/user: ${totalUsers > 0 ? (totalNudges / totalUsers).toFixed(1) : 0}`,
  ];

  // Top strategies (unique)
  const strategies = [...new Set(results
    .filter((r) => r.decision.overallStrategy)
    .map((r) => r.decision.overallStrategy.slice(0, 100))
  )].slice(0, 3);

  if (strategies.length > 0) {
    lines.push('');
    lines.push('*Top Strategies:*');
    for (const s of strategies) {
      lines.push(`• ${s}`);
    }
  }

  return {
    text: lines.join('\n'),
  };
}

/**
 * Send Slack notification via webhook.
 *
 * @param {string} webhookUrl
 * @param {object} payload
 */
export async function sendSlackNotification(webhookUrl, payload) {
  if (!webhookUrl) {
    logger.warn('SLACK_METRICS_WEBHOOK_URL not set, skipping Slack notification');
    return;
  }

  try {
    const resp = await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      logger.warn(`Slack notification failed: ${resp.status}`);
    }
  } catch (e) {
    logger.warn('Slack notification error', e);
  }
}
