// lib/i18n.js — user-facing Life Manager copy, keyed by locale and feature.
//
// LM-32 discovery text is copied verbatim from spec §9.11. Keep it here rather
// than in scheduler/callback code so copy changes have one implementation SSOT.
"use strict";

const DISCOVERY_STRINGS = Object.freeze({
  ja: Object.freeze({
    location: Object.freeze({
      text: "💡 ご存知でしたか？Telegramで位置情報を共有すると、「出た？」の確認なしで、遅れそうな時に自動で先方へ遅刻連絡を送れるようになります。共有はこのチャットの📎→位置情報→ライブ位置情報から。\n［やり方を見る］［今はしない］",
      primaryButton: "やり方を見る",
      laterButton: "今はしない",
    }),
    payout: Object.freeze({
      text: "💡 私が稼いだお金をあなたに送れるようになりました。送金先（口座かwallet）を1つ登録するだけで、毎月の利益を自動で受け取れます。\n［登録する］［今はしない］",
      primaryButton: "登録する",
      laterButton: "今はしない",
    }),
    locationHowTo: "📍 Telegramのこのチャットで、📎 →「位置情報」→「ライブ位置情報を共有」の順にタップしてください。共有中だけ、遅れそうな時の連絡が自動になります。",
  }),
});

const DAILY_STRINGS = Object.freeze({
  ja: Object.freeze({
    travelAutofill: "📅 {when}「{summary}」を確認しました。{origin}からの移動時間{travelMinutes}分をカレンダーに入れておきました。{departure}発です。",
  }),
});

const CFO_STRINGS = Object.freeze({
  ja: Object.freeze({
    title: "💰 今日のお金",
    confirmedAssets: "確認できた資産",
    confirmedLiabilities: "確認できた負債",
    confirmedDifference: "差し引き",
    change: "前回から",
    noAction: "今すること：ありません",
    partialTitle: "⚠️ 確認できた範囲のお金",
    excluded: "合計に入れていません",
    recovered: "✅ 更新の問題を自動修復し、最新データを再確認しました。",
    actionReconsent: Object.freeze({
      title: "🔐 Moneytreeの接続を1回だけ更新してください",
      body: "最新の金額を確認できないため、古い残高は合計に入れていません。",
      retry: "接続後は自動で再確認し、今日のレポートを送ります。",
    }),
    actionProviderOutage: Object.freeze({
      title: "⚠️ Moneytreeの確認に時間がかかっています",
      body: "こちらで自動的に再試行します。",
      retry: "次回の自動再試行：{nextRetryAt}",
    }),
    unknown: "不明",
    updated: "更新",
  }),
  en: Object.freeze({
    title: "💰 Today’s money",
    confirmedAssets: "Confirmed assets",
    confirmedLiabilities: "Confirmed liabilities",
    confirmedDifference: "Difference",
    change: "Since last report",
    noAction: "Action now: Nothing right now",
    partialTitle: "⚠️ Money I could confirm",
    excluded: "Not included in the total",
    recovered: "✅ I repaired the update and confirmed fresh data again.",
    actionReconsent: Object.freeze({
      title: "🔐 Reconnect Moneytree once",
      body: "I could not confirm the latest amount, so old balances are not included in the total.",
      retry: "After reconnection, I will check again and send today’s report.",
    }),
    actionProviderOutage: Object.freeze({
      title: "⚠️ Moneytree is taking longer to confirm",
      body: "I will automatically retry.",
      retry: "Next automatic retry: {nextRetryAt}",
    }),
    unknown: "Unknown",
    updated: " updated",
  }),
});

function offsetMinutes(referenceIso) {
  if (/Z$/i.test(String(referenceIso || ""))) return 0;
  const match = /([+-])(\d{2}):(\d{2})$/.exec(String(referenceIso || ""));
  if (!match) return 0;
  const minutes = Number(match[2]) * 60 + Number(match[3]);
  return match[1] === "-" ? -minutes : minutes;
}

function localDate(ms, referenceIso) {
  return new Date(ms + offsetMinutes(referenceIso) * 60_000);
}

function localDayNumber(ms, referenceIso) {
  const date = localDate(ms, referenceIso);
  return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()) / 86_400_000;
}

function dayLabel(eventMs, nowMs, referenceIso) {
  const diff = localDayNumber(eventMs, referenceIso) - localDayNumber(nowMs, referenceIso);
  if (diff === 0) return "今日";
  if (diff === 1) return "明日";
  const date = localDate(eventMs, referenceIso);
  return `${date.getUTCMonth() + 1}/${date.getUTCDate()}`;
}

function clockLabel(ms, referenceIso) {
  const date = localDate(ms, referenceIso);
  return `${String(date.getUTCHours()).padStart(2, "0")}:${String(date.getUTCMinutes()).padStart(2, "0")}`;
}

function escapeHtml(value) {
  return String(value || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function formatTravelAutofillMessage(report, nowMs = Date.now()) {
  const referenceIso = report.startIso || new Date(report.startMs).toISOString();
  const values = {
    when: `${dayLabel(report.startMs, nowMs, referenceIso)}${clockLabel(report.startMs, referenceIso)}`,
    summary: escapeHtml(report.summary || "予定"),
    origin: escapeHtml(report.origin || "出発地"),
    travelMinutes: Math.max(0, Math.round((report.arriveMs - report.leaveMs) / 60_000)),
    departure: clockLabel(report.leaveMs, referenceIso),
  };
  return DAILY_STRINGS.ja.travelAutofill.replace(/\{(\w+)\}/g, (_match, key) => String(values[key]));
}

module.exports = { DAILY_STRINGS, DISCOVERY_STRINGS, CFO_STRINGS, formatTravelAutofillMessage };
