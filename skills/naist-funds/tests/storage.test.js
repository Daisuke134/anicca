const path = require("path");
const fs = require("fs");
const os = require("os");

// テスト用一時ディレクトリを使うようにモジュールをテスト
let tmpDir;
let storage;

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "naist-funds-test-"));
  jest.resetModules();
  process.env.{{profile.education.institution}}_FUNDS_DATA_DIR = tmpDir;
  storage = require("../scripts/utils/storage");
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
  delete process.env.{{profile.education.institution}}_FUNDS_DATA_DIR;
});

describe("loadCache", () => {
  test("cache.jsonが存在しない場合は空のcacheを返す", () => {
    const cache = storage.loadCache();
    expect(cache).toEqual({ notified: [], lastFetchedAt: null });
  });

  test("既存のcache.jsonを読み込む", () => {
    const data = { notified: [{ id: "abc", notifiedAt: "2026-02-24T00:00:00Z" }], lastFetchedAt: "2026-02-24T00:00:00Z" };
    fs.writeFileSync(path.join(tmpDir, "cache.json"), JSON.stringify(data));
    const cache = storage.loadCache();
    expect(cache.notified).toHaveLength(1);
    expect(cache.notified[0].id).toBe("abc");
  });
});

describe("saveCache", () => {
  test("cacheをcache.jsonに保存する（原子的書き込み）", () => {
    const data = { notified: [{ id: "xyz", notifiedAt: "2026-02-24T00:00:00Z" }], lastFetchedAt: "2026-02-24T00:00:00Z" };
    storage.saveCache(data);
    const saved = JSON.parse(fs.readFileSync(path.join(tmpDir, "cache.json"), "utf8"));
    expect(saved.notified[0].id).toBe("xyz");
  });

  test("保存後にtmpファイルが残らない", () => {
    storage.saveCache({ notified: [], lastFetchedAt: null });
    const files = fs.readdirSync(tmpDir);
    const tmpFiles = files.filter((f) => f.endsWith(".tmp"));
    expect(tmpFiles).toHaveLength(0);
  });
});

describe("loadGuides", () => {
  test("guides.jsonが存在しない場合は空配列を返す", () => {
    const guides = storage.loadGuides();
    expect(guides).toEqual({ guides: [] });
  });

  test("既存のguides.jsonを読み込む", () => {
    const data = { guides: [{ id: "jsps-dc1", keywords: ["学振"], name: "DC1", steps: ["step1"], officialUrl: "https://example.com" }] };
    fs.writeFileSync(path.join(tmpDir, "guides.json"), JSON.stringify(data));
    const guides = storage.loadGuides();
    expect(guides.guides).toHaveLength(1);
    expect(guides.guides[0].id).toBe("jsps-dc1");
  });
});
