const { execSync } = require("child_process");

function sendMessage(message) {
  if (process.env.DRY_RUN === "1") {
    console.log("[DRY_RUN] Slack投稿スキップ:\n" + message);
    return;
  }
  const channelId = process.env.SLACK_CHANNEL_ID || "C0AGH981G84";
  const escaped = message.replace(/"/g, '\\"');
  execSync(
    `openclaw message send --channel slack --target "${channelId}" --message "${escaped}"`,
    { stdio: "inherit" }
  );
}

module.exports = { sendMessage };
