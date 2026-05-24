const mockExecSync = jest.fn();
jest.mock("child_process", () => ({ execSync: mockExecSync }));

const mockSendMessage = jest.fn();
jest.mock("../scripts/utils/slack", () => ({ sendMessage: mockSendMessage }));

beforeEach(() => {
  jest.resetModules();
  mockExecSync.mockReset();
  mockSendMessage.mockReset();
  delete process.env.DRY_RUN;
});

const MOCK_{{profile.education.institution}}_PAGE = `
# {{profile.education.institution}} 日本学術振興会 科研費

## DC1について

DC1は大学院博士課程1〜2年次の学生を対象とした特別研究員制度です。
申請書は日本語で記述することが推奨されています。
締切: 毎年6月頃
金額: 月額20万円（2年間）

詳細: https://www.jsps.go.jp/j-pd/
`;

describe("answerQuestion", () => {
  test("質問に対して回答文字列を返す", () => {
    mockExecSync.mockReturnValue(MOCK_{{profile.education.institution}}_PAGE);
    const { answerQuestion } = require("../scripts/answer");
    const result = answerQuestion("DC1の申請書は日本語で書くべきですか？");
    expect(typeof result.answer).toBe("string");
    expect(result.answer.length).toBeGreaterThan(10);
  });

  test("根拠URLを含む", () => {
    mockExecSync.mockReturnValue(MOCK_{{profile.education.institution}}_PAGE);
    const { answerQuestion } = require("../scripts/answer");
    const result = answerQuestion("DC1とは何ですか？");
    expect(result).toHaveProperty("sourceUrl");
    expect(result.sourceUrl).toMatch(/^https?:\/\//);
  });

  test("Firecrawl失敗時はfallback回答を返す（throwしない）", () => {
    mockExecSync.mockImplementation(() => { throw new Error("network error"); });
    const { answerQuestion } = require("../scripts/answer");
    const result = answerQuestion("{{profile.education.institution}}の学費は？");
    expect(() => result).not.toThrow();
    expect(result.answer).toContain("naist.jp");
  });

  test("空の質問はエラーをthrowする", () => {
    const { answerQuestion } = require("../scripts/answer");
    expect(() => answerQuestion("")).toThrow();
    expect(() => answerQuestion(null)).toThrow();
  });
});

describe("qa（エントリーポイント）", () => {
  test("DRY_RUN=1のときSlack投稿しない", () => {
    process.env.DRY_RUN = "1";
    mockExecSync.mockReturnValue(MOCK_{{profile.education.institution}}_PAGE);
    const { qa } = require("../scripts/qa");
    qa("DC1とは？");
    expect(mockSendMessage).not.toHaveBeenCalled();
  });

  test("通常モードで回答をSlackに投稿する", () => {
    mockExecSync.mockReturnValue(MOCK_{{profile.education.institution}}_PAGE);
    const { qa } = require("../scripts/qa");
    qa("DC1とは？");
    expect(mockSendMessage).toHaveBeenCalledTimes(1);
    const msg = mockSendMessage.mock.calls[0][0];
    expect(msg).toContain("DC1");
  });

  test("Firecrawl失敗時もSlackにfallbackメッセージを投稿する", () => {
    mockExecSync.mockImplementation(() => { throw new Error("timeout"); });
    const { qa } = require("../scripts/qa");
    qa("{{profile.education.institution}}の学費は？");
    expect(mockSendMessage).toHaveBeenCalledTimes(1);
    expect(mockSendMessage.mock.calls[0][0]).toContain("naist.jp");
  });
});
