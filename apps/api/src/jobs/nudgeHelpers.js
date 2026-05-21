/**
 * Phase 7+8: Nudge Generation Helper Functions
 *
 * Contains:
 * - shouldUseLLM: Day 1 vs Day 2+ detection
 * - buildUserStory: 7-day story format
 * - getHookContentPerformance: Separated hook/content metrics
 * - getTimingPerformance: Time slot analysis
 * - getWeeklyPatterns: Day-of-week patterns
 * - generateWithFallback: 3-tier LLM fallback
 * - validateNudgeSchedule: JSON schema validation
 */

import { fetch } from 'undici';
import { SCHEDULE_MAP, NUDGE_TONES, buildFlattenedSlotTable, trimSlots, getScheduleMap } from '../agents/scheduleMap.js';

// ============================================================================
// Day 1 Detection
// ============================================================================

/**
 * Determine if user should use LLM (Day 2+) or rule-based (Day 1)
 * @param {Function} query - Database query function
 * @param {string} userId - User UUID
 * @returns {Promise<boolean>} true = use LLM (Day 2+), false = use rule-based (Day 1)
 */
export async function shouldUseLLM(query, userId) {
  const result = await query(`
    SELECT MIN(created_at) as first_nudge_date
    FROM nudge_events
    WHERE user_id = $1::uuid AND domain = 'problem_nudge'
  `, [userId]);

  if (!result.rows[0]?.first_nudge_date) {
    // First-time user → Day 1 → Rule-based
    return false;
  }

  const firstNudgeDate = new Date(result.rows[0].first_nudge_date);
  const now = new Date();
  const daysSinceFirst = Math.floor((now - firstNudgeDate) / (1000 * 60 * 60 * 24));

  // Day 2+ → LLM
  return daysSinceFirst >= 1;
}

// ============================================================================
// Story Format Builder
// ============================================================================

/**
 * Build 7-day story format for LLM prompt
 * @param {Function} query - Database query function
 * @param {string} userId - User UUID
 * @returns {Promise<string>} Formatted story string
 */
export async function buildUserStory(query, userId) {
  const result = await query(`
    SELECT
      ne.subtype as problem_type,
      ne.state->>'hook' as hook,
      ne.state->>'content' as content,
      ne.state->>'tone' as tone,
      ne.state->>'reasoning' as reasoning,
      ne.state->>'rootCauseHypothesis' as root_cause,
      ne.state->>'scheduledHour' as scheduled_hour,
      ne.state->>'scheduledTime' as scheduled_time,
      ne.created_at,
      no.signals->>'hookFeedback' as hook_feedback,
      no.signals->>'contentFeedback' as content_feedback,
      no.reward
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '7 days'
    ORDER BY ne.created_at ASC
  `, [userId]);

  if (result.rows.length === 0) {
    return '## 📖 This User\'s Journey (Past 7 Days)\n\nNo history yet.\n';
  }

  let story = '## 📖 This User\'s Journey (Past 7 Days)\n\n';
  let currentDay = null;

  for (const row of result.rows) {
    const day = row.created_at.toISOString().split('T')[0];
    const dayOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][row.created_at.getDay()];

    if (day !== currentDay) {
      currentDay = day;
      story += `### ${day} (${dayOfWeek})\n`;
    }

    const time = row.scheduled_time || `${row.scheduled_hour || row.created_at.getHours()}:00`;
    // Backward compat: if hookFeedback is missing, infer from reward
    const outcome = row.hook_feedback ||
                    (row.reward === 1 ? 'tapped' :
                     row.reward === 0 ? 'ignored' : 'tapped');
    const contentFeedback = row.content_feedback === 'thumbsUp' ? ' 👍' :
                            row.content_feedback === 'thumbsDown' ? ' 👎' : '';

    story += `- ${time} ${row.problem_type}: "${row.hook || 'N/A'}" → ${outcome}${contentFeedback}\n`;
    if (row.reasoning) {
      story += `  - Reasoning: "${row.reasoning}"\n`;
    }
    if (row.root_cause) {
      story += `  - Root cause: "${row.root_cause}"\n`;
    }
  }
  story += '\n';

  return story;
}

// ============================================================================
// Hook/Content Performance
// ============================================================================

/**
 * Get separated hook and content performance metrics
 * @param {Function} query - Database query function
 * @param {string} userId - User UUID
 * @param {string[]} problems - Array of problem types
 * @returns {Promise<string>} Formatted performance string
 */
export async function getHookContentPerformance(query, userId, problems) {
  // Hook performance (tap rate)
  const hookResult = await query(`
    SELECT
      ne.state->>'hook' as hook,
      ne.subtype as problem_type,
      COUNT(*) as total,
      SUM(CASE
        WHEN no.signals->>'hookFeedback' = 'tapped' THEN 1
        WHEN no.signals->>'hookFeedback' IS NULL AND no.reward = 1 THEN 1
        ELSE 0
      END) as tapped_count
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '30 days'
      AND no.id IS NOT NULL
    GROUP BY ne.state->>'hook', ne.subtype
    ORDER BY total DESC
  `, [userId]);

  // Content performance (thumbs up rate)
  const contentResult = await query(`
    SELECT
      ne.state->>'content' as content,
      ne.subtype as problem_type,
      COUNT(*) as total,
      SUM(CASE
        WHEN no.signals->>'contentFeedback' = 'thumbsUp' THEN 1
        WHEN no.signals->>'thumbsUp' = 'true' THEN 1
        ELSE 0
      END) as thumbs_up_count
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '30 days'
      AND no.id IS NOT NULL
    GROUP BY ne.state->>'content', ne.subtype
    ORDER BY total DESC
  `, [userId]);

  let output = '';

  // Hook performance
  for (const problem of problems) {
    const hooks = hookResult.rows.filter(r => r.problem_type === problem);
    if (hooks.length === 0) continue;

    output += `## 🎣 Hook Performance (${problem})\n`;
    for (const h of hooks.slice(0, 5)) {
      const tapRate = Math.round((h.tapped_count / h.total) * 100);
      const emoji = tapRate >= 80 ? ' ✨' : tapRate <= 30 ? ' ❌' : '';
      output += `- "${h.hook}" → tap率 ${tapRate}% (${h.tapped_count}/${h.total})${emoji}\n`;
    }
    output += '\n';
  }

  // Content performance
  for (const problem of problems) {
    const contents = contentResult.rows.filter(r => r.problem_type === problem);
    if (contents.length === 0) continue;

    output += `## 📝 Content Performance (${problem})\n`;
    for (const c of contents.slice(0, 5)) {
      const thumbsRate = Math.round((c.thumbs_up_count / c.total) * 100);
      const emoji = thumbsRate >= 80 ? ' ✨' : thumbsRate <= 30 ? ' ❌' : '';
      const contentPreview = (c.content || '').slice(0, 20);
      output += `- "${contentPreview}..." → 👍率 ${thumbsRate}% (${c.thumbs_up_count}/${c.total})${emoji}\n`;
    }
    output += '\n';
  }

  return output;
}

// ============================================================================
// Timing Performance
// ============================================================================

/**
 * Get timing performance metrics by hour
 * @param {Function} query - Database query function
 * @param {string} userId - User UUID
 * @param {string[]} problems - Array of problem types
 * @returns {Promise<string>} Formatted timing string
 */
export async function getTimingPerformance(query, userId, problems) {
  const result = await query(`
    SELECT
      COALESCE(ne.state->>'scheduledTime', ne.state->>'scheduledHour' || ':00') as scheduled_time,
      ne.subtype as problem_type,
      COUNT(*) as total,
      SUM(CASE
        WHEN no.signals->>'hookFeedback' = 'tapped' THEN 1
        WHEN no.signals->>'hookFeedback' IS NULL AND no.reward = 1 THEN 1
        ELSE 0
      END) as tapped_count
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '30 days'
      AND no.id IS NOT NULL
    GROUP BY COALESCE(ne.state->>'scheduledTime', ne.state->>'scheduledHour' || ':00'), ne.subtype
    ORDER BY scheduled_time
  `, [userId]);

  let output = '';

  for (const problem of problems) {
    const timings = result.rows.filter(r => r.problem_type === problem);
    if (timings.length === 0) continue;

    output += `## ⏰ Timing Performance (${problem})\n`;
    for (const t of timings) {
      const tapRate = Math.round((t.tapped_count / t.total) * 100);
      const emoji = tapRate >= 80 ? ' ✨' : tapRate <= 30 ? ' ❌' : '';
      output += `- ${t.scheduled_time}: tap率 ${tapRate}% (${t.tapped_count}/${t.total})${emoji}\n`;
    }
    output += '\n';
  }

  return output;
}

// ============================================================================
// Weekly Patterns
// ============================================================================

/**
 * Get day-of-week patterns
 * @param {Function} query - Database query function
 * @param {string} userId - User UUID
 * @param {string[]} problems - Array of problem types
 * @returns {Promise<string>} Formatted weekly patterns string
 */
export async function getWeeklyPatterns(query, userId, problems) {
  const result = await query(`
    SELECT
      EXTRACT(DOW FROM ne.created_at) as day_of_week,
      ne.subtype as problem_type,
      COUNT(*) as total,
      SUM(CASE
        WHEN no.signals->>'hookFeedback' = 'ignored' THEN 1
        WHEN no.signals->>'hookFeedback' IS NULL AND no.reward = 0 THEN 1
        ELSE 0
      END) as ignored_count
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '30 days'
      AND no.id IS NOT NULL
    GROUP BY EXTRACT(DOW FROM ne.created_at), ne.subtype
    ORDER BY day_of_week
  `, [userId]);

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  let output = '## 📅 Weekly Patterns\n';

  // Extract high-risk days (high ignored rate)
  const highRiskDays = result.rows
    .filter(r => r.total >= 3) // Only days with enough data
    .map(r => ({
      day: dayNames[r.day_of_week],
      problem: r.problem_type,
      ignoredRate: Math.round((r.ignored_count / r.total) * 100)
    }))
    .filter(r => r.ignoredRate >= 50) // ignored rate >= 50%
    .sort((a, b) => b.ignoredRate - a.ignoredRate);

  if (highRiskDays.length > 0) {
    for (const d of highRiskDays.slice(0, 3)) {
      output += `- ${d.day}: ${d.problem} ignored率 ${d.ignoredRate}%\n`;
    }
  } else {
    output += 'No significant weekly patterns yet.\n';
  }

  // Today's day
  const today = dayNames[new Date().getDay()];
  const todayRisk = highRiskDays.find(d => d.day === today);
  if (todayRisk) {
    output += `\nToday is ${today}. High risk for ${todayRisk.problem}. Consider adjusting timing.\n`;
  } else {
    output += `\nToday is ${today}.\n`;
  }

  return output;
}

// ============================================================================
// LLM Output Validation
// ============================================================================

/**
 * Validate LLM output against expected schema
 * @param {Object} output - LLM output
 * @param {string} preferredLanguage - 'ja' or 'en'
 * @returns {Object|null} Validated output or null if invalid
 */
export function validateNudgeSchedule(output, preferredLanguage = 'en') {
  if (!output || typeof output !== 'object') return null;
  if (!Array.isArray(output.schedule)) return null;
  if (typeof output.overallStrategy !== 'string') return null;

  const charLimits = preferredLanguage === 'ja'
    ? { hook: 12, content: 40 }
    : { hook: 25, content: 80 };

  const validTones = ['strict', 'gentle', 'logical', 'provocative', 'philosophical'];

  for (const item of output.schedule) {
    // Required fields
    if (typeof item.scheduledTime !== 'string') return null;
    if (!/^([01]?[0-9]|2[0-3]):[0-5][0-9]$/.test(item.scheduledTime)) return null;
    if (typeof item.problemType !== 'string') return null;
    if (typeof item.hook !== 'string' || item.hook.length === 0) return null;
    if (typeof item.content !== 'string' || item.content.length === 0) return null;
    if (!validTones.includes(item.tone)) return null;
    if (typeof item.reasoning !== 'string') return null;

    // Enforce character limits
    if (item.hook.length > charLimits.hook * 2) return null; // Allow some flexibility
    if (item.content.length > charLimits.content * 2) return null;
  }

  // Log interval warnings (don't reject — LLM content is too valuable to throw away)
  logIntervalWarnings(output.schedule);

  return output;
}

/**
 * Validate minimum 60-minute interval between nudges
 * @param {Array} schedule - Array of schedule items
 * @throws {Error} If nudges are too close
 * @deprecated Use autoFixInterval instead
 */
export function validateMinimumInterval(schedule) {
  if (schedule.length <= 1) return;

  const sorted = [...schedule].sort((a, b) =>
    a.scheduledTime.localeCompare(b.scheduledTime)
  );

  for (let i = 1; i < sorted.length; i++) {
    const prev = timeToMinutes(sorted[i - 1].scheduledTime);
    const curr = timeToMinutes(sorted[i].scheduledTime);

    if (curr - prev < 60) {
      throw new Error(`Nudges too close: ${sorted[i - 1].scheduledTime} and ${sorted[i].scheduledTime}`);
    }
  }
}

/**
 * Auto-fix nudge schedule to enforce 60-minute minimum interval.
 * Instead of rejecting the entire schedule, shifts nudges forward to maintain the interval.
 * LLM content (hook, content, tone, reasoning) is preserved — only scheduledTime is adjusted.
 * @param {Array} schedule - Array of schedule items
 * @returns {Array} Fixed schedule with adjusted times
 */
/**
 * Log warnings for nudges closer than 30 minutes apart.
 * Does NOT reject or modify the schedule — just logs for monitoring.
 * If warnings are frequent, fix the prompt to improve LLM compliance.
 * @param {Array} schedule - Array of schedule items
 */
export function logIntervalWarnings(schedule) {
  if (schedule.length <= 1) return;

  const sorted = [...schedule].sort((a, b) =>
    a.scheduledTime.localeCompare(b.scheduledTime)
  );

  for (let i = 1; i < sorted.length; i++) {
    const prev = timeToMinutes(sorted[i - 1].scheduledTime);
    const curr = timeToMinutes(sorted[i].scheduledTime);

    if (curr - prev < 30) {
      console.log(`⚠️ [IntervalWarning] ${sorted[i - 1].scheduledTime} → ${sorted[i].scheduledTime} (${curr - prev}min apart) | ${sorted[i].problemType}: "${sorted[i].hook}"`);
    }
  }
}

/**
 * Convert HH:MM to minutes since midnight
 * @param {string} time - Time in HH:MM format
 * @returns {number} Minutes since midnight
 */
export function timeToMinutes(time) {
  const [h, m] = time.split(':').map(Number);
  return h * 60 + m;
}

// ============================================================================
// 3-Tier Fallback LLM Generation
// ============================================================================

/**
 * Generate nudge schedule with 3-tier fallback
 * @param {string} prompt - LLM prompt
 * @param {string} openaiApiKey - OpenAI API key
 * @param {string} preferredLanguage - 'ja' or 'en'
 * @returns {Promise<Object|null>} Validated schedule or null for fallback
 */
export async function generateWithFallback(prompt, openaiApiKey, preferredLanguage = 'en') {
  let attempts = 0;
  let lastError = null;
  let currentPrompt = prompt;

  while (attempts < 3) {
    try {
      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${openaiApiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: 'gpt-4o-mini',
          messages: [
            { role: 'system', content: 'You are a behavioral nudge generation assistant. Always output valid JSON.' },
            { role: 'user', content: currentPrompt }
          ],
          response_format: { type: 'json_object' }
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`OpenAI API error: ${response.status} ${errorText}`);
      }

      const data = await response.json();
      const content = JSON.parse(data.choices[0].message.content);

      const validated = validateNudgeSchedule(content, preferredLanguage);
      if (!validated) {
        // Log what LLM actually returned for debugging
        const schedulePreview = (content?.schedule || []).map(s =>
          `${s.scheduledTime} ${s.problemType}: "${s.hook}"`
        ).join(', ');
        throw new Error(`Validation failed. LLM output: [${schedulePreview}]`);
      }

      return validated;

    } catch (error) {
      attempts++;
      lastError = error;

      if (attempts < 3) {
        // Tier 2: Ask LLM to fix
        currentPrompt = `${prompt}\n\nPrevious attempt failed: ${error.message}. Please fix and ensure valid JSON.`;
        await new Promise(r => setTimeout(r, Math.pow(2, attempts) * 1000));
      }
    }
  }

  // Tier 3: Return null to trigger rule-based fallback
  console.error(`LLM failed after 3 attempts:`, lastError);
  return null;
}

// ============================================================================
// Prompt Builder for Phase 7+8
// ============================================================================

/**
 * Build full LLM prompt for Phase 7+8
 * @param {Object} params - Parameters
 * @returns {string} Complete prompt
 */
export function buildPhase78Prompt({
  problems,
  preferredLanguage,
  userStory,
  hookContentPerformance,
  timingPerformance,
  weeklyPatterns,
  crossUserPatterns = '',
  tiktokHighPerformers = '',
  wisdomPatterns = '',
}) {
  const isJapanese = preferredLanguage === 'ja';
  const limits = isJapanese ? { hook: 12, content: 40 } : { hook: 25, content: 80 };

  const problemNamesJa = {
    staying_up_late: '夜更かし',
    cant_wake_up: '朝起きられない',
    self_loathing: '自己嫌悪',
    rumination: '反芻思考',
    procrastination: '先延ばし',
    anxiety: '不安',
    lying: '嘘をつく',
    bad_mouthing: '悪口',
    porn_addiction: 'ポルノ依存',
    alcohol_dependency: 'アルコール依存',
    anger: '怒り',
    obsessive: '強迫観念',
    loneliness: '孤独'
  };

  const problemNamesEn = {
    staying_up_late: 'Staying Up Late',
    cant_wake_up: "Can't Wake Up",
    self_loathing: 'Self-Loathing',
    rumination: 'Rumination',
    procrastination: 'Procrastination',
    anxiety: 'Anxiety',
    lying: 'Lying',
    bad_mouthing: 'Bad-Mouthing',
    porn_addiction: 'Porn Addiction',
    alcohol_dependency: 'Alcohol Dependency',
    anger: 'Anger',
    obsessive: 'Obsessive Thoughts',
    loneliness: 'Loneliness'
  };

  const problemNames = isJapanese ? problemNamesJa : problemNamesEn;
  const problemList = problems.map(p => problemNames[p] || p).join(', ');

  const toneDefinitions = isJapanese
    ? `- strict: 厳しい、直接的、言い訳を許さない。例：「まだ寝てる？」
- gentle: 優しい、共感的、寄り添う。例：「大丈夫」
- logical: 論理的、データや事実ベース。例：「睡眠不足は危険」
- provocative: 挑発的、プライドを刺激。例：「また負ける？」
- philosophical: 哲学的、深い問い。例：「この5分が…」`
    : `- strict: Direct, no excuses. Example: "Still in bed?"
- gentle: Kind, empathetic. Example: "It's okay, one step at a time."
- logical: Data-driven, factual. Example: "Sleep deprivation cuts judgment by 40%."
- provocative: Challenges pride. Example: "Gonna lose again?"
- philosophical: Deep questions. Example: "These 5 minutes could change everything."`;

  const languageInstruction = isJapanese
    ? 'Use Japanese. Natural, conversational, not robotic.'
    : 'Use English. Natural, conversational, not robotic.';

  return `You are Anicca, an AI that reduces human suffering through perfectly-timed nudges.

## Your Mission
Design today's complete nudge schedule for this specific person. Learn from their journey and create nudges that will actually make them take action.

${userStory}
${hookContentPerformance}
${timingPerformance}
${weeklyPatterns}
${crossUserPatterns}
${tiktokHighPerformers}
${wisdomPatterns}
## This User's Problems
${problemList}

## Tone Definitions
${toneDefinitions}

## 🧠 Behavioral Science Grounding

For each problem type, follow these evidence-based guidelines:

### staying_up_late
- Peak: Screen use 22:00-01:00. Melatonin suppressed within 2h of bedtime
- Strategy: Preventive nudge 90min before bedtime > intervention during scrolling
- NEVER: Lecture about sleep hygiene
- DO: One concrete micro-action ("Put phone in another room for 10 min")
- Urges fade within 30 minutes if not reinforced

### cant_wake_up
- Peak: Sleep inertia upon waking = cognitive impairment equal to 40h sleep deprivation
- Strategy: Rapid micro-actions within 15min of alarm. Night-before prep is key
- NEVER: Imply laziness. Sleep inertia is biological, not moral
- DO: "Feet on the floor" or "Walk to window for light exposure"

### self_loathing
- Peak: Morning (cortisol awakening response) and evening (weakened cognitive control)
- Strategy: Radical acceptance, not productivity language
- NEVER: "You can do it!" (triggers past failure memories)
- DO: "You're here. That's enough." Self-compassion reduces the self-criticism cycle

### rumination
- Peak: Night (21:00-01:00) when external distractions fade
- Strategy: "Scheduled worry time" earlier in the day (evidence-based technique)
- NEVER: "Just stop thinking about it" (backfires)
- DO: Externalization — write it down, name the thought pattern, grounding exercise (5 senses)

### procrastination
- Peak: 13:00-15:00 (circadian energy dip). Evening bedtime procrastination
- Strategy: Address the emotion, not the task
- NEVER: "Just do it" or time management advice
- DO: "What's the 2-minute version?" Acknowledge the feeling behind the avoidance

### anxiety
- Peak: Morning — Cortisol Awakening Response (50-60% spike 30-45min after waking)
- Strategy: Physiological regulation before cognitive intervention
- NEVER: "Don't worry" or "There's nothing to be afraid of"
- DO: "Breathe in for 4, out for 6." Extended exhale activates parasympathetic system

### lying
- Peak: Afternoon (22% more likely) and evening (44% more likely) — "morning morality effect"
- Strategy: Explore the emotional need behind the lie, not the lie itself
- NEVER: Shame or moralize (triggers defensive lying)
- DO: "What were you protecting?" Lying is often a learned survival strategy

### bad_mouthing
- Peak: Social hours, afternoon self-control decline, evening social media
- Strategy: Redirect from judging others to understanding own reaction
- NEVER: "Don't talk about people" (moralizing)
- DO: "What did that person's behavior make you feel?" Address the underlying frustration

### porn_addiction
- Peak: 22:00-01:00 (privacy, fatigue, lowered inhibition). Urges last <30 minutes
- Strategy: Urge surfing — observe without acting. Address emotional trigger (HALT: Hungry/Angry/Lonely/Tired)
- NEVER: Shame or moral judgment (shame is #1 relapse trigger)
- DO: "The urge is here. It will pass. You don't have to act on it."

### alcohol_dependency
- Peak: 20:00-21:00 craving peak (replicated in multiple studies). Trough at 08:00-09:00
- Strategy: The craving is a wave — ride it past the peak
- NEVER: "You shouldn't drink"
- DO: "What can you do with your hands for the next 20 minutes?" (cooking, walking, stretching)

### anger
- Peak: Late afternoon/early evening (16:00-19:00). Biological "brake" loosens through the day
- Strategy: Physical circuit-breaker first, emotional processing later
- NEVER: "Calm down" (escalates anger)
- DO: "Step away for 90 seconds. Splash cold water on your face." (vagal dive reflex)

### obsessive
- Peak: Night (21:00-03:00). OCD patients have delayed melatonin peak by 2 hours
- Strategy: Cognitive defusion — change relationship with the thought, not the thought itself
- NEVER: Reassure "It won't happen" (feeds the OCD cycle)
- DO: "Notice the thought. Label it: 'That's an intrusive thought.' Let it pass like a cloud."

### loneliness
- Peak: Late evening/night (21:00-00:00). Circadian mood dip near midnight
- Strategy: Micro-connections, not big social commitments
- NEVER: "Join a club" or "Make more friends" (overwhelms someone already isolated)
- DO: "Text one person right now. Even just an emoji." Validate the courage it takes

## Nudge Frequency Rules
- Minimum interval: 30 minutes between nudges for different problems, 60 minutes for the same problem (EXCEPT cant_wake_up wake window 06:00-06:30: 15 min allowed)
- Guideline: 4-8 nudges per day
- Strategy mix: ~40% preventive (before peak), ~40% intervention (during peak), ~20% reflection (after/next morning)
- Base schedule on peak times from behavioral science AND user's actual response patterns

## Output Requirements

Return JSON in this exact format:
{
  "schedule": [
    {
      "scheduledTime": "HH:MM",
      "problemType": "problem_type_string",
      "hook": "≤${limits.hook} chars",
      "content": "≤${limits.content} chars",
      "tone": "strict|gentle|logical|provocative|philosophical",
      "reasoning": "Why this time, hook, content, and tone",
      "rootCauseHypothesis": "What's the underlying issue causing this behavior"
    }
  ],
  "overallStrategy": "Your overall strategy for today"
}

## DON'T
- Never schedule two nudges for the same time slot
- Maintain at least 30 minutes between nudges for different problems
- Maintain at least 60 minutes between nudges for the same problem

## Critical Rules
1. Learn from the story. Repeat what worked, avoid what failed.
2. Minimum 30 minutes between nudges for different problems, 60 minutes for same problem.
3. Character limits: Hook ≤ ${limits.hook}, Content ≤ ${limits.content}.
4. ${languageInstruction}
5. Every schedule item MUST have all required fields.`;
}

// ============================================================================
// Rule-based Fallback Generation
// ============================================================================

/**
 * Generate rule-based nudges for Day 1 or fallback
 * @param {string[]} problems - Array of problem types
 * @param {string} preferredLanguage - 'ja' or 'en'
 * @param {string} [appVersion] - Client app version for schedule map selection (v1.6.0+)
 * @returns {Object} Rule-based schedule
 */
export function generateRuleBasedNudges(problems, preferredLanguage = 'en', appVersion = null) {
  const contentJa = {
    staying_up_late: [
      { hook: 'スクロールより呼吸', content: '今夜は早めに。明日の自分が感謝する。' },
      { hook: 'まだ起きてる？', content: 'あと30分で布団に入ろう。' }
    ],
    cant_wake_up: [
      { hook: 'まだ布団の中？', content: '5秒で立て。それだけでいい。' },
      { hook: '新しい1日', content: '起きたら、今日はちょっと違う。' }
    ],
    procrastination: [
      { hook: '今、何してる？', content: '5分だけ始めてみよう。' },
      { hook: 'まだ先延ばし？', content: '完璧より完了。今すぐ手を動かせ。' }
    ]
  };

  const contentEn = {
    staying_up_late: [
      { hook: 'Still scrolling?', content: 'Put the phone down. Tomorrow-you will thank you.' },
      { hook: 'Still awake?', content: 'Get to bed in 30 minutes.' }
    ],
    cant_wake_up: [
      { hook: 'Still in bed?', content: 'Get up in 5 seconds. Just that.' },
      { hook: 'New day', content: 'Once you\'re up, today will be different.' }
    ],
    procrastination: [
      { hook: 'What are you doing?', content: 'Just start for 5 minutes.' },
      { hook: 'Still delaying?', content: 'Done beats perfect. Move now.' }
    ]
  };

  const content = preferredLanguage === 'ja' ? contentJa : contentEn;
  const defaultContent = preferredLanguage === 'ja'
    ? { hook: '今日も前に進もう', content: '小さな一歩から始めよう。' }
    : { hook: 'Keep moving forward', content: 'Start with a small step.' };

  // Use canonical SCHEDULE_MAP + buildFlattenedSlotTable for iOS slotIndex consistency
  // v1.6.0: appVersionに応じたスケジュールマップを使用
  const scheduleMap = getScheduleMap(appVersion);
  const rawSlots = buildFlattenedSlotTable(problems, scheduleMap);
  const slotTable = trimSlots(rawSlots, problems);

  // Night curfew: 23:00-05:59 slots disabled for non-exempt problems
  const NIGHT_EXEMPT = new Set(['staying_up_late', 'cant_wake_up', 'porn_addiction']);
  const isNightHour = (h) => h >= 23 || h < 6;

  // Track per-problemType index for content/tone cycling
  const problemIndexMap = new Map();
  const schedule = slotTable.map((slot) => {
    const ptIdx = problemIndexMap.get(slot.problemType) || 0;
    problemIndexMap.set(slot.problemType, ptIdx + 1);

    const problemContent = content[slot.problemType] || [defaultContent];
    const c = problemContent[ptIdx % problemContent.length];
    const nightDisabled = isNightHour(slot.scheduledHour) && !NIGHT_EXEMPT.has(slot.problemType);
    return {
      scheduledTime: slot.scheduledTime,
      problemType: slot.problemType,
      hook: c.hook,
      content: c.content,
      tone: NUDGE_TONES[ptIdx % NUDGE_TONES.length],
      reasoning: nightDisabled ? 'Night curfew (23:00-05:59)' : 'Rule-based (Day 1 or fallback)',
      rootCauseHypothesis: null,
      slotIndex: slot.slotIndex,
      enabled: !nightDisabled,
    };
  });

  return {
    schedule,
    overallStrategy: 'Rule-based schedule for Day 1 or fallback'
  };
}
