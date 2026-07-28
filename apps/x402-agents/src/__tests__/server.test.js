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
      findMany: vi.fn().mockResolvedValue([]),
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
vi.mock('../routes/fundingRates.js', () => {
  const r = express.Router();
  r.get('/', (req, res) => res.json({ ok: true }));
  return { default: r };
});

// Mock x402 packages
vi.mock('@x402/express', () => ({
  paymentMiddleware: vi.fn(() => (req, res, next) => next()),
}));
vi.mock('@x402/core/server', () => ({
  x402ResourceServer: vi.fn().mockImplementation(() => ({
    register: vi.fn(),
    initialize: vi.fn().mockResolvedValue(undefined),
    onAfterSettle: vi.fn(),
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

  it('GET /settlements exposes a bounded public feed', async () => {
    prisma.agentAuditLog.findMany.mockResolvedValueOnce([{
      id: '11111111-1111-1111-1111-111111111111',
      createdAt: new Date('2026-07-27T22:31:00.000Z'),
      requestPayload: {
        route: '/context-compressor',
        method: 'POST',
        scheme: 'exact',
        network: 'eip155:8453',
        asset: '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913',
        amount_atomic: '8000',
        pay_to: '0x6592eb8ef820abc092e8c3474fb2042dffccedc7',
      },
      responsePayload: {
        success: true,
        transaction: '0xcf095a8703837e2a07026c97f009ed874a0e8e7759a282b4d24c4884151092f0',
        payer: '0xe7747fd899d8987821bb4cb3d6adf22565f87ce9',
      },
    }]);
    const { createApp } = await import('../server.js');
    const app = await createApp();

    const res = await request(app).get('/settlements?limit=500');

    expect(res.status).toBe(200);
    expect(res.body.settlements).toHaveLength(1);
    expect(res.body.settlements[0].transaction).toMatch(/^0x[0-9a-f]{64}$/);
    expect(prisma.agentAuditLog.findMany).toHaveBeenCalledWith(expect.objectContaining({ take: 100 }));
  });

  it('GET /openapi.json is public even when the paid router is fail-closed', async () => {
    delete process.env.X402_WALLET_ADDRESS;
    const { createApp } = await import('../server.js');
    const app = await createApp();

    const spec = await request(app).get('/openapi.json');
    expect(spec.status).toBe(200);
    expect(spec.type).toMatch(/json/);
    expect(spec.body.openapi).toBe('3.1.0');
    expect(Object.keys(spec.body.paths)).toHaveLength(9);

    const paid = await request(app)
      .post('/context-compressor')
      .send({ text: 'test' });
    expect(paid.status).toBe(503);
  });

  it('GET /favicon.ico is a public image for discovery catalogs', async () => {
    delete process.env.X402_WALLET_ADDRESS;
    const { createApp } = await import('../server.js');
    const app = await createApp();

    const favicon = await request(app).get('/favicon.ico');
    expect(favicon.status).toBe(200);
    expect(favicon.type).toMatch(/^image\//);
    expect(favicon.body.toString('utf8')).toContain('<svg');
  });

  it('keeps discovery metadata available when the paid API rate limit is exhausted', async () => {
    const { createApp } = await import('../server.js');
    const app = await createApp();

    for (let requestNumber = 0; requestNumber < 30; requestNumber += 1) {
      const paid = await request(app)
        .post('/context-compressor')
        .send({ text: `request-${requestNumber}` });
      expect(paid.status).toBe(200);
    }

    const limitedPaid = await request(app)
      .post('/context-compressor')
      .send({ text: 'request-over-limit' });
    expect(limitedPaid.status).toBe(429);

    const spec = await request(app).get('/openapi.json');
    expect(spec.status).toBe(200);
    expect(spec.body.openapi).toBe('3.1.0');

    const favicon = await request(app).get('/favicon.ico');
    expect(favicon.status).toBe(200);
  });

  it('has trust proxy enabled', async () => {
    const { createApp } = await import('../server.js');
    const app = await createApp();
    expect(app.get('trust proxy')).toBe(1);
  });

  it('mounts all 9 route endpoints', async () => {
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
    const funding = await request(app).get('/funding-rates');
    expect(funding.status).not.toBe(404);
  });
});
