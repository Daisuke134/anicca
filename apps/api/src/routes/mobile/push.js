import express from 'express';
import { z } from 'zod';
import rateLimit, { ipKeyGenerator } from 'express-rate-limit';
import baseLogger from '../../utils/logger.js';
import requireAuth from '../../middleware/requireAuth.js';
import { resolveProfileId, ensureDeviceProfileId } from '../../services/mobile/userIdResolver.js';
import { prisma } from '../../lib/prisma.js';
import ApnsClient, { ApnsError } from '../../services/apns/apnsClient.js';
import { getRawPushEnv, getPushEnv } from '../../utils/pushEnv.js';

const router = express.Router();
const logger = baseLogger.withContext('MobilePush');

const bodySchema = z.object({
  token: z.string().min(1),
  platform: z.string().optional(),
});

const TOKEN_RE = /^[0-9a-fA-F]{64}$/;

function normalizeLang(lang) {
  if (!lang) return null;
  const raw = String(lang).trim();
  if (!raw) return null;
  const lower = raw.toLowerCase();
  if (lower === 'pt-br') return 'pt-BR';
  const two = lower.slice(0, 2);
  if (two === 'pt') return 'pt-BR';
  if (['en', 'ja', 'es', 'fr', 'de'].includes(two)) return two;
  return null;
}

function normalizeTimezone(tz) {
  if (!tz) return null;
  const raw = String(tz).trim();
  if (!raw) return null;
  // Validate as IANA tz. Intl throws RangeError for unknown timeZone.
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: raw }).format(new Date());
    return raw;
  } catch {
    return null;
  }
}

const pushTokenLimiterByIp = rateLimit({
  windowMs: 60 * 1000,
  max: process.env.NODE_ENV === 'test' ? 1000 : 30,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req) => {
    return ipKeyGenerator(req.ip || '');
  },
});

const pushTokenLimiterByDevice = rateLimit({
  windowMs: 60 * 1000,
  max: process.env.NODE_ENV === 'test' ? 1000 : 30,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req) => {
    const deviceId = String(req.get('device-id') || '').trim();
    return deviceId || ipKeyGenerator(req.ip || '');
  },
});

let remoteEnabledCache = { value: false, expMs: 0 };

async function computeRemoteDeliveryEnabled() {
  if (process.env.PROBLEM_NUDGE_APNS_SENDER_ENABLED !== 'true') return false;

  // Fail-closed if environment SSOT is missing or APNS_ENDPOINT doesn't match.
  // Otherwise we can incorrectly return remoteDeliveryEnabled=true and iOS may disable local delivery,
  // causing a notification blackout.
  const rawEnv = getRawPushEnv();
  if (!rawEnv) return false;
  const env = getPushEnv();
  const expectedEndpoint = env === 'prod' ? 'production' : 'development';
  const configuredEndpoint = String(process.env.APNS_ENDPOINT || '').toLowerCase();
  if (!configuredEndpoint) return false;
  if (configuredEndpoint !== expectedEndpoint) return false;

  const now = Date.now();
  const shouldCache = process.env.NODE_ENV !== 'test';
  if (shouldCache && now < remoteEnabledCache.expMs) return remoteEnabledCache.value;
  try {
    // Validate APNs envs are present and well-formed.
    const client = ApnsClient.fromEnv();
    // Ensure key parsing + JWT signing works (avoids false positives).
    // eslint-disable-next-line no-underscore-dangle
    await client._getJwt();
    // Probe APNs auth by sending to a dummy token.
    // - If auth is valid, APNs should respond 400 (BadDeviceToken / DeviceTokenNotForTopic / etc.).
    // - If auth is invalid, APNs responds 403 (InvalidProviderToken / ExpiredProviderToken / etc.).
    try {
      await client.sendAlert({
        deviceToken: '0'.repeat(64),
        payload: { aps: { alert: { title: 'Anicca', body: 'probe' } } },
        apnsIdempotencyKey: 'apns_probe',
      });
      // Unexpected, but treat as enabled if APNs accepted.
      if (shouldCache) remoteEnabledCache = { value: true, expMs: now + 5 * 60 * 1000 };
      return true;
    } catch (e) {
      if (e instanceof ApnsError) {
        const authOkReasons = new Set(['BadDeviceToken', 'DeviceTokenNotForTopic']);
        const enabled = e.status === 400 && authOkReasons.has(String(e.reason || ''));
        if (shouldCache) remoteEnabledCache = { value: enabled, expMs: now + 5 * 60 * 1000 };
        return enabled;
      }
      if (shouldCache) remoteEnabledCache = { value: false, expMs: now + 30 * 1000 };
      return false;
    }
  } catch {
    if (shouldCache) remoteEnabledCache = { value: false, expMs: Date.now() + 30 * 1000 };
    return false;
  }
}

// POST /api/mobile/push/token
router.post('/token', pushTokenLimiterByIp, pushTokenLimiterByDevice, async (req, res) => {
  const deviceId = (req.get('device-id') || '').toString().trim();
  if (!deviceId) {
    return res.status(400).json({ error: { code: 'INVALID_REQUEST', message: 'device-id is required' } });
  }

  const rawEnv = getRawPushEnv();
  if (!rawEnv) {
    return res
      .status(503)
      .json({ error: { code: 'CONFIG_MISSING', message: 'PUSH_ENV/APNS_ENV/RAILWAY_ENVIRONMENT is required' } });
  }

  const parsed = bodySchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: { code: 'INVALID_REQUEST', message: 'Invalid body', details: parsed.error.errors } });
  }

  const token = String(parsed.data.token || '').trim();
  if (!TOKEN_RE.test(token)) {
    return res.status(400).json({ error: { code: 'INVALID_TOKEN', message: 'token must be 64 hex chars' } });
  }

  const env = getPushEnv();
  const platform = 'ios';
  const tz = normalizeTimezone(req.get('x-timezone'));
  const lang = normalizeLang(req.get('x-lang'));
  const remoteDeliveryEnabled = await computeRemoteDeliveryEnabled();

  // Resolve profile_id securely:
  // - If Bearer exists: auth.sub -> resolveProfileId
  // - Else: ensureDeviceProfileId(deviceId)
  const authHeader = String(req.headers['authorization'] || '');
  let profileId = null;
  let hasAuth = false;
  if (authHeader.startsWith('Bearer ')) {
    const auth = await requireAuth(req, res);
    if (!auth) return;
    hasAuth = true;
    profileId = await resolveProfileId(auth.sub);
    if (!profileId) {
      return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Could not resolve profile_id from bearer' } });
    }
  }
  if (!profileId) {
    profileId = await ensureDeviceProfileId(deviceId);
  }
  if (!profileId) {
    return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Could not resolve profile_id' } });
  }

  // Per-user remote enablement:
  // In 1.6.3+ Problem nudges are delivered via APNs for ALL users (free/pro).
  // We keep this flag purely as a safety gate: if APNs is misconfigured, iOS must not disable local delivery.
  const remoteProblemNudgesEnabled = remoteDeliveryEnabled;

  try {
    await prisma.$transaction(async (tx) => {
      // Update SSOT settings if headers provided.
      if (tz || lang) {
        await tx.userSetting.upsert({
          where: { userId: profileId },
          update: {
            ...(tz ? { timezone: tz } : {}),
            ...(lang ? { language: lang } : {}),
            updatedAt: new Date(),
          },
          create: {
            userId: profileId,
            ...(tz ? { timezone: tz } : {}),
            ...(lang ? { language: lang } : {}),
          },
        });
      }

      // Ensure day0 exists (best-effort). If timezone missing, we leave it to sender job fallback.
      const existingSettings = await tx.userSetting.findUnique({
        where: { userId: profileId },
        select: { nudgeDay0LocalDate: true, timezone: true, nudgeDay0Source: true },
      });

      // If day0 was previously computed under UTC fallback, and we now have a valid timezone,
      // recompute exactly once to align day-cycling with the user's real locale.
      if (tz && existingSettings?.nudgeDay0LocalDate && existingSettings?.nudgeDay0Source === 'utc_fallback') {
        const profile = await tx.profile.findUnique({
          where: { id: profileId },
          select: { createdAt: true },
        });
        const createdAt = profile?.createdAt ? new Date(profile.createdAt) : new Date();
        const dateFmt = new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' });
        const localDate = dateFmt.format(createdAt); // YYYY-MM-DD
        await tx.userSetting.update({
          where: { userId: profileId },
          data: {
            nudgeDay0LocalDate: new Date(`${localDate}T00:00:00.000Z`),
            nudgeDay0Source: 'profile_created_at',
            updatedAt: new Date(),
          },
        });
      }

      if (!existingSettings?.nudgeDay0LocalDate) {
        const timezone = tz || existingSettings?.timezone || 'UTC';
        const profile = await tx.profile.findUnique({
          where: { id: profileId },
          select: { createdAt: true },
        });
        const createdAt = profile?.createdAt ? new Date(profile.createdAt) : new Date();
        // Compute local date string via Intl then store as DATE.
        const dateFmt = new Intl.DateTimeFormat('en-CA', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit' });
        const localDate = dateFmt.format(createdAt); // YYYY-MM-DD
        await tx.userSetting.upsert({
          where: { userId: profileId },
          update: {
            nudgeDay0LocalDate: new Date(`${localDate}T00:00:00.000Z`),
            nudgeDay0Source: timezone === 'UTC' && !tz ? 'utc_fallback' : (existingSettings?.nudgeDay0Source || 'profile_created_at'),
            updatedAt: new Date(),
          },
          create: {
            userId: profileId,
            nudgeDay0LocalDate: new Date(`${localDate}T00:00:00.000Z`),
            nudgeDay0Source: timezone === 'UTC' && !tz ? 'utc_fallback' : 'profile_created_at',
            ...(tz ? { timezone: tz } : {}),
            ...(lang ? { language: lang } : {}),
          },
        });
      }

      // Keep mobile_profiles user_id aligned with UUID profile_id for this device.
      // This prevents APNs sender skips when legacy rows still store device-id in user_id.
      await tx.mobileProfile.updateMany({
        where: { deviceId },
        data: { userId: profileId, updatedAt: new Date() },
      });

      // Clean up token/env conflicts (same token on a different device).
      const conflict = await tx.pushToken.findUnique({
        where: { token_env: { token, env } },
        select: { id: true, deviceId: true },
      });
      if (conflict && conflict.deviceId !== deviceId) {
        await tx.pushToken.delete({ where: { id: conflict.id } });
      }

      // Upsert per device/env.
      const existing = await tx.pushToken.findUnique({
        where: { deviceId_env: { deviceId, env } },
        select: { id: true, profileId: true },
      });

      const targetProfileId = hasAuth ? profileId : (existing?.profileId || profileId);

      await tx.pushToken.upsert({
        where: { deviceId_env: { deviceId, env } },
        update: {
          token,
          profileId: targetProfileId,
          platform,
          disabledAt: null,
          lastError: null,
          updatedAt: new Date(),
        },
        create: {
          profileId: targetProfileId,
          deviceId,
          token,
          platform,
          env,
        },
      });
    });

    return res.json({ ok: true, remoteDeliveryEnabled, remoteProblemNudgesEnabled });
  } catch (e) {
    logger.error('Failed to upsert push token', e);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to save token' } });
  }
});

export default router;
