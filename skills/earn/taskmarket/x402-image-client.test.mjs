import test from 'node:test';
import assert from 'node:assert/strict';

import {
  BLOCKRUN_IMAGE_URL,
  GPT_IMAGE_MODEL,
  USDC_BASE,
  generateImage,
} from './x402-image-client.mjs';

function paymentHeader({
  network = 'eip155:8453',
  amount = '65000',
  asset = USDC_BASE,
} = {}) {
  return Buffer.from(JSON.stringify({
    x402Version: 2,
    accepts: [{
      scheme: 'exact',
      network,
      amount,
      asset,
      payTo: '0xe9030014F5DAe217d0A152f02A043567b16c1aBf',
      maxTimeoutSeconds: 600,
      extra: { name: 'USD Coin', version: '2' },
    }],
    resource: {
      url: BLOCKRUN_IMAGE_URL,
      description: 'ChatGPT Images 2.0 image generation',
      mimeType: 'application/json',
    },
  })).toString('base64');
}

function challenge(quote = {}) {
  return new Response(JSON.stringify({ error: 'Payment Required' }), {
    status: 402,
    headers: { 'payment-required': paymentHeader(quote) },
  });
}

test('generateImage buys exactly one 1024 square GPT Image 2 output under the quote cap', async () => {
  const calls = [];
  const reservations = [];
  const fetchImpl = async (url, request) => {
    calls.push({ url, request });
    if (calls.length === 1) return challenge();
    return new Response(JSON.stringify({
      created: 1785230000,
      data: [{ url: 'https://cdn.blockrun.example/generated.png' }],
    }), { status: 200, headers: { 'content-type': 'application/json' } });
  };

  const result = await generateImage({
    prompt: 'A radial cycle plate',
    walletKey: '0x' + '1'.repeat(64),
    fetchImpl,
    createSignature: async ({ amountUsd }) => {
      assert.equal(amountUsd, 0.065);
      return 'signed-x402-payload';
    },
    reserveSpend: async (amountUsd) => reservations.push(amountUsd),
    maxQuoteUsd: 0.07,
  });

  assert.deepEqual(result, {
    url: 'https://cdn.blockrun.example/generated.png',
    model: GPT_IMAGE_MODEL,
    costUsd: 0.065,
    created: 1785230000,
  });
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, BLOCKRUN_IMAGE_URL);
  assert.deepEqual(JSON.parse(calls[0].request.body), {
    model: GPT_IMAGE_MODEL,
    prompt: 'A radial cycle plate',
    size: '1024x1024',
    n: 1,
  });
  assert.equal(calls[1].request.headers['PAYMENT-SIGNATURE'], 'signed-x402-payload');
  assert.deepEqual(reservations, [0.065]);
});

test('generateImage rejects an over-cap quote before signing or reserving spend', async () => {
  let signed = false;
  let reserved = false;
  await assert.rejects(
    generateImage({
      prompt: 'A radial cycle plate',
      walletKey: '0x' + '1'.repeat(64),
      fetchImpl: async () => challenge({ amount: '71000' }),
      createSignature: async () => { signed = true; return 'x'; },
      reserveSpend: async () => { reserved = true; },
      maxQuoteUsd: 0.07,
    }),
    /quote exceeds 0\.07 USDC cap/,
  );
  assert.equal(signed, false);
  assert.equal(reserved, false);
});

test('generateImage rejects a wrong network or token', async () => {
  await assert.rejects(
    generateImage({
      prompt: 'x',
      walletKey: '0x' + '1'.repeat(64),
      fetchImpl: async () => challenge({ network: 'eip155:1' }),
      createSignature: async () => 'x',
      reserveSpend: async () => {},
    }),
    /Base mainnet/,
  );
  await assert.rejects(
    generateImage({
      prompt: 'x',
      walletKey: '0x' + '1'.repeat(64),
      fetchImpl: async () => challenge({ asset: '0x' + '2'.repeat(40) }),
      createSignature: async () => 'x',
      reserveSpend: async () => {},
    }),
    /Base USDC/,
  );
});

test('generateImage rejects a paid response without one HTTPS image URL', async () => {
  let count = 0;
  await assert.rejects(
    generateImage({
      prompt: 'x',
      walletKey: '0x' + '1'.repeat(64),
      fetchImpl: async () => (++count === 1
        ? challenge()
        : new Response(JSON.stringify({ data: [] }), { status: 200 })),
      createSignature: async () => 'signed',
      reserveSpend: async () => {},
    }),
    /one HTTPS image URL/,
  );
});
