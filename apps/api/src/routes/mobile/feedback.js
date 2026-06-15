// v1.9.1: In-app feedback form → Resend email to Dais

import express from 'express';
import { getResend } from '../../lib/resend.js';
import { prisma } from '../../lib/prisma.js';

const router = express.Router();

const FROM = 'anicca-feedback@aniccaai.com';
const TO = 'keiodaisuke@gmail.com';

const recentSubmits = new Map();
function checkRateLimit(key) {
  const now = Date.now();
  const last = recentSubmits.get(key);
  if (last && now - last < 60_000) return false;
  recentSubmits.set(key, now);
  if (recentSubmits.size > 1000) {
    for (const [k, v] of recentSubmits) {
      if (now - v > 300_000) recentSubmits.delete(k);
    }
  }
  return true;
}

router.post('/', async (req, res) => {
  const { text, locale, appUserId, appVersion } = req.body || {};

  if (typeof text !== 'string') {
    return res.status(400).json({ error: { code: 'TEXT_REQUIRED' } });
  }
  if (text.length < 5) {
    return res.status(400).json({ error: { code: 'TEXT_TOO_SHORT' } });
  }
  if (text.length > 2000) {
    return res.status(413).json({ error: { code: 'TEXT_TOO_LONG', maxLength: 2000 } });
  }

  const safeLocale = ['en', 'ja', 'es', 'fr', 'de', 'pt-BR'].includes(locale) ? locale : 'en';
  const rateKey = appUserId || req.ip;
  if (!checkRateLimit(rateKey)) {
    return res.status(429).json({ error: { code: 'RATE_LIMITED' } });
  }

  // Always persist (regardless of Resend success/fail)
  try {
    await prisma.feedback_log.create({
      data: {
        text,
        locale: safeLocale,
        appUserId: appUserId || null,
        appVersion: appVersion || null
      }
    });
  } catch (e) {
    console.error('[feedback] DB write failed', e);
  }

  // Resend send (graceful fallback to 202 on failure — client shows success)
  try {
    await getResend().emails.send({
      from: FROM,
      to: TO,
      subject: `[Anicca Feedback] ${safeLocale} ${new Date().toISOString()}`,
      text: `App version: ${appVersion || 'unknown'}\nApp user: ${appUserId || 'anonymous'}\nLocale: ${safeLocale}\n\n---\n\n${text}`
    });
    return res.json({ ok: true });
  } catch (e) {
    console.error('[feedback] resend failed', e);
    try {
      await prisma.failed_resend_calls.create({
        data: {
          callType: 'feedback.emails.send',
          payloadJson: { text: text.slice(0, 200), locale: safeLocale },
          error: String(e)
        }
      });
    } catch {}
    return res.status(202).json({ queued: true });
  }
});

export default router;
