import { describe, expect, it } from 'vitest';

import {
  PAID_ROUTE_CATALOG,
  buildAgentCardDocument,
  buildLlmsText,
  buildOpenApiDocument,
  buildPaymentRoutes,
  buildWellKnownDocument,
} from './discovery.js';

const EXPECTED = Object.freeze({
  'POST /context-compressor': '0.008',
  'POST /emotion-detector': '0.01',
  'POST /buddhist-counsel': '0.01',
  'POST /focus-coach': '0.01',
  'POST /habit-designer': '0.01',
  'POST /prompt-sanitizer': '0.005',
  'POST /decision-clarifier': '0.008',
  'POST /intent-router': '0.005',
  'GET /funding-rates': '0.01',
});

describe('x402 discovery catalog', () => {
  it('is the single source for all nine paid runtime routes and prices', () => {
    expect(Object.keys(PAID_ROUTE_CATALOG).sort()).toEqual(Object.keys(EXPECTED).sort());

    const routes = buildPaymentRoutes({
      payTo: '0x1111111111111111111111111111111111111111',
      network: 'eip155:8453',
      declareDiscoveryExtension: input => ({ bazaar: input }),
    });

    for (const [route, price] of Object.entries(EXPECTED)) {
      expect(routes[route].accepts.price).toBe(`$${price}`);
      expect(routes[route].accepts.network).toBe('eip155:8453');
      expect(routes[route].accepts.payTo).toBe('0x1111111111111111111111111111111111111111');
      expect(routes[route].extensions.bazaar.input).toBeDefined();
      expect(routes[route].extensions.bazaar.output).toBeDefined();
    }
  });

  it('builds a complete x402scan-compatible OpenAPI contract without payee or secrets', () => {
    const document = buildOpenApiDocument({
      origin: 'https://x402-agents-production.up.railway.app',
    });

    expect(document.openapi).toBe('3.1.0');
    expect(document.info.contact.email).toBe('contact@aniccaai.com');
    expect(document.info['x-guidance']).toMatch(/agent/i);

    const operations = [];
    for (const [path, pathItem] of Object.entries(document.paths)) {
      for (const [method, operation] of Object.entries(pathItem)) {
        operations.push([`${method.toUpperCase()} ${path}`, operation]);
      }
    }
    expect(operations.map(([route]) => route).sort()).toEqual(Object.keys(EXPECTED).sort());

    for (const [route, operation] of operations) {
      expect(operation.operationId).toMatch(/^[a-z][A-Za-z0-9]+$/);
      expect(operation.description.length).toBeGreaterThan(20);
      expect(operation.responses['402'].description).toBe('Payment Required');
      expect(operation['x-payment-info']).toEqual({
        price: { mode: 'fixed', currency: 'USD', amount: EXPECTED[route] },
        protocols: [{ x402: {} }],
      });
      if (route.startsWith('POST ')) {
        expect(operation.requestBody.content['application/json'].schema.type).toBe('object');
        expect(operation.requestBody.content['application/json'].schema.properties).toBeDefined();
      } else {
        expect(operation.parameters).toBeInstanceOf(Array);
      }
      expect(operation.responses['200'].content['application/json'].schema).toBeDefined();
      expect(operation.responses['200'].content['application/json'].example).toBeDefined();
    }

    const serialized = JSON.stringify(document);
    expect(serialized).not.toContain('X402_WALLET_ADDRESS');
    expect(serialized).not.toContain('OPENAI_API_KEY');
    expect(serialized).not.toContain('DATABASE_URL');
    expect(serialized).not.toMatch(/0x[a-fA-F0-9]{40}/);
  });
});

describe('x402 well-known discovery document', () => {
  it('lists every catalog route as an absolute resource URL (spec B minimal payload)', () => {
    const doc = buildWellKnownDocument({ origin: 'https://example.com/' });

    expect(doc.version).toBe(1);
    expect(doc.ownershipProofs).toEqual([]);
    expect(doc.resources).toHaveLength(Object.keys(PAID_ROUTE_CATALOG).length);
    for (const route of Object.keys(PAID_ROUTE_CATALOG)) {
      const path = route.split(' ')[1];
      expect(doc.resources).toContain(`https://example.com${path}`);
    }
    const serialized = JSON.stringify(doc);
    expect(serialized).not.toMatch(/0x[a-fA-F0-9]{40}/);
  });
});

describe('x402 unpaid response body', () => {
  const stubParsePrice = async () => ({
    amount: '8000',
    asset: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    extra: { name: 'USD Coin', version: '2' },
  });

  it('mirrors the Payment Required document into the 402 body when a price parser is supplied', async () => {
    const routes = buildPaymentRoutes({
      payTo: '0x1111111111111111111111111111111111111111',
      network: 'eip155:8453',
      declareDiscoveryExtension: input => ({ bazaar: input }),
      parsePrice: stubParsePrice,
    });

    const config = routes['POST /context-compressor'];
    expect(typeof config.unpaidResponseBody).toBe('function');

    const { contentType, body } = await config.unpaidResponseBody({
      adapter: { getUrl: () => 'https://example.com/context-compressor' },
    });

    expect(contentType).toBe('application/json');
    expect(body.x402Version).toBe(2);
    expect(body.error).toBe('Payment required');
    expect(body.resource).toEqual({
      url: 'https://example.com/context-compressor',
      description: PAID_ROUTE_CATALOG['POST /context-compressor'].description,
      mimeType: 'application/json',
    });
    expect(body.accepts).toEqual([{
      scheme: 'exact',
      network: 'eip155:8453',
      amount: '8000',
      asset: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
      payTo: '0x1111111111111111111111111111111111111111',
      maxTimeoutSeconds: 300,
      extra: { name: 'USD Coin', version: '2' },
    }]);
  });

  it('converts each route price through the supplied parser', async () => {
    const seen = [];
    const routes = buildPaymentRoutes({
      payTo: '0x1111111111111111111111111111111111111111',
      network: 'eip155:8453',
      declareDiscoveryExtension: input => ({ bazaar: input }),
      parsePrice: async (price, network) => {
        seen.push([price, network]);
        return { amount: '1', asset: '0x0000000000000000000000000000000000000000', extra: {} };
      },
    });

    await routes['GET /funding-rates'].unpaidResponseBody({ adapter: { getUrl: () => 'https://example.com/funding-rates' } });
    expect(seen).toEqual([['$0.01', 'eip155:8453']]);
  });

  it('omits unpaidResponseBody when no price parser is supplied', () => {
    const routes = buildPaymentRoutes({
      payTo: '0x1111111111111111111111111111111111111111',
      network: 'eip155:8453',
      declareDiscoveryExtension: input => ({ bazaar: input }),
    });

    for (const config of Object.values(routes)) {
      expect(config.unpaidResponseBody).toBeUndefined();
    }
  });
});

describe('x402 agent card and llms.txt', () => {
  it('builds an agent card indexing every endpoint with its price and no payee address', () => {
    const card = buildAgentCardDocument({ origin: 'https://example.com/' });

    expect(card.name).toBe('Anicca x402 Agent APIs');
    expect(card.url).toBe('https://example.com');
    expect(card.discovery).toEqual({
      x402Manifest: 'https://example.com/.well-known/x402',
      openapi: 'https://example.com/openapi.json',
      llms: 'https://example.com/llms.txt',
    });
    expect(card.endpoints).toHaveLength(Object.keys(PAID_ROUTE_CATALOG).length);
    for (const [route, price] of Object.entries(EXPECTED)) {
      const [method, path] = route.split(' ');
      const endpoint = card.endpoints.find(e => e.method === method && e.url === `https://example.com${path}`);
      expect(endpoint).toBeDefined();
      expect(endpoint.price).toEqual({ currency: 'USD', amount: price, per: 'call' });
    }
    expect(JSON.stringify(card)).not.toMatch(/0x[a-fA-F0-9]{40}/);
  });

  it('renders llms.txt with the discovery links and every priced endpoint', () => {
    const text = buildLlmsText({ origin: 'https://example.com' });

    expect(text.startsWith('# Anicca x402 Agent APIs')).toBe(true);
    expect(text).toContain('(https://example.com/.well-known/x402)');
    expect(text).toContain('(https://example.com/openapi.json)');
    for (const [route, price] of Object.entries(EXPECTED)) {
      const [method, path] = route.split(' ');
      expect(text).toContain(`[${method} ${path}](https://example.com${path})`);
      expect(text).toContain(`Price: $${price} per call.`);
    }
    expect(text).not.toMatch(/0x[a-fA-F0-9]{40}/);
  });
});
