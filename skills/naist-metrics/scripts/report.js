// 数値を読みやすい形式にフォーマット
function formatNumber(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
  if (n >= 1000) return (n / 1000).toFixed(1) + "k";
  return String(n);
}

// 変化率を計算（前日比）
function calcGrowthRate(current, previous) {
  if (!previous || previous === 0) return null;
  const rate = ((current - previous) / previous) * 100;
  return rate.toFixed(1);
}

// 動画リストから最高再生数の動画を取得
function getTopVideo(videos) {
  if (!videos || videos.length === 0) return null;
  return videos.reduce((best, v) =>
    (v.playCount || 0) > (best.playCount || 0) ? v : best
  );
}

// Slack メッセージを生成
function buildReport(data) {
  if (!data || !data.videos || data.videos.length === 0) {
    return "📊 昨日のデータが取得できませんでした";
  }

  const totalPlays = data.videos.reduce((s, v) => s + (v.playCount || 0), 0);
  const totalLikes = data.videos.reduce((s, v) => s + (v.diggCount || 0), 0);
  const topVideo = getTopVideo(data.videos);

  const lines = [
    `📊 *TikTok パフォーマンス（${data.date || "昨日"}）*`,
    "",
    `▶️  総再生数: ${formatNumber(totalPlays)}`,
    `❤️  総いいね: ${formatNumber(totalLikes)}`,
    `🎬  動画数: ${data.videos.length}件`,
  ];

  if (topVideo) {
    const title =
      topVideo.text
        ? topVideo.text.slice(0, 30) + (topVideo.text.length > 30 ? "..." : "")
        : "タイトルなし";
    lines.push(
      `🏆  最高動画: 「${title}」(${formatNumber(topVideo.playCount || 0)}再生)`
    );
  }

  if (data.followerCount != null && data.prevFollowerCount != null) {
    const diff = data.followerCount - data.prevFollowerCount;
    const sign = diff >= 0 ? "+" : "";
    lines.push(`👥  フォロワー増: ${sign}${diff}`);
  }

  return lines.join("\n");
}

module.exports = { formatNumber, calcGrowthRate, getTopVideo, buildReport };
