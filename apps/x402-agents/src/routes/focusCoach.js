/**
 * POST /api/x402/focus-coach
 *
 * x402-gated endpoint: AI agents pay $0.01 USDC to diagnose why a user
 * can't focus using B=MAP (BJ Fogg Behavior Model) and get one tiny action.
 *
 * Auth: x402 payment (no Bearer token needed)
 */

import { Router } from 'express';
import { z } from 'zod';
import OpenAI from 'openai';
import { prisma } from '../lib/prisma.js';

const router = Router();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const SYSTEM_PROMPT = `You are a focus coach grounded in BJ Fogg's Behavior Design (B=MAP).

## Framework
B = MAP: Behavior happens when Motivation (M), Ability (A), and a Prompt (P) converge.
When someone can't focus, exactly ONE of these three is insufficient:
- Motivation: They don't want to do the task enough (task feels meaningless, boring, or overwhelming)
- Ability: The task is too hard, unclear, or requires resources they lack right now
- Prompt: There's no clear trigger to start, or the environment has competing prompts (notifications, noise)

## Tiny Habits Recipe
Format: "After I [ANCHOR], I will [TINY BEHAVIOR]"
- ANCHOR: An existing routine moment (e.g., "sit down at my desk", "close my last tab", "take a sip of water")
- TINY BEHAVIOR: The smallest possible version of the focus task (under 30 seconds to start)

## Rules
- Diagnose EXACTLY ONE primary blocker (motivation, ability, or prompt)
- Return EXACTLY ONE tiny action (not a list)
- The tiny action must take under 120 seconds
- Never give generic motivational advice ("just do it", "believe in yourself")
- Never suggest long planning sessions or complex systems
- Environment design should be one physical change
- If user shows signs of burnout, exhaustion, or crisis -> set safe_t_flag to true

Respond ONLY with valid JSON:
{
  "focus_id": "fcs_<8-char-hex>",
  "diagnosis": {
    "primary_blocker": "<motivation|ability|prompt>",
    "explanation": "<1-2 sentences why this is the blocker>"
  },
  "tiny_action": {
    "action": "<one specific tiny action>",
    "duration_seconds": <estimated seconds>,
    "anchor": "<After I [existing habit], I will [tiny action]>"
  },
  "environment_design": "<one physical/digital change to support focus, or null>",
  "safe_t_flag": <true if burnout/exhaustion/crisis detected>
}`;

const RequestSchema = z.object({
  situation: z.string().min(5).max(1000),
  blocker: z.string().max(500).optional(),
  energy_level: z.enum(['low', 'medium', 'high']),
  time_available_minutes: z.number().min(1).max(480).optional(),
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
  if (s.length > 1000) s = s.slice(0, 1000);
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

    const situation = sanitizeInput(parsed.data.situation);
    const blocker = parsed.data.blocker ? sanitizeInput(parsed.data.blocker) : null;
    const { energy_level, time_available_minutes, language } = parsed.data;

    let userMessage = `Situation: "${situation}"`;
    if (blocker) userMessage += `\nBlocker: "${blocker}"`;
    userMessage += `\nEnergy level: ${energy_level}`;
    if (time_available_minutes) userMessage += `\nTime available: ${time_available_minutes} minutes`;
    userMessage += `\nLanguage: ${language}`;

    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: userMessage },
      ],
      response_format: { type: 'json_object' },
      temperature: 0.4,
    });

    const result = JSON.parse(completion.choices[0].message.content);

    await prisma.agentAuditLog.create({
      data: {
        eventType: 'x402_focus_coach',
        executedBy: 'x402_external',
        requestPayload: {
          situation_length: situation.length,
          energy_level,
          time_available_minutes: time_available_minutes ?? null,
          language,
          has_blocker: !!blocker,
        },
        responsePayload: {
          focus_id: result.focus_id,
          primary_blocker: result.diagnosis?.primary_blocker,
          safe_t_flag: result.safe_t_flag ?? false,
        },
      },
    });

    return res.json(result);
  } catch (err) {
    console.error('focus-coach error:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
