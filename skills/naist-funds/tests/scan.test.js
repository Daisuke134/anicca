const mockNotifyGrants = jest.fn();
jest.mock("../scripts/notify", () => ({ notifyGrants: mockNotifyGrants }));

const mockSendMessage = jest.fn();
jest.mock("../scripts/utils/slack", () => ({ sendMessage: mockSendMessage }));

const mockFetchGrants = jest.fn().mockReturnValue([]);
jest.mock("../scripts/fetch", () => ({ fetchGrants: mockFetchGrants }));

describe("scan", () => {
  beforeEach(() => {
    mockNotifyGrants.mockClear();
    mockSendMessage.mockClear();
    mockFetchGrants.mockClear();
    mockFetchGrants.mockReturnValue([]);
  });

  test("fetchGrantsとnotifyGrantsを実行する", () => {
    const { scan } = require("../scripts/scan");
    scan();
    expect(mockFetchGrants).toHaveBeenCalledTimes(1);
    expect(mockNotifyGrants).toHaveBeenCalledTimes(1);
  });

  test("fetchGrantsが例外を投げた場合にSlackエラー通知する", () => {
    mockFetchGrants.mockImplementation(() => { throw new Error("取得失敗"); });
    const { scan } = require("../scripts/scan");
    expect(() => scan()).not.toThrow();
    expect(mockSendMessage).toHaveBeenCalledWith(expect.stringContaining("エラー"));
  });
});
