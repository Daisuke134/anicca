import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import express from 'express';
import request from 'supertest';

describe('requireInternalAuth middleware', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    vi.resetModules();
    process.env = { ...originalEnv };
    delete process.env.INTERNAL_API_TOKEN;
    delete process.env.INTERNAL_AUTH_SECRET;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  const createApp = async () => {
    const { default: requireInternalAuth } = await import('../requireInternalAuth.js');
    const app = express();
    app.use(express.json());
    app.use(requireInternalAuth);
    app.get('/test', (_req, res) => res.json({ ok: true }));
    return app;
  };

  it('rejects when Authorization header is missing', async () => {
    process.env.INTERNAL_API_TOKEN = 'internal-token';
    const app = await createApp();
    const res = await request(app).get('/test');
    expect(res.status).toBe(401);
    expect(res.body.error).toContain('Missing Authorization bearer');
  });

  it('accepts INTERNAL_API_TOKEN bearer', async () => {
    process.env.INTERNAL_API_TOKEN = 'internal-token';
    const app = await createApp();
    const res = await request(app)
      .get('/test')
      .set('Authorization', 'Bearer internal-token');
    expect(res.status).toBe(200);
    expect(res.body.ok).toBe(true);
  });

  it('accepts INTERNAL_AUTH_SECRET bearer as fallback', async () => {
    process.env.INTERNAL_AUTH_SECRET = 'legacy-token';
    const app = await createApp();
    const res = await request(app)
      .get('/test')
      .set('Authorization', 'Bearer legacy-token');
    expect(res.status).toBe(200);
    expect(res.body.ok).toBe(true);
  });
});
