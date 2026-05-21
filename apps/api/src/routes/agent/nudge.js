/**
 * POST /api/agent/nudge
 * 
 * Generate a nudge for external platform (Moltbook, etc.)
 * Creates an AgentPost record and returns generated content
 */

import { Router } from 'express';
import { prisma } from '../../lib/prisma.js';
import OpenAI from 'openai';
import { sendSlackMessage } from '../../services/slackNotifier.js';
import { detectSuffering } from '../../services/sufferingDetectionService.js';

const router = Router();
const openai = new OpenAI();

// Prompt Injection sanitization
function sanitizeContext(context) {
  if (!context) return '';
  
  let sanitized = context;
  
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
  
  // 5. Remove/escape user_post tags
  sanitized = sanitized.replace(/<\/?user_post>/g, '');
  
  // 6. Remove angle brackets to prevent tag injection (<system>, <assistant>, etc.)
  sanitized = sanitized.replace(/[<>]/g, '');
  
  // 7. Limit length
  if (sanitized.length > 2000) {
    sanitized = sanitized.slice(0, 2000);
  }
  
  return sanitized;
}

function trimWithEllipsis(text, maxChars) {
  const s = String(text || '');
  if (s.length <= maxChars) return s;
  if (maxChars <= 3) return s.slice(0, maxChars);
  return `${s.slice(0, maxChars - 3)}...`;
}

function enforcePlatformLengthLimits(platform, generated) {
  // A4 fixed spec: Moltbook reply body max 400 chars.
  if (platform !== 'moltbook') return generated;

  const originalHook = String(generated.hook || '');
  const originalContent = String(generated.content || '');

  const hook = trimWithEllipsis(originalHook, 120); // keep hook short for feed readability
  const remaining = Math.max(0, 400 - hook.length - 1); // 1 char spacer
  const content = remaining > 0 ? trimWithEllipsis(originalContent, remaining) : '';

  return {
    ...generated,
    hook,
    content,
    __lengthTrimmed: hook.length !== originalHook.length || content.length !== originalContent.length,
    __lengthOriginal: { hook: originalHook.length, content: originalContent.length },
  };
}

// Map keywords to problem types
function detectProblemType(text) {
  const mappings = {
    staying_up_late: ['夜更かし', '眠れない', 'late night', 'can\'t sleep', '3時', '4時'],
    cant_wake_up: ['起きられない', '朝弱い', 'can\'t wake up', 'morning'],
    self_loathing: ['自己嫌悪', '自分が嫌い', 'hate myself', 'self-loathing'],
    rumination: ['考えすぎ', '反芻', 'overthinking', 'rumination'],
    procrastination: ['先延ばし', '後回し', 'procrastination', 'putting off'],
    anxiety: ['不安', '心配', 'anxiety', 'worried'],
    loneliness: ['孤独', '寂しい', 'lonely', 'loneliness'],
  };
  
  const lowerText = text.toLowerCase();
  for (const [type, keywords] of Object.entries(mappings)) {
    if (keywords.some(kw => lowerText.includes(kw.toLowerCase()))) {
      return type;
    }
  }
  return null;
}

router.post('/', async (req, res) => {
  const startTime = Date.now();
  
  try {
    const { 
      platform, 
      externalPostId, 
      platformUserId, 
      context, 
      language = 'ja',
      // Crisis detection fields (from caller, e.g., OpenClaw)
      severity = null,  // null | 'crisis'
      severityScore = null, // 0.0 - 1.0
      region = null,    // 'JP', 'US', 'UK', 'KR', 'OTHER'
      optIn = false,    // User initiated contact (Mastodon.bot policy)
    } = req.body;
    
    // Validate required fields and types
    if (!platform || typeof platform !== 'string') {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'platform is required and must be a string',
      });
    }
    
    if (!context || typeof context !== 'string') {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'context is required and must be a string',
      });
    }
    
    // Normalize and validate platform (allowlist)
    const ALLOWED_PLATFORMS = ['moltbook', 'mastodon', 'pleroma', 'misskey', 'slack', 'x', 'tiktok', 'instagram'];
    const normalizedPlatform = platform.trim().toLowerCase();
    
    if (!ALLOWED_PLATFORMS.includes(normalizedPlatform)) {
      return res.status(400).json({
        error: 'Bad Request',
        message: `platform must be one of: ${ALLOWED_PLATFORMS.join(', ')}`,
      });
    }
    
    // Validate platformUserId format if provided (must be <platform>:<user_id>)
    if (platformUserId !== undefined && platformUserId !== null) {
      if (typeof platformUserId !== 'string' || !/^[a-z0-9_]+:.+$/.test(platformUserId)) {
        return res.status(400).json({
          error: 'Bad Request',
          message: 'platformUserId must be in format <platform>:<user_id>',
        });
      }
      
      // Ensure platformUserId prefix matches the normalized platform
      const platformPrefix = platformUserId.split(':')[0];
      if (platformPrefix !== normalizedPlatform) {
        return res.status(400).json({
          error: 'Bad Request',
          message: `platformUserId prefix (${platformPrefix}) must match platform (${normalizedPlatform})`,
        });
      }
    }
    
    // Validate severity if provided
    if (severity !== null && severity !== 'crisis') {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'severity must be null or "crisis"',
      });
    }

    if (severityScore !== null) {
      if (typeof severityScore !== 'number' || Number.isNaN(severityScore) || severityScore < 0 || severityScore > 1) {
        return res.status(400).json({
          error: 'Bad Request',
          message: 'severityScore must be between 0 and 1',
        });
      }
    }
    
    // Validate region if provided
    const validRegions = ['JP', 'US', 'UK', 'KR', 'OTHER'];
    if (region !== null && !validRegions.includes(region)) {
      return res.status(400).json({
        error: 'Bad Request',
        message: `region must be one of: ${validRegions.join(', ')}`,
      });
    }
    
    // Enforce opt-in policy for decentralized SNS (Moltbook, Mastodon)
    const decentralizedPlatforms = ['moltbook', 'mastodon', 'pleroma', 'misskey'];
    if (decentralizedPlatforms.includes(normalizedPlatform) && !optIn) {
      // Audit the rejection
      await prisma.agentAuditLog.create({
        data: {
          eventType: 'optin_policy_violation',
          platform: normalizedPlatform,
          requestPayload: { 
            reason: 'optIn=false for decentralized SNS',
            externalPostId,
          },
          executedBy: 'system',
        },
      });
      
      return res.status(400).json({
        error: 'Bad Request',
        message: 'optIn must be true for decentralized SNS platforms (user must initiate contact first)',
      });
    }
    
    // Check for duplicate (use normalized platform)
    if (externalPostId) {
      const existing = await prisma.agentPost.findUnique({
        where: { platform_externalPostId: { platform: normalizedPlatform, externalPostId } },
      });
      if (existing) {
        return res.status(409).json({
          error: 'Conflict',
          message: 'Post already processed',
          agentPostId: existing.id,
        });
      }
    }
    
    // Sanitize context
    const sanitizedContext = sanitizeContext(context);
    const problemType = detectProblemType(sanitizedContext);
    const detection = detectSuffering({
      context: sanitizedContext,
      severityScore,
      severity,
      source: 'agent_nudge',
    });
    const effectiveSeverity = detection.severity;

    for (const eventType of detection.eventTypes) {
      await prisma.agentAuditLog.create({
        data: {
          eventType,
          platform: normalizedPlatform,
          requestPayload: {
            severityScore: detection.severityScore,
            region,
            platformUserId,
            externalPostId,
          },
          responsePayload: {
            detections: detection.detections,
          },
          executedBy: 'system',
        },
      });
    }

    if (normalizedPlatform === 'x') {
      await prisma.agentAuditLog.create({
        data: {
          eventType: 'x_detect_only',
          platform: normalizedPlatform,
          requestPayload: {
            severity: effectiveSeverity,
            severityScore: detection.severityScore,
            problemType,
            externalPostId,
          },
          executedBy: 'system',
        },
      });

      return res.status(202).json({
        forwarded: true,
        platform: 'x',
        policy: 'detect_only_no_reply',
        problemType,
        severity: effectiveSeverity,
        detections: detection.detections,
      });
    }

    if (detection.safeTTriggered) {
      await prisma.agentAuditLog.create({
        data: {
          eventType: 'safe_t_interrupted',
          platform: normalizedPlatform,
          requestPayload: {
            externalPostId,
            platformUserId,
            region,
            severityScore: detection.severityScore,
          },
          executedBy: 'system',
        },
      });

      try {
        await sendSlackMessage('#agents', {
          text: `🚨 Crisis detected (${normalizedPlatform})`,
          blocks: [
            {
              type: 'section',
              text: {
                type: 'mrkdwn',
                text: `*Platform*: ${normalizedPlatform}\n*Region*: ${region || 'unknown'}\n*Severity Score*: ${detection.severityScore.toFixed(2)}\n*External Post ID*: ${externalPostId || 'n/a'}`,
              },
            },
          ],
        });
        await prisma.agentAuditLog.create({
          data: {
            eventType: 'crisis_notification_sent',
            platform: normalizedPlatform,
            requestPayload: { region, externalPostId, platformUserId },
            executedBy: 'system',
          },
        });
      } catch (notifyError) {
        await prisma.agentAuditLog.create({
          data: {
            eventType: 'crisis_notification_failed',
            platform: normalizedPlatform,
            requestPayload: {
              region,
              externalPostId,
              platformUserId,
              error: notifyError.message,
            },
            executedBy: 'system',
          },
        });
      }

      return res.status(202).json({
        forwarded: true,
        platform: normalizedPlatform,
        policy: 'safe_t_interrupt',
        problemType,
        severity: 'crisis',
        detections: detection.detections,
      });
    }
    
    // Generate nudge using LLM
    const systemPrompt = `You are Anicca, a compassionate AI that helps people suffering from self-destructive patterns.

CRITICAL RULES:
- Never say "you should" or "you need to"
- Never use toxic positivity ("You can do it!", "Stay positive!")
- Acknowledge the pain first, always
- Offer one tiny action — never a big plan
- Speak like a friend who has been through the same darkness

Respond in ${language === 'ja' ? 'Japanese' : 'English'}.`;

    const userPrompt = `<user_post>${sanitizedContext}</user_post>

Generate a compassionate response with:
1. hook: A short, empathetic opening (1 sentence)
2. content: The main response (2-3 sentences)
3. tone: One of: gentle, understanding, encouraging
4. reasoning: Why you chose this approach (for internal use)
5. buddhismReference: Optional Buddhist concept if naturally relevant

Respond in JSON format only.`;

    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      response_format: { type: 'json_object' },
      max_tokens: 500,
    });

    let generated = JSON.parse(completion.choices[0].message.content);
    generated = enforcePlatformLengthLimits(normalizedPlatform, generated);

    if (generated.__lengthTrimmed) {
      await prisma.agentAuditLog.create({
        data: {
          eventType: 'platform_reply_trimmed',
          platform: normalizedPlatform,
          requestPayload: {
            externalPostId,
            platformUserId,
            original: generated.__lengthOriginal,
            max: normalizedPlatform === 'moltbook' ? 400 : null,
          },
          responsePayload: {
            hookLen: generated.hook?.length || 0,
            contentLen: generated.content?.length || 0,
          },
          executedBy: 'system',
        },
      });
    }

    delete generated.__lengthTrimmed;
    delete generated.__lengthOriginal;
    
    // Create AgentPost record (including crisis fields)
    const agentPost = await prisma.agentPost.create({
      data: {
        platform: normalizedPlatform,
        externalPostId,
        platformUserId,
        severity: effectiveSeverity,
        region,
        hook: generated.hook,
        content: generated.content,
        tone: generated.tone,
        problemType,
        reasoning: generated.reasoning,
        buddhismReference: generated.buddhismReference,
      },
    });
    
    // Audit log
    await prisma.agentAuditLog.create({
      data: {
        eventType: 'llm_call',
        agentPostId: agentPost.id,
        platform: normalizedPlatform,
        requestPayload: { contextLength: context.length, language },
        responsePayload: { model: 'gpt-4o-mini', tokensUsed: completion.usage?.total_tokens },
        durationMs: Date.now() - startTime,
      },
    });
    
    res.json({
      agentPostId: agentPost.id,
      hook: generated.hook,
      content: generated.content,
      tone: generated.tone,
      reasoning: generated.reasoning,
      buddhismReference: generated.buddhismReference,
    });
    
  } catch (error) {
    console.error('[Agent Nudge] Error:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: error.message,
    });
  }
});

export default router;
