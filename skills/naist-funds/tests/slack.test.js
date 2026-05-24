const mockExecSync = jest.fn();
jest.mock("child_process", () => ({
  execSync: mockExecSync
}));

const slack = require("../scripts/utils/slack");

describe("sendMessage", () => {
  beforeEach(() => {
    mockExecSync.mockClear();
    delete process.env.DRY_RUN;
    delete process.env.SLACK_CHANNEL_ID;
  });

  test("DRY_RUN=1のとき execSync を呼ばない", () => {
    process.env.DRY_RUN = "1";
    slack.sendMessage("テストメッセージ");
    expect(mockExecSync).not.toHaveBeenCalled();
  });

  test("DRY_RUN未設定のとき openclaw message send コマンドを呼ぶ", () => {
    process.env.SLACK_CHANNEL_ID = "C_TEST";
    slack.sendMessage("テストメッセージ");
    expect(mockExecSync).toHaveBeenCalledWith(
      expect.stringContaining("openclaw message send"),
      expect.any(Object)
    );
  });
});
