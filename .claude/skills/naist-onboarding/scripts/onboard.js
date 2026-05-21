/**
 * naist-onboarding/scripts/onboard.js
 *
 * Creates #ai-<name> channel, invites user, sends welcome message.
 *
 * Source: slack-api v1.0.7 (ClawHub) API call patterns
 *   https://api.slack.com/methods/conversations.create
 *   https://api.slack.com/methods/conversations.invite
 *
 * Usage: node onboard.js <slackUserId>
 */

const { WebClient } = require('@slack/web-api');

const CHANNEL_AI = 'C08RZ98SBUL'; // #ai チャンネル

async function onboard(userId) {
  const web = new WebClient(process.env.SLACK_BOT_TOKEN);

  // 1. ユーザー情報取得
  const userInfo = await web.users.info({ user: userId });
  const user = userInfo.user;
  const profile = user.profile;

  // NAIST Slack username format: <familyname>.<givenname>.<code>  (e.g. narita.daisuke.nd4)
  // チャンネル名は先頭パートを使う（narita → #ai-narita）
  const usernameParts = user.name.split('.');
  const rawName = profile.display_name || profile.real_name || user.name;
  const safeName = usernameParts[0]
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '')
    .slice(0, 20);

  const channelName = `ai-${safeName}`;

  // 2. チャンネル作成（name_taken なら既存を使う）
  let channel;
  try {
    const created = await web.conversations.create({ name: channelName });
    channel = created.channel;
    console.log(`✅ Created #${channelName} (${channel.id})`);
  } catch (e) {
    if (e.data?.error === 'name_taken' || e.data?.error === 'missing_scope') {
      if (e.data?.error === 'missing_scope') {
        console.log(`⚠️ create skipped: missing scope (${e.data?.needed}). Looking for existing #${channelName}`);
      }
      const list = await web.conversations.list({
        types: 'public_channel,private_channel',
        limit: 200
      });
      channel = list.channels.find(c => c.name === channelName);
      if (!channel) throw new Error(`Channel #${channelName} not found`);
      console.log(`ℹ️ Channel #${channelName} already exists (${channel.id})`);
    } else {
      throw e;
    }
  }

  // 3. Bot 自身をチャンネルに参加させる（作成直後は自動参加だが念のため）
  try {
    await web.conversations.join({ channel: channel.id });
  } catch (_) {}

  // 4. ユーザーを招待（channels:manage スコープが必要。なければスキップ）
  try {
    await web.conversations.invite({ channel: channel.id, users: userId });
    console.log(`✅ Invited ${rawName} to #${channelName}`);
  } catch (e) {
    if (e.data?.error === 'already_in_channel') {
      console.log(`ℹ️ User already in #${channelName}`);
    } else if (e.data?.error === 'missing_scope') {
      console.log(`⚠️ invite skipped: missing scope (${e.data?.needed}). Add channels:manage to Slack app.`);
    } else {
      throw e;
    }
  }

  // 5. #ai に通知
  await web.chat.postMessage({
    channel: CHANNEL_AI,
    text: `✅ <#${channel.id}> 作ったよ！そっちで話しかけて。`
  });

  // 6. 新チャンネルでウェルカムメッセージ
  await web.chat.postMessage({
    channel: channel.id,
    text: [
      `yo 👋 ${rawName}さん！`,
      '',
      'こんなことできるよ:',
      '• 📬 NAISTメール読む・返信する',
      '• 📅 カレンダー確認・予定追加',
      '• 📄 最新arXiv論文をまとめる',
      '• ⏰ 締切リマインド登録',
      '• 🏛 ポータルで履修・成績確認',
      '• 💰 科研費・奨学金の新着情報',
      '',
      'まず何か試してみる？'
    ].join('\n')
  });

  console.log(`✅ Onboarding complete for ${rawName} → #${channelName}`);
}

const userId = process.argv[2];
if (!userId) {
  console.error('Usage: node onboard.js <slackUserId>');
  process.exit(1);
}

onboard(userId).catch(e => {
  console.error('Error:', e.data?.error || e.message);
  process.exit(1);
});
