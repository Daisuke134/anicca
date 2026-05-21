import crypto from 'crypto';
import { query } from '../../lib/db.js';
import baseLogger from '../../utils/logger.js';
import { resolveProfileId } from './userIdResolver.js';

const logger = baseLogger.withContext('NudgeSendService');

/**
 * Internal helper used by /api/mobile/nudge/send and cron jobs.
 * Enforces kill switch + daily quota + best-effort idempotency via dedupeKey.
 */
export async function sendNudgeInternal(payload) {
  const {
    userId,
    message,
    title = '',
    problemType = 'unknown',
    templateId = 'send_nudge',
    metadata = {},
    nudgeId = null,
    dedupeKey = null,
  } = payload || {};

  if (String(process.env.NUDGE_SEND_KILL_SWITCH || '').toLowerCase() === 'true') {
    return { sent: false, error: { code: 'KILL_SWITCH_ENABLED' } };
  }

  const dailyLimit = Number(process.env.NUDGE_DAILY_QUOTA || 3);
  const profileId = await resolveProfileId(userId);
  if (!profileId) {
    return { sent: false, error: { code: 'PROFILE_NOT_FOUND' } };
  }

  // Ensure a backing profiles row exists (idempotent). This supports alpha routing
  // where userId may be a device UUID (no sign-in) and avoids FK failures.
  await query(
    `insert into profiles (id, metadata, created_at, updated_at)
     values ($1::uuid, jsonb_build_object('source','alpha'), timezone('utc', now()), timezone('utc', now()))
     on conflict (id) do nothing`,
    [profileId]
  );

  // Idempotency: if dedupeKey already exists for this user, do nothing.
  if (dedupeKey) {
    const existing = await query(
      `select id
         from nudge_events
        where user_id = $1::uuid
          and decision_point = 'send_nudge'
          and state->>'dedupeKey' = $2
        limit 1`,
      [profileId, String(dedupeKey)]
    );
    if (existing.rows?.[0]?.id) {
      return { sent: false, deduped: true, nudgeId: String(existing.rows[0].id) };
    }
  }

  const todayCountResult = await query(
    `select count(*)::int as count
       from nudge_events
      where user_id = $1::uuid
        and decision_point = 'send_nudge'
        and created_at >= date_trunc('day', timezone('utc', now()))`,
    [profileId]
  );
  const todayCount = todayCountResult.rows?.[0]?.count || 0;
  if (todayCount >= dailyLimit) {
    return { sent: false, error: { code: 'DAILY_QUOTA_EXCEEDED' }, quota: { limit: dailyLimit, used: todayCount } };
  }

  const nudgeEventId = nudgeId || crypto.randomUUID();
  const state = {
    id: nudgeEventId,
    hook: String(title || ''),
    content: String(message || ''),
    problemType: problemType || null,
    templateId: templateId || null,
    metadata: metadata || {},
    source: 'app-nudge-sender',
    dedupeKey: dedupeKey || null,
  };

  try {
    await query(
      `insert into nudge_events (id, user_id, domain, subtype, decision_point, state, action_template, channel, sent, created_at)
       values ($1::uuid, $2::uuid, $3, $4, $5, $6::jsonb, $7, $8, $9, timezone('utc', now()))`,
      [
        nudgeEventId,
        profileId,
        'problem_nudge',
        problemType || 'unknown',
        'send_nudge',
        JSON.stringify(state),
        templateId || 'send_nudge',
        'notification',
        true,
      ]
    );
  } catch (e) {
    // Handle a race (two workers insert same id) gracefully.
    logger.warn('send_nudge insert failed', e);
    throw e;
  }

  return { sent: true, nudgeId: nudgeEventId, quota: { limit: dailyLimit, used: todayCount + 1 } };
}

export default {
  sendNudgeInternal,
};
