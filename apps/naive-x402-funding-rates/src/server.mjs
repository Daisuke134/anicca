import { HTTPFacilitatorClient } from '@x402/core/server';
import { ExactEvmScheme } from '@x402/evm/exact/server';
import { declareDiscoveryExtension } from '@x402/extensions/bazaar';
import { paymentMiddleware, x402ResourceServer } from '@x402/hono';
import { facilitator } from '@payai/facilitator';
import { Hono } from 'hono';
import { buildFundingRatesResponse, getFundingRatesCached } from '../funding-rates.mjs';

const NETWORK = 'eip155:8453';
const PRICE = '$0.003';
const AMOUNT = '3000';
const USDC_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const ADDRESS_RE = /^0x[0-9a-fA-F]{40}$/;
const PRODUCT_DESCRIPTION = 'Cross-exchange perpetual funding rates and divergence from Binance, Bybit, and Hyperliquid public market data. GET /funding-rates?symbol=BTC; paid per request in native USDC on Base.';

function baseOrigin(request) {
  const url = new URL(request.url);
  return `${url.protocol}//${url.host}`;
}

function manifest(origin, payTo) {
  return {
    x402Version: 2,
    resources: [{
      resource: `${origin}/funding-rates`,
      method: 'GET',
      price: PRICE,
      network: NETWORK,
      payTo,
      asset: USDC_BASE,
      description: PRODUCT_DESCRIPTION,
    }],
  };
}

function hasInvalidSymbol(request) {
  const symbols = new URL(request.url).searchParams.getAll('symbol');
  return symbols.length > 1 || (symbols[0] !== undefined && !/^[A-Z0-9]{1,20}$/i.test(symbols[0]));
}

export function createSellerApp({ env = process.env, getRates = getFundingRatesCached } = {}) {
  const payTo = env.EVM_ADDRESS;
  const app = new Hono();

  app.get('/healthz', (c) => c.json({ ok: true, product: 'funding-rates' }));
  app.get('/', (c) => c.json({
    product: 'Cross-exchange funding rates',
    route: '/funding-rates?symbol=BTC',
    price: PRICE,
    network: NETWORK,
    asset: USDC_BASE,
    manifest: '/.well-known/x402.json',
    discovery: '/llms.txt',
  }));
  app.get('/.well-known/x402.json', (c) => c.json(manifest(baseOrigin(c.req.raw), payTo)));
  app.get('/llms.txt', (c) => c.text([
    '# Cross-exchange funding rates API',
    'Pay per request in native USDC on Base through x402.',
    `GET ${baseOrigin(c.req.raw)}/funding-rates?symbol=BTC (${PRICE})`,
    PRODUCT_DESCRIPTION,
    `Manifest: ${baseOrigin(c.req.raw)}/.well-known/x402.json`,
  ].join('\n')));
  app.use('/funding-rates', async (c, next) => {
    if (hasInvalidSymbol(c.req.raw)) return c.json({ error: 'invalid_symbol' }, 400);
    await next();
  });

  if (!ADDRESS_RE.test(payTo ?? '')) {
    app.get('/funding-rates', (c) => c.json({ error: 'seller_not_configured' }, 503));
    return app;
  }

  const facilitatorClient = new HTTPFacilitatorClient(facilitator);
  const resourceServer = new x402ResourceServer(facilitatorClient)
    .register(NETWORK, new ExactEvmScheme());

  app.use(paymentMiddleware({
    'GET /funding-rates': {
      accepts: [{
        scheme: 'exact',
        network: NETWORK,
        payTo,
        price: { amount: AMOUNT, asset: USDC_BASE, extra: { name: 'USD Coin', version: '2' } },
        maxTimeoutSeconds: 60,
      }],
      description: PRODUCT_DESCRIPTION,
      mimeType: 'application/json',
      extensions: declareDiscoveryExtension({
        method: 'GET',
        input: { symbol: 'BTC' },
        inputSchema: {
          properties: { symbol: { type: 'string', description: 'Optional market symbol, for example BTC.' } },
          required: [],
        },
        output: { example: { rates: [], divergenceTop20: [], exchanges: [], degraded: false, errors: [], generatedAt: '2026-01-01T00:00:00.000Z' } },
      }),
    },
  }, resourceServer));

  app.get('/funding-rates', async (c) => {
    const symbols = c.req.queries('symbol') ?? [];
    try {
      const { rows, errors } = await getRates();
      return c.json(buildFundingRatesResponse(rows, { symbol: symbols[0], errors }), 200, { 'cache-control': 'no-store' });
    } catch {
      return c.json({ error: 'funding_rates_unavailable' }, 502);
    }
  });

  return app;
}
