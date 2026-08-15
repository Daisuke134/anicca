import { beforeEach, describe, expect, it, vi } from 'vitest';
import express from 'express';
import request from 'supertest';

const prisma = vi.hoisted(() => ({ opsEvent: { create: vi.fn() } }));
vi.mock('../../lib/prisma.js', () => ({ default: prisma }));

import affiliateRouter, { signAttribution } from '../affiliate.js';

const app = express();
app.use('/api/affiliate', affiliateRouter);
const fields = {
  offer: 'elevenlabs', placement: 'article-1', locale: 'en',
  experiment: 'e0', variant: 'control',
};
const secret = 'test-secret-that-is-at-least-32-bytes-long';

function path(sig = signAttribution(secret, fields)) {
  const query = new URLSearchParams({ ...fields, sig });
  return `/api/affiliate/go/elevenlabs?${query}`;
}

describe('GET /api/affiliate/go/:offer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.AFFILIATE_REDIRECT_SECRET = secret;
    process.env.AFFILIATE_ELEVENLABS_URL = 'https://try.elevenlabs.io/example';
  });

  it('persists one click receipt before redirecting to the fixed offer', async () => {
    prisma.opsEvent.create.mockResolvedValueOnce({ id: 'event-1' });
    const response = await request(app).get(path());
    expect(response.status).toBe(302);
    expect(response.headers.location).toBe('https://try.elevenlabs.io/example');
    expect(prisma.opsEvent.create).toHaveBeenCalledTimes(1);
    expect(prisma.opsEvent.create.mock.calls[0][0].data.payload).toMatchObject(fields);
  });

  it('rejects a forged signature without writing or redirecting', async () => {
    const response = await request(app).get(path('0'.repeat(64)));
    expect(response.status).toBe(404);
    expect(response.headers.location).toBeUndefined();
    expect(prisma.opsEvent.create).not.toHaveBeenCalled();
  });

  it('does not create an untracked redirect when receipt persistence fails', async () => {
    prisma.opsEvent.create.mockRejectedValueOnce(new Error('database down'));
    const response = await request(app).get(path());
    expect(response.status).toBe(503);
    expect(response.headers.location).toBeUndefined();
  });
});
