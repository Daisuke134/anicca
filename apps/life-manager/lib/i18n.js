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

// FIN-b: the payout-destination closed question, and FIN-c: the monthly report — both verbatim from
// spec §9.11 FINANCIAL. The payout button labels are read out of the copy itself rather than restated,
// so the keyboard can never drift from the sentence the user reads. The monthly report has two shapes,
// because a losing month must not be dressed as a quiet one: `monthly` is the profit shape,
// `monthlyLoss` is the 盛らない原則 shape. The `verify` line is the same sentence in both — a month we
// lost money on has to be exactly as checkable on-chain as a month we made money on, and only showing
// the link when the news is good would be the precise asymmetry that principle forbids. This copy is
// Dais-owned — the implementation quotes it, it never invents it.
const FINANCIAL_STRINGS = Object.freeze({
  ja: Object.freeze({
    payoutQuestion: Object.freeze({
      text: "収益の送金先を1つだけ教えてください。これ以外の個人情報は不要です。\n［銀行口座を登録］［walletアドレスを登録］［あとで］",
      bankButton: "銀行口座を登録",
      walletButton: "walletアドレスを登録",
      laterButton: "あとで",
      // CB-1 (§10.0-15 ③): the visible reply to a second tap / already-registered destination.
      // {rail} is filled with the registered rail's name. This copy is Dais-editable.
      alreadyRegistered: "送金先は登録済みです（{rail}）。変更したい時は「送金先を変更」と送ってください。",
    }),
    // FIN-d (13d-a): the typed wallet-address intake. `ask` and `confirmed` are the 2026-07-26 ruling's
    // copy (button では渡せない情報がある → the manager asks, the user TYPES). The reject/save-failed
    // strings are new; like every FINANCIAL string here they are Dais-owned and Dais-editable — the
    // implementation quotes them, it never invents copy inline. {short} = 0x6592…EDc7-style shortening.
    payoutAddress: Object.freeze({
      ask: "walletアドレスを1つ送ってください（Base, USDC）。例: 0x1234…abcd\nこれは収益の送金にだけ使います。",
      confirmed: "✅ 登録しました: {short}（Base）\n利益が出た月はここへ送金します。変更は「送金先を変更」と送信。",
      rejectedChecksum: "そのアドレスは checksum の検証に失敗しました（EIP-55）。walletからコピーし直して、もう一度送ってください。",
      rejectedFormat: "walletアドレスとして読めませんでした。0xで始まる42文字のアドレスを、1つだけ送ってください。",
      saveFailed: "保存を確認できませんでした。登録はまだ完了していません。少し待ってから、もう一度アドレスを送ってください。",
      // The typed command that re-opens the intake — quoted verbatim in alreadyRegistered/confirmed above.
      changeCommand: "送金先を変更",
    }),
    monthly: Object.freeze({
      header: "💰 今月の収支報告です。",
      revenue: "・私のwalletでの収益: {revenue}",
      transfer: "・あなたへの送金: {transfer}（送金済み）",
      // A profitable month that has not sent anything yet keeps the profit shape's label and borrows
      // the loss shape's explanation, rather than rendering a misleading 「$0.00（送金済み）」.
      transferNone: "・あなたへの送金: なし（利益が出た月のみ送金します）",
      cost: "・手数料・実費: {cost}",
      balance: "・私の残高: {balance}",
      verify: "取引はすべてこちらで確認できます: {explorer}/address/{address}",
    }),
    monthlyLoss: Object.freeze({
      revenue: "・収益: {revenue}（マイナスでした）",
      transfer: "・送金: なし（利益が出た月のみ送金します）",
      outlook: "先月比の要因: {cause}。来月の方針: {plan}。",
    }),
    reports: Object.freeze({
      dailyHeader: "💰 今日のagent収支",
      balance: "・残高: {balance}",
      gross: "・Gross: {gross}",
      cost: "・Cost: {cost}",
      net: "・Net: {net}",
      state: "・状態: {state}",
      weeklyHeader: "💰 週次agent収支",
      rail: "・{rail}: {net}",
      selfFunded: "・Self-funded率: {ratio}",
      distributable: "・User分配可能額: {amount}",
      states: Object.freeze({
        running: "稼働中",
        negative_net: "赤字",
        no_external_income: "外部収入なし",
        reserve_floor: "reserve floor",
      }),
    }),
  }),
});

const DAILY_STRINGS = Object.freeze({
  ja: Object.freeze({
    travelAutofill: "📅 {when}「{summary}」を確認しました。{origin}からの移動時間{travelMinutes}分をカレンダーに入れておきました。{departure}発です。",
  }),
});

// 11d PHYSICAL 事後報告 — spec §9.11 PHYSICAL. **This copy is Dais-editable**（No-human-loop 例外3）:
// edit the strings here and the implementation follows; the implementation never writes copy inline.
//
// Two deliberate departures from the §9.11 table, both in the direction of not lying:
//   1. 「当日17:40にお電話します。」 is DROPPED. The same-day call is a separate 11d leg gated by
//      lib/physical-aftercare.js (it needs a confirmed booking id AND a start time); promising a call
//      this module does not schedule would be exactly the false success §9.5 forbids.
//   2. 「オフィスから徒歩5分の」 is DROPPED. We do not measure walking distance anywhere in the
//      pipeline, so stating one would be fabricated detail.
// {emoji} is a placeholder because §9.11 only writes copy for dental (🦷) and haircut (💈); clinic is
// a real 11a care type with no line in the bank, so its emoji is named here rather than invented at
// the call site. `booked` is the 歯医者予約の事後報告 sentence; `bookedUsual` is the 散髪 sentence
// (used whenever the chosen provider is the user's usual one — that is what 「いつものお店」 means).
// `bookingFailed` / `bookingUncertain` have no §9.11 line at all: §9.5 demands 候補提示 + 正直報告
// when booking is impossible, and an unverifiable submit must never be reported as a booking.
const PHYSICAL_STRINGS = Object.freeze({
  ja: Object.freeze({
    booked: "{emoji} 前回の{careLabel}から{sinceLabel}経っていたので、{providerName}を{slotLabel}で予約しました。{calendarLine}\n（都合が悪ければ［変更する］）",
    bookedUsual: "{emoji} そろそろ{sinceLabel}なので、いつものお店を{slotLabel}で取りました。{calendarLine}\n（［変更する］）",
    // 「カレンダーに入れてあります」 is a claim about a write that may not have happened (no calendar
    // connected, the transport refused, an untimezoned slot we refuse to guess at). It is therefore
    // its OWN sentence and the renderer picks which one to say — §9.5's 正直報告 covers the half of a
    // report that failed just as much as it covers a booking that failed outright.
    calendarAdded: "カレンダーに入れてあります。",
    calendarMissing: "ただ、カレンダーへの登録はできませんでした。お手数ですがご自身で入れてください。",
    bookingFailed: "{emoji} そろそろ{careLabel}の時期なので予約を試しましたが、{reason}のため私では取れませんでした。候補はこちらです。\n{candidateLines}\nどれにするか教えてもらえれば、続きは私がやります。",
    bookingUncertain: "{emoji} {providerName}を{slotLabel}で申し込みましたが、予約できたかの確認が取れませんでした。二重予約になるので送り直していません。お手数ですが{reservationUrl}でご確認ください。",
    candidateLine: "・{publicName}（{routeLabel}）{officialUrl}",
    careLabels: Object.freeze({
      gastric_screening: "胃がん検診",
      colorectal_screening: "大腸がん検診",
      brain_dock: "脳ドック",
      dental: "歯科検診",
      haircut: "散髪",
      clinic: "通院",
    }),
    emoji: Object.freeze({
      gastric_screening: "🩺",
      colorectal_screening: "🩺",
      brain_dock: "🧠",
      dental: "🦷",
      haircut: "💈",
      clinic: "🏥",
    }),
    routeLabels: Object.freeze({
      web: "ネット予約",
      email: "メール予約",
      walk_in: "予約不要",
      phone_only: "電話のみ",
      unavailable: "予約経路不明",
    }),
  }),
});

// H2 ORG-diet — the lunch closed question and the intervention line (spec §10 NEXT HORIZON row H2,
// tone from §9.11). **This copy is Dais-editable**（No-human-loop 例外3）: edit the strings here and
// the implementation follows; diet-question.js / diet-nudge.js never write copy inline.
//
// Two rules the copy itself must carry, not just the code around it:
//   RECORD, NEVER JUDGE (H2 ⑥) — 診断・カロリー計算はしない. The question asks what happened; the
//     nudge states a count and names one place. Neither ever says a choice was good or bad, and
//     neither uses 健康/カロリー/栄養 vocabulary. That restraint is the whole difference between an
//     organ the user keeps and a diet app they delete.
//   ONE DIRECTION (§9.11) — the nudge asks for nothing. One 用件, one leading emoji, no question
//     mark, no buttons. The user does not owe us a reply for having eaten a burger.
//
// The question's four labels are read back out of `text` by the keyboard builder, so the sentence
// the user reads and the buttons they tap can never drift apart.
const DIET_STRINGS = Object.freeze({
  ja: Object.freeze({
    lunchQuestion: Object.freeze({
      text: "今日のお昼は?\n［定食・野菜系］［麺・丼］［バーガー・ファスト］［食べてない］",
      teishokuButton: "定食・野菜系",
      menButton: "麺・丼",
      fastButton: "バーガー・ファスト",
      skipButton: "食べてない",
      // CB-1 (§10.0-15 ③): a second tap is never silent. {choice} is the label already on file —
      // what was RECORDED, not what was just tapped.
      alreadyAnswered: "今日のお昼はもう記録済みです（{choice}）。",
      // A tap on a question from an earlier day. The keyboard is stripped and this says why: a
      // button that silently does nothing reads as a broken bot.
      expired: "この質問は期限切れです。",
    }),
    // The intervention. `withoutVenue` is not a fallback to be embarrassed about: §9.5 says an
    // honest failure beats a fabricated success, so when Places finds nothing we say we found
    // nothing rather than dropping the sentence or inventing a shop.
    //
    // TWO venue variants, and which one is used is a matter of fact rather than tone: 「職場の近く」
    // may only be said when the shop was found around a WORK anchor. deriveAnchors needs three
    // repeats of the same calendar location before it will call anything a workplace, which almost
    // never holds on the short event slice the nudge runs on — so the home-anchored fallback is the
    // COMMON case and it says 「近くだと」. Claiming the office when we searched near their flat is a
    // small lie that makes every other sentence in the message less believable.
    lunchNudge: Object.freeze({
      withVenue: "🍚 直近2週間のお昼は{sampleCount}回中{fastCount}回がバーガー・ファストでした。職場の近くだと{venueName}（{venueAddress}）があります。",
      withVenueNearby: "🍚 直近2週間のお昼は{sampleCount}回中{fastCount}回がバーガー・ファストでした。近くだと{venueName}（{venueAddress}）があります。",
      withoutVenue: "🍚 直近2週間のお昼は{sampleCount}回中{fastCount}回がバーガー・ファストでした。近くの定食・サラダのお店は今日は見つけられませんでした。",
    }),
  }),
});

// H4 ORG-precepts — the bedtime closed question and the weekly mirror (spec §10 NEXT HORIZON row H4,
// tone from §9.11). **This copy is Dais-editable**（No-human-loop 例外3）: edit the strings here and
// the implementation follows; precepts-question.js / precepts-mirror.js never write copy inline.
//
// THE THREE THINGS THIS COPY MAY NEVER DO, because the templates are the only place they can be
// prevented — a generator would eventually produce all three:
//   NO RELIGIOUS VOCABULARY (H4 ①). The five choices are the 五戒 translated into ordinary Japanese:
//     嘘 / きつく当たった / 時間を奪った / 飲酒・衝動 / 穏やかだった. The words 戒・罪・業・懺悔・
//     煩悩・悟り・修行・善・悪 appear nowhere, in any message. A person looking at their own day does
//     not need to be told which tradition the list came from.
//   NO SCORE (H4 ③). The mirror states counts. It never totals them, never grades a week, never
//     compares this week to last week, never says 改善/悪化/点数/評価. A count is a fact the user can
//     check against their own memory; a score is a verdict about a person.
//   NO ADVICE (H4 ③). 説教・評価・スコア化禁止 in the spec's own words. The mirror ends after the
//     fact and (when one exists) the context. It never says 〜しましょう / 〜すべき / おすすめ, and it
//     asks for nothing — no question mark, no buttons, nothing owed back (§9.11 ④).
//
// The mirror is assembled from `countItem` joined by `countSeparator` into one of the four whole-
// message templates. Which template is used is a matter of FACT (see precepts-mirror.js's pattern
// rule), never of tone: the weekday sentence may only be said when the same weekday really did
// repeat, and the busy sentence only when those days really did carry three or more events.
//
// AND THE BUSY SENTENCES SAY WHAT WAS CHECKED. H4 ③'s example wording is 「連続MTGの後」 — back-to-
// back meetings — but the rule behind it counts events per day and measures how late the last one
// ran; it never checks whether any two of them touch. Three scattered half-hour calls would have
// been announced as a solid block of meetings. So both templates say 「予定が3件以上あった…の後」,
// which is exactly the evidence that exists. §9.5: the honest statement, not the comfortable one.
const PRECEPTS_STRINGS = Object.freeze({
  ja: Object.freeze({
    nightQuestion: Object.freeze({
      text: "今日、心に引っかかったことは?\n［嘘をついた］［きつく当たった］［時間を奪った/遅刻］［飲酒/衝動］［なし・穏やかだった］",
      lieButton: "嘘をついた",
      harshButton: "きつく当たった",
      timeButton: "時間を奪った/遅刻",
      impulseButton: "飲酒/衝動",
      calmButton: "なし・穏やかだった",
      // CB-1 (§10.0-15 ③): a second tap is never silent. {choice} is the label already on file —
      // what was RECORDED, not what was just tapped.
      alreadyAnswered: "今日の記録はもう残っています（{choice}）。",
      // A tap on a question from an earlier night. The keyboard is stripped and this says why: a
      // button that silently does nothing reads as a broken bot.
      expired: "この質問は期限切れです。",
    }),
    weeklyMirror: Object.freeze({
      facts: "🌙 最近4週間の記録です。{counts}。",
      weekday: "🌙 最近4週間の記録です。{counts}。{patternCount}回とも{weekday}曜でした。",
      busy: "🌙 最近4週間の記録です。{counts}。{patternCount}回とも予定が3件以上あった日の後でした。",
      weekdayBusy: "🌙 最近4週間の記録です。{counts}。{patternCount}回とも予定が3件以上あった{weekday}曜の後でした。",
      countItem: "「{label}」が{count}回",
      countSeparator: "、",
    }),
  }),
});

const RELATIONS_STRINGS = Object.freeze({
  ja: Object.freeze({
    suggestion: "🌿 カレンダーでは、{name}との1対1の時間が{daysSince}日空いています。いつもの間隔は約{intervalDays}日でした。今週、10分だけ連絡する余白があります。",
  }),
});

function formatRelationSuggestion(candidate) {
  const values = {
    name: String(candidate && candidate.label || ""),
    daysSince: Math.max(0, Math.round(Number(candidate && candidate.daysSince) || 0)),
    intervalDays: Math.max(0, Math.round(Number(candidate && candidate.personalIntervalDays) || 0)),
  };
  return RELATIONS_STRINGS.ja.suggestion.replace(/\{(\w+)\}/g, (_match, key) => String(values[key]));
}

// Elapsed time in the units §9.11 speaks: 「4ヶ月」「6週間」「10日」. Deterministic thresholds, no
// calendar arithmetic — the input is already a day count the detector measured.
function elapsedLabel(days) {
  const d = Math.max(0, Math.round(Number(days) || 0));
  if (d >= 60) return `${Math.round(d / 30)}ヶ月`;
  if (d >= 14) return `${Math.round(d / 7)}週間`;
  return `${d}日`;
}

const WEEKDAY_JA = ["日", "月", "火", "水", "木", "金", "土"];

// 「木曜18:00」 from an ISO string, read in the string's OWN offset (the provider's local clock is the
// clock the user will show up on). Returns "" for anything unparseable rather than a wrong time.
function slotLabel(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(String(iso || ""));
  if (!match) return "";
  const [, y, mo, d, hh, mm] = match;
  const weekday = WEEKDAY_JA[new Date(Date.UTC(Number(y), Number(mo) - 1, Number(d))).getUTCDay()];
  return `${weekday}曜${hh}:${mm}`;
}

function fill(template, values) {
  return String(template).replace(/\{(\w+)\}/g, (match, key) =>
    (key in values ? String(values[key]) : match));
}

// The single renderer for every 11c booking outcome. `outcome` is the executor's own verdict, so a
// possibly_booked can never accidentally render as a booking.
function formatCareBookingReport(input = {}) {
  const strings = PHYSICAL_STRINGS.ja;
  const careType = String(input.careType || "");
  const emoji = strings.emoji[careType] || "";
  const careLabel = strings.careLabels[careType] || careType;

  if (input.outcome === "booked") {
    const usual = input.usualProvider === true;
    return fill(usual ? strings.bookedUsual : strings.booked, {
      emoji,
      careLabel,
      sinceLabel: elapsedLabel(input.sinceDays),
      providerName: input.providerName || "",
      slotLabel: slotLabel(input.slotIso),
      // Strictly true-only: anything other than a proven write says the entry could not be made.
      calendarLine: input.calendarEventCreated === true ? strings.calendarAdded : strings.calendarMissing,
    });
  }
  if (input.outcome === "possibly_booked") {
    return fill(strings.bookingUncertain, {
      emoji,
      providerName: input.providerName || "",
      slotLabel: slotLabel(input.slotIso),
      reservationUrl: input.reservationUrl || "",
    });
  }
  const candidateLines = (Array.isArray(input.candidates) ? input.candidates : [])
    .map((candidate) => fill(strings.candidateLine, {
      publicName: candidate.public_name || "",
      routeLabel: strings.routeLabels[candidate.reservation_route] || strings.routeLabels.unavailable,
      officialUrl: candidate.official_url || "",
    }))
    .join("\n");
  return fill(strings.bookingFailed, {
    emoji,
    careLabel,
    reason: input.reason || "",
    candidateLines,
  });
}

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

module.exports = {
  DAILY_STRINGS,
  DIET_STRINGS,
  DISCOVERY_STRINGS,
  FINANCIAL_STRINGS,
  PHYSICAL_STRINGS,
  PRECEPTS_STRINGS,
  RELATIONS_STRINGS,
  WEEKDAY_JA,
  elapsedLabel,
  formatCareBookingReport,
  formatRelationSuggestion,
  formatTravelAutofillMessage,
  slotLabel,
};
