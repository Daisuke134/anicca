import { fetch } from 'undici';

const SLACK_CHANNELS = {
  metrics: process.env.SLACK_CHANNEL_METRICS || '#metrics',
  ai: process.env.SLACK_CHANNEL_AI || '#ai',
};

function getWebhookUrl() {
  return process.env.SLACK_WEBHOOK_AGENTS || process.env.SLACK_WEBHOOK_URL || null;
}

async function sendSlackMessage(channel, payload) {
  const webhookUrl = getWebhookUrl();
  if (!webhookUrl) {
    return { sent: false, skipped: true, reason: 'webhook_not_configured' };
  }

  const body = {
    channel,
    ...payload,
  };

  const res = await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const details = await res.text().catch(() => 'unknown');
    throw new Error(`Slack webhook failed: HTTP ${res.status} ${details}`);
  }

  return { sent: true, skipped: false };
}

async function notifyPostSuccess(platform, postId, verificationScore) {
  return sendSlackMessage(SLACK_CHANNELS.metrics, {
    text: `✅ ${platform} post completed`,
    blocks: [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*Platform*: ${platform}\n*Post ID*: ${postId}\n*Score*: ${verificationScore}/5`,
        },
      },
    ],
  });
}

async function notifyDLQEntry(skillName, error, context = {}) {
  return sendSlackMessage(SLACK_CHANNELS.ai, {
    text: `🚨 DLQ Entry: ${skillName}`,
    blocks: [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*Skill*: ${skillName}\n*Error*: ${error}\n*Context*: ${JSON.stringify(context)}`,
        },
      },
    ],
  });
}

export {
  sendSlackMessage,
  notifyPostSuccess,
  notifyDLQEntry,
  SLACK_CHANNELS,
};

export default {
  sendSlackMessage,
  notifyPostSuccess,
  notifyDLQEntry,
  SLACK_CHANNELS,
};
