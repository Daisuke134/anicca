import test from 'node:test';
import assert from 'node:assert/strict';

import {
  IMAGE_OFFER,
  assertProfitableImageOffer,
  makeImageResaleHandler,
} from '../image-resale.mjs';

function responseHarness() {
  return {
    statusCode: 200,
    body: null,
    status(code) { this.statusCode = code; return this; },
    json(body) { this.body = body; return this; },
  };
}

const challenge = (amount = '17751') => Buffer.from(JSON.stringify({
  x402Version: 2,
  resource: {
    url: 'https://blockrun.ai/api/v1/images/generations',
    description: 'image generation',
    mimeType: 'application/json',
  },
  accepts: [{
    scheme: 'exact', network: 'eip155:8453', amount,
    asset: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    payTo: '0x00000000000000000000000000000000000000aa', maxTimeoutSeconds: 120,
    extra: { name: 'USD Coin', version: '2' },
  }],
})).toString('base64');

function fake402(amount) {
  return {
    status: 402,
    headers: { get: (name) => name.toLowerCase() === 'payment-required' ? challenge(amount) : null },
  };
}

test('image offer stays profitable against the guarded upstream quote', () => {
  assert.doesNotThrow(() => assertProfitableImageOffer(IMAGE_OFFER));
  assert.equal(IMAGE_OFFER.model, 'zai/cogview-4');
  assert.equal(IMAGE_OFFER.price, '$0.05');
  assert.equal(IMAGE_OFFER.upstreamMaxUsd, 0.018);
  assert.ok(IMAGE_OFFER.grossMarginUsd >= 0.032);
  assert.throws(
    () => assertProfitableImageOffer({ price: '$0.018', upstreamMaxUsd: 0.018 }),
    /must exceed upstream/i,
  );
});

test('image resale rejects missing and oversized prompts before any upstream spend', async () => {
  let calls = 0;
  const handler = makeImageResaleHandler({
    loadKey: () => `0x${'1'.repeat(64)}`,
    getBalanceUsd: async () => 4.5,
    bareFetch: async () => { calls += 1; return fake402(); },
  });

  const missing = responseHarness();
  await handler({ body: {} }, missing);
  assert.equal(missing.statusCode, 400);

  const oversized = responseHarness();
  await handler({ body: { prompt: 'x'.repeat(2001) } }, oversized);
  assert.equal(oversized.statusCode, 400);
  assert.equal(calls, 0);
});

test('image resale rejects an upstream quote above the unit-cost guard before signing', async () => {
  let signed = 0;
  const handler = makeImageResaleHandler({
    loadKey: () => `0x${'2'.repeat(64)}`,
    getBalanceUsd: async () => 4.5,
    bareFetch: async () => fake402('18001'),
    signPayment: async () => { signed += 1; return 'signature'; },
  });
  const res = responseHarness();
  await handler({ body: { prompt: 'a blue robot' } }, res);

  assert.equal(res.statusCode, 503);
  assert.equal(signed, 0);
});

test('image resale forces the fixed cheap model, reserves actual spend, and returns the image URL', async () => {
  const writes = [];
  let requestBody;
  let signing;
  const key = `0x${'3'.repeat(64)}`;
  const handler = makeImageResaleHandler({
    loadKey: () => key,
    getBalanceUsd: async () => 4.5,
    readState: () => null,
    writeState: (_path, state) => writes.push(state),
    now: () => new Date('2026-07-22T12:00:00Z'),
    bareFetch: async (_url, options) => {
      requestBody = JSON.parse(options.body);
      return fake402();
    },
    signPayment: async (input) => { signing = input; return 'signature'; },
    paidFetch: async () => ({
      status: 200,
      json: async () => ({ created: 123, data: [{ url: 'https://cdn.example/image.png' }] }),
    }),
  });
  const res = responseHarness();
  await handler({ body: { prompt: 'a blue robot', model: 'google/nano-banana-pro', n: 99 } }, res);

  assert.equal(res.statusCode, 200);
  assert.equal(res.body.url, 'https://cdn.example/image.png');
  assert.deepEqual(requestBody, {
    model: 'zai/cogview-4', prompt: 'a blue robot', size: '1024x1024', n: 1,
  });
  assert.equal(signing.walletKey, key);
  assert.deepEqual(writes, [{ date: '2026-07-22', spentUsd: 0.017751 }]);
});

test('image resale sends no inherited human credentials upstream', async () => {
  let paidHeaders;
  const handler = makeImageResaleHandler({
    loadKey: () => `0x${'4'.repeat(64)}`,
    getBalanceUsd: async () => 4.5,
    readState: () => null,
    writeState: () => {},
    bareFetch: async () => fake402(),
    signPayment: async () => 'signature',
    paidFetch: async (_url, options) => {
      paidHeaders = options.headers;
      return { status: 200, json: async () => ({ data: [{ url: 'https://cdn.example/x.png' }] }) };
    },
  });
  const res = responseHarness();
  await handler({
    body: { prompt: 'safe landscape' },
    headers: {
      authorization: 'Bearer inherited-human-credential',
      cookie: 'session=inherited-human-credential',
      'x-api-key': 'inherited-human-credential',
    },
  }, res);

  assert.deepEqual(Object.keys(paidHeaders).sort(), ['Content-Type', 'PAYMENT-SIGNATURE', 'User-Agent'].sort());
});

test('image resale fails closed on low float', async () => {
  let calls = 0;
  const handler = makeImageResaleHandler({
    loadKey: () => `0x${'5'.repeat(64)}`,
    getBalanceUsd: async () => 0.49,
    bareFetch: async () => { calls += 1; return fake402(); },
  });
  const res = responseHarness();
  await handler({ body: { prompt: 'safe landscape' } }, res);

  assert.equal(res.statusCode, 503);
  assert.equal(calls, 0);
});

test('a failure after signing keeps the conservative image-spend reservation', async () => {
  let state = null;
  const handler = makeImageResaleHandler({
    loadKey: () => `0x${'6'.repeat(64)}`,
    getBalanceUsd: async () => 4.5,
    readState: () => state,
    writeState: (_path, value) => { state = value; },
    bareFetch: async () => fake402(),
    signPayment: async () => 'signature',
    paidFetch: async () => ({ status: 500, json: async () => ({ error: 'failed' }) }),
  });
  const res = responseHarness();
  await handler({ body: { prompt: 'safe landscape' } }, res);

  assert.equal(res.statusCode, 502);
  assert.equal(state.spentUsd, 0.017751);
});
