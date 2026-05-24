const fs = require("fs");
const os = require("os");
const path = require("path");

const mockSendMessage = jest.fn();
jest.mock("../scripts/utils/slack", () => ({ sendMessage: mockSendMessage }));

let tmpDir;

beforeEach(() => {
  jest.resetModules();
  mockSendMessage.mockReset();
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "naist-events-notify-"));
  process.env.{{profile.education.institution}}_EVENTS_DATA_DIR = tmpDir;
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
  delete process.env.{{profile.education.institution}}_EVENTS_DATA_DIR;
});

const mockEvents = [
  { id: "テスト講演会:2026-03-02", title: "テスト講演会", date: "2026-03-02", time: "14:00", location: "D207", url: "https://www.naist.jp/event/test1", description: null },
  { id: "研究発表会:2026-03-03", title: "研究発表会", date: "2026-03-03", time: "10:00", location: "大会議室", url: "https://www.naist.jp/event/test2", description: null }
];

describe("notifyEvents", () => {
  test("新規イベントをSlackに投稿してposted=1を返す", () => {
    const { notifyEvents } = require("../scripts/notify");
    const result = notifyEvents([mockEvents[0]]);
    expect(result.posted).toBe(1);
    expect(result.skipped).toBe(0);
    expect(mockSendMessage).toHaveBeenCalledTimes(1);
  });

  test("通知済みイベントはスキップされる", () => {
    const cache = { notified: ["テスト講演会:2026-03-02"], lastFetchedAt: null };
    fs.writeFileSync(path.join(tmpDir, "cache.json"), JSON.stringify(cache));
    const { notifyEvents } = require("../scripts/notify");
    const result = notifyEvents([mockEvents[0]]);
    expect(result.posted).toBe(0);
    expect(result.skipped).toBe(1);
    expect(mockSendMessage).not.toHaveBeenCalled();
  });

  test("イベントが0件のときは空メッセージを投稿する", () => {
    const { notifyEvents } = require("../scripts/notify");
    const result = notifyEvents([]);
    expect(result.posted).toBe(0);
    expect(mockSendMessage).toHaveBeenCalledTimes(1);
    expect(mockSendMessage.mock.calls[0][0]).toContain("イベントはありません");
  });

  test("複数イベントを投稿してcacheに保存する", () => {
    const { notifyEvents, loadCacheForTest } = require("../scripts/notify");
    const result = notifyEvents(mockEvents);
    expect(result.posted).toBe(2);
    // cacheが更新されていることを確認
    const { loadCache } = require("../scripts/utils/storage");
    const saved = loadCache();
    expect(saved.notified).toContain("テスト講演会:2026-03-02");
    expect(saved.notified).toContain("研究発表会:2026-03-03");
  });
});
