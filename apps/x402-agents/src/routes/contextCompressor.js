/**
 * POST /api/x402/context-compressor
 *
 * x402-gated endpoint: AI agents pay $0.008 USDC to compress long context
 * into concise summaries, key facts, or episodic memory chunks.
 *
 * Auth: x402 payment (no Bearer token needed)
 */

import { Router } from 'express';
import { z } from 'zod';
import OpenAI from 'openai';
import { prisma } from '../lib/prisma.js';

const router = Router();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const SYSTEM_PROMPT = `You are a context compression specialist for AI agents.
Compress the given text into the target token budget using the specified mode.

Modes:
- summary: A coherent narrative summary preserving the main points and flow.
- facts: A bullet list of discrete, self-contained facts extracted from the text.
- episodes: Chronologically ordered episodic memory chunks, each with a timestamp or sequence marker if available.

Respond ONLY with valid JSON in this exact format:
{
  "compressor_id": "cmp_<8-char-hex>",
  "mode": "<summary|facts|episodes>",
  "compressed": "<the compressed text>",
  "original_chars": <number>,
  "compressed_chars": <number>,
  "compression_ratio": <float, original/compressed>,
  "key_entities": ["<entity1>", "<entity2>"],
  "safe_t_flag": false
}

Rules:
- Stay within the target token budget for the compressed output.
- Preserve all key entities (people, places, dates, numbers, URLs).
- Never fabricate information not present in the source text.
- Set safe_t_flag to true only if the text contains crisis/self-harm content.`;

const RequestSchema = z.object({
  text: z.string().min(1).max(50000),
  target_tokens: z.number().int().min(100).max(2000).optional().default(500),
  mode: z.enum(['summary', 'facts', 'episodes']).optional().default('summary'),
  language: z.enum(['en', 'ja']).optional().default('en'),
});

function sanitizeInput(text) {
  if (!text) return '';
  let s = text;
  // Keep URLs — they carry meaning in context
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
  if (s.length > 50000) s = s.slice(0, 50000);
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
    const { target_tokens, mode, language } = parsed.data;

    const userMessage = `Text to compress:\n"${text}"\n\nMode: ${mode}\nTarget tokens: ${target_tokens}\nLanguage: ${language}`;

    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
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
        eventType: 'x402_context_compressor',
        executedBy: 'x402_external',
        requestPayload: {
          text_length: text.length,
          target_tokens,
          mode,
          language,
        },
        responsePayload: {
          compressor_id: result.compressor_id,
          mode: result.mode,
          original_chars: result.original_chars,
          compressed_chars: result.compressed_chars,
          compression_ratio: result.compression_ratio,
          key_entities_count: result.key_entities?.length ?? 0,
          safe_t_flag: result.safe_t_flag ?? false,
        },
      },
    });

    return res.json(result);
  } catch (err) {
    console.error('context-compressor error:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
