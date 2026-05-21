/**
 * x402-agents server.js Tests
 *
 * Tests: health endpoint, fail-closed guard, trust proxy, route mounting
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import express from 'express';
import request from 'supertest';

// Mock prisma
vi.mock('../lib/prisma.js', () => ({
  prisma: {
    $queryRaw: vi.fn().mockResolvedValue([{ '?column?': 1 }]),
    $disconnect: vi.fn().mockResolvedValue(undefined),
    agentAuditLog: {
      create: vi.fn().mockResolvedValue({ id: 'test-id' }),
    },
  },
}));

import { prisma } from '../lib/prisma.js';

// Mock route files with simple routers
function makeMockRouter() {
  const r = express.Router();
  r.post('/', (req, res) => res.json({ ok: true }));
  return { default: r };
}

vi.mock('../routes/emotionDetector.js', () => makeMockRouter());
vi.mock('../routes/buddhistCounsel.js', () => makeMockRouter());
vi.mock('../routes/contextCompressor.js', () => makeMockRouter());
vi.mock('../routes/decisionClarifier.js', () => makeMockRouter());
vi.mock('../routes/focusCoach.js', () => makeMockRouter());
vi.mock('../routes/habitDesigner.js', () => makeMockRouter());
vi.mock('../routes/intentRouter.js', () => makeMockRouter());
vi.mock('../routes/promptSanitizer.js', () => makeMockRouter());

// Mock x402 packages
vi.mock('@x402/express', () => ({
  paymentMiddleware: vi.fn(() => (req, res, next) => next()),
}));
vi.mock('@x402/core/server', () => ({
  x402ResourceServer: vi.fn().mockImplementation(() => ({
    register: vi.fn(),
    initialize: vi.fn().mockResolvedValue(undefined),
  })),
  HTTPFacilitatorClient: vi.fn(),
}));
vi.mock('@x402/evm/exact/server', () => ({
  ExactEvmScheme: vi.fn(),
}));
vi.mock('@x402/extensions/bazaar', () => ({
  declareDiscoveryExtension: vi.fn(() => ({})),
}));
vi.mock('@coinbase/x402', () => ({
  facilitator: { url: 'https://example.com' },
}));

describe('x402-agents server', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.X402_WALLET_ADDRESS = '0xTestWallet';
    process.env.OPENAI_API_KEY = 'sk-test';
    process.env.DATABASE_URL = 'postgresql://test';
    process.env.X402_NETWORK = 'eip155:84532';
  });

  afterEach(() => {
    delete process.env.X402_WALLET_ADDRESS;
    delete process.env.OPENAI_API_KEY;
    delete process.env.DATABASE_URL;
    delete process.env.X402_NETWORK;
  });

  it('GET /health returns 200 when DB is connected', async () => {
    const { createApp } = await import('../server.js');
    const app = await createApp();

    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
  });

  it('GET /health returns 503 when DB is down', async () => {
    prisma.$queryRaw.mockRejectedValueOnce(new Error('DB down'));

    const { createApp } = await import('../server.js');
    const app = await createApp();

    const res = await request(app).get('/health');
    expect(res.status).toBe(503);
    expect(res.body.status).toBe('error');
  });

  it('has trust proxy enabled', async () => {
    const { createApp } = await import('../server.js');
    const app = await createApp();
    expect(app.get('trust proxy')).toBe(1);
  });

  it('mounts all 8 route endpoints', async () => {
    const { createApp } = await import('../server.js');
    const app = await createApp();

    const routes = [
      '/emotion-detector', '/buddhist-counsel', '/context-compressor',
      '/decision-clarifier', '/focus-coach', '/habit-designer',
      '/intent-router', '/prompt-sanitizer',
    ];

    for (const route of routes) {
      const res = await request(app)
        .post(route)
        .send({ text: 'test' });
      expect(res.status).not.toBe(404);
    }
  });
});
