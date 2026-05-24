const { loadGuides } = require("./utils/storage");

const FALLBACK_URLS = [
  "https://www.jsps.go.jp/ (日本学術振興会)",
  "https://www.jst.go.jp/boshu.html (JST公募情報)",
  "https://www.jfund.or.jp/ (日本財団助成金)"
];

function searchGuide(query) {
  const { guides } = loadGuides();
  const q = query.toLowerCase();
  const found = guides.find((g) =>
    g.keywords.some((kw) => q.includes(kw.toLowerCase()) || kw.toLowerCase().includes(q))
  );
  if (found) return { hit: true, guide: found, fallbackUrls: [] };
  return { hit: false, guide: null, fallbackUrls: FALLBACK_URLS };
}

function formatGuideResponse(result, query) {
  if (result.hit) {
    const g = result.guide;
    const lines = [`📋 *${g.name}* の申請手順:`, ""];
    g.steps.forEach((s) => lines.push(s));
    lines.push("");
    if (g.deadline) lines.push(`📅 締切目安: ${g.deadline}`);
    lines.push(`🔗 公式サイト: ${g.officialUrl}`);
    return lines.join("\n");
  }
  const lines = [
    `「${query}」に該当する申請手順は見つかりませんでした。`,
    "以下の公式サイトで詳細をご確認ください:",
    ""
  ];
  result.fallbackUrls.forEach((u) => lines.push(`• ${u}`));
  return lines.join("\n");
}

module.exports = { searchGuide, formatGuideResponse };

if (require.main === module) {
  const query = process.argv[2] || "";
  const result = searchGuide(query);
  console.log(formatGuideResponse(result, query));
}
