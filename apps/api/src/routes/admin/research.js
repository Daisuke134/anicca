import express from 'express';
import { z } from 'zod';
import prisma from '../../lib/prisma.js';
import requireInternalAuth from '../../middleware/requireInternalAuth.js';
import baseLogger from '../../utils/logger.js';

const router = express.Router();
const logger = baseLogger.withContext('AdminResearch');

router.use(requireInternalAuth);

const createSchema = z.object({
  source: z.string().min(1).max(50),
  query: z.string().max(2000).optional().nullable(),
  summary: z.string().min(1).max(8000),
  payload: z.any().optional(),
});

router.post('/items', async (req, res) => {
  const parsed = createSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: 'Bad Request', issues: parsed.error.issues });
  }

  try {
    const item = await prisma.researchItem.create({
      data: {
        source: parsed.data.source,
        query: parsed.data.query ?? null,
        summary: parsed.data.summary,
        payload: parsed.data.payload ?? {},
      },
      select: { id: true, source: true, query: true, summary: true, createdAt: true },
    });
    return res.status(201).json(item);
  } catch (error) {
    logger.error('create failed', error);
    return res.status(500).json({ error: 'Internal Server Error' });
  }
});

router.get('/items', async (req, res) => {
  const source = req.query.source ? String(req.query.source) : null;
  const limit = Math.min(100, Math.max(1, Number(req.query.limit || 20)));

  try {
    const items = await prisma.researchItem.findMany({
      where: source ? { source } : {},
      orderBy: { createdAt: 'desc' },
      take: limit,
      select: { id: true, source: true, query: true, summary: true, createdAt: true },
    });
    return res.json({ items });
  } catch (error) {
    logger.error('list failed', error);
    return res.status(500).json({ error: 'Internal Server Error' });
  }
});

export default router;

