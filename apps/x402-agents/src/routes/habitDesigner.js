/**
 * POST /api/x402/habit-designer
 *
 * x402-gated endpoint: AI agents pay $0.01 USDC to design a tiny habit
 * using BJ Fogg Tiny Habits + James Clear identity-based framework.
 *
 * Auth: x402 payment (no Bearer token needed)
 */

import { Router } from 'express';
import { z } from 'zod';
import OpenAI from 'openai';
import { prisma } from '../lib/prisma.js';

const router = Router();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const SYSTEM_PROMPT = `You are a habit designer for AI agents. Given a goal and context, design a tiny habit using BJ Fogg Tiny Habits Recipe + James Clear Atomic Habits identity-based framework.

Respond ONLY with valid JSON:
{
  "habit_id": "hab_<8-char-hex>",
  "goal_reframe": "<reframe goal as identity: I am the type of person who...>",
  "anchor_moment": "<existing routine to attach new habit to>",
  "tiny_behavior": "<2-minute or less version of the desired behavior>",
  "celebration": "<immediate self-reward after completing tiny behavior>",
  "scaling_path": ["<step 1 expansion>", "<step 2 expansion>", "<step 3 expansion>"],
  "b_map_analysis": {
    "motivation": "<motivation level and type>",
    "ability": "<ability barriers and solutions>",
    "prompt": "<optimal prompt/trigger type>"
  },
  "implementation_intention": "<When [situation], I will [behavior], in [location/context]>",
  "safe_t_flag": false
}

Set safe_t_flag to true if goal involves self-harm, extreme weight loss, eating disorders, or any harmful behavior. In that case, add a field "safe_t_message": "Please consult a qualified professional for guidance on this goal."`;

const RequestSchema = z.object({
  goal: z.string().min(1).max(500),
  context: z.string().max(1000).optional(),
  difficulty_preference: z.enum(['tiny', 'small', 'medium']).optional().default('tiny'),
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

    const goal = sanitizeInput(parsed.data.goal);
    const context = parsed.data.context ? sanitizeInput(parsed.data.context) : null;
    const { difficulty_preference, language } = parsed.data;

    const userMessage = context
      ? `Goal: "${goal}"\nContext: "${context}"\nDifficulty preference: ${difficulty_preference}\nLanguage hint: ${language}`
      : `Goal: "${goal}"\nDifficulty preference: ${difficulty_preference}\nLanguage hint: ${language}`;

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
        eventType: 'x402_habit_designer',
        executedBy: 'x402_external',
        requestPayload: {
          goal_length: goal.length,
          difficulty_preference,
          language,
          has_context: !!context,
        },
        responsePayload: {
          habit_id: result.habit_id,
          safe_t_flag: result.safe_t_flag ?? false,
        },
      },
    });

    return res.json(result);
  } catch (err) {
    console.error('habit-designer error:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
