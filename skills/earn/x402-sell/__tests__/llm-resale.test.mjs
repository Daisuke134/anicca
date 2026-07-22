import test from 'node:test';
import assert from 'node:assert/strict';

import {
  LLM_OFFER_VARIANTS,
  assertProfitableOffer,
  makeLlmResaleHandler,
} from '../llm-resale.mjs';

function responseHarness() {
  return {
    statusCode: 200,
    body: null,
    status(code) { this.statusCode = code; return this; },
    json(body) { this.body = body; return this; },
  };
}

test('every LLM offer price stays strictly above its capped upstream cost', () => {
  for (const offer of LLM_OFFER_VARIANTS) {
    assert.doesNotThrow(() => assertProfitableOffer(offer));
    assert.ok(Number(offer.price.slice(1)) > offer.upstreamMaxUsd);
  }
  assert.throws(
    () => assertProfitableOffer({ price: '$0.010', upstreamMaxUsd: 0.010 }),
    /must exceed upstream/i,
  );
});

test('LLM resale rejects missing and oversized prompts before spending', async () => {
  let calls = 0;
  const handler = makeLlmResaleHandler({
    getBalanceUsd: async () => 4.5,
    loadKey: () => `0x${'1'.repeat(64)}`,
    bareFetch: async () => { calls += 1; return fake402('10000'); },
  });

  const missing = responseHarness();
  await handler({ query: {} }, missing);
  assert.equal(missing.statusCode, 400);

  const oversized = responseHarness();
  await handler({ query: { prompt: 'x'.repeat(2001) } }, oversized);
  assert.equal(oversized.statusCode, 400);
  assert.equal(calls, 0);
});

test('LLM resale fails closed on low float and daily cap', async () => {
  let signed = 0;
  const common = {
    loadKey: () => `0x${'1'.repeat(64)}`,
    bareFetch: async () => fake402('10000'),
    signPayment: async () => { signed += 1; return 'signature'; },
  };

  const lowFloat = makeLlmResaleHandler({ ...common, getBalanceUsd: async () => 0.49 });
  const lowFloatRes = responseHarness();
  await lowFloat({ query: { prompt: 'hello' } }, lowFloatRes);
  assert.equal(lowFloatRes.statusCode, 503);

  const capped = makeLlmResaleHandler({
    ...common,
    getBalanceUsd: async () => 4.5,
    readState: () => ({ date: '2026-07-22', spentUsd: 0.25 }),
    now: () => new Date('2026-07-22T12:00:00Z'),
    dailyCapUsd: 0.25,
  });
  const cappedRes = responseHarness();
  await capped({ query: { prompt: 'hello' } }, cappedRes);
  assert.equal(cappedRes.statusCode, 503);
  assert.equal(signed, 0);
});

test('LLM resale passes buyer text as data, caps tokens, uses own key, and records conservative spend', async () => {
  const writes = [];
  let requestBody;
  let signing;
  const key = `0x${'2'.repeat(64)}`;
  const handler = makeLlmResaleHandler({
    getBalanceUsd: async () => 4.5,
    loadKey: () => key,
    readState: () => null,
    writeState: (_path, state) => writes.push(state),
    now: () => new Date('2026-07-22T12:00:00Z'),
    bareFetch: async (_url, options) => {
      requestBody = JSON.parse(options.body);
      return fake402('10000');
    },
    signPayment: async (input) => { signing = input; return 'signature'; },
    paidFetch: async () => ({
      status: 200,
      json: async () => ({ model: 'test/model', choices: [{ message: { content: 'safe answer' } }] }),
    }),
  });
  const res = responseHarness();
  const prompt = 'hello; $(touch /tmp/must-not-run)';
  await handler({ query: { prompt, maxTokens: '99999' } }, res);

  assert.equal(res.statusCode, 200);
  assert.equal(res.body.response, 'safe answer');
  assert.equal(requestBody.messages[0].content, prompt);
  assert.equal(requestBody.max_tokens, 512);
  assert.equal(signing.walletKey, key);
  assert.deepEqual(writes, [{ date: '2026-07-22', spentUsd: 0.01 }]);
});

test('LLM resale returns 502 and does not book spend when the unpaid probe fails', async () => {
  let wrote = false;
  const handler = makeLlmResaleHandler({
    getBalanceUsd: async () => 4.5,
    loadKey: () => `0x${'3'.repeat(64)}`,
    writeState: () => { wrote = true; },
    bareFetch: async () => { throw new Error('provider down'); },
  });
  const res = responseHarness();
  await handler({ query: { prompt: 'hello' } }, res);

  assert.equal(res.statusCode, 502);
  assert.equal(wrote, false);
});

const challenge = (amount = '1000') => Buffer.from(JSON.stringify({
  x402Version: 2,
  resource: { url: 'https://blockrun.ai/api/v1/chat/completions', description: 'chat', mimeType: 'application/json' },
  accepts: [{
    scheme: 'exact', network: 'eip155:8453', amount,
    asset: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    payTo: '0x00000000000000000000000000000000000000aa', maxTimeoutSeconds: 60,
    extra: { name: 'USD Coin', version: '2' },
  }],
})).toString('base64');

function fake402(amount) {
  return { status: 402, headers: { get: (name) => name.toLowerCase() === 'payment-required' ? challenge(amount) : null } };
}

test('real BlockRun quote above the offer cap is rejected before signing', async () => {
  let signed = 0;
  const handler = makeLlmResaleHandler({
    getBalanceUsd: async () => 4.5,
    loadKey: () => `0x${'4'.repeat(64)}`,
    bareFetch: async () => fake402('11000'),
    signPayment: async () => { signed += 1; return 'signature'; },
  });
  const res = responseHarness();
  await handler({ query: { prompt: 'hello' } }, res);
  assert.equal(res.statusCode, 503);
  assert.equal(signed, 0);
});

test('concurrent requests reserve atomically so only one can consume the remaining daily cap', async () => {
  let state = null;
  let signed = 0;
  const handler = makeLlmResaleHandler({
    getBalanceUsd: async () => 4.5,
    loadKey: () => `0x${'5'.repeat(64)}`,
    readState: () => state,
    writeState: (_path, value) => { state = value; },
    dailyCapUsd: 0.01,
    bareFetch: async () => fake402('10000'),
    signPayment: async () => { signed += 1; return 'signature'; },
    paidFetch: async () => ({
      status: 200,
      json: async () => ({ model: 'zai/glm-5-turbo', choices: [{ message: { content: 'ok' } }] }),
    }),
  });
  const a = responseHarness();
  const b = responseHarness();
  await Promise.all([
    handler({ query: { prompt: 'one' } }, a),
    handler({ query: { prompt: 'two' } }, b),
  ]);
  assert.deepEqual([a.statusCode, b.statusCode].sort(), [200, 503]);
  assert.equal(signed, 1);
  assert.deepEqual(state, { date: new Date().toISOString().slice(0, 10), spentUsd: 0.01 });
});

test('a failure after signing keeps the conservative reservation', async () => {
  let state = null;
  const handler = makeLlmResaleHandler({
    getBalanceUsd: async () => 4.5,
    loadKey: () => `0x${'6'.repeat(64)}`,
    readState: () => state,
    writeState: (_path, value) => { state = value; },
    bareFetch: async () => fake402('10000'),
    signPayment: async () => 'signature',
    paidFetch: async () => ({ status: 500, json: async () => ({ error: 'after payment' }) }),
  });
  const res = responseHarness();
  await handler({ query: { prompt: 'hello' } }, res);
  assert.equal(res.statusCode, 502);
  assert.equal(state.spentUsd, 0.01);
});

test('paid BlockRun request exposes no inherited human credentials', async () => {
  let paidHeaders;
  const handler = makeLlmResaleHandler({
    getBalanceUsd: async () => 4.5,
    loadKey: () => `0x${'7'.repeat(64)}`,
    bareFetch: async () => fake402('10000'),
    signPayment: async () => 'signature',
    paidFetch: async (_url, options) => {
      paidHeaders = options.headers;
      return { status: 200, json: async () => ({ model: 'zai/glm-5-turbo', choices: [{ message: { content: 'ok' } }] }) };
    },
  });
  const res = responseHarness();
  await handler({ query: { prompt: 'hello' } }, res);
  assert.deepEqual(Object.keys(paidHeaders).sort(), ['Content-Type', 'PAYMENT-SIGNATURE', 'User-Agent'].sort());
});
