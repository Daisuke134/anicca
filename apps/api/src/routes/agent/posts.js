/**
 * GET /api/agent/posts/recent
 * 
 * Get recent agent posts for feedback-fetch skill
 */

import { Router } from 'express';
import { prisma } from '../../lib/prisma.js';

const router = Router();

const ALLOWED_PLATFORMS = ['moltbook', 'slack', 'x', 'tiktok', 'instagram'];
const MAX_DAYS = 30;
const MAX_LIMIT = 100;
const MIN_LIMIT = 1;
const DEFAULT_LIMIT = 50;

router.get('/recent', async (req, res) => {
  try {
    const { platform, days = 7, limit = DEFAULT_LIMIT, cursor } = req.query;
    
    // Validate platform
    if (platform !== undefined) {
      const normalizedPlatform = String(platform).trim().toLowerCase();
      if (!ALLOWED_PLATFORMS.includes(normalizedPlatform)) {
        return res.status(400).json({
          error: 'INVALID_PLATFORM',
          message: `Invalid platform: ${platform}. Must be one of: ${ALLOWED_PLATFORMS.join(', ')}`,
        });
      }
    }
    
    // Validate days
    const daysNum = parseInt(days, 10);
    if (isNaN(daysNum) || daysNum < 1 || daysNum > MAX_DAYS) {
      return res.status(400).json({
        error: 'INVALID_DAYS',
        message: `days must be between 1 and ${MAX_DAYS}`,
      });
    }
    
    // Validate limit with proper bounds checking
    const parsedLimit = parseInt(limit, 10);
    if (isNaN(parsedLimit)) {
      return res.status(400).json({
        error: 'INVALID_LIMIT',
        message: `limit must be a number between ${MIN_LIMIT} and ${MAX_LIMIT}`,
      });
    }
    const limitNum = Math.max(MIN_LIMIT, Math.min(parsedLimit, MAX_LIMIT));
    
    // Build where clause
    const since = new Date();
    since.setDate(since.getDate() - daysNum);
    
    const where = {
      createdAt: { gte: since },
    };
    
    if (platform) {
      where.platform = String(platform).trim().toLowerCase();
    }
    
    // Cursor-based pagination using createdAt (ISO string)
    if (cursor) {
      const cursorDate = new Date(cursor);
      if (isNaN(cursorDate.getTime())) {
        return res.status(400).json({
          error: 'INVALID_CURSOR',
          message: 'cursor must be a valid ISO date string',
        });
      }
      where.createdAt = { 
        ...where.createdAt,
        lt: cursorDate,
      };
    }
    
    // Query posts
    const posts = await prisma.agentPost.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      take: limitNum + 1, // +1 to check if there are more
      select: {
        id: true,
        platform: true,
        externalPostId: true,
        content: true,
        upvotes: true,
        views: true,
        likes: true,
        shares: true,
        createdAt: true,
      },
    });
    
    // Check if there are more results
    const hasMore = posts.length > limitNum;
    const results = hasMore ? posts.slice(0, limitNum) : posts;
    // Use createdAt as cursor to match orderBy
    const nextCursor = hasMore && results.length > 0 
      ? results[results.length - 1].createdAt.toISOString() 
      : null;
    
    res.json({
      posts: results,
      nextCursor,
      hasMore,
    });
    
  } catch (error) {
    console.error('[Agent Posts] Error:', error);
    // Don't expose internal error details to client
    res.status(500).json({
      error: 'Internal Server Error',
    });
  }
});

export default router;
