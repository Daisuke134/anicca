/**
 * POST /api/x402/decision-clarifier
 *
 * x402-gated endpoint: AI agents pay $0.008 USDC to analyze a decision
 * situation for cognitive biases and receive a clarified recommendation.
 *
 * Auth: x402 payment (no Bearer token needed)
 */

import { Router } from 'express';
import { z } from 'zod';
import OpenAI from 'openai';
import { prisma } from '../lib/prisma.js';

const router = Router();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const SYSTEM_PROMPT = `You are a decision clarifier for AI agents, specializing in behavioral economics bias detection.

Analyze the decision situation and detect cognitive biases from this list:

1. loss_aversion — People feel losses ~2x more than equivalent gains. Detection: language emphasizing what might be lost, fear of giving up current position, disproportionate focus on downsides.
2. status_quo — Preference for the current state of affairs. Detection: resistance to change without rational justification, "it's always been this way" reasoning, comfort-based rather than outcome-based preference.
3. sunk_cost — Continuing a behavior due to previously invested resources. Detection: references to time/money already spent, "too far to quit" reasoning, inability to evaluate future value independently.
4. anchoring — Over-relying on the first piece of information encountered. Detection: fixation on initial numbers/offers/frames, insufficient adjustment from starting point, first-mentioned option receiving undue weight.
5. availability — Judging probability by how easily examples come to mind. Detection: recent vivid events driving decisions, anecdotal evidence overriding statistics, "I heard about someone who..." reasoning.
6. confirmation — Seeking information that confirms existing beliefs. Detection: selective evidence gathering, dismissing contradictory data, "I already know" attitude, cherry-picking supporting facts.
7. framing — Being influenced by how information is presented rather than the information itself. Detection: different reactions to equivalent scenarios presented differently, sensitivity to wording (e.g., "90% survival" vs "10% mortality").

Respond ONLY with valid JSON in this exact format:
{
  "decision_id": "dec_<8-char-hex>",
  "recommended_option": "<the option you recommend or a synthesized recommendation>",
  "confidence": <0.0 to 1.0>,
  "biases_detected": [
    {
      "bias": "<one of: loss_aversion, status_quo, sunk_cost, anchoring, availability, confirmation, framing>",
      "description": "<how this bias manifests in the situation>",
      "impact": "<how it distorts the decision>"
    }
  ],
  "reasoning": "<clear reasoning for the recommendation, max 200 words>",
  "reframe": "<one sentence that reframes the decision without the detected biases>",
  "safe_t_flag": <true if the situation involves self-harm, crisis, or danger>
}

Be precise and evidence-based. Only report biases clearly present in the text.
If the situation involves self-harm, suicidal ideation, or crisis, set safe_t_flag to true.`;

const RequestSchema = z.object({
  situation: z.string().min(1).max(2000),
  options: z.array(z.string()).max(5).optional(),
  constraints: z.string().max(500).optional(),
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

    const situation = sanitizeInput(parsed.data.situation);
    const options = parsed.data.options?.map(o => sanitizeInput(o)) ?? null;
    const constraints = parsed.data.constraints ? sanitizeInput(parsed.data.constraints) : null;
    const { language } = parsed.data;

    let userMessage = `Situation: "${situation}"`;
    if (options && options.length > 0) {
      userMessage += `\nOptions: ${options.map((o, i) => `${i + 1}. ${o}`).join('; ')}`;
    }
    if (constraints) {
      userMessage += `\nConstraints: "${constraints}"`;
    }
    userMessage += `\nLanguage: ${language}`;

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
        eventType: 'x402_decision_clarifier',
        executedBy: 'x402_external',
        requestPayload: {
          situation_length: situation.length,
          language,
          has_options: !!options,
          options_count: options?.length ?? 0,
          has_constraints: !!constraints,
        },
        responsePayload: {
          decision_id: result.decision_id,
          confidence: result.confidence,
          biases_count: result.biases_detected?.length ?? 0,
          safe_t_flag: result.safe_t_flag ?? false,
        },
      },
    });

    return res.json(result);
  } catch (err) {
    console.error('decision-clarifier error:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
