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

import buddhistCounselRouter from './routes/buddhistCounsel.js';
import contextCompressorRouter from './routes/contextCompressor.js';
import decisionClarifierRouter from './routes/decisionClarifier.js';
import emotionDetectorRouter from './routes/emotionDetector.js';
import focusCoachRouter from './routes/focusCoach.js';
import habitDesignerRouter from './routes/habitDesigner.js';
import intentRouterRouter from './routes/intentRouter.js';
import promptSanitizerRouter from './routes/promptSanitizer.js';

const REQUIRED_ENV = ['X402_WALLET_ADDRESS', 'OPENAI_API_KEY', 'DATABASE_URL'];

function checkRequiredEnv() {
  const missing = REQUIRED_ENV.filter(key => !process.env[key]);
  if (missing.length > 0) {
    console.error(`Missing required env vars: ${missing.join(', ')}`);
    process.exit(1);
  }
}

export async function createApp() {
  const app = express();

  app.set('trust proxy', 1);

  app.use(cors({
    origin: '*',
    credentials: false,
    methods: ['GET', 'POST'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Payment-*'],
  }));

  app.use(express.json());

  const limiter = rateLimit({ windowMs: 60 * 1000, max: 30 });
  app.use(limiter);

  // Health check with DB verification
  app.get('/health', async (req, res) => {
    try {
      await prisma.$queryRaw`SELECT 1`;
      return res.json({ status: 'ok', service: 'x402-agents' });
    } catch {
      return res.status(503).json({ status: 'error', service: 'x402-agents' });
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
      server.register(network, new ExactEvmScheme());

      try {
        await server.initialize();
        isX402Ready = true;
        console.log('x402 server initialized successfully');
      } catch (initErr) {
        console.error('x402 server.initialize() failed:', initErr.message);
      }

      if (isX402Ready) {
        app.use(
          paymentMiddleware(
            {
              'POST /context-compressor': {
                accepts: { scheme: 'exact', price: '$0.008', network, payTo: PAY_TO },
                description: 'Context compressor for AI agents',
                mimeType: 'application/json',
                extensions: { ...declareDiscoveryExtension({ output: { example: {}, schema: { properties: {} } } }) },
              },
              'POST /emotion-detector': {
                accepts: { scheme: 'exact', price: '$0.01', network, payTo: PAY_TO },
                description: 'Emotion detection for AI agents',
                mimeType: 'application/json',
                extensions: { ...declareDiscoveryExtension({ output: { example: {}, schema: { properties: {} } } }) },
              },
              'POST /buddhist-counsel': {
                accepts: { scheme: 'exact', price: '$0.01', network, payTo: PAY_TO },
                description: 'Buddhist counsel for AI agents',
                mimeType: 'application/json',
                extensions: { ...declareDiscoveryExtension({ output: { example: {}, schema: { properties: {} } } }) },
              },
              'POST /focus-coach': {
                accepts: { scheme: 'exact', price: '$0.01', network, payTo: PAY_TO },
                description: 'Focus coach for AI agents',
                mimeType: 'application/json',
                extensions: { ...declareDiscoveryExtension({ output: { example: {}, schema: { properties: {} } } }) },
              },
              'POST /habit-designer': {
                accepts: { scheme: 'exact', price: '$0.01', network, payTo: PAY_TO },
                description: 'Habit designer for AI agents',
                mimeType: 'application/json',
                extensions: { ...declareDiscoveryExtension({ output: { example: {}, schema: { properties: {} } } }) },
              },
              'POST /prompt-sanitizer': {
                accepts: { scheme: 'exact', price: '$0.005', network: 'eip155:8453', payTo: PAY_TO },
                description: 'Prompt sanitizer for AI agents',
                mimeType: 'application/json',
                extensions: { ...declareDiscoveryExtension({ output: { example: {}, schema: { properties: {} } } }) },
              },
              'POST /decision-clarifier': {
                accepts: { scheme: 'exact', price: '$0.008', network, payTo: PAY_TO },
                description: 'Decision clarifier for AI agents',
                mimeType: 'application/json',
                extensions: { ...declareDiscoveryExtension({ output: { example: {}, schema: { properties: {} } } }) },
              },
              'POST /intent-router': {
                accepts: { scheme: 'exact', price: '$0.005', network, payTo: PAY_TO },
                description: 'Intent router for AI agents',
                mimeType: 'application/json',
                extensions: { ...declareDiscoveryExtension({ output: { example: {}, schema: { properties: {} } } }) },
              },
            },
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
      if (req.path === '/health') return next();
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
