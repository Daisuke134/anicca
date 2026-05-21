/**
 * GET /api/agent/wisdom
 * 
 * Get wisdom content for posting to external platforms
 */

import { Router } from 'express';
import { prisma } from '../../lib/prisma.js';

const router = Router();

router.get('/', async (req, res) => {
  try {
    const { problemType, tone } = req.query;
    
    // Build query
    const where = { isWisdom: true };
    if (tone) where.tone = tone;
    if (problemType) {
      where.targetProblemTypes = { has: problemType };
    }
    
    // Get random wisdom from hook_candidates
    const wisdoms = await prisma.hookCandidate.findMany({
      where,
      take: 10,
      orderBy: { updatedAt: 'desc' },
    });
    
    if (wisdoms.length === 0) {
      return res.status(404).json({
        error: 'Not Found',
        message: 'No wisdom found for the given criteria',
      });
    }
    
    // Pick random one
    const wisdom = wisdoms[Math.floor(Math.random() * wisdoms.length)];
    
    res.json({
      id: wisdom.id,
      hook: wisdom.text,
      content: wisdom.text, // For wisdom, hook and content are the same
      tone: wisdom.tone,
      problemType: wisdom.targetProblemTypes?.[0] || null,
      source: 'hook_candidates',
      reasoning: 'Selected from verified wisdom patterns',
    });
    
  } catch (error) {
    console.error('[Agent Wisdom] Error:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: error.message,
    });
  }
});

export default router;
