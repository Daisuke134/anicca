/**
 * slack-approval/scripts/approve.js
 *
 * Block Kit approval button utility for all OpenClaw skills.
 *
 * Source:
 *   - Block Kit JSON pattern: sickn33/slack-bot-builder (253★)
 *   - Node.js SDK: Slack official @slack/web-api + @slack/socket-mode
 *     https://slack.dev/node-slack-sdk/
 */

const { WebClient } = require('@slack/web-api');
const { SocketModeClient } = require('@slack/socket-mode');

/**
 * Post a Block Kit approval message and wait for button click.
 *
 * @param {object} opts
 * @param {string} opts.channel  - Slack channel ID (e.g. 'C091G3PKHL2')
 * @param {string} opts.title    - Bold header text (e.g. '📧 メール返信')
 * @param {string} opts.detail   - Body text (mrkdwn, e.g. '宛先: 山田教授\n本文: ...')
 * @returns {Promise<'approved'|'denied'>}
 */
async function requestApproval({ channel, title, detail }) {
  const web = new WebClient(process.env.SLACK_BOT_TOKEN);
  const sm = new SocketModeClient({ appToken: process.env.SLACK_APP_TOKEN });

  await sm.start();

  // Block Kit pattern from slack-bot-builder (sickn33, 253★)
  const blockId = `approval_${Date.now()}`;
  const posted = await web.chat.postMessage({
    channel,
    text: title, // fallback for notifications/accessibility
    blocks: [
      {
        type: 'section',
        text: { type: 'mrkdwn', text: `*${title}*\n${detail}` }
      },
      {
        type: 'actions',
        block_id: blockId,
        elements: [
          {
            type: 'button',
            action_id: 'approved',
            style: 'primary',
            text: { type: 'plain_text', text: '✅ 実行する' }
          },
          {
            type: 'button',
            action_id: 'denied',
            style: 'danger',
            text: { type: 'plain_text', text: '❌ キャンセル' }
          }
        ]
      }
    ]
  });

  // Wait for button click via Socket Mode
  // block_actions は body で受け取る（event ではなく body を使う）
  return new Promise((resolve) => {
    sm.on('slack_event', async ({ body, ack }) => {
      if (
        body?.type === 'block_actions' &&
        body?.actions?.[0]?.block_id === blockId
      ) {
        await ack();
        const action = body.actions[0].action_id; // 'approved' | 'denied'

        // Update message: replace buttons with result text (prevent double-click)
        const resultText = action === 'approved'
          ? `*${title}*\n✅ 実行しました`
          : `*${title}*\n❌ キャンセルしました`;

        await web.chat.update({
          channel,
          ts: posted.ts,
          text: resultText,
          blocks: [
            { type: 'section', text: { type: 'mrkdwn', text: resultText } }
          ]
        });

        await sm.disconnect();
        resolve(action);
      }
    });
  });
}

module.exports = { requestApproval };
