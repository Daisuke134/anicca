const {
  checkFirstPerson,
  checkOrphanRefs,
  countWords,
  readabilityScore,
  buildReport,
} = require("../scripts/review");

describe("checkFirstPerson", () => {
  test('一人称 "we propose" を検出する', () => {
    const text = "In this paper, we propose a novel method.";
    const issues = checkFirstPerson(text);
    expect(issues.length).toBeGreaterThan(0);
    expect(issues[0].match.toLowerCase()).toContain("we propose");
  });

  test('一人称 "I believe" を検出する', () => {
    const text = "I believe this approach is fundamentally correct.";
    const issues = checkFirstPerson(text);
    expect(issues.length).toBeGreaterThan(0);
  });

  test('"our method" を検出する', () => {
    const text = "Our method achieves state-of-the-art results.";
    const issues = checkFirstPerson(text);
    expect(issues.length).toBeGreaterThan(0);
  });

  test("三人称表現はスルーする", () => {
    const text =
      "This thesis proposes a novel method for solving NP-hard problems.";
    const issues = checkFirstPerson(text);
    expect(issues.length).toBe(0);
  });
});

describe("checkOrphanRefs", () => {
  test("本文で引用されているが文献リストにない参照を検出する", () => {
    const text =
      "\\cite{Smith2023} showed that...\n\\bibitem{Jones2022} Jones, A. 2022.";
    const issues = checkOrphanRefs(text);
    expect(issues.some((i) => i.key === "Smith2023" && i.type === "orphan_cite")).toBe(true);
  });

  test("全ての引用が文献リストに存在する場合は問題なし", () => {
    const text =
      "\\cite{Smith2023} showed that...\n\\bibitem{Smith2023} Smith, J. 2023.";
    const issues = checkOrphanRefs(text);
    expect(issues.filter((i) => i.type === "orphan_cite").length).toBe(0);
  });
});

describe("countWords", () => {
  test("単語数を正確にカウントする", () => {
    const text = "This is a test sentence with seven distinct words here.";
    const count = countWords(text);
    expect(count).toBeGreaterThanOrEqual(9);
  });
});

describe("buildReport", () => {
  test("レポートに issueCount, wordCount, score が含まれる", () => {
    const text =
      "We propose a method. \\cite{X} is cited.\n\\bibitem{X} Author. 2023.";
    const report = buildReport(text);
    expect(report).toHaveProperty("issueCount");
    expect(report).toHaveProperty("wordCount");
    expect(report).toHaveProperty("score");
    expect(report.issueCount).toBeGreaterThan(0); // "we propose" が引っかかる
  });

  test("空テキストは例外を投げる", () => {
    expect(() => buildReport("")).toThrow("論文テキストが空です");
  });
});
