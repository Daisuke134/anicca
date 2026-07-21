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

module.exports = { DISCOVERY_STRINGS };
