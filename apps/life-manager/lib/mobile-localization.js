"use strict";

const { MobileError, normalizeLocale } = require("./mobile-utils.js");

const CJK_RE = /[\u3040-\u30ff\u3400-\u9fff]/u;
const ASCII_WORD_RE = /\b[A-Za-z]{2,}\b/gu;
const JA_ALLOWED_WORDS = new Set(["IC", "JR", "API", "APNs", "Google", "Life", "Manager"]);
const TRANSLITERATIONS = new Map([
  ["渋谷駅", "Shibuya Station"], ["渋谷", "Shibuya"], ["六本木", "Roppongi"], ["東京駅", "Tokyo Station"],
  ["新宿駅", "Shinjuku Station"], ["都営大江戸線", "Toei Oedo Line"], ["大門", "Daimon"],
]);

function assertLocalizedText(locale, text, allowlist = []) {
  const active = normalizeLocale(locale);
  const value = String(text || "");
  if (active === "en" && CJK_RE.test(value)) throw new MobileError("mixed_locale", "Generated English text contains non-English script.");
  if (active === "ja") {
    const allowed = new Set([...JA_ALLOWED_WORDS, ...allowlist]);
    const words = value.match(ASCII_WORD_RE) || [];
    if (words.some((word) => !allowed.has(word))) throw new MobileError("mixed_locale", "Generated Japanese text contains untranslated English prose.");
  }
  return true;
}

function nameParts(value) {
  if (value && typeof value === "object") {
    const displayNames = value.displayNames || value.display_names || value.names;
    if (displayNames && typeof displayNames === "object") return displayNames;
    if (value.en || value.ja) return { en: value.en, ja: value.ja };
    if (typeof value.displayName === "string") return { raw: value.displayName };
  }
  return { raw: value };
}

function projectLocalizedRouteName(value, locale) {
  const active = normalizeLocale(locale);
  const parts = nameParts(value);
  if (typeof parts[active] === "string" && parts[active].trim()) return parts[active].trim();
  if (active === "en" && typeof parts.raw === "string" && !CJK_RE.test(parts.raw)) return parts.raw.trim();
  if (active === "en" && typeof parts.ja === "string" && TRANSLITERATIONS.has(parts.ja.trim())) return TRANSLITERATIONS.get(parts.ja.trim());
  if (active === "ja" && typeof parts.raw === "string" && CJK_RE.test(parts.raw)) return parts.raw.trim();
  throw new MobileError("localization_unavailable", "A provider navigation name could not be localized.", 422);
}

function routeValue(route, locale) {
  if (!route) return null;
  const output = { ...route };
  for (const key of ["origin", "destination"]) {
    if (route[key]) output[key] = { ...route[key], displayName: projectLocalizedRouteName(route[key], locale) };
  }
  if (Array.isArray(route.steps)) {
    output.steps = route.steps.map((step) => {
      const item = { ...step };
      for (const key of ["from", "to", "service", "headsign"]) {
        if (step[key] !== null && step[key] !== undefined) item[key] = projectLocalizedRouteName(step[key], locale);
        else item[key] = null;
      }
      if (step.instruction && typeof step.instruction === "object") item.instruction = projectLocalizedRouteName(step.instruction, locale);
      if (typeof item.instruction !== "string") item.instruction = String(item.instruction || "");
      for (const unsupported of ["entrance", "exit", "optimalCar", "crowding"]) delete item[unsupported];
      return item;
    });
  }
  if (locale === "ja") {
    if (output.provider === "transit") output.providerAttribution = "交通情報（非公式）";
    else if (output.provider === "google") output.providerAttribution = "Google経路情報";
  }
  return output;
}

function formatTime(value, locale, timezone) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale === "ja" ? "ja-JP" : "en-US", { timeZone: timezone || "UTC", hour: "numeric", minute: "2-digit" }).format(date);
}

function bufferMinutes(value) {
  const seconds = Number(value);
  return Number.isFinite(seconds) ? Math.max(0, Math.round(seconds / 60)) : 0;
}

const ACTION_LABELS = {
  en: { reply: "Reply", refresh: "Refresh", show_route: "Show full route", call: "Call me now", upgrade: "Upgrade", restore: "Restore purchases", delete: "Delete account" },
  ja: { reply: "返信", refresh: "更新", show_route: "経路全体を表示", call: "今すぐ電話する", upgrade: "アップグレード", restore: "購入を復元", delete: "アカウントを削除" },
};

const QUESTION_PROMPTS = {
  en: {
    calendar: "Connect Google Calendar to analyze your next event.",
    name: "What should Life Manager call you?",
    origin: "Where will you be leaving from?",
    destination: "Where will this event take place?",
  },
  ja: {
    calendar: "次の予定を分析するため、Googleカレンダーを接続してください。",
    name: "Life Managerでは何とお呼びすればよいですか？",
    origin: "出発地点を教えてください。",
    destination: "予定の場所を教えてください。",
  },
};

const UNAVAILABLE_REASONS = {
  en: {
    missing_origin: "the starting point is missing",
    missing_destination: "the destination is missing",
    provider_unavailable: "the route provider is unavailable",
    no_journey: "the provider returned no journey",
    timeout: "the route provider timed out",
    localization_unavailable: "the navigation names could not be localized",
  },
  ja: {
    missing_origin: "出発地点がありません",
    missing_destination: "目的地がありません",
    provider_unavailable: "経路プロバイダーを利用できません",
    no_journey: "プロバイダーから経路が返りませんでした",
    timeout: "経路プロバイダーがタイムアウトしました",
    localization_unavailable: "ナビゲーション名を翻訳できませんでした",
  },
};

function action(id, locale) {
  return { id, label: ACTION_LABELS[locale][id] || id };
}

function projectQuestion(value, locale) {
  if (!value) return null;
  const active = normalizeLocale(locale);
  const prompt = QUESTION_PROMPTS[active][value.type];
  if (prompt) return { ...value, prompt };
  if (active === "en") return { ...value };
  if (typeof value.prompt === "string") assertLocalizedText(active, value.prompt);
  return { ...value };
}

function projectSemanticMessage(row, locale = "en") {
  const active = normalizeLocale(locale);
  const route = routeValue(row.route || null, active);
  const args = row.args || {};
  const timezone = (route && route.timezone) || "UTC";
  let type = row.type || "system";
  let text;
  let question = projectQuestion(row.question || null, active);
  let actions;
  switch (row.key) {
    case "chat.route_ready":
      type = "route";
      text = active === "ja"
        ? `次の予定を確認しました。${formatTime(route && route.leaveAt, active, timezone)}に出発すると、${bufferMinutes(route && route.bufferSeconds)}分の余裕を持って到着できます。`
        : `Your next event is ready. Leave by ${formatTime(route && route.leaveAt, active, timezone)} to arrive with ${bufferMinutes(route && route.bufferSeconds)} minutes of buffer.`;
      actions = [action("show_route", active), action("refresh", active)];
      break;
    case "chat.needs_information":
      type = "question";
      if (question && question.type === "destination") {
        text = active === "ja" ? "経路を計算するため、予定の場所を教えてください。" : "I need the event destination before I can calculate the route.";
      } else if (question && question.type === "calendar") {
        text = active === "ja" ? "経路を計算するには、Googleカレンダーを接続してください。" : "Connect Google Calendar before I can analyze your next event.";
      } else if (question && question.type === "name") {
        text = active === "ja" ? "分析を始める前に、お名前を教えてください。" : "Tell me your name before I analyze your next event.";
      } else {
        text = active === "ja" ? "経路を計算するため、出発地点を教えてください。" : "I need your starting point before I can calculate the route.";
      }
      actions = [action("reply", active), action("refresh", active)];
      break;
    case "chat.no_upcoming_event":
      type = "system";
      text = active === "ja" ? "経路が必要な予定はありません。" : "There are no upcoming events that need a route.";
      actions = [action("refresh", active)];
      break;
    case "chat.route_unavailable":
      type = "route_unavailable";
      {
        const reasonKey = typeof args.reason === "string" ? args.reason : "provider_unavailable";
        const reason = UNAVAILABLE_REASONS[active][reasonKey] || UNAVAILABLE_REASONS[active].provider_unavailable;
        text = active === "ja" ? `経路を利用できません。理由：${reason}。` : `The route is unavailable because ${reason}. Try again.`;
      }
      actions = [action("refresh", active)];
      break;
    case "chat.failed":
      type = "system";
      text = active === "ja" ? "次の予定を分析できませんでした。もう一度お試しください。" : "I could not analyze your next event. Try again.";
      actions = [action("refresh", active)];
      break;
    case "chat.welcome":
    default:
      type = row.type || "system";
      text = active === "ja" ? "チャットを利用できます。" : "Your Life Manager chat is ready.";
      actions = [action("refresh", active)];
      break;
  }
  assertLocalizedText(active, text);
  if (route && route.providerAttribution) assertLocalizedText(active, route.providerAttribution, ["Google", "Transit", "API"]);
  return {
    id: row.id,
    cursor: row.cursor,
    createdAt: row.createdAt || row.created_at,
    locale: active,
    type,
    text,
    userContent: row.userContent || row.user_content || { eventTitle: null, eventLocation: null },
    question,
    route,
    actions,
  };
}

module.exports = { CJK_RE, assertLocalizedText, projectLocalizedRouteName, projectSemanticMessage, routeValue, formatTime };
