/**
 * POST /api/agent/content
 * 
 * Generate platform-specific content (different formats for X, TikTok, etc.)
 */

import { Router } from 'express';
import OpenAI from 'openai';
import { prisma } from '../../lib/prisma.js';

const router = Router();
const openai = new OpenAI();

// Input sanitization (same as nudge.js)
function sanitizeInput(input) {
  if (!input || typeof input !== 'string') return '';
  
  let sanitized = input;
  
  // 1. Remove URLs
  sanitized = sanitized.replace(/https?:\/\/[^\s]+/g, '');
  
  // 2. Remove code blocks
  sanitized = sanitized.replace(/```[\s\S]*?```/g, '');
  
  // 3. Remove known injection patterns
  const injectionPatterns = [
    /ignore\s+previous/gi,
    /disregard/gi,
    /override/gi,
    /system:/gi,
    /assistant:/gi,
  ];
  for (const pattern of injectionPatterns) {
    sanitized = sanitized.replace(pattern, '');
  }
  
  // 4. Remove Unicode control characters
  sanitized = sanitized.replace(/[\u200B-\u200F\u202A-\u202E]/g, '');
  
  // 5. Remove all angle brackets (prevent prompt structure manipulation)
  // Escape or strip ALL < and > to prevent any form of tag injection
  sanitized = sanitized.replace(/[<>]/g, '');
  
  // 6. Limit length
  if (sanitized.length > 500) {
    sanitized = sanitized.slice(0, 500);
  }
  
  return sanitized.trim();
}

// Validate tone
const VALID_TONES = ['gentle', 'understanding', 'encouraging', 'empathetic', 'playful'];
const VALID_LANGUAGES = ['ja', 'en'];

router.post('/', async (req, res) => {
  const startTime = Date.now();
  
  try {
    const { topic, problemType, tone = 'gentle', language = 'ja' } = req.body;
    
    if (!topic) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'topic is required',
      });
    }
    
    // Sanitize inputs
    const sanitizedTopic = sanitizeInput(topic);
    const sanitizedProblemType = problemType ? sanitizeInput(problemType) : null;
    const validTone = VALID_TONES.includes(tone) ? tone : 'gentle';
    const validLanguage = VALID_LANGUAGES.includes(language) ? language : 'ja';
    
    if (!sanitizedTopic) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'topic is required after sanitization',
      });
    }
    
    const systemPrompt = `You are Anicca, creating content for social media platforms.

CRITICAL RULES:
- Never use toxic positivity
- Always acknowledge pain/struggle
- Offer hope through Buddhist wisdom
- Be authentic and human

Generate content in ${validLanguage === 'ja' ? 'Japanese' : 'English'}.`;

    const userPrompt = `<topic>${sanitizedTopic}</topic>
${sanitizedProblemType ? `<problem_type>${sanitizedProblemType}</problem_type>` : ''}
<tone>${validTone}</tone>

Generate JSON with:
1. hook: Attention-grabbing opening (1 sentence)
2. content: Main content (2-3 sentences)
3. tone: The tone used
4. formats:
   - short: Twitter/X version (≤280 chars)
   - medium: Instagram/TikTok caption (≤500 chars)
   - long: Blog/longer format (≤1000 chars)
   - hashtags: Array of relevant hashtags (5-7)`;

    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      response_format: { type: 'json_object' },
      max_tokens: 1000,
    });

    const generated = JSON.parse(completion.choices[0].message.content);
    
    // Validate short format length
    if (generated.formats?.short && generated.formats.short.length > 280) {
      generated.formats.short = generated.formats.short.slice(0, 277) + '...';
    }
    
    // Audit log (per spec: all LLM calls must be logged)
    await prisma.agentAuditLog.create({
      data: {
        eventType: 'llm_call',
        platform: 'content_generation',
        requestPayload: { 
          topicLength: topic.length,
          problemType: sanitizedProblemType,
          tone: validTone,
          language: validLanguage,
        },
        responsePayload: { 
          model: 'gpt-4o-mini', 
          tokensUsed: completion.usage?.total_tokens,
        },
        durationMs: Date.now() - startTime,
      },
    });
    
    res.json({
      hook: generated.hook,
      content: generated.content,
      tone: generated.tone,
      formats: generated.formats,
    });
    
  } catch (error) {
    console.error('[Agent Content] Error:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: error.message,
    });
  }
});

export default router;
