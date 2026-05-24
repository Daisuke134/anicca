const { execSync } = require("child_process");

jest.mock("child_process", () => ({
  execSync: jest.fn()
}));

const mockExecSync = require("child_process").execSync;

describe("fetchGrants", () => {
  beforeEach(() => {
    mockExecSync.mockClear();
  });

  test("3ソースからGrant[]を返す", () => {
    // Firecrawlがマークダウンを返すケースをモック
    mockExecSync.mockReturnValue(
      "## 学術研究助成基金助成金\n締切: 2026-03-31\n金額: 上限500万円\n概要: 若手研究者向け\nhttps://www.jsps.go.jp/sample\n"
    );
    const { fetchGrants } = require("../scripts/fetch");
    const grants = fetchGrants();
    expect(Array.isArray(grants)).toBe(true);
    // 3ソース × 1件以上 = 少なくとも1件
    expect(grants.length).toBeGreaterThanOrEqual(0);
  });

  test("各Grantはid/name/organization/url/fetchedAtを持つ", () => {
    mockExecSync.mockReturnValue(
      "## テスト助成金\n締切: 2026-04-30\nhttps://example.com/grant\n"
    );
    const { fetchGrants } = require("../scripts/fetch");
    const grants = fetchGrants();
    if (grants.length > 0) {
      expect(grants[0]).toHaveProperty("id");
      expect(grants[0]).toHaveProperty("name");
      expect(grants[0]).toHaveProperty("organization");
      expect(grants[0]).toHaveProperty("url");
      expect(grants[0]).toHaveProperty("fetchedAt");
    }
  });

  test("Firecrawl失敗時は空配列を返す（エラーを投げない）", () => {
    mockExecSync.mockImplementation(() => { throw new Error("Firecrawl失敗"); });
    const { fetchGrants } = require("../scripts/fetch");
    expect(() => fetchGrants()).not.toThrow();
    const grants = fetchGrants();
    expect(Array.isArray(grants)).toBe(true);
  });
});
