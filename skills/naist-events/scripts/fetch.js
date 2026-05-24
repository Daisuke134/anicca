const { execSync } = require("child_process");

const SCRAPE_URL = "https://www.naist.jp/event/";
const FALLBACK_URL = "https://www.naist.jp/seminar/";

function getThisWeekRange() {
  const now = new Date();
  const day = now.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(now);
  monday.setDate(now.getDate() + diff);
  monday.setHours(0, 0, 0, 0);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  sunday.setHours(23, 59, 59, 999);
  return { monday, sunday };
}

function isThisWeek(dateStr, monday, sunday) {
  const d = new Date(dateStr + "T00:00:00+09:00");
  return d >= monday && d <= sunday;
}

function makeId(title, date) {
  return `${title.slice(0, 20)}:${date}`;
}

function parseMarkdown(markdown) {
  const events = [];
  const { monday, sunday } = getThisWeekRange();

  // {{profile.education.institution}}のイベントページは様々な形式があるため、柔軟にパース
  // パターン: "日時：YYYY-MM-DD" または "YYYY年MM月DD日"
  const lines = markdown.split("\n");
  let currentEvent = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // 見出し行（## タイトル）
    if (line.startsWith("## ") || line.startsWith("# ")) {
      if (currentEvent && currentEvent.date) {
        events.push(currentEvent);
      }
      currentEvent = {
        id: "",
        title: line.replace(/^#{1,3}\s+/, "").trim(),
        date: null,
        time: null,
        location: null,
        url: "https://www.naist.jp/event/",
        description: null
      };
      continue;
    }

    if (!currentEvent) continue;

    // 日時パース: "日時：2026-03-02 14:00" or "日時：2026年3月2日"
    const dateMatch = line.match(/日時[：:]\s*(\d{4})[年\-\/](\d{1,2})[月\-\/](\d{1,2})日?\s*(\d{1,2}:\d{2})?/);
    if (dateMatch) {
      const y = dateMatch[1];
      const m = String(parseInt(dateMatch[2])).padStart(2, "0");
      const d = String(parseInt(dateMatch[3])).padStart(2, "0");
      currentEvent.date = `${y}-${m}-${d}`;
      currentEvent.time = dateMatch[4] || null;
      currentEvent.id = makeId(currentEvent.title, currentEvent.date);
    }

    // ISO日付パターン: "2026-03-02"
    const isoMatch = line.match(/(\d{4}-\d{2}-\d{2})/);
    if (isoMatch && !currentEvent.date) {
      currentEvent.date = isoMatch[1];
      const timeMatch = line.match(/(\d{1,2}:\d{2})/);
      if (timeMatch) currentEvent.time = timeMatch[1];
      currentEvent.id = makeId(currentEvent.title, currentEvent.date);
    }

    // 場所パース
    const locationMatch = line.match(/場所[：:]\s*(.+)/);
    if (locationMatch) currentEvent.location = locationMatch[1].trim();

    // URLパース: [テキスト](URL)
    const urlMatch = line.match(/\[.*?\]\((https?:\/\/[^\)]+)\)/);
    if (urlMatch) currentEvent.url = urlMatch[1];
  }

  // 最後のイベントを追加
  if (currentEvent && currentEvent.date) {
    events.push(currentEvent);
  }

  // 今週のイベントのみフィルタ
  return events.filter(e => e.date && isThisWeek(e.date, monday, sunday));
}

function fetchEvents() {
  let markdown;
  try {
    markdown = execSync(
      `export PATH=/opt/homebrew/bin:$PATH && firecrawl scrape "${SCRAPE_URL}" markdown`,
      { encoding: "utf8", timeout: 30000 }
    );
  } catch (e) {
    // フォールバックURL試行
    try {
      markdown = execSync(
        `export PATH=/opt/homebrew/bin:$PATH && firecrawl scrape "${FALLBACK_URL}" markdown`,
        { encoding: "utf8", timeout: 30000 }
      );
    } catch (e2) {
      throw new Error(`fetch failed: ${e2.message}`);
    }
  }

  return parseMarkdown(markdown);
}

module.exports = { fetchEvents };
