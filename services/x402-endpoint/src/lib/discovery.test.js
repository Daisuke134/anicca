import { describe, expect, it } from 'vitest';

import {
  PAID_ROUTE_CATALOG,
  buildOpenApiDocument,
  buildPaymentRoutes,
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
