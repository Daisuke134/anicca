// ★ mem0aiテレメトリーを最初に無効化（ESモジュールのimport巻き上げ対策）
process.env.MEM0_TELEMETRY = 'false';

import express from 'express';
import cors from 'cors';
import { runMigrationsOnce } from './lib/migrate.js';
import apiRouter from './routes/index.js';
import { pool } from './lib/db.js';

// Only load dotenv in development
if (process.env.NODE_ENV !== 'production') {
  import('dotenv').then(dotenv => dotenv.config());
}

// サーバー起動時の初期化処理（DB初期化のみ）
async function initializeServer() {
  // マイグレーション（初回のみ実行）
  await runMigrationsOnce();
  console.log('✅ Database initialized.');

  // 月次クレジットジョブ（UTC 00:05 付近で起動、当月未付与のみ実行）
  const { runMonthlyCredits } = await import('./jobs/monthlyCredits.js');
  setInterval(async () => {
    const now = new Date();
    if (now.getUTCHours() === 0 && now.getUTCMinutes() < 10) {
      try {
        await runMonthlyCredits(now);
      } catch (e) {
        console.error('monthly credits failed', e);
      }
    }
  }, 60_000); // 1分ごとにチェック

  // 1.6.3: Problem Nudge APNs sender (run every minute, guarded by env flag).
  // NOTE: This is the SSOT execution path for "app not opened but still receives nudges".
  if (process.env.PROBLEM_NUDGE_APNS_SENDER_ENABLED === 'true') {
    const { runProblemNudgeApnsSender } = await import('./jobs/problemNudgeApnsSenderJob.js');
    let running = false;
    const tick = async () => {
      if (running) return;
      running = true;
      try {
        await runProblemNudgeApnsSender(new Date());
      } catch (e) {
        console.error('problem nudge apns sender failed', e);
      } finally {
        running = false;
      }
    };

    // Align to wall-clock minute boundaries to reduce drift.
    const scheduleNext = () => {
      const now = Date.now();
      const msIntoMinute = now % 60_000;
      const delay = Math.max(0, 60_000 - msIntoMinute);
      setTimeout(async () => {
        await tick();
        scheduleNext();
      }, delay);
    };
    scheduleNext();
  }
}

const app = express();
app.set('trust proxy', 1); // Railway runs behind a reverse proxy
const PORT = process.env.PORT || 3000;
const controller = new AbortController();

await initializeServer().catch(err => {
  console.error('❌ Failed to initialize server', err);
  process.exit(1);
});

// mem0aiテレメトリーのETIMEDOUTエラーを無視
process.on('unhandledRejection', (reason, promise) => {
  // テレメトリーエラーは完全に無視（ログ出力もしない）
  if (reason?.message?.includes('Telemetry') ||
      reason?.message?.includes('fetch failed') ||
      reason?.stack?.includes('captureClientEvent') ||
      reason?.stack?.includes('captureEvent') ||
      reason?.cause?.code === 'ETIMEDOUT' ||
      (reason?.cause?.errors && Array.isArray(reason.cause.errors))) {
    return;
  }
  console.error('Unhandled Rejection:', reason);
});

// Middleware
const corsOptions = {
  origin: process.env.CORS_ORIGINS ? process.env.CORS_ORIGINS.split(',') : '*',
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Authorization', 'Content-Type', 'X-API-Key', 'user-id', 'device-id', 'x-timezone', 'x-lang']
};
app.use(cors(corsOptions));

const revenuecatWebhookPath = '/api/billing/webhook/revenuecat';
app.use(revenuecatWebhookPath, express.raw({ type: 'application/json' }));

const jsonParser = express.json({ limit: '50mb' });
const urlencodedParser = express.urlencoded({ extended: true, limit: '50mb' });
app.use((req, res, next) => {
  if (req.originalUrl === revenuecatWebhookPath) return next();
  return jsonParser(req, res, next);
});
app.use((req, res, next) => {
  if (req.originalUrl === revenuecatWebhookPath) return next();
  return urlencodedParser(req, res, next);
});

// Preflight 全面対応
app.options('*', cors(corsOptions));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// x402 service discovery for MCP agents
app.get('/.well-known/x402.json', (req, res) => {
  res.json({
    endpoints: [{
      path: '/api/x402/buddhist-counsel',
      method: 'POST',
      price: '$0.01 USDC',
      network: 'Base (EIP-155:84532 testnet / EIP-155:8453 mainnet)',
      description: 'Buddhist counsel for AI agents — reduce suffering with wisdom',
      input: {
        who_is_suffering: 'myself | my_human | my_peer_agent | other_humans',
        situation: 'string (max 2000 chars)',
        language: 'en | ja',
      },
      output: {
        counsel_id: 'string',
        acknowledgment: 'string',
        guidance: 'string',
        buddhist_reference: '{ concept, teaching, source }',
        persuasion_strategy: '{ framework, techniques_used[] }',
        change_stage: 'precontemplation | contemplation | preparation | action | maintenance',
      },
    }],
  });
});

// Mount new routing layer under /api
app.use('/api', apiRouter);

// Root endpoint -> health
app.get('/', (req, res) => {
  res.redirect('/health');
});

// Start server
const server = app.listen(PORT, () => {
  console.log(`🚀 Anicca API Server running on port ${PORT}`);
  console.log(`📍 Health check: http://localhost:${PORT}/health`);
  console.log(`🌐 Environment: ${process.env.NODE_ENV || 'development'}`);
});

['SIGTERM', 'SIGINT'].forEach(signal => {
  process.on(signal, async () => {
    console.log(`⚠️ Received ${signal}, shutting down gracefully...`);
    controller.abort();
    server.close(() => {
      pool.end().then(() => process.exit(0));
    });
  });
});
