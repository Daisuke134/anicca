/**
 * x402-agents discovery surface tests
 *
 * Tests: /.well-known/x402, /.well-known/agent.json, /llms.txt, / stay public
 * (including fail-closed), and the payment middleware receives a GET variant
 * of every POST paid route so directory probes (402index) get a 402 instead
 * of a 404.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import express from 'express';
import request from 'supertest';

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

vi.mock('@x402/express', () => ({
  paymentMiddleware: vi.fn(() => (req, res, next) => next()),
}));
vi.mock('@x402/core/server', () => ({
  // Plain function implementations (not arrows): vitest 4 refuses to use an
  // arrow function as a constructor, and server.js news these classes up.
  x402ResourceServer: vi.fn().mockImplementation(function () {
    return {
      register: vi.fn(),
      initialize: vi.fn().mockResolvedValue(undefined),
      onAfterSettle: vi.fn(),
    };
  }),
  HTTPFacilitatorClient: vi.fn().mockImplementation(function () {
    return {};
  }),
}));
vi.mock('@x402/evm/exact/server', () => ({
  ExactEvmScheme: vi.fn().mockImplementation(function () {
    return {
      parsePrice: vi.fn().mockResolvedValue({ amount: '0', asset: '0x0', extra: {} }),
    };
  }),
}));
vi.mock('@x402/extensions/bazaar', () => ({
  declareDiscoveryExtension: vi.fn(() => ({})),
}));
vi.mock('@coinbase/x402', () => ({
  facilitator: { url: 'https://example.com' },
}));

describe('x402-agents discovery surface', () => {
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

  it('GET /.well-known/x402 lists every paid resource', async () => {
    const { createApp } = await import('../server.js');
    const app = await createApp();

    const res = await request(app).get('/.well-known/x402');
    expect(res.status).toBe(200);
    expect(res.body.version).toBe(1);
    expect(res.body.resources).toHaveLength(9);
    expect(res.body.resources.some(u => u.endsWith('/context-compressor'))).toBe(true);
    expect(res.body.resources.some(u => u.endsWith('/funding-rates'))).toBe(true);
  });

  it('GET /.well-known/agent.json returns the agent card', async () => {
    const { createApp } = await import('../server.js');
    const app = await createApp();

    const res = await request(app).get('/.well-known/agent.json');
    expect(res.status).toBe(200);
    expect(res.body.name).toBe('Anicca x402 Agent APIs');
    expect(res.body.endpoints).toHaveLength(9);
    expect(res.body.discovery.llms).toMatch(/\/llms\.txt$/);
  });

  it('GET /llms.txt returns the plain-text index', async () => {
    const { createApp } = await import('../server.js');
    const app = await createApp();

    const res = await request(app).get('/llms.txt');
    expect(res.status).toBe(200);
    expect(res.type).toMatch(/text\/plain/);
    expect(res.text).toContain('# Anicca x402 Agent APIs');
    expect(res.text).toContain('/context-compressor');
    expect(res.text).toContain('/funding-rates');
  });

  it('GET /.well-known/402index-verify.txt serves only the 402index verification hash', async () => {
    const { createApp } = await import('../server.js');
    const app = await createApp();

    const res = await request(app).get('/.well-known/402index-verify.txt');
    expect(res.status).toBe(200);
    expect(res.type).toMatch(/text\/plain/);
    // Hash issued by POST /api/v1/claim on 402index.io for this hostname;
    // the claim instructions require the file to contain only this hash.
    expect(res.text.trim()).toBe('4886e2fe03089311796e0447f4802daab00c0f3e57df2149d8488c0d1fdfcb36');
  });

  it('GET / returns the service index instead of 404', async () => {
    const { createApp } = await import('../server.js');
    const app = await createApp();

    const res = await request(app).get('/');
    expect(res.status).toBe(200);
    expect(res.body.name).toBe('Anicca x402 Agent APIs');
    expect(res.body.endpoints).toHaveLength(9);
  });

  it('keeps the discovery surface public when the paid router is fail-closed', async () => {
    delete process.env.X402_WALLET_ADDRESS;
    const { createApp } = await import('../server.js');
    const app = await createApp();

    for (const path of ['/.well-known/x402', '/.well-known/agent.json', '/.well-known/402index-verify.txt', '/llms.txt', '/']) {
      const res = await request(app).get(path);
      expect(res.status).toBe(200);
    }

    const paid = await request(app).post('/context-compressor').send({ text: 'test' });
    expect(paid.status).toBe(503);
  });

  it('registers a GET variant of every POST paid route with the payment middleware', async () => {
    const { createApp } = await import('../server.js');
    await createApp();

    const { paymentMiddleware } = await import('@x402/express');
    expect(paymentMiddleware).toHaveBeenCalled();
    const routes = paymentMiddleware.mock.calls.at(-1)[0];

    const postRoutes = Object.keys(routes).filter(r => r.startsWith('POST '));
    expect(postRoutes).toHaveLength(8);
    for (const route of postRoutes) {
      const getVariant = `GET ${route.slice('POST '.length)}`;
      expect(routes[getVariant]).toBeDefined();
      expect(routes[getVariant].accepts).toEqual(routes[route].accepts);
      expect(typeof routes[getVariant].unpaidResponseBody).toBe('function');
      // The bazaar discovery extension declares the POST body schema and
      // is invalid under a GET route, so GET variants must not carry it.
      expect(routes[getVariant].extensions).toBeUndefined();
    }
    expect(routes['GET /funding-rates']).toBeDefined();
  });
});
