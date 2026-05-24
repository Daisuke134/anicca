const mockExecSync = jest.fn();
jest.mock("child_process", () => ({ execSync: mockExecSync }));

beforeEach(() => {
  jest.resetModules();
  mockExecSync.mockReset();
  delete process.env.{{profile.education.institution}}_EVENTS_DATA_DIR;
});

// 今週（月〜日）の日付を生成するヘルパー
function getThisWeekDate(offsetDays = 0) {
  const now = new Date();
  const monday = new Date(now);
  const day = now.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  monday.setDate(now.getDate() + diff + offsetDays);
  return monday.toISOString().split("T")[0];
}

const MOCK_MARKDOWN = `
# {{profile.education.institution}}イベント

## テスト講演会
日時：${getThisWeekDate(2)} 14:00
場所：D207
[詳細](https://www.naist.jp/event/test1)

## 研究発表会
日時：${getThisWeekDate(3)} 10:00-12:00
場所：大会議室
[詳細](https://www.naist.jp/event/test2)
`;

describe("fetchEvents", () => {
  test("今週のイベントを返す", () => {
    mockExecSync.mockReturnValue(MOCK_MARKDOWN);
    const { fetchEvents } = require("../scripts/fetch");
    const events = fetchEvents();
    expect(Array.isArray(events)).toBe(true);
    // Firecrawlが呼ばれたことを確認
    expect(mockExecSync).toHaveBeenCalledTimes(1);
    expect(mockExecSync.mock.calls[0][0]).toContain("firecrawl");
  });

  test("Firecrawlがエラーを投げた場合はthrowする", () => {
    mockExecSync.mockImplementation(() => { throw new Error("fetch failed"); });
    const { fetchEvents } = require("../scripts/fetch");
    expect(() => fetchEvents()).toThrow("fetch failed");
  });

  test("返り値は配列（空配列あり）", () => {
    mockExecSync.mockReturnValue("# {{profile.education.institution}}イベント\n（今週のイベントはありません）");
    const { fetchEvents } = require("../scripts/fetch");
    const events = fetchEvents();
    expect(Array.isArray(events)).toBe(true);
  });

  test("各イベントはid/title/date/urlを持つ", () => {
    mockExecSync.mockReturnValue(MOCK_MARKDOWN);
    const { fetchEvents } = require("../scripts/fetch");
    const events = fetchEvents();
    if (events.length > 0) {
      expect(events[0]).toHaveProperty("id");
      expect(events[0]).toHaveProperty("title");
      expect(events[0]).toHaveProperty("date");
      expect(events[0]).toHaveProperty("url");
    }
  });
});
