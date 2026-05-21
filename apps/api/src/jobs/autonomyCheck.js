import * as fs from 'node:fs/promises';
import path from 'node:path';
import { prisma } from '../lib/prisma.js';
import baseLogger from '../utils/logger.js';

const logger = baseLogger.withContext('AutonomyCheckJob');

const DEFAULT_DLQ_DIR = process.env.DLQ_DIR || '/tmp/anicca/dlq';

async function countDlqStaleEntries(options = {}) {
  const baseDir = options.dir || DEFAULT_DLQ_DIR;
  const nowMs = options.nowMs || Date.now();
  const staleMs = options.staleMs || 24 * 60 * 60 * 1000;

  let files = [];
  try {
    files = await fs.readdir(baseDir);
  } catch (e) {
    if (e?.code === 'ENOENT') return 0;
    throw e;
  }

  let stale = 0;
  for (const file of files) {
    if (!file.endsWith('.jsonl')) continue;
    const fullPath = path.join(baseDir, file);
    const raw = await fs.readFile(fullPath, 'utf-8').catch(() => '');
    const lines = String(raw || '')
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean);
    for (const line of lines) {
      try {
        const entry = JSON.parse(line);
        const ts = new Date(entry.timestamp || entry.createdAt || 0).getTime();
        if (Number.isFinite(ts) && nowMs - ts > staleMs) stale += 1;
      } catch {
        // ignore
      }
    }
  }
  return stale;
}

export async function runAutonomyCheck(options = {}) {
  const now = options.now instanceof Date ? options.now : new Date();
  const since24h = new Date(now.getTime() - 24 * 60 * 60 * 1000);

  const [safeTViolations, xReplies] = await Promise.all([
    prisma.agentAuditLog.count({ where: { eventType: 'safe_t_violation', createdAt: { gte: since24h } } }),
    prisma.agentAuditLog.count({ where: { eventType: 'x_reply_sent', createdAt: { gte: since24h } } }),
  ]);

  const dlqStale = await countDlqStaleEntries({
    dir: options.dlqDir,
    nowMs: now.getTime(),
    staleMs: 24 * 60 * 60 * 1000,
  });

  const pass =
    safeTViolations === 0 &&
    xReplies === 0 &&
    dlqStale === 0;

  const result = {
    pass,
    now: now.toISOString(),
    metrics: {
      safeTViolations,
      xReplies,
      dlqStale,
    },
  };

  logger.info('Autonomy check completed', result);
  return result;
}

export default runAutonomyCheck;
