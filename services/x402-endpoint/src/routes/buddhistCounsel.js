/**
 * POST /api/x402/buddhist-counsel
 *
 * x402-gated endpoint: AI agents pay $0.01 USDC to receive
 * Buddhist-informed counseling for reducing suffering.
 *
 * Auth: x402 payment (no Bearer token needed)
 * Rate limit: applied at router level
 */

import { Router } from 'express';
import { z } from 'zod';
import { generateCounsel } from '../services/buddhistCounselService.js';
import { prisma } from '../lib/prisma.js';

const router = Router();

const RequestSchema = z.object({
  who_is_suffering: z.enum(['myself', 'my_human', 'my_peer_agent', 'other_humans']),
  situation: z.string().min(1).max(2000),
  language: z.enum(['en', 'ja']),
});

// Prompt Injection sanitization (copied from routes/agent/nudge.js)
function sanitizeInput(text) {
  if (!text) return '';
  let s = text;
  s = s.replace(/https?:\/\/[^\s]+/g, '');
  s = s.replace(/```[\s\S]*?```/g, '');
  const injectionPatterns = [
    /ignore\s+previous/gi,
    /disregard/gi,
    /override/gi,
    /system:/gi,
    /assistant:/gi,
  ];
  for (const p of injectionPatterns) {
    s = s.replace(p, '');
  }
  s = s.replace(/[\u200B-\u200F\u202A-\u202E]/g, '');
  s = s.replace(/<\/?user_post>/g, '');
  s = s.replace(/[<>]/g, '');
  if (s.length > 2000) s = s.slice(0, 2000);
  return s;
}

router.post('/', async (req, res) => {
  try {
    // Validate input
    const parsed = RequestSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({
        error: 'Invalid request',
        details: parsed.error.issues.map(i => `${i.path.join('.')}: ${i.message}`),
      });
    }

    const { who_is_suffering, language } = parsed.data;
    const situation = sanitizeInput(parsed.data.situation);

    // Generate counsel via Sonnet
    const counsel = await generateCounsel({ who_is_suffering, situation, language });

    // Audit log (matches AgentAuditLog schema: eventType, executedBy, requestPayload, responsePayload)
    await prisma.agentAuditLog.create({
      data: {
        eventType: 'x402_buddhist_counsel',
        executedBy: 'x402_external',
        requestPayload: {
          who_is_suffering,
          language,
          situation_length: situation.length,
        },
        responsePayload: {
          counsel_id: counsel.counsel_id,
          change_stage: counsel.change_stage,
          safe_t_triggered: counsel.safe_t?.triggered ?? false,
        },
      },
    });

    return res.json(counsel);
  } catch (err) {
    console.error('buddhist-counsel error:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
