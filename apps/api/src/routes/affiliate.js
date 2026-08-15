import crypto from 'node:crypto';
import express from 'express';
import prisma from '../lib/prisma.js';

const router = express.Router();
const VALUE = /^[a-z0-9][a-z0-9_.-]{0,79}$/;
const OFFERS = {
  elevenlabs: {
    env: 'AFFILIATE_ELEVENLABS_URL',
    host: 'try.elevenlabs.io',
  },
};

function clean(value) {
  const text = String(value || '').toLowerCase();
  return VALUE.test(text) ? text : null;
}

function material({ offer, placement, locale, experiment, variant }) {
  return [offer, placement, locale, experiment, variant].join('\n');
}

export function signAttribution(secret, fields) {
  return crypto.createHmac('sha256', secret).update(material(fields)).digest('hex');
}

function validSignature(secret, fields, supplied) {
  if (Buffer.byteLength(secret || '') < 32 || !/^[a-f0-9]{64}$/.test(String(supplied || ''))) return false;
  const expected = Buffer.from(signAttribution(secret, fields), 'hex');
  const received = Buffer.from(supplied, 'hex');
  return crypto.timingSafeEqual(expected, received);
}

function targetFor(offer) {
  const config = OFFERS[offer];
  if (!config) return null;
  try {
    const target = new URL(process.env[config.env] || '');
    return target.protocol === 'https:' && target.hostname === config.host
      ? target.toString()
      : null;
  } catch {
    return null;
  }
}

router.get('/go/:offer', async (req, res) => {
  const fields = {
    offer: clean(req.params.offer),
    placement: clean(req.query.placement),
    locale: clean(req.query.locale),
    experiment: clean(req.query.experiment),
    variant: clean(req.query.variant),
  };
  const target = targetFor(fields.offer);
  if (
    !target || Object.values(fields).some(value => !value) ||
    !validSignature(process.env.AFFILIATE_REDIRECT_SECRET, fields, req.query.sig)
  ) {
    return res.status(404).json({ error: 'AFFILIATE_LINK_NOT_FOUND' });
  }

  const clickId = crypto.randomUUID();
  try {
    await prisma.opsEvent.create({
      data: {
        source: 'affiliate-agent',
        kind: 'affiliate_click',
        tags: ['affiliate', fields.offer, fields.locale],
        payload: { clickId, ...fields },
      },
    });
  } catch {
    return res.status(503).json({ error: 'AFFILIATE_RECEIPT_UNAVAILABLE' });
  }

  res.set({
    'Cache-Control': 'no-store, max-age=0',
    'Referrer-Policy': 'origin-when-cross-origin',
    'X-Affiliate-Click-Id': clickId,
    'X-Robots-Tag': 'noindex, nofollow, noarchive',
  });
  return res.redirect(302, target);
});

export default router;
