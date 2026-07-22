#!/usr/bin/env node
import express from 'express';
import { pathToFileURL } from 'node:url';
import { privateKeyToAccount } from 'viem/accounts';

import { loadEvmKey } from '../lib/resolve-identity.mjs';
import { IMAGE_OFFER, imageResaleHandler } from './image-resale.mjs';

const USDC_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

export function imageProduct({ publicUrl = '', payTo = '' } = {}) {
  const origin = String(publicUrl).replace(/\/+$/, '');
  return {
    ...IMAGE_OFFER,
    method: 'POST',
    payTo,
    resource: origin ? `${origin}${IMAGE_OFFER.path}` : IMAGE_OFFER.path,
  };
}

export function createImageApp({ product, paymentGate, handler = imageResaleHandler }) {
  if (!product) throw new TypeError('product is required');
  if (typeof paymentGate !== 'function') throw new TypeError('paymentGate is required');
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
      extensions: declareDiscoveryExtension({
        method: 'POST',
        input: { prompt: 'A blue robot building a self-funded agent economy' },
        inputSchema: {
          properties: { prompt: { type: 'string', description: 'Image prompt, 1..2000 characters' } },
          required: ['prompt'],
        },
        output: { example: { url: 'https://cdn.example/generated.png' } },
      }),
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
  const app = createImageApp({ product, paymentGate });
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
