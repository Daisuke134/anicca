const mockSendMessage = jest.fn();
jest.mock("../scripts/utils/slack", () => ({ sendMessage: mockSendMessage }));

const mockExecSync = jest.fn();
jest.mock("child_process", () => ({ execSync: mockExecSync }));

describe("notifyGrants", () => {
  let storage;
  const fs = require("fs");
  const os = require("os");
  const path = require("path");
  let tmpDir;

  beforeEach(() => {
    jest.resetModules();
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "naist-funds-notify-"));
    process.env.{{profile.education.institution}}_FUNDS_DATA_DIR = tmpDir;
    fs.writeFileSync(path.join(tmpDir, "cache.json"), JSON.stringify({ notified: [], lastFetchedAt: null }));
    mockSendMessage.mockClear();
    jest.mock("../scripts/utils/slack", () => ({ sendMessage: mockSendMessage }));
    jest.mock("child_process", () => ({ execSync: mockExecSync }));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
    delete process.env.{{profile.education.institution}}_FUNDS_DATA_DIR;
  });

  test("新規Grantのみ投稿し、キャッシュに追加する", () => {
    const grants = [
      { id: "abc123", name: "テスト助成金", organization: "JSPS", deadline: null, amount: null, summary: "テスト", url: "https://example.com", category: "研究助成", fetchedAt: new Date().toISOString() }
    ];
    const { notifyGrants } = require("../scripts/notify");
    notifyGrants(grants);
    expect(mockSendMessage).toHaveBeenCalledTimes(1);
    const { loadCache } = require("../scripts/utils/storage");
    const cache = loadCache();
    expect(cache.notified.some((n) => n.id === "abc123")).toBe(true);
  });

  test("既通知Grantはスキップする（重複防止）", () => {
    const fs = require("fs");
    const path = require("path");
    const cache = { notified: [{ id: "already", notifiedAt: new Date().toISOString() }], lastFetchedAt: null };
    fs.writeFileSync(path.join(tmpDir, "cache.json"), JSON.stringify(cache));
    const grants = [
      { id: "already", name: "既通知", organization: "JSPS", deadline: null, amount: null, summary: "テスト", url: "https://example.com", category: "研究助成", fetchedAt: new Date().toISOString() }
    ];
    const { notifyGrants } = require("../scripts/notify");
    notifyGrants(grants);
    expect(mockSendMessage).not.toHaveBeenCalled();
  });

  test("締切30日以内のGrantに⚠️マークを付ける", () => {
    const soon = new Date();
    soon.setDate(soon.getDate() + 10);
    const deadline = soon.toISOString().slice(0, 10);
    const grants = [
      { id: "urgent1", name: "緊急助成金", organization: "JST", deadline, amount: "100万円", summary: "急ぎ", url: "https://example.com", category: "研究助成", fetchedAt: new Date().toISOString() }
    ];
    const { notifyGrants } = require("../scripts/notify");
    notifyGrants(grants);
    expect(mockSendMessage).toHaveBeenCalledTimes(1);
    const msg = mockSendMessage.mock.calls[0][0];
    expect(msg).toContain("⚠️");
  });
});
