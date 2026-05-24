const mockExecSync = jest.fn();
jest.mock("child_process", () => ({ execSync: mockExecSync }));

const slack = require("../scripts/utils/slack");

beforeEach(() => {
  mockExecSync.mockReset();
  delete process.env.DRY_RUN;
  delete process.env.SLACK_CHANNEL_ID;
});

describe("sendMessage", () => {
  test("DRY_RUN=1のとき execSync を呼ばない", () => {
    process.env.DRY_RUN = "1";
    slack.sendMessage("テストメッセージ");
    expect(mockExecSync).not.toHaveBeenCalled();
  });

  test("通常モードで openclaw message send を呼ぶ", () => {
    slack.sendMessage("テストメッセージ");
    expect(mockExecSync).toHaveBeenCalledTimes(1);
    expect(mockExecSync.mock.calls[0][0]).toContain("openclaw message send");
    expect(mockExecSync.mock.calls[0][0]).toContain("C0AGH981G84");
  });

  test("SLACK_CHANNEL_IDを環境変数で上書きできる", () => {
    process.env.SLACK_CHANNEL_ID = "C999TEST";
    slack.sendMessage("テスト");
    expect(mockExecSync.mock.calls[0][0]).toContain("C999TEST");
  });

  test("メッセージ内のダブルクォートをエスケープする", () => {
    slack.sendMessage('He said "hello"');
    const cmd = mockExecSync.mock.calls[0][0];
    expect(cmd).toContain('\\"hello\\"');
  });
});
