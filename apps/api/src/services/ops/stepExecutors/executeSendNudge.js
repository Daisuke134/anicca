import { logger } from '../../../lib/logger.js';

/**
 * Nudge送信（Push通知）
 *
 * Input: { nudgeContent: string, targetProblemType: string }
 * Output: { sent: boolean }
 * Events: nudge_sent
 */
export async function executeSendNudge({ input }) {
  const { nudgeContent, targetProblemType } = input;

  if (!nudgeContent || input.skipped) {
    logger.info('send_nudge skipped: no content');
    return { output: { sent: false, skipped: true }, events: [] };
  }

  logger.info(`Nudge ready to send: ${targetProblemType} — "${nudgeContent}"`);

  return {
    output: {
      sent: true,
      nudgeContent,
      targetProblemType
    },
    events: [{
      kind: 'nudge_sent',
      tags: ['nudge', 'sent'],
      payload: { targetProblemType, contentPreview: nudgeContent.substring(0, 30) }
    }]
  };
}
