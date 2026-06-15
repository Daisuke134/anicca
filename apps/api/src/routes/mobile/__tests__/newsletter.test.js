import { describe, it, expect, vi, beforeEach } from 'vitest';
import request from 'supertest';
import express from 'express';

const prismaMocks = vi.hoisted(() => ({
  newsletter_subscribers: {
    findUnique: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    updateMany: vi.fn(),
    findMany: vi.fn(),
  },
  failed_resend_calls: {
    create: vi.fn(),
  },
}));

const resendMocks = vi.hoisted(() => ({
  send: vi.fn(),
}));

vi.mock('../../../lib/prisma.js', () => ({ default: prismaMocks, prisma: prismaMocks }));
vi.mock('../../../lib/resend.js', () => ({
  getResend: () => ({ emails: { send: resendMocks.send } }),
}));

import newsletterRouter, { sendDailyNewsletter } from '../newsletter.js';

const app = express();
app.use(express.json());
app.use('/api/mobile/newsletter', newsletterRouter);

// Unique deviceId per test to avoid in-memory rate-limit bleed across tests.
let seq = 0;
const nextDevice = () => `dev-${Date.now()}-${seq++}`;

describe('POST /api/mobile/newsletter/subscribers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns 400 INVALID_EMAIL when email missing', async () => {
    const res = await request(app)
      .post('/api/mobile/newsletter/subscribers')
      .send({ deviceId: nextDevice() });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('INVALID_EMAIL');
  });

  it('returns 400 INVALID_EMAIL for malformed email', async () => {
    const res = await request(app)
      .post('/api/mobile/newsletter/subscribers')
      .send({ email: 'not-an-email', deviceId: nextDevice() });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('INVALID_EMAIL');
  });

  it('returns 400 DEVICE_ID_REQUIRED when deviceId missing', async () => {
    const res = await request(app)
      .post('/api/mobile/newsletter/subscribers')
      .send({ email: 'user@example.com' });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('DEVICE_ID_REQUIRED');
  });

  it('creates a new subscriber and returns 200 ok', async () => {
    prismaMocks.newsletter_subscribers.findUnique.mockResolvedValueOnce(null);
    prismaMocks.newsletter_subscribers.create.mockResolvedValueOnce({ id: 1n });
    const deviceId = nextDevice();
    const res = await request(app)
      .post('/api/mobile/newsletter/subscribers')
      .send({ email: 'user@example.com', locale: 'ja', deviceId });
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ ok: true });
    expect(prismaMocks.newsletter_subscribers.create).toHaveBeenCalledWith({
      data: { email: 'user@example.com', locale: 'ja', deviceId },
    });
  });

  it('updates existing subscriber (resets optedOutAt) and returns 200', async () => {
    const deviceId = nextDevice();
    prismaMocks.newsletter_subscribers.findUnique.mockResolvedValueOnce({ id: 9n, deviceId });
    prismaMocks.newsletter_subscribers.update.mockResolvedValueOnce({ id: 9n });
    const res = await request(app)
      .post('/api/mobile/newsletter/subscribers')
      .send({ email: 'again@example.com', locale: 'en', deviceId });
    expect(res.status).toBe(200);
    expect(prismaMocks.newsletter_subscribers.update).toHaveBeenCalledWith({
      where: { deviceId },
      data: { email: 'again@example.com', locale: 'en', optedOutAt: null },
    });
  });

  it('sanitizes unknown locale to en', async () => {
    prismaMocks.newsletter_subscribers.findUnique.mockResolvedValueOnce(null);
    prismaMocks.newsletter_subscribers.create.mockResolvedValueOnce({ id: 2n });
    const deviceId = nextDevice();
    await request(app)
      .post('/api/mobile/newsletter/subscribers')
      .send({ email: 'user@example.com', locale: 'zz', deviceId });
    expect(prismaMocks.newsletter_subscribers.create).toHaveBeenCalledWith({
      data: { email: 'user@example.com', locale: 'en', deviceId },
    });
  });

  it('returns 429 RATE_LIMITED on second submit within 60s for same deviceId', async () => {
    const deviceId = nextDevice();
    prismaMocks.newsletter_subscribers.findUnique.mockResolvedValue(null);
    prismaMocks.newsletter_subscribers.create.mockResolvedValue({ id: 3n });
    const first = await request(app)
      .post('/api/mobile/newsletter/subscribers')
      .send({ email: 'user@example.com', locale: 'en', deviceId });
    expect(first.status).toBe(200);
    const second = await request(app)
      .post('/api/mobile/newsletter/subscribers')
      .send({ email: 'user@example.com', locale: 'en', deviceId });
    expect(second.status).toBe(429);
    expect(second.body.error.code).toBe('RATE_LIMITED');
  });

  it('returns 500 INTERNAL_ERROR when DB throws', async () => {
    prismaMocks.newsletter_subscribers.findUnique.mockRejectedValueOnce(new Error('db down'));
    const res = await request(app)
      .post('/api/mobile/newsletter/subscribers')
      .send({ email: 'user@example.com', locale: 'en', deviceId: nextDevice() });
    expect(res.status).toBe(500);
    expect(res.body.error.code).toBe('INTERNAL_ERROR');
  });
});

describe('DELETE /api/mobile/newsletter/subscribers/:deviceId', () => {
  beforeEach(() => vi.clearAllMocks());

  it('soft-unsubscribes (sets optedOutAt) and returns 200', async () => {
    prismaMocks.newsletter_subscribers.updateMany.mockResolvedValueOnce({ count: 1 });
    const res = await request(app).delete('/api/mobile/newsletter/subscribers/dev-x');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ ok: true });
    const arg = prismaMocks.newsletter_subscribers.updateMany.mock.calls[0][0];
    expect(arg.where).toEqual({ deviceId: 'dev-x' });
    expect(arg.data.optedOutAt).toBeInstanceOf(Date);
  });
});

describe('GET /api/mobile/newsletter/unsubscribe/:deviceId (email link)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns 200 HTML and sets optedOutAt (GET, for mail clients)', async () => {
    prismaMocks.newsletter_subscribers.updateMany.mockResolvedValueOnce({ count: 1 });
    const res = await request(app).get('/api/mobile/newsletter/unsubscribe/dev-mail');
    expect(res.status).toBe(200);
    expect(res.headers['content-type']).toMatch(/text\/html/);
    expect(res.text).toMatch(/unsubscribed|配信を停止/);
    const arg = prismaMocks.newsletter_subscribers.updateMany.mock.calls[0][0];
    expect(arg.where).toEqual({ deviceId: 'dev-mail' });
    expect(arg.data.optedOutAt).toBeInstanceOf(Date);
  });

  it('still returns 200 (no leak) even if DB throws', async () => {
    prismaMocks.newsletter_subscribers.updateMany.mockRejectedValueOnce(new Error('db down'));
    const res = await request(app).get('/api/mobile/newsletter/unsubscribe/dev-err');
    expect(res.status).toBe(200);
  });
});

describe('sendDailyNewsletter()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns {sent:0} when there are no subscribers', async () => {
    prismaMocks.newsletter_subscribers.findMany.mockResolvedValueOnce([]);
    const result = await sendDailyNewsletter();
    expect(result).toEqual({ sent: 0 });
    expect(resendMocks.send).not.toHaveBeenCalled();
  });

  it('sends one email and updates lastSentAt on success', async () => {
    prismaMocks.newsletter_subscribers.findMany.mockResolvedValueOnce([
      { id: 5n, email: 'a@b.com', locale: 'ja', deviceId: 'd5' },
    ]);
    resendMocks.send.mockResolvedValueOnce({ id: 'email_1' });
    prismaMocks.newsletter_subscribers.update.mockResolvedValueOnce({});
    const result = await sendDailyNewsletter();
    expect(resendMocks.send).toHaveBeenCalledTimes(1);
    expect(prismaMocks.newsletter_subscribers.update).toHaveBeenCalledWith({
      where: { id: 5n },
      data: { lastSentAt: expect.any(Date) },
    });
    expect(result).toEqual({ sent: 1, total: 1 });
  });

  it('records failed_resend_calls after 3 failed attempts and does not update lastSentAt', async () => {
    prismaMocks.newsletter_subscribers.findMany.mockResolvedValueOnce([
      { id: 6n, email: 'fail@b.com', locale: 'en', deviceId: 'd6' },
    ]);
    resendMocks.send.mockRejectedValue(new Error('resend 401'));
    prismaMocks.failed_resend_calls.create.mockResolvedValueOnce({});
    const result = await sendDailyNewsletter();
    expect(resendMocks.send).toHaveBeenCalledTimes(3);
    expect(prismaMocks.failed_resend_calls.create).toHaveBeenCalledTimes(1);
    expect(prismaMocks.newsletter_subscribers.update).not.toHaveBeenCalled();
    expect(result).toEqual({ sent: 0, total: 1 });
  });
});
