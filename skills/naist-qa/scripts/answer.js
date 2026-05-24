const { execSync } = require("child_process");

const SEARCH_URLS = [
  "https://www.naist.jp/",
  "https://www.jsps.go.jp/j-pd/",
  "https://www.jst.go.jp/",
];

// キーワードからスクレイプ先URLを選ぶ
function pickUrl(question) {
  if (/DC1|DC2|学振|科研費|JSPS|特別研究員/.test(question)) {
    return "https://www.jsps.go.jp/j-pd/";
  }
  if (/JST|ACT-X|さきがけ/.test(question)) {
    return "https://www.jst.go.jp/";
  }
  return "https://www.naist.jp/";
}

function scrape(url) {
  return execSync(
    `export PATH=/opt/homebrew/bin:$PATH && firecrawl scrape "${url}" markdown`,
    { encoding: "utf8", timeout: 30000 }
  );
}

// マークダウンから質問に関連する段落を抽出
function extractRelevant(markdown, question) {
  const keywords = question
    .replace(/[？?。、]/g, " ")
    .split(/\s+/)
    .filter(w => w.length >= 2)
    .slice(0, 5);

  const paragraphs = markdown.split(/\n{2,}/);
  const scored = paragraphs.map(p => {
    const score = keywords.filter(k => p.includes(k)).length;
    return { p, score };
  });

  const top = scored
    .filter(x => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
    .map(x => x.p.trim())
    .join("\n\n");

  return top || paragraphs.slice(0, 3).join("\n\n");
}

function answerQuestion(question) {
  if (!question || question.trim() === "") {
    throw new Error("質問が空です");
  }

  const sourceUrl = pickUrl(question);

  let markdown;
  try {
    markdown = scrape(sourceUrl);
  } catch (e) {
    // Firecrawl失敗時のfallback
    return {
      answer: `公式サイトで確認してください: ${sourceUrl}\n（自動取得に失敗しました: ${e.message}）`,
      sourceUrl,
    };
  }

  const relevant = extractRelevant(markdown, question);
  const answer = `${relevant}\n\n📎 参照: ${sourceUrl}`;

  return { answer, sourceUrl };
}

module.exports = { answerQuestion };
