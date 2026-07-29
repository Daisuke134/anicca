/**
 * POST /api/x402/emotion-detector
 *
 * x402-gated endpoint: AI agents pay $0.01 USDC to detect the primary
 * emotion in a text input, with intensity and recommended response strategy.
 *
 * Auth: x402 payment (no Bearer token needed)
 */

import { Router } from 'express';
import { z } from 'zod';
import OpenAI from 'openai';
import { prisma } from '../lib/prisma.js';

const router = Router();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const SYSTEM_PROMPT = `You are an emotion detection specialist for AI agents.
Analyze the text and identify the primary emotion being expressed.

Respond ONLY with valid JSON in this exact format:
{
  "emotion_id": "emo_<6-char-hex>",
  "primary_emotion": "<one of: joy, sadness, anger, fear, disgust, surprise, anxiety, shame, grief, hope, neutral>",
  "secondary_emotion": "<optional secondary emotion or null>",
  "intensity": "<low|medium|high|critical>",
  "valence": "<positive|negative|neutral>",
  "confidence": <0.0 to 1.0>,
  "response_strategy": "<brief recommended strategy for responding to this emotion>",
  "safe_t_flag": <true if intensity=critical and primary_emotion is one of: grief, shame, fear, despair>
}

Be precise and evidence-based. Only report what the text clearly conveys.`;

const RequestSchema = z.object({
  text: z.string().min(1).max(2000),
  context: z.string().max(500).optional(),
  language: z.enum(['en', 'ja']).optional().default('en'),
});

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
    const parsed = RequestSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({
        error: 'Invalid request',
        details: parsed.error.issues.map(i => `${i.path.join('.')}: ${i.message}`),
      });
    }

    const text = sanitizeInput(parsed.data.text);
    const context = parsed.data.context ? sanitizeInput(parsed.data.context) : null;
    const { language } = parsed.data;

    const userMessage = context
      ? `Text: "${text}"\nContext: "${context}"\nLanguage hint: ${language}`
      : `Text: "${text}"\nLanguage hint: ${language}`;

    const completion = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: userMessage },
      ],
      response_format: { type: 'json_object' },
      temperature: 0.3,
    });

    const result = JSON.parse(completion.choices[0].message.content);

    await prisma.agentAuditLog.create({
      data: {
        eventType: 'x402_emotion_detector',
        executedBy: 'x402_external',
        requestPayload: {
          text_length: text.length,
          language,
          has_context: !!context,
        },
        responsePayload: {
          emotion_id: result.emotion_id,
          primary_emotion: result.primary_emotion,
          intensity: result.intensity,
          safe_t_flag: result.safe_t_flag ?? false,
        },
      },
    });

    return res.json(result);
  } catch (err) {
    console.error('emotion-detector error:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
