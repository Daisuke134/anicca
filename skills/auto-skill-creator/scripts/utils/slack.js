const { execSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

// Canonical Slack target resolver. Priority:
//   1. SLACK_CHANNEL_ID env (per-invocation override)
//   2. ~/.openclaw/state/anicca.json :: slack.metrics_channel  (canonical)
//   3. hard fallback (only used if both above missing)
// Skills MUST resolve their channel through this resolver — never hardcode.
function resolveTarget() {
  if (process.env.SLACK_CHANNEL_ID) return process.env.SLACK_CHANNEL_ID;
  try {
    const p = path.join(os.homedir(), ".openclaw", "state", "anicca.json");
    const s = JSON.parse(fs.readFileSync(p, "utf8"));
    if (s && s.slack && s.slack.metrics_channel) return s.slack.metrics_channel;
  } catch {}
  return "{{profile.channels.reportChannel}}"; // canonical anicca metrics channel; last-resort fallback
}

function sendMessage(message) {
  if (process.env.DRY_RUN === "1") {
    console.log("[DRY_RUN] Slack投稿スキップ:\n" + message);
    return;
  }
  const channelId = resolveTarget();
  const escaped = message.replace(/"/g, '\\"');
  execSync(
    `openclaw message send --channel slack --target "${channelId}" --message "${escaped}"`,
    { stdio: "inherit" }
  );
}

module.exports = { sendMessage, resolveTarget };
