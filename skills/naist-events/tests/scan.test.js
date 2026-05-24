const mockFetchEvents = jest.fn();
const mockNotifyEvents = jest.fn();
const mockSendMessage = jest.fn();

jest.mock("../scripts/fetch", () => ({ fetchEvents: mockFetchEvents }));
jest.mock("../scripts/notify", () => ({ notifyEvents: mockNotifyEvents }));
jest.mock("../scripts/utils/slack", () => ({ sendMessage: mockSendMessage }));

beforeEach(() => {
  mockFetchEvents.mockReset();
  mockNotifyEvents.mockReset();
  mockSendMessage.mockReset();
});

describe("scan", () => {
  test("fetchEventsとnotifyEventsを呼び出す", () => {
    mockFetchEvents.mockReturnValue([]);
    mockNotifyEvents.mockReturnValue({ posted: 0, skipped: 0 });
    const { scan } = require("../scripts/scan");
    scan();
    expect(mockFetchEvents).toHaveBeenCalledTimes(1);
    expect(mockNotifyEvents).toHaveBeenCalledTimes(1);
  });

  test("エラー発生時はSlackにエラーメッセージを投稿する", () => {
    mockFetchEvents.mockImplementation(() => { throw new Error("network error"); });
    const { scan } = require("../scripts/scan");
    expect(() => scan()).not.toThrow();
    expect(mockSendMessage).toHaveBeenCalledTimes(1);
    expect(mockSendMessage.mock.calls[0][0]).toContain("エラー");
  });

  test("notifyEventsの結果をコンソールに出力する", () => {
    mockFetchEvents.mockReturnValue([]);
    mockNotifyEvents.mockReturnValue({ posted: 2, skipped: 1 });
    const consoleSpy = jest.spyOn(console, "log").mockImplementation(() => {});
    const { scan } = require("../scripts/scan");
    scan();
    expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining("新着2件"));
    consoleSpy.mockRestore();
  });
});
