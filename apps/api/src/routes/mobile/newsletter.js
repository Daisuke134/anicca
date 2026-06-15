// v1.9.1: Newsletter pipeline — POST /mobile/newsletter/subscribers + GET /unsubscribe
// Design: per-subscriber resend.emails.send loop (v5.1 pivot, no Segments/Broadcasts)

import express from 'express';
import { getResend } from '../../lib/resend.js';
import { prisma } from '../../lib/prisma.js';

const router = express.Router();

const EMAIL_REGEX = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const FROM = 'anicca@aniccaai.com';

// In-memory rate limit (per deviceId per minute). For 100-1000 scale this is sufficient.
const recentSubmits = new Map();
function checkRateLimit(deviceId) {
  const now = Date.now();
  const last = recentSubmits.get(deviceId);
  if (last && now - last < 60_000) return false;
  recentSubmits.set(deviceId, now);
  // Cleanup old entries (avoid memory leak)
  if (recentSubmits.size > 1000) {
    for (const [k, v] of recentSubmits) {
      if (now - v > 300_000) recentSubmits.delete(k);
    }
  }
  return true;
}

router.post('/subscribers', async (req, res) => {
  const { email, locale, deviceId } = req.body || {};
  if (!email || !EMAIL_REGEX.test(email)) {
    return res.status(400).json({ error: { code: 'INVALID_EMAIL' } });
  }
  if (!deviceId) {
    return res.status(400).json({ error: { code: 'DEVICE_ID_REQUIRED' } });
  }
  if (!checkRateLimit(deviceId)) {
    return res.status(429).json({ error: { code: 'RATE_LIMITED' } });
  }

  const safeLocale = ['en', 'ja', 'es', 'fr', 'de', 'pt-BR'].includes(locale) ? locale : 'en';

  try {
    // upsert by deviceId (second-wins on conflict)
    const existing = await prisma.newsletter_subscribers.findUnique({ where: { deviceId } });
    if (existing) {
      await prisma.newsletter_subscribers.update({
        where: { deviceId },
        data: { email, locale: safeLocale, optedOutAt: null }
      });
    } else {
      await prisma.newsletter_subscribers.create({
        data: { email, locale: safeLocale, deviceId }
      });
    }
    return res.json({ ok: true });
  } catch (e) {
    console.error('[newsletter] subscribe failed', e);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR' } });
  }
});

router.delete('/subscribers/:deviceId', async (req, res) => {
  const { deviceId } = req.params;
  try {
    await prisma.newsletter_subscribers.updateMany({
      where: { deviceId },
      data: { optedOutAt: new Date() }
    });
    return res.json({ ok: true });
  } catch (e) {
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR' } });
  }
});

// GET unsubscribe — the link embedded in daily emails. Mail clients open links
// with GET, so this must be a GET (not the in-app DELETE). Idempotent: always
// returns a 200 HTML confirmation page so prefetch/scanners never leak state or 404.
router.get('/unsubscribe/:deviceId', async (req, res) => {
  const { deviceId } = req.params;
  try {
    await prisma.newsletter_subscribers.updateMany({
      where: { deviceId },
      data: { optedOutAt: new Date() }
    });
  } catch (e) {
    console.error('[newsletter] unsubscribe (GET) failed', e);
  }
  res.set('Content-Type', 'text/html; charset=utf-8');
  return res.send('<!doctype html><meta charset="utf-8"><div style="font-family:-apple-system,sans-serif;max-width:420px;margin:48px auto;text-align:center;color:#333"><p>配信を停止しました。</p><p>You have been unsubscribed.</p></div>');
});

// Daily sender — invoked by setInterval in server.js OR by external cron.
// per-subscriber emails.send (no Segments/Broadcasts).
export async function sendDailyNewsletter() {
  const subscribers = await prisma.newsletter_subscribers.findMany({
    where: { optedOutAt: null }
  });
  if (subscribers.length === 0) return { sent: 0 };

  let sent = 0;
  for (const sub of subscribers) {
    const quote = pickRandomAffirmation(sub.locale);
    const subject = subjectFor(sub.locale, quote);
    const html = renderHtml(sub.locale, quote, sub.deviceId);

    // 3-retry exponential
    let success = false;
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        await getResend().emails.send({
          from: FROM,
          to: sub.email,
          subject,
          html,
          text: stripHtml(html)
        });
        success = true;
        break;
      } catch (e) {
        if (attempt === 3) {
          try {
            await prisma.failed_resend_calls.create({
              data: {
                callType: 'emails.send',
                payloadJson: { to: sub.email, subject },
                error: String(e)
              }
            });
          } catch {}
        } else {
          await new Promise(r => setTimeout(r, 1000 * Math.pow(2, attempt - 1)));
        }
      }
    }
    if (success) {
      await prisma.newsletter_subscribers.update({
        where: { id: sub.id },
        data: { lastSentAt: new Date() }
      });
      sent++;
    }
  }
  return { sent, total: subscribers.length };
}

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const catalogCache = new Map();
function pickRandomAffirmation(locale) {
  try {
    const key = ['ja', 'es', 'en'].includes(locale) ? locale : 'en';
    if (!catalogCache.has(key)) {
      const p = path.join(__dirname, '..', '..', 'modules', 'affirmations', 'catalog', `${key}.json`);
      catalogCache.set(key, JSON.parse(fs.readFileSync(p, 'utf-8')));
    }
    const catalog = catalogCache.get(key);
    const ids = Object.keys(catalog.quotes || {});
    if (ids.length === 0) throw new Error('empty catalog');
    const id = ids[Math.floor(Math.random() * ids.length)];
    return { id, text: catalog.quotes[id] };
  } catch (e) {
    return { id: 'q001', text: locale === 'ja' ? '今日は、 一呼吸から。' : 'Today, start with one breath.' };
  }
}

function subjectFor(locale, quote) {
  const truncated = quote.text.slice(0, 40);
  return locale === 'ja' ? `🌅 ${truncated}` : `🌅 ${truncated}`;
}

function renderHtml(locale, quote, deviceId) {
  const greeting = locale === 'ja' ? 'おはようございます。' : 'Good morning.';
  const unsubLine = locale === 'ja' ? '配信停止' : 'Unsubscribe';
  const unsubURL = `https://anicca-proxy-production.up.railway.app/api/mobile/newsletter/unsubscribe/${encodeURIComponent(deviceId)}`;
  return `<div style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:480px;margin:0 auto;padding:24px">
  <p style="color:#888;font-size:14px">${greeting}</p>
  <blockquote style="font-size:18px;line-height:1.5;color:#333;border-left:3px solid #ccc;padding-left:16px;margin:24px 0">
    ${quote.text}
  </blockquote>
  <p style="color:#bbb;font-size:11px;margin-top:32px">
    <a href="${unsubURL}" style="color:#bbb">${unsubLine}</a>
  </p>
</div>`;
}

function stripHtml(html) {
  return html.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
}

export default router;
