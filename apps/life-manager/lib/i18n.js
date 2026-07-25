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

// FIN-b: the payout-destination closed question, verbatim from spec §9.11 FINANCIAL. The three button
// labels are read out of the copy itself rather than restated, so the keyboard can never drift from the
// sentence the user reads. This copy is Dais-owned — the implementation quotes it, it never invents it.
const FINANCIAL_STRINGS = Object.freeze({
  ja: Object.freeze({
    payoutQuestion: Object.freeze({
      text: "収益の送金先を1つだけ教えてください。これ以外の個人情報は不要です。\n［銀行口座を登録］［walletアドレスを登録］［あとで］",
      bankButton: "銀行口座を登録",
      walletButton: "walletアドレスを登録",
      laterButton: "あとで",
    }),
  }),
});

const DAILY_STRINGS = Object.freeze({
  ja: Object.freeze({
    travelAutofill: "📅 {when}「{summary}」を確認しました。{origin}からの移動時間{travelMinutes}分をカレンダーに入れておきました。{departure}発です。",
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

module.exports = { DAILY_STRINGS, DISCOVERY_STRINGS, FINANCIAL_STRINGS, formatTravelAutofillMessage };
