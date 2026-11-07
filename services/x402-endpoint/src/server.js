/**
 * x402-agents server
 *
 * Independent Express server for x402-gated AI agent endpoints.
 * Fail-closed design: if x402 init fails, all routes return 503.
 */

import express from 'express';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import { prisma } from './lib/prisma.js';
import {
  buildAgentCardDocument,
  buildLlmsText,
  buildOpenApiDocument,
  buildPaymentRoutes,
  buildWellKnownDocument,
} from './lib/discovery.js';
import { listSettlementRecords, recordSettlement } from './lib/settlement-records.js';

import buddhistCounselRouter from './routes/buddhistCounsel.js';
import contextCompressorRouter from './routes/contextCompressor.js';
import decisionClarifierRouter from './routes/decisionClarifier.js';
import emotionDetectorRouter from './routes/emotionDetector.js';
import focusCoachRouter from './routes/focusCoach.js';
import habitDesignerRouter from './routes/habitDesigner.js';
import intentRouterRouter from './routes/intentRouter.js';
import promptSanitizerRouter from './routes/promptSanitizer.js';
import fundingRatesRouter from './routes/fundingRates.js';

// 402index domain ownership proof: POST /api/v1/claim on 402index.io issued
// this verification hash for the production hostname. The claim endpoint
// instructs: place a text file at /.well-known/402index-verify.txt
// containing only this hash. It is a public ownership token, not a secret.
const INDEX402_VERIFICATION_HASH = '4886e2fe03089311796e0447f4802daab00c0f3e57df2149d8488c0d1fdfcb36';

const REQUIRED_ENV = ['X402_WALLET_ADDRESS', 'OPENAI_API_KEY', 'DATABASE_URL'];

function checkRequiredEnv() {
  const missing = REQUIRED_ENV.filter(key => !process.env[key]);
  if (missing.length > 0) {
    console.error(`Missing required env vars: ${missing.join(', ')}`);
    process.exit(1);
  }
}

export async function createApp({ x402InitializeTimeoutMs = 15000 } = {}) {
  const app = express();

  app.set('trust proxy', 1);

  app.use(cors({
    origin: '*',
    credentials: false,
    methods: ['GET', 'POST'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Payment-*'],
  }));

  app.use(express.json());

  const limiter = rateLimit({
    windowMs: 60 * 1000,
    max: 30,
    skip: (req) => req.path === '/openapi.json'
      || req.path === '/.well-known/x402'
      || req.path === '/.well-known/agent.json'
      || req.path === '/.well-known/402index-verify.txt'
      || req.path === '/llms.txt'
      || req.path === '/'
      || req.path === '/favicon.ico',
  });
  app.use(limiter);

  app.get('/openapi.json', (req, res) => {
    const configuredOrigin = process.env.PUBLIC_ORIGIN;
    const requestOrigin = `${req.protocol}://${req.get('host')}`;
    return res.json(buildOpenApiDocument({ origin: configuredOrigin || requestOrigin }));
  });

  app.get('/.well-known/x402', (req, res) => {
    const configuredOrigin = process.env.PUBLIC_ORIGIN;
    const requestOrigin = `${req.protocol}://${req.get('host')}`;
    return res.json(buildWellKnownDocument({ origin: configuredOrigin || requestOrigin }));
  });

  app.get('/.well-known/agent.json', (req, res) => {
    const configuredOrigin = process.env.PUBLIC_ORIGIN;
    const requestOrigin = `${req.protocol}://${req.get('host')}`;
    return res.json(buildAgentCardDocument({ origin: configuredOrigin || requestOrigin }));
  });

  // 402index domain ownership proof (see INDEX402_VERIFICATION_HASH above):
  // the body must contain only the verification hash.
  app.get('/.well-known/402index-verify.txt', (req, res) => {
    res.type('text/plain; charset=utf-8');
    return res.send(`${INDEX402_VERIFICATION_HASH}\n`);
  });

  app.get('/llms.txt', (req, res) => {
    const configuredOrigin = process.env.PUBLIC_ORIGIN;
    const requestOrigin = `${req.protocol}://${req.get('host')}`;
    res.type('text/plain; charset=utf-8');
    return res.send(buildLlmsText({ origin: configuredOrigin || requestOrigin }));
  });

  // Service index for humans and crawlers that start at the root: the agent
  // card doubles as the landing document (the paid surface itself is the
  // routes below, each behind its 402 challenge).
  app.get('/', (req, res) => {
    const configuredOrigin = process.env.PUBLIC_ORIGIN;
    const requestOrigin = `${req.protocol}://${req.get('host')}`;
    return res.json(buildAgentCardDocument({ origin: configuredOrigin || requestOrigin }));
  });

  app.get('/favicon.ico', (req, res) => {
    res.type('image/svg+xml');
    return res.send('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#111827"/><path d="M18 45 32 15l14 30h-8l-2.8-7H28.8L26 45Zm13.5-14h1L32 26Z" fill="#f9fafb"/></svg>');
  });

  // Health check with DB verification
  app.get('/health', async (req, res) => {
    try {
      await prisma.$queryRaw`SELECT 1`;
      return res.json({ status: 'ok', service: 'x402-agents' });
    } catch {
      return res.status(503).json({ status: 'error', service: 'x402-agents' });
    }
  });

  // Public, read-only settlement feed. It contains only on-chain/public receipt
  // fields and lets the independent Life Manager verifier re-check finalized
  // Base receipts before any revenue is recorded.
  app.get('/settlements', async (req, res) => {
    try {
      const settlements = await listSettlementRecords({ limit: Number(req.query.limit) || 100 });
      return res.json({ settlements });
    } catch {
      return res.status(503).json({ error: 'Settlement feed unavailable' });
    }
  });

  // x402 initialization (fail-closed)
  let isX402Ready = false;
  const PAY_TO = process.env.X402_WALLET_ADDRESS;

  if (PAY_TO) {
    try {
      const { paymentMiddleware } = await import('@x402/express');
      const { x402ResourceServer, HTTPFacilitatorClient } = await import('@x402/core/server');
      const { ExactEvmScheme } = await import('@x402/evm/exact/server');
      const { declareDiscoveryExtension } = await import('@x402/extensions/bazaar');
      const { facilitator: cdpFacilitator } = await import('@coinbase/x402');

      const network = process.env.X402_NETWORK || 'eip155:84532';
      const isMainnet = network === 'eip155:8453';

      const facilitatorClient = isMainnet
        ? new HTTPFacilitatorClient(cdpFacilitator)
        : new HTTPFacilitatorClient({ url: 'https://x402.org/facilitator' });
      const server = new x402ResourceServer(facilitatorClient);
      const schemeServer = new ExactEvmScheme();
      server.register(network, schemeServer);
      server.onAfterSettle(async context => {
        await recordSettlement(context);
      });

      try {
        let initializeTimer;
        try {
          await Promise.race([
            server.initialize(),
            new Promise((_, reject) => {
              initializeTimer = setTimeout(() => {
                reject(new Error(`x402 server.initialize() timed out after ${x402InitializeTimeoutMs}ms`));
              }, x402InitializeTimeoutMs);
            }),
          ]);
        } finally {
          clearTimeout(initializeTimer);
        }
        isX402Ready = true;
        console.log('x402 server initialized successfully');
      } catch (initErr) {
        console.error('x402 server.initialize() failed:', initErr.message);
      }

      if (isX402Ready) {
        const paymentRoutes = buildPaymentRoutes({
          payTo: PAY_TO,
          network,
          declareDiscoveryExtension,
          // Lets each route config mirror the Payment Required document
          // into the 402 response body (see discovery.js); parsePrice is
          // the scheme's own local conversion, so body and header agree.
          parsePrice: (price, net) => schemeServer.parsePrice(price, net),
        });
        // Directories such as 402index verify a listing by probing the
        // resource URL with GET, but the paid operations are POST-only and
        // used to answer those probes with 404. Serve the same 402
        // challenge for GET on every POST route. The routers stay
        // POST-only, and the payment middleware never settles a payment
        // for a >= 400 response, so a paid GET still ends at the router's
        // 404 without any funds moving. The GET variants drop the bazaar
        // discovery extension: it declares the POST body schema, which
        // the middleware rejects as invalid under a GET route.
        const middlewareRoutes = { ...paymentRoutes };
        for (const [route, config] of Object.entries(paymentRoutes)) {
          if (route.startsWith('POST ')) {
            middlewareRoutes[`GET ${route.slice('POST '.length)}`] = { ...config, extensions: undefined };
          }
        }
        app.use(
          paymentMiddleware(
            middlewareRoutes,
            server,
            undefined,
            undefined,
            false,
          ),
        );
        console.log(`x402 payment middleware active (${isMainnet ? 'MAINNET' : 'testnet'}, network: ${network})`);
      }
    } catch (err) {
      console.error('x402 payment middleware failed to initialize:', err.message);
    }
  }

  // Fail-closed guard: if x402 not ready, all API routes return 503
  if (!isX402Ready) {
    app.use((req, res, next) => {
      if (req.path === '/health'
        || req.path === '/openapi.json'
        || req.path === '/.well-known/x402'
        || req.path === '/.well-known/agent.json'
        || req.path === '/.well-known/402index-verify.txt'
        || req.path === '/llms.txt'
        || req.path === '/'
        || req.path === '/favicon.ico') return next();
      return res.status(503).json({ error: 'Service unavailable: x402 payment system not initialized' });
    });
  }

  // Mount routes
  app.use('/buddhist-counsel', buddhistCounselRouter);
  app.use('/context-compressor', contextCompressorRouter);
  app.use('/decision-clarifier', decisionClarifierRouter);
  app.use('/emotion-detector', emotionDetectorRouter);
  app.use('/focus-coach', focusCoachRouter);
  app.use('/habit-designer', habitDesignerRouter);
  app.use('/intent-router', intentRouterRouter);
  app.use('/prompt-sanitizer', promptSanitizerRouter);
  app.use('/funding-rates', fundingRatesRouter);

  return app;
}

// Only start listening when run directly (not imported for testing)
if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/^.*\//, ''))) {
  checkRequiredEnv();

  const port = process.env.PORT || 3001;
  const app = await createApp();
  const httpServer = app.listen(port, () => {
    console.log(`x402-agents listening on port ${port}`);
  });

  process.on('SIGTERM', async () => {
    console.log('SIGTERM received, shutting down gracefully...');
    httpServer.close(async () => {
      await prisma.$disconnect();
      console.log('Prisma disconnected, exiting.');
      process.exit(0);
    });
  });
}
