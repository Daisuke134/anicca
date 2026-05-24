const {
  formatNumber,
  calcGrowthRate,
  getTopVideo,
  buildReport,
} = require("../scripts/report");

describe("formatNumber", () => {
  test("1000未満はそのまま返す", () => {
    expect(formatNumber(999)).toBe("999");
  });

  test("1000以上はkで返す", () => {
    expect(formatNumber(12847)).toBe("12.8k");
  });

  test("1000000以上はMで返す", () => {
    expect(formatNumber(1200000)).toBe("1.2M");
  });
});

describe("calcGrowthRate", () => {
  test("前日比を正しく計算する", () => {
    expect(calcGrowthRate(12000, 10000)).toBe("20.0");
  });

  test("previous が 0 の場合は null を返す", () => {
    expect(calcGrowthRate(100, 0)).toBeNull();
  });
});

describe("getTopVideo", () => {
  test("最高再生数の動画を返す", () => {
    const videos = [
      { playCount: 1000, text: "low" },
      { playCount: 45000, text: "high" },
      { playCount: 500, text: "lowest" },
    ];
    expect(getTopVideo(videos).text).toBe("high");
  });

  test("空配列は null を返す", () => {
    expect(getTopVideo([])).toBeNull();
  });
});

describe("buildReport", () => {
  test("動画データからレポートメッセージを生成する", () => {
    const data = {
      date: "2026-02-24",
      videos: [
        { playCount: 12847, diggCount: 500, text: "AIエージェントの使い方" },
        { playCount: 3000, diggCount: 100, text: "OpenClaw入門" },
      ],
    };
    const msg = buildReport(data);
    expect(msg).toContain("TikTok");
    expect(msg).toContain("12.8k");
    expect(msg).toContain("AIエージェントの使い方");
  });

  test("データなし時はエラーメッセージを返す", () => {
    const msg = buildReport(null);
    expect(msg).toContain("取得できませんでした");
  });
});
