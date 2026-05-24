const { parseSkillsOutput, stripAnsi } = require("../scripts/search");
const { extractQuery } = require("../scripts/creator");

describe("stripAnsi", () => {
  test("ANSIエスケープコードを除去する", () => {
    const input = "\x1B[38;5;145mkarpathy/nanochat@read-arxiv-paper\x1B[0m";
    expect(stripAnsi(input)).toBe("karpathy/nanochat@read-arxiv-paper");
  });
});

describe("parseSkillsOutput", () => {
  test("ANSIコード付きの実際の出力をパースする", () => {
    const output = [
      "\x1B[38;5;145mkarpathy/nanochat@read-arxiv-paper\x1B[0m \x1B[36m170 installs\x1B[0m",
      "\x1B[38;5;102m└ https://skills.sh/karpathy/nanochat/read-arxiv-paper\x1B[0m",
      "",
      "\x1B[38;5;145myorkeccak/scientific-skills@arxiv-search\x1B[0m \x1B[36m163 installs\x1B[0m",
      "\x1B[38;5;102m└ https://skills.sh/yorkeccak/scientific-skills/arxiv-search\x1B[0m",
    ].join("\n");

    const results = parseSkillsOutput(output);
    expect(results.length).toBeGreaterThanOrEqual(2);
    expect(results[0].name).toBe("karpathy/nanochat@read-arxiv-paper");
    expect(results[0].installs).toBe(170);
    expect(results[0].url).toContain("skills.sh");
  });

  test("スキルなしの出力は空配列を返す", () => {
    const output = "No skills found matching your query.";
    const results = parseSkillsOutput(output);
    expect(results).toEqual([]);
  });
});

describe("extractQuery", () => {
  test("依頼文からキーワードを抽出する", () => {
    const q = extractQuery("arXiv論文を毎日要約するスキルを作ってください");
    expect(q).toContain("arXiv論文");
    expect(q).not.toContain("スキルを作って");
  });

  test("シンプルな依頼もキーワード化する", () => {
    const q = extractQuery("Hacker Newsを要約して");
    expect(q).toContain("Hacker News");
  });
});
