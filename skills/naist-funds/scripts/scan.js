const { fetchGrants } = require("./fetch");
const { notifyGrants } = require("./notify");
const { sendMessage } = require("./utils/slack");

// .envからAPIキーを読み込む
function loadEnv() {
  const fs = require("fs");
  const path = require("path");
  const envFile = path.join("/Users/anicca/.openclaw", ".env");
  if (!fs.existsSync(envFile)) return;
  const lines = fs.readFileSync(envFile, "utf8").split("\n");
  for (const line of lines) {
    const m = line.match(/^([A-Z_]+)=(.+)$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].trim();
  }
}

function scan() {
  loadEnv();
  try {
    const grants = fetchGrants();
    const result = notifyGrants(grants);
    console.log(`[naist-funds] スキャン完了: 新着${result.posted}件 / スキップ${result.skipped}件`);
  } catch (e) {
    const msg = `[naist-funds] エラーが発生しました: ${e.message}`;
    console.error(msg);
    try {
      sendMessage(msg);
    } catch (slackErr) {
      console.error("[naist-funds] Slackエラー通知も失敗:", slackErr.message);
    }
  }
}

module.exports = { scan };

if (require.main === module) {
  scan();
}
