import test from 'node:test';
import assert from 'node:assert/strict';

import { createImageApp, imageDiscoveryConfig, imageProduct, mergeImageOpenApi } from '../image-server.mjs';

test('image product publishes positive unit economics and POST discovery metadata', () => {
  const product = imageProduct({ publicUrl: 'https://seller.example', payTo: '0xabc' });
  assert.equal(product.method, 'POST');
  assert.equal(product.path, '/image');
  assert.equal(product.price, '$0.05');
  assert.equal(product.upstreamMaxUsd, 0.018);
  assert.equal(product.resource, 'https://seller.example/image');
});

test('POST Bazaar discovery declares a JSON body instead of query parameters', () => {
  const discovery = imageDiscoveryConfig();
  assert.equal(discovery.method, 'POST');
  assert.equal(discovery.bodyType, 'json');
  assert.deepEqual(discovery.input, { prompt: 'A blue robot building a self-funded agent economy' });
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
    price: { mode: 'fixed', currency: 'USD', amount: '0.05' },
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
