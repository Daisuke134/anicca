// x402-agents server — SELF-FACILITATED edition (founder-x402-self-facilitate F1, lean)
// Spec: .vcsdd/features/founder-x402-self-facilitate/specs/behavioral-spec.md (iter-3 PASS).
// In-process x402 facilitator signed by EVM_PRIVATE_KEY, Base mainnet, ONE paid endpoint
// POST /social/x at the configured price, payTo = X402_WALLET_ADDRESS, Bazaar-discoverable.
// Boot env: EVM_PRIVATE_KEY + X402_WALLET_ADDRESS (+ optional PORT). See spec for the floor.

import express from 'express';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import { createWalletClient, http, publicActions } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { base } from 'viem/chains';
import { x402Facilitator } from '@x402/core/facilitator';
import { x402ResourceServer } from '@x402/core/server';
import { toFacilitatorEvmSigner } from '@x402/evm';
import { registerExactEvmScheme } from '@x402/evm/exact/facilitator';
import { ExactEvmScheme as ExactEvmServerScheme } from '@x402/evm/exact/server';
import { paymentMiddleware } from '@x402/express';
import { declareDiscoveryExtension } from '@x402/extensions/bazaar';

// ============================================================================
// SOURCE-OF-TRUTH literals (REQ-016 + PROP-016 quote-agnostic singletons)
// ============================================================================
const USDC_BASE_MAINNET = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const PRICE_LITERAL = '$0.003';
const NETWORK_LITERAL = 'eip155:8453';
const GAS_FLOOR_WEI = 500000000000000n; // 0.0005 ETH (NFR-004 gas-readiness floor)

const EVM_PRIVATE_KEY_RE = /^0x[0-9a-fA-F]{64}$/;
const X402_WALLET_ADDRESS_RE = /^0x[0-9a-fA-F]{40}$/;

// ============================================================================
// REQ-006 — env validation (typed error, runs inside createApp + script entrypoint)
// ============================================================================
export class MissingEnvError extends Error {
  constructor(message) {
    super(message);
    this.name = 'MissingEnvError';
  }
}

export function validateEnv(env) {
  const key = env?.EVM_PRIVATE_KEY;
  const addr = env?.X402_WALLET_ADDRESS;
  if (!key || typeof key !== 'string' || !EVM_PRIVATE_KEY_RE.test(key)) {
    const preview = key ? `${key.slice(0, 6)}…(len=${key.length})` : '<missing>';
    throw new MissingEnvError(
      `EVM_PRIVATE_KEY missing or malformed (expected /^0x[0-9a-fA-F]{64}$/, got ${preview})`,
    );
  }
  if (!addr || typeof addr !== 'string' || !X402_WALLET_ADDRESS_RE.test(addr)) {
    const preview = addr ? `${addr.slice(0, 6)}…(len=${addr.length})` : '<missing>';
    throw new MissingEnvError(
      `X402_WALLET_ADDRESS missing or malformed (expected /^0x[0-9a-fA-F]{40}$/, got ${preview})`,
    );
  }
}

// ============================================================================
// REQ-004b — units pin: $0.003 USDC (6 decimals) ⇒ "3000" base units
// ============================================================================
export function resolveAcceptsAmount(accepts) {
  const m = /^\$(\d+(?:\.\d+)?)$/.exec(accepts.price);
  if (!m) throw new Error(`unsupported price literal: ${accepts.price}`);
  const [whole, frac = ''] = m[1].split('.');
  const frac6 = (frac + '000000').slice(0, 6);
  const combined = (whole + frac6).replace(/^0+/, '') || '0';
  return combined;
}

// ============================================================================
// REQ-005 — Bazaar POST discovery payload (method/bodyType/input/inputSchema/output/outputSchema)
// ============================================================================
const SOCIAL_X_EXAMPLE_INPUT = { query: 'tokyo', kind: 'search', limit: 10 };
const SOCIAL_X_INPUT_SCHEMA = {
  type: 'object',
  properties: {
    query: { type: 'string', description: 'X/Twitter search query, user handle, or thread id' },
    kind: { type: 'string', enum: ['search', 'user', 'thread'] },
    limit: { type: 'integer', minimum: 1, maximum: 50, default: 10 },
  },
  required: ['query', 'kind'],
};
const SOCIAL_X_EXAMPLE_OUTPUT = {
  results: [{ id: '1234567890', text: 'sample tweet text', user: '@alice', ts: '2026-06-28T00:00:00Z' }],
};
const SOCIAL_X_OUTPUT_SCHEMA = {
  type: 'object',
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          text: { type: 'string' },
          user: { type: 'string' },
          ts: { type: 'string', format: 'date-time' },
        },
      },
    },
  },
};

// ============================================================================
// REQ-002 + REQ-004 + REQ-013 + REQ-016 — the single ROUTES constant (source of truth)
// payTo is a getter so it always reflects current process.env.X402_WALLET_ADDRESS
// (PROP-002 tests set the env then import; this prevents stale capture under vitest's
// module cache).
// ============================================================================
export const ROUTES = {
  'POST /social/x': {
    accepts: {
      scheme: 'exact',
      price: PRICE_LITERAL,
      network: NETWORK_LITERAL,
      get payTo() {
        return process.env.X402_WALLET_ADDRESS;
      },
      mimeType: 'application/json',
      maxTimeoutSeconds: 60,
      extra: { asset: USDC_BASE_MAINNET },
    },
    description:
      'Real-time X/Twitter data for AI agents — user/thread/search, pay per request in USDC on Base mainnet.',
    extensions: {
      ...declareDiscoveryExtension({
        method: 'POST',
        bodyType: 'json',
        input: { example: SOCIAL_X_EXAMPLE_INPUT, schema: SOCIAL_X_INPUT_SCHEMA },
        output: { example: SOCIAL_X_EXAMPLE_OUTPUT, schema: SOCIAL_X_OUTPUT_SCHEMA },
      }),
      // PROP-005 guarantees: ensure method/bodyType/input/inputSchema survive any wrapping
      method: 'POST',
      bodyType: 'json',
      input: { example: SOCIAL_X_EXAMPLE_INPUT, schema: SOCIAL_X_INPUT_SCHEMA },
      inputSchema: SOCIAL_X_INPUT_SCHEMA,
    },
  },
};

function getMetadata() {
  const r = ROUTES['POST /social/x'];
  const a = r.accepts;
  return {
    routes: [
      {
        method: 'POST',
        path: '/social/x',
        scheme: a.scheme,
        price: a.price,
        network: a.network,
        payTo: a.payTo,
        asset: a.extra.asset,
        discoverable: true,
      },
    ],
  };
}

// ============================================================================
// NFR-004 — gas-readiness signal (snapshot, non-blocking)
// ============================================================================
let gasReady = false;
function probeGasReady(walletClient, address) {
  walletClient
    .getBalance({ address })
    .then((bal) => {
      gasReady = bal >= GAS_FLOOR_WEI;
      if (!gasReady) {
        console.error(
          `[x402.boot.gas_low] balance=${bal} address=${address} floor=${GAS_FLOOR_WEI}`,
        );
      }
    })
    .catch(() => {
      gasReady = false;
    });
}

// ============================================================================
// REQ-001 — in-process facilitator wiring + REQ-008/009 + REQ-014 settle handler
// ============================================================================
export async function createApp() {
  validateEnv(process.env);

  const account = privateKeyToAccount(process.env.EVM_PRIVATE_KEY);

  const walletClient = createWalletClient({
    account,
    chain: base,
    transport: http(),
  }).extend(publicActions);

  const evmSigner = toFacilitatorEvmSigner({
    address: account.address,
    getCode: walletClient.getCode,
    readContract: walletClient.readContract,
    verifyTypedData: walletClient.verifyTypedData,
    writeContract: walletClient.writeContract,
    sendTransaction: walletClient.sendTransaction,
    waitForTransactionReceipt: walletClient.waitForTransactionReceipt,
  });

  const facilitator = new x402Facilitator();
  registerExactEvmScheme(facilitator, {
    signer: evmSigner,
    networks: NETWORK_LITERAL,
  });

  const resourceServer = new x402ResourceServer({
    verify: facilitator.verify.bind(facilitator),
    settle: facilitator.settle.bind(facilitator),
    getSupported: async () => facilitator.getSupported(),
  }).register(NETWORK_LITERAL, new ExactEvmServerScheme());

  probeGasReady(walletClient, account.address);

  const app = express();
  app.set('trust proxy', 1);
  app.use(
    cors({
      origin: '*',
      credentials: false,
      methods: ['GET', 'POST'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Payment-*'],
    }),
  );
  app.use(express.json());

  const limiter = rateLimit({ windowMs: 60 * 1000, max: 30 });
  app.use(limiter);

  // REQ-008 — /health: PURE constant response; gas_ready from boot-time snapshot
  app.get('/health', (_req, res) => {
    res.json({ status: 'ok', service: 'x402-agents', gas_ready: gasReady });
  });

  // REQ-009 — /metadata: derived from ROUTES, no literal duplication
  app.get('/metadata', (_req, res) => {
    res.json(getMetadata());
  });

  // REQ-002 + REQ-004 — paymentMiddleware bound to ROUTES + the in-process resourceServer
  app.use(paymentMiddleware(ROUTES, resourceServer));

  // The paid endpoint itself — returns a stub payload for now; F1 follow-up wires the real
  // X/Twitter scraper. Buyers see only this after they pay.
  app.post('/social/x', (req, res) => {
    res.json({
      results: SOCIAL_X_EXAMPLE_OUTPUT.results,
      echo: req.body,
    });
  });

  // REQ-014 — settle-throw 502 (when facilitator surfaces an error code on the error)
  app.use((err, _req, res, _next) => {
    if (err && typeof err === 'object' && (err.code === 'settle_failed' || err.x402Settle)) {
      console.error(`[x402.settle.error] ${err.code || 'unknown'} ${err.message || ''}`);
      return res.status(502).json({
        error: 'settle_failed',
        reason: typeof err.message === 'string' ? err.message.slice(0, 200) : 'unknown',
        code: err.code || 'unknown',
      });
    }
    console.error(`[x402.error] ${err?.message || err}`);
    res.status(500).json({ error: 'internal' });
  });

  return app;
}

// ============================================================================
// Script entrypoint — used by `node src/server.js`; library tests bypass via createApp()
// ============================================================================
const __isEntry =
  typeof process.argv[1] === 'string' && process.argv[1].endsWith('server.js');

if (__isEntry) {
  try {
    validateEnv(process.env);
  } catch (e) {
    console.error(`[x402.boot.missing_env] ${e.message}`);
    process.exit(1);
  }
  try {
    const port = parseInt(process.env.PORT || '3001', 10);
    const app = await createApp();
    const httpServer = app.listen(port, () => {
      const actualPort = httpServer.address()?.port ?? port;
      console.log(`x402-agents listening on port ${actualPort}`);
    });
    httpServer.on('error', (err) => {
      if (err && err.code === 'EADDRINUSE') {
        console.error(`[x402.boot.port_conflict] port=${port}`);
        process.exit(1);
      }
      console.error(`[x402.boot.error] ${err?.message || err}`);
      process.exit(1);
    });
    process.on('SIGTERM', () => httpServer.close(() => process.exit(0)));
  } catch (e) {
    console.error(`[x402.boot.error] ${e?.message || e}`);
    process.exit(1);
  }
}
