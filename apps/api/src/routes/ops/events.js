import { Router } from 'express';
import { z } from 'zod';
import { emitEvent } from '../../services/ops/eventEmitter.js';
import { logger } from '../../lib/logger.js';

const router = Router();

const EventInputSchema = z.object({
  source: z.string().max(50),
  kind: z.string().max(100),
  tags: z.array(z.string().max(50)).max(10),
  payload: z.record(z.unknown()).default({})
});

/**
 * POST /api/ops/events
 * VPS (trend-hunter etc.) sends events to Railway
 */
router.post('/events', async (req, res) => {
  const parsed = EventInputSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: parsed.error.flatten() });
  }

  const { source, kind, tags, payload } = parsed.data;

  try {
    const event = await emitEvent(source, kind, tags, payload);
    res.status(201).json({ id: event.id });
  } catch (err) {
    logger.error('Event creation failed:', err);
    res.status(500).json({ error: err.message });
  }
});

export default router;
