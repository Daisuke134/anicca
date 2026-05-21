/**
 * Agent Auth Middleware Tests (1.6.1)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import express from 'express';
import request from 'supertest';

describe('requireAgentAuth middleware', () => {
  let app;
  const originalEnv = process.env;

  beforeEach(() => {
    // Reset module cache to reload with new env
    vi.resetModules();
    process.env = { ...originalEnv };
    process.env.ANICCA_AGENT_TOKEN = 'test-token-current';
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  const createApp = async () => {
    const { requireAgentAuth } = await import('../requireAgentAuth.js');
    app = express();
    app.use(express.json());
    app.use(requireAgentAuth);
    app.get('/test', (req, res) => {
      res.json({ success: true, tokenType: req.agentAuth?.tokenType });
    });
    return app;
  };

  it('should reject requests without Authorization header (AC-5)', async () => {
    await createApp();
    const res = await request(app).get('/test');
    expect(res.status).toBe(401);
    expect(res.body.message).toContain('Missing');
  });

  it('should reject requests with invalid token format', async () => {
    await createApp();
    const res = await request(app)
      .get('/test')
      .set('Authorization', 'InvalidFormat token');
    expect(res.status).toBe(401);
  });

  it('should reject requests with wrong token (AC-5)', async () => {
    await createApp();
    const res = await request(app)
      .get('/test')
      .set('Authorization', 'Bearer wrong-token');
    expect(res.status).toBe(401);
    expect(res.body.message).toContain('Invalid');
  });

  it('should accept current token (AC-5)', async () => {
    await createApp();
    const res = await request(app)
      .get('/test')
      .set('Authorization', 'Bearer test-token-current');
    expect(res.status).toBe(200);
    expect(res.body.tokenType).toBe('current');
  });

  it('should accept old token during rotation grace period (AC-5)', async () => {
    process.env.ANICCA_AGENT_TOKEN_OLD = 'test-token-old';
    await createApp();
    const res = await request(app)
      .get('/test')
      .set('Authorization', 'Bearer test-token-old');
    expect(res.status).toBe(200);
    expect(res.body.tokenType).toBe('legacy');
  });

  it('should prefer current token over old token', async () => {
    process.env.ANICCA_AGENT_TOKEN_OLD = 'test-token-current';
    await createApp();
    const res = await request(app)
      .get('/test')
      .set('Authorization', 'Bearer test-token-current');
    expect(res.status).toBe(200);
    expect(res.body.tokenType).toBe('current');
  });
});
