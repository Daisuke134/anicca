const { execSync } = require("child_process");
const { buildReport } = require("./report");
const { sendMessage } = require("./utils/slack");

function fetchTikTokMetrics(username) {
  const token = process.env.APIFY_API_TOKEN;
  if (!token) throw new Error("APIFY_API_TOKEN が設定されていません");

  const body = JSON.stringify({
    profiles: [`https://www.tiktok.com/@${username}`],
    resultsPerPage: 10,
    shouldDownloadVideos: false,
    shouldDownloadCovers: false,
  });

  const result = execSync(
    `curl -s -X POST "https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items?token=${token}" -H 'Content-Type: application/json' -d '${body}'`,
    { encoding: "utf8", timeout: 60000 }
  );

  return JSON.parse(result);
}

function run() {
  const username = process.env.TIKTOK_USERNAME || "your-handle";
  const today = new Date().toISOString().slice(0, 10);

  let videos;
  try {
    videos = fetchTikTokMetrics(username);
  } catch (e) {
    sendMessage(`❌ naist-metrics エラー: ${e.message}`);
    return;
  }

  const data = { videos, date: today };
  const message = buildReport(data);

  if (process.env.DRY_RUN === "1") {
    console.log(`[DRY_RUN] メトリクス:\n${message}`);
    return;
  }

  sendMessage(message);
}

module.exports = { run };

if (require.main === module) {
  run();
}
