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

function projectRouteName(value, locale) {
  const active = normalizeLocale(locale);
  const parts = nameParts(value);
  if (typeof parts[active] === "string" && parts[active].trim()) return { value: parts[active].trim(), source: "provider" };
  if (active === "en" && typeof parts.raw === "string" && !CJK_RE.test(parts.raw)) return { value: parts.raw.trim(), source: "provider" };
  if (active === "en" && typeof parts.raw === "string" && TRANSLITERATIONS.has(parts.raw.trim())) return { value: TRANSLITERATIONS.get(parts.raw.trim()), source: "transliteration" };
  if (active === "en" && typeof parts.ja === "string" && TRANSLITERATIONS.has(parts.ja.trim())) return { value: TRANSLITERATIONS.get(parts.ja.trim()), source: "transliteration" };
  if (active === "ja" && typeof parts.raw === "string" && CJK_RE.test(parts.raw)) return { value: parts.raw.trim(), source: "provider" };
  throw new MobileError("localization_unavailable", "A provider navigation name could not be localized.", 422);
}

function projectLocalizedRouteName(value, locale) {
  return projectRouteName(value, locale).value;
}

function routeValue(route, locale) {
  if (!route) return null;
  const active = normalizeLocale(locale);
  const provider = route.provider || null;
  const providerAttribution = Object.hasOwn(route, "providerAttribution")
    ? route.providerAttribution
    : (Object.hasOwn(route, "provider_attribution") ? route.provider_attribution : null);
  const output = {
    status: route.status || "route_ready",
    provider,
    providerAttribution,
    computedAt: route.computedAt || route.computed_at || null,
    timezone: route.timezone || null,
    eventId: route.eventId || route.event_id || null,
    origin: null,
    destination: null,
    leaveAt: route.leaveAt || route.leave_at || null,
    arriveAt: route.arriveAt || route.arrive_at || null,
    durationSeconds: route.durationSeconds === undefined && route.duration_secs === undefined
      ? null : Number(route.durationSeconds ?? route.duration_secs),
    bufferSeconds: route.bufferSeconds === undefined && route.buffer_secs === undefined
      ? null : Number(route.bufferSeconds ?? route.buffer_secs),
    transferCount: route.transferCount === undefined && route.transfer_count === undefined
      ? null : Number(route.transferCount ?? route.transfer_count),
    fare: route.fare === undefined ? null : route.fare,
    geometry: route.geometry === undefined ? null : route.geometry,
    steps: [],
  };
  let usedTransliteration = false;
  for (const unsupported of ["entrance", "exit", "optimalCar", "crowding"]) delete output[unsupported];
  for (const key of ["origin", "destination"]) {
    if (route[key] !== null && route[key] !== undefined) {
      const projected = projectRouteName(route[key], active);
      usedTransliteration ||= projected.source === "transliteration";
      const userContent = typeof route[key] === "object"
        ? (route[key].userContent ?? route[key].user_content ?? null)
        : route[key];
      output[key] = { displayName: projected.value, userContent };
    }
  }
  if (Array.isArray(route.steps)) {
    output.steps = route.steps.map((step, index) => {
      const item = {
        sequence: Number.isSafeInteger(step.sequence) ? step.sequence : index + 1,
        mode: String(step.mode || step.kind || "other"),
        instruction: null,
        from: null,
        to: null,
        service: null,
        headsign: null,
        platform: step.platform === undefined ? null : step.platform,
        departAt: step.departAt || step.depart_at || null,
        arriveAt: step.arriveAt || step.arrive_at || null,
        durationSeconds: step.durationSeconds === undefined && step.duration_secs === undefined
          ? null
          : Number(step.durationSeconds ?? step.duration_secs),
      };
      for (const key of ["from", "to", "service", "headsign"]) {
        if (step[key] !== null && step[key] !== undefined) {
          const projected = projectRouteName(step[key], active);
          usedTransliteration ||= projected.source === "transliteration";
          item[key] = projected.value;
        }
        else item[key] = null;
      }
      if (step.instruction !== null && step.instruction !== undefined) {
        const projected = projectRouteName(step.instruction, active);
        usedTransliteration ||= projected.source === "transliteration";
        item.instruction = projected.value;
      } else {
        item.instruction = null;
      }
      for (const unsupported of ["entrance", "exit", "optimalCar", "crowding"]) delete item[unsupported];
      return item;
    });
  }
  for (const [key, aliases] of [["accessWalkSeconds", ["access_walk_seconds"]], ["egressWalkSeconds", ["egress_walk_seconds"]], ["freshness", ["sourceFreshness", "source_freshness"]]]) {
    const source = [key, ...aliases].find((candidate) => Object.hasOwn(route, candidate));
    if (source) output[key] = route[source] === undefined ? null : route[source];
  }
  if (route.bufferReason !== undefined) output.bufferReason = route.bufferReason;
  if (active === "ja") {
    if (provider === "transit" && output.providerAttribution !== null) output.providerAttribution = "交通情報（非公式）";
    else if (provider === "google" && output.providerAttribution !== null) output.providerAttribution = "Google経路情報";
  }
  if (usedTransliteration) output.localization_source = "transliteration";
  return output;
}

function formatTime(value, locale, timezone) {
  if (!timezone) throw new MobileError("route_timezone_required", "The Calendar event timezone is required to format route times.");
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  try {
    return new Intl.DateTimeFormat(locale === "ja" ? "ja-JP" : "en-US", { timeZone: timezone, hour: "numeric", minute: "2-digit" }).format(date);
  } catch {
    throw new MobileError("route_timezone_invalid", "The Calendar event timezone is not a valid IANA timezone.");
  }
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

const TRAVEL_BLOCK_FAILURE_REASONS = {
  en: {
    provider_write_failed: "the Calendar write failed",
    provider_readback_failed: "the Calendar result could not be verified",
    claim_pending: "another Calendar update is still in progress",
    budget_denied: "the provider budget is unavailable",
    analysis_conflict: "the route data changed before the Calendar update",
    provider_collision: "the Calendar event ID is already in use",
  },
  ja: {
    provider_write_failed: "カレンダーへの書き込みに失敗しました",
    provider_readback_failed: "カレンダーの結果を確認できませんでした",
    claim_pending: "別のカレンダー更新が進行中です",
    budget_denied: "プロバイダー予算を利用できません",
    analysis_conflict: "カレンダー更新前に経路情報が変わりました",
    provider_collision: "カレンダーの予定IDがすでに使われています",
  },
};

function action(id, locale) {
  return { id, label: ACTION_LABELS[locale][id] || id };
}

function projectQuestion(value, locale) {
  if (!value) return null;
  const active = normalizeLocale(locale);
  const prompt = QUESTION_PROMPTS[active][value.type];
  const projectedPrompt = prompt || (typeof value.prompt === "string" ? value.prompt : null);
  if (typeof projectedPrompt === "string") assertLocalizedText(active, projectedPrompt);
  return {
    id: value.id || null,
    prompt: projectedPrompt,
  };
}

function projectUserContent(value) {
  const source = value && typeof value === "object" ? value : {};
  return {
    eventTitle: source.eventTitle === undefined ? null : source.eventTitle,
    eventLocation: source.eventLocation === undefined ? null : source.eventLocation,
  };
}

function projectSemanticMessage(row, locale = "en") {
  const active = normalizeLocale(locale);
  const route = routeValue(row.route || null, active);
  const args = row.args || {};
  const timezone = (route && route.timezone) || "UTC";
  let type = row.type || "system";
  let text;
  const questionSource = row.question || null;
  let question = projectQuestion(questionSource, active);
  let actions;
  switch (row.key) {
    case "chat.route_ready":
      type = "route";
      if (!route || !route.timezone) throw new MobileError("route_timezone_required", "The Calendar event timezone is required for route messaging.");
      const rawEventTitle = row.userContent && typeof row.userContent.eventTitle === "string" ? row.userContent.eventTitle.trim() : "";
      const eventTitle = (active === "en" && rawEventTitle && !CJK_RE.test(rawEventTitle))
        || (active === "ja" && rawEventTitle && CJK_RE.test(rawEventTitle)) ? rawEventTitle : "";
      text = active === "ja"
        ? `${eventTitle ? `次の予定は${eventTitle}です。` : "次の予定を確認しました。"}${formatTime(route && route.leaveAt, active, timezone)}に出発すると、${bufferMinutes(route && route.bufferSeconds)}分の余裕を持って到着できます。`
        : `${eventTitle ? `Your next event is ${eventTitle}.` : "Your next event is ready."} Leave by ${formatTime(route && route.leaveAt, active, timezone)} to arrive with ${bufferMinutes(route && route.bufferSeconds)} minutes of buffer.`;
      actions = [action("show_route", active), action("refresh", active)];
      break;
    case "chat.needs_information":
      type = "question";
      if (questionSource && questionSource.type === "destination") {
        text = active === "ja" ? "経路を計算するため、予定の場所を教えてください。" : "I need the event destination before I can calculate the route.";
      } else if (questionSource && questionSource.type === "calendar") {
        text = active === "ja" ? "経路を計算するには、Googleカレンダーを接続してください。" : "Connect Google Calendar before I can analyze your next event.";
      } else if (questionSource && questionSource.type === "name") {
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
    case "chat.travel_block_confirmed":
      type = "system";
      text = active === "ja"
        ? (args.status === "existing" ? "移動時間はカレンダーに登録済みで、確認できました。" : "移動時間をカレンダーに追加し、確認できました。")
        : (args.status === "existing" ? "Travel time was already on your Calendar and was verified." : "Travel time was added to your Calendar and verified.");
      actions = [action("refresh", active)];
      break;
    case "chat.travel_block_not_added":
      type = "system";
      {
        const reasonKey = typeof args.reason === "string" ? args.reason : "provider_write_failed";
        const reason = TRAVEL_BLOCK_FAILURE_REASONS[active][reasonKey] || TRAVEL_BLOCK_FAILURE_REASONS[active].provider_write_failed;
        text = active === "ja"
          ? `移動時間をカレンダーに追加できませんでした。理由：${reason}。もう一度お試しください。`
          : `Travel time was not added to your Calendar because ${reason}. Try again.`;
      }
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
  const kind = type === "route_unavailable" ? "error" : type;
  const projected = {
    id: row.id,
    cursor: row.cursor,
    createdAt: row.createdAt || row.created_at,
    locale: active,
    type,
    text,
    userContent: projectUserContent(row.userContent || row.user_content),
    question,
    route,
    actions,
  };
  // The native client uses semantic IDs only for the new travel receipts. Keep
  // the existing message shape unchanged for the frozen Gate 3 fixtures.
  if (row.key === "chat.travel_block_confirmed" || row.key === "chat.travel_block_not_added") projected.semanticKey = row.key;
  return projected;
}

module.exports = { CJK_RE, assertLocalizedText, projectLocalizedRouteName, projectRouteName, projectSemanticMessage, routeValue, formatTime };
