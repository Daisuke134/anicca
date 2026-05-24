const fs = require("fs");
const os = require("os");
const path = require("path");

let tmpDir;

beforeEach(() => {
  jest.resetModules();
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "naist-funds-guide-"));
  process.env.{{profile.education.institution}}_FUNDS_DATA_DIR = tmpDir;
  const guides = {
    guides: [
      {
        id: "jsps-dc1",
        keywords: ["学振", "DC1", "特別研究員"],
        name: "日本学術振興会 特別研究員DC1",
        steps: ["1. 公募要領を確認", "2. 指導教員と相談"],
        officialUrl: "https://www.jsps.go.jp/j-pd/"
      }
    ]
  };
  fs.writeFileSync(path.join(tmpDir, "guides.json"), JSON.stringify(guides));
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
  delete process.env.{{profile.education.institution}}_FUNDS_DATA_DIR;
});

describe("searchGuide", () => {
  test("キーワードHIT時にstepsを返す", () => {
    const { searchGuide } = require("../scripts/guide");
    const result = searchGuide("学振DC1の申請方法");
    expect(result.hit).toBe(true);
    expect(result.guide.id).toBe("jsps-dc1");
    expect(result.guide.steps).toHaveLength(2);
  });

  test("部分一致（DC1のみ）でもHITする", () => {
    const { searchGuide } = require("../scripts/guide");
    const result = searchGuide("DC1");
    expect(result.hit).toBe(true);
  });

  test("マッチしないキーワードでMISSを返す", () => {
    const { searchGuide } = require("../scripts/guide");
    const result = searchGuide("全く関係ないキーワード");
    expect(result.hit).toBe(false);
    expect(result.guide).toBeNull();
  });

  test("MISS時は officialUrls を返す", () => {
    const { searchGuide } = require("../scripts/guide");
    const result = searchGuide("存在しない助成金");
    expect(result.fallbackUrls).toBeDefined();
    expect(result.fallbackUrls.length).toBeGreaterThan(0);
  });
});
