import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

process.env.EVM_ADDRESS ??= '0x0000000000000000000000000000000000000001';

test('uses Vercel api/index with explicit route rewrites on Node 22', async () => {
  const packageJson = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
  assert.equal(packageJson.engines.node, '22.x');
  assert.equal(packageJson.main, undefined);
  assert.equal(fs.existsSync(new URL('../api/index.mjs', import.meta.url)), true);
  const rewrites = JSON.parse(fs.readFileSync(new URL('../vercel.json', import.meta.url), 'utf8')).rewrites;
  assert.ok(rewrites.some(({ source, destination }) => source === '/' && destination === '/api/index'));
  assert.ok(rewrites.some(({ source, destination }) => source === '/funding-rates' && destination === '/api/index?__route=/funding-rates'));

  const { GET } = await import('../api/index.mjs');
  assert.equal(typeof GET, 'function');
  const response = await invoke(GET, '/healthz');
  const root = await GET(new Request('https://seller.example/api/index'));
  assert.equal(response.status, 200);
  assert.equal(root.status, 200);
  assert.equal((await root.json()).product, 'Cross-exchange funding rates');
  assert.deepEqual(await response.json(), { ok: true, product: 'funding-rates' });
});

test('protects only the existing funding-rates GET with a Base USDC x402 challenge', async () => {
  const { GET } = await import('../api/index.mjs');
  const response = await invoke(GET, '/funding-rates', { symbol: 'BTC' });

  assert.equal(response.status, 402);
  const encoded = response.headers.get('payment-required');
  assert.ok(encoded, 'x402 v2 challenge must use the PAYMENT-REQUIRED header');
  const challenge = JSON.parse(Buffer.from(encoded, 'base64').toString('utf8'));
  assert.equal(challenge.accepts[0].scheme, 'exact');
  assert.equal(challenge.accepts[0].network, 'eip155:8453');
  assert.equal(challenge.accepts[0].amount, '3000');
  assert.equal(challenge.accepts[0].asset.toLowerCase(), '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913');
  assert.equal(challenge.accepts[0].payTo, process.env.EVM_ADDRESS);
});

test('does not require payment for health and rejects other paths', async () => {
  const { GET } = await import('../api/index.mjs');
  const health = await invoke(GET, '/healthz');
  const other = await invoke(GET, '/other');
  const manifestResponse = await invoke(GET, '/.well-known/x402.json');
  const manifest = await manifestResponse.json();
  assert.equal(health.status, 200);
  assert.equal(other.status, 404);
  assert.equal(manifestResponse.status, 200);
  assert.equal(manifest.resources[0].resource, 'https://seller.example/funding-rates');
  assert.equal(manifest.resources[0].price, '$0.003');
  assert.equal(manifest.resources[0].payTo, process.env.EVM_ADDRESS);
});

test('rejects invalid symbols before asking for payment', async () => {
  const { GET } = await import('../api/index.mjs');
  const response = await invoke(GET, '/funding-rates', { symbol: ['BTC', 'ETH'] });
  assert.equal(response.status, 400);
  assert.deepEqual(await response.json(), { error: 'invalid_symbol' });
});

function invoke(app, path, query = {}) {
  const url = new URL('https://seller.example/api/index');
  url.searchParams.set('__route', path);
  for (const [key, value] of Object.entries(query)) {
    for (const item of Array.isArray(value) ? value : [value]) url.searchParams.append(key, item);
  }
  return app(new Request(url));
}
