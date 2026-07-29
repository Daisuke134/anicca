/**
 * POST /api/x402/intent-router
 *
 * x402-gated endpoint: AI agents pay $0.005 USDC to classify the intent
 * of a text input against a set of candidate intents.
 *
 * Auth: x402 payment (no Bearer token needed)
 */

import { Router } from 'express';
import { z } from 'zod';
import OpenAI from 'openai';
import { prisma } from '../lib/prisma.js';

const router = Router();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const SYSTEM_PROMPT = `You are an intent classification specialist for AI agents.
Analyze the text and match it to one of the provided candidate intents.

Respond ONLY with valid JSON in this exact format:
{
  "intent_id": "int_<6-char-hex>",
  "matched_intent": "<the best matching intent from the candidates list>",
  "confidence": <0.0 to 1.0>,
  "reasoning": "<brief explanation of why this intent was matched>",
  "secondary_intent": "<second best matching intent or null>",
  "secondary_confidence": <0.0 to 1.0 or null>,
  "entities": [{"type": "<entity type>", "value": "<extracted value>"}],
  "language_detected": "<detected language code e.g. en, ja, es>"
}

Be precise and evidence-based. Only match intents from the provided candidates list.`;

const RequestSchema = z.object({
  text: z.string().min(1).max(2000),
  intents: z.array(z.string()).min(2).max(20),
  language: z.enum(['en', 'ja', 'es', 'fr', 'de', 'zh', 'ko']).optional().default('en'),
  context: z.string().max(500).optional(),
});

function sanitizeInput(text) {
  if (!text) return '';
  let s = text;
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
    const { intents, language } = parsed.data;

    const userMessage = context
      ? `Text: "${text}"\nCandidates: ${JSON.stringify(intents)}\nContext: "${context}"\nLanguage hint: ${language}`
      : `Text: "${text}"\nCandidates: ${JSON.stringify(intents)}\nLanguage hint: ${language}`;

    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: userMessage },
      ],
      response_format: { type: 'json_object' },
      temperature: 0.2,
    });

    const result = JSON.parse(completion.choices[0].message.content);

    await prisma.agentAuditLog.create({
      data: {
        eventType: 'x402_intent_router',
        executedBy: 'x402_external',
        requestPayload: {
          text_length: text.length,
          intents_count: intents.length,
          language,
          has_context: !!context,
        },
        responsePayload: {
          intent_id: result.intent_id,
          matched_intent: result.matched_intent,
          confidence: result.confidence,
          language_detected: result.language_detected,
        },
      },
    });

    return res.json(result);
  } catch (err) {
    console.error('intent-router error:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
