/**
 * POST /api/agent/feedback
 * 
 * Save feedback from external platforms (upvotes, reactions, views, etc.)
 */

import { Router } from 'express';
import { prisma } from '../../lib/prisma.js';

const router = Router();

router.post('/', async (req, res) => {
  try {
    const {
      agentPostId,
      platform,
      externalPostId,
      upvotes,
      reactions,
      views,
      likes,
      shares,
      comments,
    } = req.body;
    
    // Validate agentPostId type if provided
    if (agentPostId !== undefined && (typeof agentPostId !== 'string' || agentPostId.trim() === '')) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'agentPostId must be a non-empty string',
      });
    }
    
    // Validate externalPostId type if provided
    if (externalPostId !== undefined && (typeof externalPostId !== 'string' || externalPostId.trim() === '')) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'externalPostId must be a non-empty string',
      });
    }
    
    // Validate: need agentPostId OR (platform + externalPostId)
    if (!agentPostId && (!platform || !externalPostId)) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'agentPostId OR (platform + externalPostId) is required',
      });
    }
    
    // Normalize and validate platform if provided
    const ALLOWED_PLATFORMS = ['moltbook', 'mastodon', 'pleroma', 'misskey', 'slack', 'x', 'tiktok', 'instagram'];
    let normalizedPlatform = null;
    
    if (platform) {
      if (typeof platform !== 'string') {
        return res.status(400).json({
          error: 'Bad Request',
          message: 'platform must be a string',
        });
      }
      normalizedPlatform = platform.trim().toLowerCase();
      
      if (!ALLOWED_PLATFORMS.includes(normalizedPlatform)) {
        return res.status(400).json({
          error: 'Bad Request',
          message: `platform must be one of: ${ALLOWED_PLATFORMS.join(', ')}`,
        });
      }
    }
    
    // Validate numeric fields are non-negative integers
    const numericFields = { upvotes, views, likes, shares, comments };
    for (const [key, value] of Object.entries(numericFields)) {
      if (value !== undefined) {
        if (!Number.isFinite(value) || !Number.isInteger(value) || value < 0) {
          return res.status(400).json({
            error: 'Bad Request',
            message: `${key} must be a non-negative integer`,
          });
        }
      }
    }
    
    // Validate reactions format
    if (reactions !== undefined) {
      if (typeof reactions !== 'object' || Array.isArray(reactions)) {
        return res.status(400).json({
          error: 'Bad Request',
          message: 'reactions must be an object (Record<string, number>)',
        });
      }
      for (const [emoji, count] of Object.entries(reactions)) {
        if (!Number.isFinite(count) || !Number.isInteger(count) || count < 0) {
          return res.status(400).json({
            error: 'Bad Request',
            message: 'reactions values must be non-negative integers',
          });
        }
      }
    }
    
    // Find the agent post
    let agentPost;
    if (agentPostId) {
      agentPost = await prisma.agentPost.findUnique({
        where: { id: agentPostId },
      });
    } else {
      agentPost = await prisma.agentPost.findUnique({
        where: { platform_externalPostId: { platform: normalizedPlatform, externalPostId } },
      });
    }
    
    if (!agentPost) {
      return res.status(404).json({
        error: 'Not Found',
        message: 'Agent post not found',
      });
    }
    
    // Build update data
    const updateData = {};
    if (upvotes !== undefined) updateData.upvotes = upvotes;
    if (reactions !== undefined) updateData.reactions = reactions;
    if (views !== undefined) updateData.views = views;
    if (likes !== undefined) updateData.likes = likes;
    if (shares !== undefined) updateData.shares = shares;
    if (comments !== undefined) updateData.comments = comments;
    
    // Reject empty updates
    if (Object.keys(updateData).length === 0) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'At least one feedback field (upvotes, reactions, views, likes, shares, comments) is required',
      });
    }
    
    // Update the post
    const updated = await prisma.agentPost.update({
      where: { id: agentPost.id },
      data: updateData,
    });
    
    res.json({
      success: true,
      agentPostId: updated.id,
      updated: Object.keys(updateData),
    });
    
  } catch (error) {
    console.error('[Agent Feedback] Error:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: error.message,
    });
  }
});

export default router;
