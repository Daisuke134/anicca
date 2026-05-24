const {
  extractUserTexts,
  countPatterns,
  findTopPattern,
  buildRecommendation,
} = require("../scripts/analyze");
const fs = require("fs");
const os = require("os");
const path = require("path");

// テスト用一時ファイル生成ヘルパー
function writeTempJsonl(lines) {
  const tmpFile = path.join(os.tmpdir(), `test-session-${Date.now()}.jsonl`);
  fs.writeFileSync(tmpFile, lines.join("\n"), "utf8");
  return tmpFile;
}

describe("extractUserTexts", () => {
  test("JSONL ファイルからユーザーメッセージのテキストを抽出する", () => {
    const tmpFile = writeTempJsonl([
      JSON.stringify({
        type: "message",
        message: {
          role: "user",
          content: [{ type: "text", text: "arXiv論文を探して" }],
        },
      }),
      JSON.stringify({
        type: "message",
        message: {
          role: "assistant",
          content: [{ type: "text", text: "はい" }],
        },
      }),
    ]);

    const texts = extractUserTexts(tmpFile);
    expect(texts).toContain("arXiv論文を探して");
    expect(texts.length).toBe(1);
    fs.unlinkSync(tmpFile);
  });

  test("存在しないファイルは空配列を返す", () => {
    const texts = extractUserTexts("/nonexistent/path/file.jsonl");
    expect(texts).toEqual([]);
  });
});

describe("countPatterns", () => {
  test("論文関連テキストを正しくカウントする", () => {
    const texts = ["arXiv論文を調べて", "最新の論文まとめて", "研究論文ある？"];
    const counts = countPatterns(texts);
    expect(counts["論文"]).toBeGreaterThanOrEqual(3);
  });

  test("テキストなしは全て0を返す", () => {
    const counts = countPatterns([]);
    Object.values(counts).forEach((v) => expect(v).toBe(0));
  });
});

describe("findTopPattern", () => {
  test("最頻値のパターンを返す", () => {
    const counts = { 論文: 5, メール: 2, カレンダー: 1 };
    const top = findTopPattern(counts);
    expect(top.key).toBe("論文");
    expect(top.count).toBe(5);
  });

  test("全て0の場合はnullを返す", () => {
    const counts = { 論文: 0, メール: 0 };
    const top = findTopPattern(counts);
    expect(top).toBeNull();
  });
});

describe("buildRecommendation", () => {
  test("スキル提案メッセージを生成する", () => {
    const pattern = { key: "論文", count: 11 };
    const skill = {
      name: "karpathy/nanochat@read-arxiv-paper",
      url: "https://skills.sh/karpathy/nanochat/read-arxiv-paper",
      description: "arXiv論文を自動取得・要約→Slack通知",
    };
    const msg = buildRecommendation(pattern, skill, 50);
    expect(msg).toContain("おすすめのスキル");
    expect(msg).toContain("11回");
    expect(msg).toContain("karpathy/nanochat@read-arxiv-paper");
  });

  test("count=0のパターンはnullを返す", () => {
    const pattern = { key: "論文", count: 0 };
    const skill = { name: "test", url: "https://test.com", description: "test" };
    expect(buildRecommendation(pattern, skill, 0)).toBeNull();
  });
});
