#!/usr/bin/env node
import express from 'express';
import { appendFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { privateKeyToAccount } from 'viem/accounts';

import { loadEvmKey } from '../lib/resolve-identity.mjs';
import { IMAGE_OFFER, imageResaleHandler } from './image-resale.mjs';
import { decodePayer, isSettled } from './lib/settle-gate.mjs';

const USDC_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const HERE = dirname(fileURLToPath(import.meta.url));

export function imageProduct({ publicUrl = '', payTo = '' } = {}) {
  const origin = String(publicUrl).replace(/\/+$/, '');
  return {
    ...IMAGE_OFFER,
    method: 'POST',
    payTo,
    resource: origin ? `${origin}${IMAGE_OFFER.path}` : IMAGE_OFFER.path,
  };
}

export function imageDiscoveryConfig() {
  return {
    method: 'POST',
    bodyType: 'json',
    input: { prompt: 'A blue robot building a self-funded agent economy' },
    inputSchema: {
      properties: { prompt: { type: 'string', description: 'Image prompt, 1..2000 characters' } },
      required: ['prompt'],
    },
    output: { example: { url: 'https://cdn.example/generated.png' } },
  };
}

export function mergeImageOpenApi(upstream, product) {
  if (!upstream || typeof upstream !== 'object' || !upstream.paths || typeof upstream.paths !== 'object') {
    throw new TypeError('upstream OpenAPI document must contain paths');
  }
  const existingPath = upstream.paths[product.path] || {};
  return {
    ...upstream,
    paths: {
      ...upstream.paths,
      [product.path]: {
        ...existingPath,
        post: {
          operationId: 'generateImage',
          summary: 'Generate an image from a text prompt',
          description: product.description,
          requestBody: {
            required: true,
            content: {
              'application/json': {
                schema: {
                  type: 'object',
                  properties: {
                    prompt: { type: 'string', minLength: 1, maxLength: 2000 },
                  },
                  required: ['prompt'],
                  additionalProperties: false,
                },
              },
            },
          },
          'x-payment-info': {
            price: { mode: 'fixed', currency: 'USD', amount: '0.05' },
            protocols: [{ x402: {} }],
          },
          responses: {
            200: {
              description: 'Generated image URL',
              content: {
                'application/json': {
                  schema: {
                    type: 'object',
                    properties: { url: { type: 'string', format: 'uri' } },
                    required: ['url'],
                  },
                },
              },
            },
            402: { description: 'Payment Required' },
          },
        },
      },
    },
  };
}

export function createImageTelemetryRecorder({ stateDir, payTo }) {
  if (!stateDir) throw new TypeError('stateDir is required');
  if (!payTo) throw new TypeError('payTo is required');
  const wallet = String(payTo).toLowerCase();
  const attemptsLog = join(stateDir, `attempts-${wallet}.jsonl`);
  const salesLog = join(stateDir, `sales-${wallet}.jsonl`);
  try { mkdirSync(stateDir, { recursive: true }); } catch { /* best-effort telemetry */ }
  return (row) => {
    const safeRow = {
      ts: String(row.ts),
      route: String(row.route),
      price: String(row.price),
      payer: row.payer ? String(row.payer) : null,
      settled: row.settled === true,
      status: Number(row.status),
    };
    try {
      appendFileSync(safeRow.settled ? salesLog : attemptsLog, `${JSON.stringify(safeRow)}\n`);
    } catch { /* logging must never break serving */ }
  };
}

function paymentPayer(req) {
  try {
    const decoded = JSON.parse(Buffer.from(req.header('x-payment') || '', 'base64').toString('utf8'));
    return decoded?.payload?.authorization?.from || null;
  } catch { return null; }
}

export function createImageApp({
  product,
  paymentGate,
  handler = imageResaleHandler,
  loadUpstreamOpenApi,
  recordAccess,
}) {
  if (!product) throw new TypeError('product is required');
  if (typeof paymentGate !== 'function') throw new TypeError('paymentGate is required');
  if (recordAccess !== undefined && typeof recordAccess !== 'function') throw new TypeError('recordAccess must be a function');
  const app = express();
  app.use(express.json({ limit: '16kb' }));
  app.get('/.well-known/x402.json', (_req, res) => res.json({
    x402Version: 2,
    resources: [{
      resource: product.resource,
      method: product.method,
      price: product.price,
      network: 'eip155:8453',
      payTo: product.payTo,
      asset: USDC_BASE,
      description: product.description,
    }],
  }));
  app.get('/', (_req, res) => res.json({
    products: [{ path: product.path, method: product.method, price: product.price, what: product.what }],
    manifest: '/.well-known/x402.json',
  }));
  app.get('/openapi.json', async (_req, res) => {
    try {
      if (typeof loadUpstreamOpenApi !== 'function') throw new Error('upstream loader missing');
      res.json(mergeImageOpenApi(await loadUpstreamOpenApi(), product));
    } catch {
      res.status(502).json({ error: 'upstream_openapi_unavailable' });
    }
  });
  if (recordAccess) {
    app.use((req, res, next) => {
      if (req.path !== product.path) return next();
      const requestPayer = paymentPayer(req);
      res.on('finish', () => {
        const paymentResponse = res.getHeader('PAYMENT-RESPONSE');
        recordAccess({
          ts: new Date().toISOString(),
          route: req.path,
          price: product.price,
          payer: requestPayer || decodePayer(paymentResponse),
          settled: isSettled(paymentResponse),
          status: res.statusCode,
        });
      });
      next();
    });
  }
  app.use(paymentGate);
  app.post(product.path, handler);
  return app;
}

function resolvePayTo(env) {
  if (env.X402_PAYTO) return env.X402_PAYTO;
  const key = loadEvmKey({ env });
  if (!key) throw new Error('set X402_PAYTO (no per-instance EVM key resolvable)');
  return privateKeyToAccount(key).address;
}

async function createRuntimePaymentGate(product, env) {
  const { paymentMiddleware, x402ResourceServer } = await import('@x402/express');
  const { HTTPFacilitatorClient } = await import('@x402/core/server');
  const { ExactEvmScheme } = await import('@x402/evm/exact/server');
  const { declareDiscoveryExtension } = await import('@x402/extensions/bazaar');

  let facilitatorClient;
  if (env.CDP_API_KEY_ID && env.CDP_API_KEY_SECRET) {
    const { createFacilitatorConfig } = await import('@coinbase/x402');
    const config = createFacilitatorConfig(env.CDP_API_KEY_ID, env.CDP_API_KEY_SECRET);
    facilitatorClient = new HTTPFacilitatorClient({
      url: config.url,
      createAuthHeaders: config.createAuthHeaders,
    });
  } else {
    facilitatorClient = new HTTPFacilitatorClient({ url: 'https://x402.org/facilitator' });
  }
  const resourceServer = new x402ResourceServer(facilitatorClient)
    .register('eip155:8453', new ExactEvmScheme());
  const routes = {
    [`${product.method} ${product.path}`]: {
      accepts: [{
        scheme: 'exact',
        price: product.price,
        network: 'eip155:8453',
        payTo: product.payTo,
        extra: { asset: USDC_BASE },
      }],
      resource: product.resource,
      description: product.description,
      mimeType: 'application/json',
      extensions: declareDiscoveryExtension(imageDiscoveryConfig()),
    },
  };
  return paymentMiddleware(routes, resourceServer);
}

async function main(env = process.env) {
  const product = imageProduct({
    publicUrl: env.X402_IMAGE_PUBLIC_URL || env.X402_PUBLIC_URL || '',
    payTo: resolvePayTo(env),
  });
  const paymentGate = await createRuntimePaymentGate(product, env);
  const upstreamOpenApi = env.X402_IMAGE_UPSTREAM_OPENAPI;
  if (!upstreamOpenApi) throw new Error('set X402_IMAGE_UPSTREAM_OPENAPI');
  const app = createImageApp({
    product,
    paymentGate,
    recordAccess: createImageTelemetryRecorder({
      stateDir: env.X402_STATE_DIR || join(HERE, 'state'),
      payTo: product.payTo,
    }),
    loadUpstreamOpenApi: async () => {
      const response = await fetch(upstreamOpenApi, { signal: AbortSignal.timeout(10_000) });
      if (!response.ok) throw new Error(`upstream OpenAPI HTTP ${response.status}`);
      return response.json();
    },
  });
  const port = Number(env.X402_IMAGE_PORT || 8093);
  app.listen(port, '127.0.0.1', () => {
    process.stdout.write(`${JSON.stringify({ status: 'up', port, product })}\n`);
  });
}

const isEntry = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isEntry) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
