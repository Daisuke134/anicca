const storage = require('./utils/storage');

// リマインドの閾値（分）
const THRESHOLDS = [
  { key: '1h', minutes: 60, label: 'あと1時間' },
  { key: '1d', minutes: 60 * 24, label: '明日が締切' },
];

function checkAndNotify(options = {}) {
  const { dryRun = false } = options;
  const data = storage.read();
  const now = Date.now();
  const sent = [];

  const active = data.deadlines.filter(d => !d.done);

  for (const deadline of active) {
    const due = new Date(deadline.due).getTime();
    const diffMin = (due - now) / (1000 * 60);

    for (const threshold of THRESHOLDS) {
      if (diffMin <= threshold.minutes && diffMin > 0) {
        const hourKey = threshold.key + '_' + new Date().toISOString().substring(0, 13);
        if (deadline.remindedAt.includes(hourKey)) continue;

        const msg = '⏰ ' + threshold.label + ': ' + deadline.title;
        sent.push(msg);

        if (!dryRun) {
          deadline.remindedAt.push(hourKey);
          sendSlack(msg);
        }
      }
    }
  }

  if (!dryRun && sent.length > 0) {
    storage.write(data);
  }

  return sent;
}

function sendSlack(message) {
  const token = process.env.SLACK_BOT_TOKEN;
  const channel = process.env.SLACK_CHANNEL_ID;
  if (!token || !channel) return;

  const { WebClient } = require('@slack/web-api');
  const client = new WebClient(token);
  client.chat.postMessage({ channel, text: message }).catch(console.error);
}

module.exports = { checkAndNotify };

// CLIとして直接実行された場合
if (require.main === module) {
  const sent = checkAndNotify({ dryRun: false });
  console.log('[SCAN] ' + (sent.length > 0 ? sent.length + '件通知送信' : '通知なし'));
}
