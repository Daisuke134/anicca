/**
 * Deletion Request Handler (1.6.1)
 * 
 * Handles deletion requests from:
 * - Moltbook DM (via deletion-handler process)
 * - Slack #agents commands
 * - Admin CLI commands
 * 
 * Per spec section 6.6:
 * - Deletes: external_post_id, platform_user_id, content, reasoning
 * - Retains: hook, upvotes, views (for learning)
 * - SLA: 24 calendar hours
 */

import { Router } from 'express';
import { prisma } from '../../lib/prisma.js';

const router = Router();

/**
 * POST /api/agent/deletion
 * 
 * Body:
 * - platformUserId: string (format: <platform>:<user_id>)
 * - requestedBy: string ('moltbook_dm', 'slack_command', 'admin_cli')
 * - adminId?: string (required if requestedBy === 'admin_cli')
 */
router.post('/', async (req, res) => {
  try {
    const { platformUserId, requestedBy, adminId } = req.body;

    // Validate required fields
    if (!platformUserId) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'platformUserId is required (format: <platform>:<user_id>)',
      });
    }

    // Validate requestedBy with strict allowlist
    const ALLOWED_REQUESTED_BY = ['moltbook_dm', 'slack_command', 'admin_cli'];
    if (!requestedBy || !ALLOWED_REQUESTED_BY.includes(requestedBy)) {
      return res.status(400).json({
        error: 'Bad Request',
        message: `requestedBy must be one of: ${ALLOWED_REQUESTED_BY.join(', ')}`,
      });
    }

    // Validate platformUserId format (strict regex validation)
    const PLATFORM_USER_ID_REGEX = /^[a-z0-9_]+:.+$/;
    if (!PLATFORM_USER_ID_REGEX.test(platformUserId)) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'platformUserId must be in format <platform>:<user_id> (lowercase platform, non-empty user_id)',
      });
    }

    // Authorization check for admin
    if (requestedBy === 'admin_cli' && !adminId) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'adminId is required for admin_cli requests',
      });
    }

    // Audit: deletion request received
    await prisma.agentAuditLog.create({
      data: {
        eventType: 'deletion_request',
        requestPayload: { platformUserId, requestedBy, adminId },
        executedBy: requestedBy === 'admin_cli' ? `admin:${adminId}` : 'system',
      },
    });

    // Execute deletion (must NULL all PII including platform_user_id)
    const result = await prisma.$executeRaw`
      UPDATE agent_posts
      SET 
        external_post_id = NULL,
        platform_user_id = NULL,
        content = NULL,
        reasoning = NULL,
        anonymized_at = NOW()
      WHERE platform_user_id = ${platformUserId}
        AND anonymized_at IS NULL
    `;

    // Audit: deletion completed
    await prisma.agentAuditLog.create({
      data: {
        eventType: 'deletion_completed',
        requestPayload: { platformUserId },
        responsePayload: { deletedCount: result },
        executedBy: requestedBy === 'admin_cli' ? `admin:${adminId}` : 'system',
      },
    });

    res.json({
      success: true,
      deletedCount: result,
      message: `Deleted personal data from ${result} posts for ${platformUserId}`,
    });

  } catch (error) {
    console.error('[Agent Deletion] Error:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: error.message,
    });
  }
});

/**
 * GET /api/agent/deletion/status/:platformUserId
 * 
 * Check if deletion has been completed for a user.
 */
router.get('/status/:platformUserId', async (req, res) => {
  try {
    const { platformUserId } = req.params;
    
    // Validate platformUserId format (same as POST endpoint)
    const PLATFORM_USER_ID_REGEX = /^[a-z0-9_]+:.+$/;
    if (!PLATFORM_USER_ID_REGEX.test(platformUserId)) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'platformUserId must be in format <platform>:<user_id> (lowercase platform, non-empty user_id)',
      });
    }

    // Count remaining non-anonymized posts
    const remaining = await prisma.agentPost.count({
      where: {
        platformUserId,
        anonymizedAt: null,
      },
    });

    // Get last deletion audit log
    const lastDeletion = await prisma.agentAuditLog.findFirst({
      where: {
        eventType: 'deletion_completed',
        requestPayload: {
          path: ['platformUserId'],
          equals: platformUserId,
        },
      },
      orderBy: { createdAt: 'desc' },
    });

    res.json({
      platformUserId,
      remainingPosts: remaining,
      deleted: remaining === 0 && lastDeletion != null,
      lastDeletionAt: lastDeletion?.createdAt || null,
    });

  } catch (error) {
    console.error('[Agent Deletion Status] Error:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: error.message,
    });
  }
});

export default router;
