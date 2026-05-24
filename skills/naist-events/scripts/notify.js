const { loadCache, saveCache } = require("./utils/storage");
const { sendMessage } = require("./utils/slack");

function formatWeekRange() {
  const now = new Date();
  const day = now.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(now);
  monday.setDate(now.getDate() + diff);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  const fmt = (d) => `${d.getMonth() + 1}/${d.getDate()}`;
  return `${fmt(monday)}〜${fmt(sunday)}`;
}

function notifyEvents(events) {
  const cache = loadCache();
  const newEvents = events.filter(e => !cache.notified.includes(e.id));
  const skipped = events.length - newEvents.length;

  if (newEvents.length === 0) {
    // 元のリストが空のときだけ「ありません」メッセージを送る
    // すでに通知済みでスキップした場合は送らない
    if (events.length === 0) {
      sendMessage(`📅 今週（${formatWeekRange()}）の開催予定イベントはありません`);
    }
    return { posted: 0, skipped };
  }

  const lines = [`📅 今週の{{profile.education.institution}}イベント（${formatWeekRange()}）`, ""];
  for (const e of newEvents) {
    lines.push(`• *${e.title}*`);
    const details = [];
    if (e.date || e.time) details.push(`🕐 ${e.date || ""}${e.time ? " " + e.time : ""}`);
    if (e.location) details.push(`📍 ${e.location}`);
    if (details.length) lines.push(`  ${details.join("  ")}`);
    lines.push(`  🔗 ${e.url}`);
    lines.push("");
  }

  sendMessage(lines.join("\n"));

  // cacheを更新
  cache.notified = [...cache.notified, ...newEvents.map(e => e.id)];
  cache.lastFetchedAt = new Date().toISOString();
  saveCache(cache);

  return { posted: newEvents.length, skipped };
}

module.exports = { notifyEvents };
