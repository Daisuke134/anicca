import express from 'express';
import { z } from 'zod';
import crypto from 'crypto';
import { fetch } from 'undici';
import rateLimit, { ipKeyGenerator } from 'express-rate-limit';
import baseLogger from '../../utils/logger.js';
import extractUserId from '../../middleware/extractUserId.js';
import requireInternalAuth from '../../middleware/requireInternalAuth.js';
import requireAuth from '../../middleware/requireAuth.js';
import { query } from '../../lib/db.js';
import { resolveProfileId, ensureDeviceProfileId } from '../../services/mobile/userIdResolver.js';
import { getUserTimezone, buildScreenState, buildMovementState, getUserTraits } from '../../modules/nudge/features/stateBuilder.js';
import { computeReward } from '../../modules/nudge/reward/rewardCalculator.js';
import { getMem0Client } from '../../modules/memory/mem0Client.js';
import { sendNudgeInternal } from '../../services/mobile/nudgeSendService.js';
import { prisma } from '../../lib/prisma.js';
import { getRawPushEnv, getPushEnv } from '../../utils/pushEnv.js';

const router = express.Router();
const logger = baseLogger.withContext('MobileNudge');

const deliveryLimiterByIp = rateLimit({
  windowMs: 60 * 1000,
  max: process.env.NODE_ENV === 'test' ? 2000 : 120,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req) => {
    return ipKeyGenerator(req.ip || '');
  },
});

const deliveryLimiterByDevice = rateLimit({
  windowMs: 60 * 1000,
  max: process.env.NODE_ENV === 'test' ? 2000 : 120,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req) => {
    const deviceId = String(req.get('device-id') || '').trim();
    return deviceId || ipKeyGenerator(req.ip || '');
  },
});

const triggerSchema = z.object({
  eventType: z.string(),
  timestamp: z.string().optional(),
  payload: z.any().optional()
});

// Phase 7+8: hookFeedback/contentFeedback分離対応
const feedbackSchema = z.object({
  nudgeId: z.string(),
  outcome: z.enum(['success', 'failed', 'ignored']).optional(),
  signals: z.object({
    hookFeedback: z.enum(['tapped', 'ignored']).optional(),
    contentFeedback: z.enum(['thumbsUp', 'thumbsDown']).nullish(),
    timeSpentSeconds: z.number().optional(),
    // 後方互換: 旧フィールド
    thumbsUp: z.boolean().optional(),
    thumbsDown: z.boolean().optional(),
    outcome: z.string().optional()
  }).passthrough().optional()
});

const sendSchema = z.object({
  userId: z.string().min(1),
  message: z.string().min(1).max(500),
  title: z.string().min(1).max(120).optional(),
  problemType: z.string().max(100).optional(),
  nudgeId: z.string().optional(),
  templateId: z.string().max(100).optional(),
  metadata: z.record(z.unknown()).optional(),
  dedupeKey: z.string().max(200).optional(),
});

const ackSchema = z.object({
  nudgeIds: z.array(z.string().uuid()).min(1).max(50),
});

// GET /api/mobile/nudge/delivery/:id
// Fetch immutable snapshot for APNs-delivered Problem Nudge card.
router.get('/delivery/:id', deliveryLimiterByIp, deliveryLimiterByDevice, async (req, res) => {
  const idRaw = String(req.params.id || '').trim();
  if (!idRaw) return res.status(400).json({ error: { code: 'INVALID_REQUEST', message: 'id is required' } });
  const idParsed = z.string().uuid().safeParse(idRaw);
  if (!idParsed.success) {
    return res.status(400).json({ error: { code: 'INVALID_REQUEST', message: 'id must be uuid' } });
  }
  const id = idParsed.data;

  const deviceId = (req.get('device-id') || '').toString().trim();
  if (!deviceId) return res.status(400).json({ error: { code: 'INVALID_REQUEST', message: 'device-id is required' } });

  const rawEnv = getRawPushEnv();
  if (!rawEnv) {
    return res
      .status(503)
      .json({ error: { code: 'CONFIG_MISSING', message: 'PUSH_ENV/APNS_ENV/RAILWAY_ENVIRONMENT is required' } });
  }

  try {
    // Resolve-only: do not create profiles on GET. We must match the profileId used for sending.
    const env = getPushEnv();
    const tok = await prisma.pushToken.findUnique({
      where: { deviceId_env: { deviceId, env } },
      select: { profileId: true, disabledAt: true },
    });
    if (!tok || tok.disabledAt) {
      return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'No active push token for device' } });
    }
    const pushProfileId = tok.profileId;

    // Authorization: optional Bearer. If present, it must resolve successfully and match pushProfileId.
    const authHeader = String(req.headers['authorization'] || '');
    if (authHeader.startsWith('Bearer ')) {
      const auth = await requireAuth(req, res);
      if (!auth) return;
      const bearerProfileId = await resolveProfileId(auth.sub);
      if (!bearerProfileId) {
        return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Could not resolve profile from bearer' } });
      }
      if (bearerProfileId !== pushProfileId) {
        return res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Profile mismatch' } });
      }
    }

    const profileId = pushProfileId;

    const row = await prisma.nudgeDelivery.findFirst({
      where: { id, profileId },
      select: {
        id: true,
        problemType: true,
        scheduledTime: true,
        deliveryDayLocal: true,
        timezone: true,
        lang: true,
        variantIndex: true,
        messageTitle: true,
        messageBody: true,
        messageDetail: true,
      },
    });
    if (!row) {
      return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'delivery not found' } });
    }
    return res.json({
      id: row.id,
      problemType: row.problemType,
      scheduledTime: row.scheduledTime,
      deliveryDayLocal: row.deliveryDayLocal ? row.deliveryDayLocal.toISOString().slice(0, 10) : null,
      timezone: row.timezone,
      lang: row.lang,
      variantIndex: row.variantIndex,
      title: row.messageTitle,
      hook: row.messageBody,
      detail: row.messageDetail,
    });
  } catch (e) {
    logger.error('Failed to fetch nudge delivery', e);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to fetch delivery' } });
  }
});

function pickTemplate({ domain, eventType, intensity }) {
  // Minimal mapping per prompts-v3.md examples.
  if (domain === 'screen') {
    if (String(eventType).includes('60')) return 'direct_sns_stop';
    return intensity === 'active' ? 'direct_sns_stop' : 'gentle_sns_break';
  }
  if (domain === 'movement') {
    return intensity === 'active' ? 'walk_invite' : 'short_break';
  }
  if (String(eventType).includes('e2e_pause') || String(eventType).includes('manual_pause')) {
    return 'gentle_pause';
  }
  return 'do_nothing';
}

const TRIGGER_MESSAGES = {
  gentle_sns_break: {
    en: "You've been scrolling for a while. How about a one-minute pause to let your eyes and mind breathe?",
    ja: '少しスクロールが続いてるみたい。1分だけ、目と心を休めよう。',
    es: 'Llevas un rato deslizando. ¿Qué tal una pausa de un minuto para descansar los ojos y la mente?',
    fr: 'Tu scrolles depuis un moment. Et si tu faisais une pause d\'une minute pour reposer tes yeux et ton esprit ?',
    de: 'Du scrollst schon eine Weile. Wie wäre es mit einer einminütigen Pause für Augen und Geist?',
    pt: 'Você está rolando há um tempo. Que tal uma pausa de um minuto para descansar os olhos e a mente?'
  },
  direct_sns_stop: {
    en: "Let's cut it here. Put the phone face-down and reclaim the next few minutes.",
    ja: 'ここで一度切ろう。スマホを伏せて、次の数分を取り戻そう。',
    es: 'Cortemos aquí. Pon el teléfono boca abajo y recupera los próximos minutos.',
    fr: 'Coupons ici. Pose le téléphone face cachée et récupère les prochaines minutes.',
    de: 'Lass uns hier aufhören. Leg das Handy mit dem Display nach unten und nimm dir die nächsten Minuten zurück.',
    pt: 'Vamos parar aqui. Coloque o celular virado para baixo e recupere os próximos minutos.'
  },
  short_break: {
    en: "You've been still for a while. Stand up, stretch, take a few steps—just one minute.",
    ja: '座りっぱなしが続いてるよ。立って、伸びて、数歩だけ。',
    es: 'Llevas un rato quieto. Levántate, estírate, da unos pasos—solo un minuto.',
    fr: 'Tu es resté immobile un moment. Lève-toi, étire-toi, fais quelques pas—juste une minute.',
    de: 'Du sitzt schon eine Weile still. Steh auf, streck dich, mach ein paar Schritte—nur eine Minute.',
    pt: 'Você está parado há um tempo. Levante-se, alongue-se, dê alguns passos—só um minuto.'
  },
  walk_invite: {
    en: "Let's walk for five minutes. When the body moves, the mind often shifts too.",
    ja: '今、5分だけ歩こう。体が動くと、気分も少し変わるよ。',
    es: 'Caminemos cinco minutos. Cuando el cuerpo se mueve, la mente también cambia.',
    fr: 'Marchons cinq minutes. Quand le corps bouge, l\'esprit suit souvent.',
    de: 'Lass uns fünf Minuten gehen. Wenn der Körper sich bewegt, verändert sich oft auch der Geist.',
    pt: 'Vamos caminhar cinco minutos. Quando o corpo se move, a mente também muda.'
  }
  ,
  gentle_pause: {
    en: 'Pause for one breath. That is enough for now.',
    ja: '呼吸を1回だけ。いまはそれで十分。',
    es: 'Pausa para una respiración. Por ahora es suficiente.',
    fr: 'Fais une pause pour une respiration. C’est suffisant pour l’instant.',
    de: 'Pause für einen Atemzug. Das reicht für jetzt.',
    pt: 'Pausa para uma respiração. Por agora, é suficiente.'
  }
};

function normalizeLangKey(lang) {
  if (!lang) return 'en';
  const l = String(lang).toLowerCase().slice(0, 2);
  if (TRIGGER_MESSAGES.gentle_sns_break[l]) return l;
  return 'en';
}

function renderMessage(templateId, lang) {
  const msgs = TRIGGER_MESSAGES[templateId];
  if (!msgs) return '';
  return msgs[normalizeLangKey(lang)] || msgs.en;
}

function classifyDomain(eventType) {
  const t = String(eventType);
  if (t.includes('sns') || t.includes('screen')) return { domain: 'screen', subtype: t };
  if (t.includes('sedentary') || t.includes('movement')) return { domain: 'movement', subtype: t };
  if (t.includes('pause')) return { domain: 'mental', subtype: t };
  return { domain: 'unknown', subtype: t };
}

// POST /api/mobile/nudge/trigger
router.post('/trigger', async (req, res) => {
  const userId = await extractUserId(req, res);
  if (!userId) return;
  const deviceId = (req.get('device-id') || '').toString().trim();

  const parsed = triggerSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: { code: 'INVALID_REQUEST', message: 'Invalid body', details: parsed.error.errors } });
  }

  let profileId = await resolveProfileId(userId);
  if (!profileId && deviceId) {
    profileId = await ensureDeviceProfileId(deviceId);
  }
  if (!profileId) {
    return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Could not resolve profile_id' } });
  }

  try {
    const tz = await getUserTimezone(profileId);
    const traits = await getUserTraits(profileId);
    const { domain, subtype } = classifyDomain(parsed.data.eventType);

    let state = null;
    if (domain === 'screen') state = await buildScreenState({ profileId, now: new Date(), tz });
    if (domain === 'movement') state = await buildMovementState({ profileId, now: new Date(), tz });

    const templateId = pickTemplate({ domain, eventType: parsed.data.eventType, intensity: traits.nudgeIntensity || 'normal' });
    const langR = await query(`select language from user_settings where user_id = $1::uuid limit 1`, [profileId]);
    const lang = langR.rows?.[0]?.language || 'en';
    const message = renderMessage(templateId, lang);
    const nudgeId = crypto.randomUUID();
    const sent = Boolean(message && String(message).trim());

    await query(
      `insert into nudge_events (id, user_id, domain, subtype, decision_point, state, action_template, channel, sent, created_at)
       values ($1::uuid, $2::uuid, $3, $4, $5, $6::jsonb, $7, $8, $9, timezone('utc', now()))`,
      [
        nudgeId,
        profileId,
        domain,
        subtype,
        parsed.data.eventType,
        JSON.stringify(state || {}),
        templateId,
        'notification',
        sent
      ]
    );

    return res.json({ nudgeId, templateId, message, domain });
  } catch (e) {
    logger.error('Failed to trigger nudge', e);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to trigger nudge' } });
  }
});

// POST /api/mobile/nudge/send (internal worker -> mobile feed)
router.post('/send', requireInternalAuth, async (req, res) => {
  const parsed = sendSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({
      error: { code: 'INVALID_REQUEST', message: 'Invalid body', details: parsed.error.errors },
    });
  }

  try {
    const out = await sendNudgeInternal({
      userId: parsed.data.userId,
      message: parsed.data.message,
      title: parsed.data.title || '',
      problemType: parsed.data.problemType || 'unknown',
      templateId: parsed.data.templateId || 'send_nudge',
      metadata: parsed.data.metadata || {},
      nudgeId: parsed.data.nudgeId || crypto.randomUUID(),
      dedupeKey: parsed.data.dedupeKey || null,
    });

    if (out?.error?.code === 'KILL_SWITCH_ENABLED') {
      return res.status(503).json({
        error: { code: 'KILL_SWITCH_ENABLED', message: 'Nudge sending is disabled by kill switch' },
      });
    }
    if (out?.error?.code === 'PROFILE_NOT_FOUND') {
      return res.status(404).json({
        error: { code: 'PROFILE_NOT_FOUND', message: 'Could not resolve profile_id' },
      });
    }
    if (out?.error?.code === 'DAILY_QUOTA_EXCEEDED') {
      return res.status(429).json({
        error: { code: 'DAILY_QUOTA_EXCEEDED', message: 'Daily nudge quota exceeded' },
        quota: out.quota,
      });
    }
    if (out?.deduped) {
      return res.json({ sent: false, deduped: true, nudgeId: out.nudgeId });
    }

    return res.json({ sent: true, nudgeId: out.nudgeId, quota: out.quota });
  } catch (e) {
    logger.error('Failed to send nudge', e);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to send nudge' } });
  }
});

// GET /api/mobile/nudge/pending
// Mobile polls for pending server-driven nudges created by internal workers via /send.
router.get('/pending', async (req, res) => {
  const userId = await extractUserId(req, res);
  if (!userId) return;
  const deviceId = (req.get('device-id') || '').toString().trim();

  let profileId = await resolveProfileId(userId);
  if (!profileId && deviceId) profileId = await ensureDeviceProfileId(deviceId);
  if (!profileId) {
    return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Could not resolve profile_id' } });
  }

  try {
    const result = await query(
      `select id, domain, subtype, state, created_at
         from nudge_events
        where user_id = $1::uuid
          and decision_point = 'send_nudge'
          and (state->>'deliveredAtMs') is null
        order by created_at asc
        limit 20`,
      [profileId]
    );

    const nudges = (result.rows || []).map((r) => {
      const state = r.state || {};
      return {
        nudgeId: r.id,
        domain: r.domain,
        subtype: r.subtype,
        title: state.hook || state.title || '',
        message: state.content || state.message || '',
        problemType: state.problemType || null,
        templateId: state.templateId || null,
        metadata: state.metadata || {},
        createdAt: r.created_at instanceof Date ? r.created_at.toISOString() : String(r.created_at),
      };
    });

    return res.json({ nudges, version: '1' });
  } catch (e) {
    logger.error('Failed to fetch pending nudges', e);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to fetch pending nudges' } });
  }
});

// POST /api/mobile/nudge/ack
// Mark pending nudges as delivered after the app has scheduled a local notification.
router.post('/ack', async (req, res) => {
  const userId = await extractUserId(req, res);
  if (!userId) return;
  const deviceId = (req.get('device-id') || '').toString().trim();

  const parsed = ackSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: { code: 'INVALID_REQUEST', message: 'Invalid body', details: parsed.error.errors } });
  }

  let profileId = await resolveProfileId(userId);
  if (!profileId && deviceId) profileId = await ensureDeviceProfileId(deviceId);
  if (!profileId) {
    return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Could not resolve profile_id' } });
  }

  try {
    const result = await query(
      `update nudge_events
          set state = jsonb_set(
            coalesce(state, '{}'::jsonb),
            '{deliveredAtMs}',
            to_jsonb((extract(epoch from timezone('utc', now())) * 1000)::bigint),
            true
          )
        where user_id = $1::uuid
          and id = any($2::uuid[])
          and decision_point = 'send_nudge'
          and (state->>'deliveredAtMs') is null`,
      [profileId, parsed.data.nudgeIds]
    );

    return res.json({ acked: result.rowCount || 0 });
  } catch (e) {
    logger.error('Failed to ack pending nudges', e);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to ack pending nudges' } });
  }
});

// POST /api/mobile/nudge/feedback
router.post('/feedback', async (req, res) => {
  const userId = await extractUserId(req, res);
  if (!userId) return;

  const parsed = feedbackSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: { code: 'INVALID_REQUEST', message: 'Invalid body', details: parsed.error.errors } });
  }

  const profileId = await resolveProfileId(userId);
  if (!profileId) {
    return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Could not resolve profile_id' } });
  }

  try {
    const ev = await query(
      `select id, domain, subtype, action_template
         from nudge_events
        where id = $1::uuid and user_id = $2::uuid
        limit 1`,
      [parsed.data.nudgeId, profileId]
    );
    const row = ev.rows?.[0];
    if (!row) return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Nudge not found' } });

    const signals = parsed.data.signals || {};
    const reward = computeReward({ domain: row.domain, subtype: row.subtype, signals });

    await query(
      `insert into nudge_outcomes (id, nudge_event_id, reward, short_term, ema_score, signals, created_at)
       values ($1::uuid, $2::uuid, $3, $4::jsonb, $5::jsonb, $6::jsonb, timezone('utc', now()))`,
      [
        crypto.randomUUID(),
        row.id,
        reward,
        JSON.stringify({ outcome: parsed.data.outcome || null }),
        null,
        JSON.stringify(signals)
      ]
    );

    // Save nudge_meta to mem0 (best-effort)
    try {
      const mem0 = await getMem0Client();
      await mem0.addNudgeMeta({
        userId: profileId,
        content: `Nudge ${row.action_template} outcome=${parsed.data.outcome || ''} reward=${reward}`,
        metadata: {
          nudgeId: row.id,
          templateId: row.action_template,
          reward,
          timestamp: new Date().toISOString()
        }
      });
    } catch (e) {
      logger.warn('mem0 nudge_meta save failed', e);
    }

    return res.json({ recorded: true, reward });
  } catch (e) {
    logger.error('Failed to record nudge feedback', e);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to record nudge feedback' } });
  }
});

// Phase 7+8: LLM生成Nudge

// GET /api/nudge/today - 今日生成されたNudgeを取得
router.get('/today', async (req, res) => {
  const userId = await extractUserId(req, res);
  if (!userId) return;

  try {
    const profileId = await resolveProfileId(userId);
    if (!profileId) {
      return res.json({ nudges: [], version: '2' });
    }

    // 今日の00:00 JST以降に生成されたNudgeを取得
    const nowJST = new Date(Date.now() + 9 * 60 * 60 * 1000);
    const todayStartJST = new Date(Date.UTC(
      nowJST.getUTCFullYear(),
      nowJST.getUTCMonth(),
      nowJST.getUTCDate(),
      0, 0, 0, 0
    ) - 9 * 60 * 60 * 1000);

    const result = await query(
      `SELECT state, subtype, created_at
       FROM nudge_events
       WHERE user_id = $1::uuid
         AND domain = 'problem_nudge'
         AND decision_point IN ('llm_generation', 'rule_based')
         AND created_at >= $2::timestamp
       ORDER BY created_at DESC`,
      [profileId, todayStartJST]
    );

    // Phase 7+8: overallStrategyを取得（最初のレコードから）
    const overallStrategy = result.rows[0]?.state?.overallStrategy || null;

    // LLMGeneratedNudge形式に変換（1.6.0: slotIndex + enabled 追加）
    const nudges = result.rows.map(row => {
      const scheduledTime = row.state.scheduledTime || `${String(row.state.scheduledHour || 9).padStart(2, '0')}:00`;
      const [h, m] = scheduledTime.split(':').map(Number);
      return {
        id: row.state.id,
        problemType: row.subtype,
        scheduledTime,
        scheduledHour: h,
        scheduledMinute: m,
        // 1.6.0: slotIndex（フラット化テーブルのインデックス、iOS完全一致マッチ用）
        slotIndex: row.state.slotIndex ?? null,
        // 1.6.0: enabled（Phase 7 Dynamic Frequency用、デフォルトtrue）
        enabled: row.state.enabled ?? true,
        hook: row.state.hook,
        content: row.state.content,
        tone: row.state.tone,
        reasoning: row.state.reasoning,
        rootCauseHypothesis: row.state.rootCauseHypothesis || null,
        createdAt: row.created_at.toISOString(),
      };
    });

    return res.json({
      nudges,
      overallStrategy,
      version: '3',  // 1.6.0: slotIndex + enabled
    });
  } catch (e) {
    logger.error('Failed to fetch today\'s nudges', e);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to fetch today\'s nudges' } });
  }
});

export default router;
