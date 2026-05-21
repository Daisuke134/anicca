import express from 'express';
import { z } from 'zod';
import requireInternalAuth from '../../middleware/requireInternalAuth.js';
import baseLogger from '../../utils/logger.js';
import { prisma } from '../../lib/prisma.js';
import { ensureDeviceProfileId } from '../../services/mobile/userIdResolver.js';
import { loadProblemNudgeCatalog, normalizeCatalogLang } from '../../modules/problem_nudges/catalogLoader.js';
import { SCHEDULE_MAP } from '../../agents/scheduleMap.js';
import { getVariantIndex } from '../../agents/dayCycling.js';
import { toLocalDateString } from '../../utils/timezone.js';

const router = express.Router();
const logger = baseLogger.withContext('AdminTest');

const seedSchema = z.object({
  deviceId: z.string().min(1),
  problemType: z.string().min(1),
  scheduledTime: z.string().regex(/^[0-2][0-9]:[0-5][0-9]$/),
  // Optional: override "now" for repeatable tests (ISO string, UTC).
  nowUtcIso: z.string().optional(),
});

function effectiveDeliveryDayLocal({ nowUtc, timezone, problemType, scheduledTime }) {
  const isLate = problemType === 'staying_up_late' && (scheduledTime === '00:00' || scheduledTime === '01:00');
  const base = isLate ? new Date(nowUtc.getTime() - 24 * 60 * 60 * 1000) : nowUtc;
  return toLocalDateString(base, timezone);
}

// POST /api/admin/test/nudge-delivery
router.post('/nudge-delivery', requireInternalAuth, async (req, res) => {
  const parsed = seedSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: { code: 'INVALID_REQUEST', message: 'Invalid body', details: parsed.error.errors } });
  }

  const { deviceId, problemType, scheduledTime } = parsed.data;
  const nowUtc = parsed.data.nowUtcIso ? new Date(parsed.data.nowUtcIso) : new Date();

  if (!SCHEDULE_MAP[problemType] || !SCHEDULE_MAP[problemType].includes(scheduledTime)) {
    return res.status(400).json({ error: { code: 'INVALID_REQUEST', message: 'problemType/scheduledTime not in schedule map' } });
  }

  const profileId = await ensureDeviceProfileId(deviceId);
  if (!profileId) return res.status(400).json({ error: { code: 'INVALID_REQUEST', message: 'could not ensure device profile' } });

  try {
    const settings = await prisma.userSetting.findUnique({
      where: { userId: profileId },
      select: { timezone: true, language: true, nudgeDay0LocalDate: true },
    });
    const timezone = settings?.timezone || 'UTC';
    const lang = normalizeCatalogLang(settings?.language || 'en');
    const catalog = loadProblemNudgeCatalog(lang);

    const deliveryDayLocal = effectiveDeliveryDayLocal({ nowUtc, timezone, problemType, scheduledTime });
    const slotsPerDay = SCHEDULE_MAP[problemType].length;
    const slotIndex = SCHEDULE_MAP[problemType].indexOf(scheduledTime);
    // DATE is date-only. Never reinterpret via timezone conversion.
    const day0 = settings?.nudgeDay0LocalDate
      ? new Date(settings.nudgeDay0LocalDate).toISOString().slice(0, 10)
      : deliveryDayLocal;
    const dayIndex = Math.max(0, Math.floor((new Date(`${deliveryDayLocal}T00:00:00.000Z`).getTime() - new Date(`${day0}T00:00:00.000Z`).getTime()) / (24 * 60 * 60 * 1000)));
    const totalVariants = problemType === 'staying_up_late' ? 70 : 42;
    const variantIndex = getVariantIndex(dayIndex, slotIndex, slotsPerDay, totalVariants);

    const title = catalog.titles[problemType] || 'Anicca';
    const hook = catalog.hooks[problemType]?.[variantIndex] || '';
    const detail = catalog.details[problemType]?.[variantIndex] || '';

    const created = await prisma.nudgeDelivery.create({
      data: {
        profileId,
        problemType,
        scheduledTime,
        deliveryDayLocal: new Date(`${deliveryDayLocal}T00:00:00.000Z`),
        timezone,
        lang,
        variantIndex,
        messageTitle: title,
        messageBody: hook,
        messageDetail: detail,
        status: 'queued',
      },
      select: { id: true },
    });

    return res.json({ ok: true, id: created.id, problemType, scheduledTime, deliveryDayLocal, lang, variantIndex });
  } catch (e) {
    logger.error('Failed to seed nudge delivery', e);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to seed delivery' } });
  }
});

export default router;
