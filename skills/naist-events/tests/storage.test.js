const fs = require("fs");
const os = require("os");
const path = require("path");

let tmpDir;

beforeEach(() => {
  jest.resetModules();
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "naist-events-storage-"));
  process.env.{{profile.education.institution}}_EVENTS_DATA_DIR = tmpDir;
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
  delete process.env.{{profile.education.institution}}_EVENTS_DATA_DIR;
});

describe("loadCache", () => {
  test("cache.jsonが存在しない場合はデフォルト値を返す", () => {
    const { loadCache } = require("../scripts/utils/storage");
    const result = loadCache();
    expect(result).toEqual({ notified: [], lastFetchedAt: null });
  });

  test("cache.jsonが壊れている場合はデフォルト値を返す", () => {
    fs.writeFileSync(path.join(tmpDir, "cache.json"), "invalid json");
    const { loadCache } = require("../scripts/utils/storage");
    const result = loadCache();
    expect(result).toEqual({ notified: [], lastFetchedAt: null });
  });

  test("正常なcache.jsonを読み込む", () => {
    const cache = { notified: ["event1:2026-03-02"], lastFetchedAt: "2026-03-02T09:20:00.000Z" };
    fs.writeFileSync(path.join(tmpDir, "cache.json"), JSON.stringify(cache));
    const { loadCache } = require("../scripts/utils/storage");
    expect(loadCache()).toEqual(cache);
  });
});

describe("saveCache", () => {
  test("cache.jsonをatomicに書き込む", () => {
    const { saveCache, loadCache } = require("../scripts/utils/storage");
    const cache = { notified: ["test:2026-03-02"], lastFetchedAt: "2026-03-02T09:20:00.000Z" };
    saveCache(cache);
    expect(loadCache()).toEqual(cache);
  });

  test("データディレクトリが存在しない場合は作成する", () => {
    const newDir = path.join(tmpDir, "sub", "dir");
    process.env.{{profile.education.institution}}_EVENTS_DATA_DIR = newDir;
    const { saveCache } = require("../scripts/utils/storage");
    saveCache({ notified: [], lastFetchedAt: null });
    expect(fs.existsSync(newDir)).toBe(true);
  });
});
