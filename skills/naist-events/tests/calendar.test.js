const mockExecSync = jest.fn();
jest.mock("child_process", () => ({ execSync: mockExecSync }));

beforeEach(() => {
  jest.resetModules();
  mockExecSync.mockReset();
  delete process.env.DRY_RUN;
});

const mockEvent = {
  id: "テスト講演会:2026-03-02",
  title: "テスト講演会",
  date: "2026-03-02",
  time: "14:00",
  location: "D207",
  url: "https://www.naist.jp/event/test1"
};

describe("addToCalendar", () => {
  test("DRY_RUN=1のときgogを呼ばない", () => {
    process.env.DRY_RUN = "1";
    const { addToCalendar } = require("../scripts/add-to-calendar");
    addToCalendar(mockEvent);
    expect(mockExecSync).not.toHaveBeenCalled();
  });

  test("イベントをgogでカレンダー登録する", () => {
    mockExecSync.mockReturnValue(Buffer.from(""));
    const { addToCalendar } = require("../scripts/add-to-calendar");
    addToCalendar(mockEvent);
    expect(mockExecSync).toHaveBeenCalledTimes(1);
    const cmd = mockExecSync.mock.calls[0][0];
    expect(cmd).toContain("gog");
    expect(cmd).toContain("テスト講演会");
    expect(cmd).toContain("2026-03-02");
  });

  test("execSyncエラーはthrowせずwarnのみ", () => {
    mockExecSync.mockImplementation(() => { throw new Error("gog failed"); });
    const { addToCalendar } = require("../scripts/add-to-calendar");
    expect(() => addToCalendar(mockEvent)).not.toThrow();
  });

  test("日付のみ（時刻なし）でも登録できる", () => {
    mockExecSync.mockReturnValue(Buffer.from(""));
    const { addToCalendar } = require("../scripts/add-to-calendar");
    const eventNoTime = { ...mockEvent, time: null };
    expect(() => addToCalendar(eventNoTime)).not.toThrow();
    expect(mockExecSync).toHaveBeenCalledTimes(1);
  });
});
