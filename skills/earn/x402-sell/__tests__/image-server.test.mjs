import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import {
  createImageApp,
  createImageTelemetryRecorder,
  imageDiscoveryConfig,
  imageProduct,
  makeUsdcBalanceHandler,
  mergeImageOpenApi,
  usdcBalanceDiscoveryConfig,
  usdcBalanceProduct,
} from '../image-server.mjs';

test('image product publishes positive unit economics and POST discovery metadata', () => {
  const product = imageProduct({ publicUrl: 'https://seller.example', payTo: '0xabc' });
  assert.equal(product.method, 'POST');
  assert.equal(product.path, '/image');
  assert.equal(product.price, '$0.03');
  assert.equal(product.upstreamMaxUsd, 0.018);
  assert.equal(product.resource, 'https://seller.example/image');
});

test('POST Bazaar discovery declares a JSON body instead of query parameters', () => {
  const discovery = imageDiscoveryConfig();
  assert.equal(discovery.method, 'POST');
  assert.equal(discovery.bodyType, 'json');
  assert.deepEqual(discovery.input, { prompt: 'A blue robot building a self-funded agent economy' });
});

test('finalized Base USDC balance product is a low-cost paid GET', () => {
  const product = usdcBalanceProduct({ publicUrl: 'https://seller.example', payTo: '0xabc' });
  assert.equal(product.method, 'GET');
  assert.equal(product.path, '/base-usdc-balance');
  assert.equal(product.price, '$0.003');
  assert.equal(product.resource, 'https://seller.example/base-usdc-balance');
});

test('Base USDC balance discovery uses a query address without an image prompt', () => {
  const discovery = usdcBalanceDiscoveryConfig();
  assert.equal(discovery.method, 'GET');
  assert.deepEqual(discovery.inputSchema.required, ['address']);
  assert.equal('prompt' in discovery.input, false);
});

test('Base USDC balance handler reads the finalized block and returns atomic plus display units', async (t) => {
  const product = imageProduct({ publicUrl: 'https://seller.example', payTo: '0xabc' });
  const balanceProduct = usdcBalanceProduct({ publicUrl: 'https://seller.example', payTo: '0xabc' });
  const app = createImageApp({
    product,
    balanceProduct,
    paymentGate(_req, _res, next) { next(); },
    balanceHandler: makeUsdcBalanceHandler({
      createClient: () => ({
        getBlock: async () => ({ number: 123n }),
        readContract: async ({ blockNumber }) => {
          assert.equal(blockNumber, 123n);
          return 1_234_567n;
        },
      }),
    }),
    loadUpstreamOpenApi: async () => ({ openapi: '3.1.0', info: {}, paths: {} }),
  });
  const server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  t.after(() => server.close());
  const { port } = server.address();

  const response = await fetch(`http://127.0.0.1:${port}/base-usdc-balance?address=0x0000000000000000000000000000000000000001`);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    chain_id: 8453,
    asset: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    address: '0x0000000000000000000000000000000000000001',
    balance_atomic: '1234567',
    balance_usdc: '1.234567',
    finalized_block: '123',
  });
});

test('combined OpenAPI preserves upstream routes and declares the paid POST image operation', () => {
  const upstream = {
    openapi: '3.1.0',
    info: { title: 'Existing seller', version: '1', 'x-guidance': 'existing guidance' },
    paths: { '/research': { get: { operationId: 'research' } } },
  };
  const before = structuredClone(upstream);
  const product = imageProduct({ publicUrl: 'https://seller.example', payTo: '0xabc' });

  const combined = mergeImageOpenApi(upstream, product);
  const image = combined.paths['/image'].post;

  assert.deepEqual(upstream, before);
  assert.deepEqual(combined.paths['/research'], upstream.paths['/research']);
  assert.equal(image.requestBody.required, true);
  assert.deepEqual(image.requestBody.content['application/json'].schema.required, ['prompt']);
  assert.equal(image.responses['200'].content['application/json'].schema.properties.url.format, 'uri');
  assert.equal(image.responses['402'].description, 'Payment Required');
  assert.deepEqual(image['x-payment-info'], {
    price: { mode: 'fixed', currency: 'USD', amount: '0.03' },
    protocols: [{ x402: {} }],
  });
});

test('combined OpenAPI fails closed when the upstream seller manifest is unavailable', async (t) => {
  const product = imageProduct({ publicUrl: 'https://seller.example', payTo: '0xabc' });
  const app = createImageApp({
    product,
    paymentGate(_req, _res, next) { next(); },
    loadUpstreamOpenApi: async () => { throw new Error('upstream unavailable'); },
  });
  const server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  t.after(() => server.close());
  const { port } = server.address();

  const response = await fetch(`http://127.0.0.1:${port}/openapi.json`);
  assert.equal(response.status, 502);
  assert.deepEqual(await response.json(), { error: 'upstream_openapi_unavailable' });
});

test('image app keeps discovery free and gates the image handler before delivery', async (t) => {
  const order = [];
  const product = imageProduct({ publicUrl: 'https://seller.example', payTo: '0xabc' });
  const app = createImageApp({
    product,
    paymentGate(req, _res, next) { order.push(`gate:${req.path}`); next(); },
    handler(req, res) { order.push(`handler:${req.body.prompt}`); res.json({ url: 'https://cdn.example/x.png' }); },
    loadUpstreamOpenApi: async () => ({
      openapi: '3.1.0',
      info: { title: 'Existing seller', version: '1', 'x-guidance': 'existing guidance' },
      paths: { '/research': { get: { operationId: 'research' } } },
    }),
  });
  const server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  t.after(() => server.close());
  const { port } = server.address();

  const manifest = await fetch(`http://127.0.0.1:${port}/.well-known/x402.json`).then((res) => res.json());
  assert.equal(manifest.resources[0].method, 'POST');
  const openApi = await fetch(`http://127.0.0.1:${port}/openapi.json`).then((res) => res.json());
  assert.ok(openApi.paths['/research']);
  assert.ok(openApi.paths['/image'].post);
  assert.deepEqual(order, []);

  const response = await fetch(`http://127.0.0.1:${port}/image`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ prompt: 'blue robot' }),
  });
  assert.equal(response.status, 200);
  assert.deepEqual(order, ['gate:/image', 'handler:blue robot']);
});

test('image app records a privacy-safe 402 attempt without prompt or payment headers', async (t) => {
  const rows = [];
  const product = imageProduct({ publicUrl: 'https://seller.example', payTo: '0xabc' });
  const app = createImageApp({
    product,
    paymentGate(_req, res) { res.status(402).json({ error: 'payment_required' }); },
    recordAccess(row) { rows.push(row); },
    loadUpstreamOpenApi: async () => ({ openapi: '3.1.0', info: {}, paths: {} }),
  });
  const server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  t.after(() => server.close());
  const { port } = server.address();

  const response = await fetch(`http://127.0.0.1:${port}/image`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-payment': 'not-a-valid-payment' },
    body: JSON.stringify({ prompt: 'private buyer prompt' }),
  });
  assert.equal(response.status, 402);
  assert.equal(rows.length, 1);
  assert.deepEqual(rows[0], {
    ts: rows[0].ts,
    route: '/image',
    price: '$0.03',
    payer: null,
    tx: null,
    settled: false,
    status: 402,
  });
  assert.equal('prompt' in rows[0], false);
  assert.equal('headers' in rows[0], false);
});

test('image telemetry recorder separates attempts and settled sales by seller wallet', (t) => {
  const stateDir = mkdtempSync(join(tmpdir(), 'image-telemetry-'));
  t.after(() => rmSync(stateDir, { recursive: true, force: true }));
  const payTo = '0xAbC';
  const record = createImageTelemetryRecorder({ stateDir, payTo });
  const attempt = { ts: '2026-07-23T00:00:00.000Z', route: '/image', price: '$0.03', payer: null, tx: null, settled: false, status: 402 };
  const sale = { ts: '2026-07-23T00:01:00.000Z', route: '/image', price: '$0.03', payer: '0xBuyer', tx: '0xTransaction', settled: true, status: 200 };

  record(attempt);
  record(sale);

  assert.deepEqual(
    JSON.parse(readFileSync(join(stateDir, 'attempts-0xabc.jsonl'), 'utf8').trim()),
    attempt,
  );
  assert.deepEqual(
    JSON.parse(readFileSync(join(stateDir, 'sales-0xabc.jsonl'), 'utf8').trim()),
    sale,
  );
});
