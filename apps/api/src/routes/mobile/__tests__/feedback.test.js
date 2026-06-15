import { describe, it, expect, vi, beforeEach } from 'vitest';
import request from 'supertest';
import express from 'express';

const prismaMocks = vi.hoisted(() => ({
  feedback_log: {
    create: vi.fn(),
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

import feedbackRouter from '../feedback.js';

const app = express();
app.use(express.json());
app.use('/api/mobile/feedback', feedbackRouter);

let seq = 0;
const nextUser = () => `user-${Date.now()}-${seq++}`;

describe('POST /api/mobile/feedback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns 400 TEXT_REQUIRED when text is not a string', async () => {
    const res = await request(app)
      .post('/api/mobile/feedback')
      .send({ locale: 'ja', appUserId: nextUser() });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('TEXT_REQUIRED');
  });

  it('returns 400 TEXT_TOO_SHORT when text < 5 chars', async () => {
    const res = await request(app)
      .post('/api/mobile/feedback')
      .send({ text: 'hi', locale: 'ja', appUserId: nextUser() });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('TEXT_TOO_SHORT');
  });

  it('returns 413 TEXT_TOO_LONG when text > 2000 chars', async () => {
    const res = await request(app)
      .post('/api/mobile/feedback')
      .send({ text: 'a'.repeat(2001), locale: 'ja', appUserId: nextUser() });
    expect(res.status).toBe(413);
    expect(res.body.error.code).toBe('TEXT_TOO_LONG');
    expect(res.body.error.maxLength).toBe(2000);
  });

  it('persists feedback, sends email, returns 200 ok on success', async () => {
    prismaMocks.feedback_log.create.mockResolvedValueOnce({ id: 1n });
    resendMocks.send.mockResolvedValueOnce({ id: 'email_1' });
    const res = await request(app)
      .post('/api/mobile/feedback')
      .send({ text: 'please add dark mode', locale: 'ja', appUserId: nextUser(), appVersion: '1.9.1' });
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ ok: true });
    expect(prismaMocks.feedback_log.create).toHaveBeenCalledTimes(1);
    expect(resendMocks.send).toHaveBeenCalledTimes(1);
  });

  it('sanitizes unknown locale to en in the persisted row', async () => {
    prismaMocks.feedback_log.create.mockResolvedValueOnce({ id: 2n });
    resendMocks.send.mockResolvedValueOnce({ id: 'email_2' });
    await request(app)
      .post('/api/mobile/feedback')
      .send({ text: 'hello world feedback', locale: 'zz', appUserId: nextUser() });
    const arg = prismaMocks.feedback_log.create.mock.calls[0][0];
    expect(arg.data.locale).toBe('en');
  });

  it('returns 202 queued and records failed_resend_calls when Resend fails', async () => {
    prismaMocks.feedback_log.create.mockResolvedValueOnce({ id: 3n });
    resendMocks.send.mockRejectedValueOnce(new Error('resend 401'));
    prismaMocks.failed_resend_calls.create.mockResolvedValueOnce({});
    const res = await request(app)
      .post('/api/mobile/feedback')
      .send({ text: 'feedback that fails to email', locale: 'en', appUserId: nextUser() });
    expect(res.status).toBe(202);
    expect(res.body).toEqual({ queued: true });
    expect(prismaMocks.failed_resend_calls.create).toHaveBeenCalledTimes(1);
  });

  it('returns 429 RATE_LIMITED on second submit within 60s for same appUserId', async () => {
    const appUserId = nextUser();
    prismaMocks.feedback_log.create.mockResolvedValue({ id: 4n });
    resendMocks.send.mockResolvedValue({ id: 'email_x' });
    const first = await request(app)
      .post('/api/mobile/feedback')
      .send({ text: 'first feedback message', locale: 'en', appUserId });
    expect(first.status).toBe(200);
    const second = await request(app)
      .post('/api/mobile/feedback')
      .send({ text: 'second feedback message', locale: 'en', appUserId });
    expect(second.status).toBe(429);
    expect(second.body.error.code).toBe('RATE_LIMITED');
  });
});
