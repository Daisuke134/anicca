"use strict";

const { CFO_STRINGS } = require("./i18n.js");
const { tgCall } = require("./telegram.js");

const STATES = new Set(["complete", "partial", "recovered", "action_required"]);
const VIEWS = new Set(["summary", "accounts", "accuracy", "why"]);
const STATUSES = new Set(["fresh", "stale", "unavailable"]);
const EVIDENCE = Object.freeze({
  provider_billed: { ja: "確定", en: "Confirmed" },
  provider_reported: { ja: "実測", en: "Measured" },
  locally_estimated: { ja: "推定", en: "Estimated" },
  unavailable: { ja: "不明", en: "Unknown" },
});
const ROOT_KEYS = new Set(["schemaVersion", "reportingDate", "revision", "state", "currency", "totals", "sources", "excluded", "repair", "action"]);
const TOTAL_KEYS = new Set(["assetsMinor", "liabilitiesMinor", "netWorthMinor", "changeMinor"]);
const SOURCE_KEYS = new Set(["sourceId", "label", "status", "asOf", "amountMinor", "verificationStatus"]);
const EXCLUDED_KEYS = new Set(["label", "reason"]);
const REPAIR_KEYS = new Set(["sourceLabel", "freshReread", "reconciled"]);
const ACTION_KEYS = new Set(["kind", "sourceLabel", "retryLabel", "nextRetryAt"]); const ACTION_LABELS = Object.freeze({ reconsent: "接続後に自動再確認", provider_outage: "30分後に自動再確認" }); const RFC3339 = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;
const BUTTONS = Object.freeze({
  summary: [["accounts", "口座を見る", "View accounts"], ["accuracy", "正確さを見る", "View accuracy"]],
  accounts: [["summary", "概要に戻る", "Back to summary"], ["accuracy", "正確さを見る", "View accuracy"]],
  accuracy: [["summary", "概要に戻る", "Back to summary"], ["why", "なぜこの金額？", "Why this amount?"]],
  why: [["summary", "概要に戻る", "Back to summary"]],
});
const CALLBACK = /^cfo:(summary|accounts|accuracy|why):(\d{8}):([1-9]\d*)$/;
const RETRY_TOAST = "読み込めませんでした。もう一度お試しください";

function fail(reason) { throw new Error(`cfo_telegram_invalid:${reason}`); }
function plain(value) { return value !== null && typeof value === "object" && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype; }
function sanitize(snapshot) {
  if (!plain(snapshot)) return snapshot;
  const strip = (value) => Object.fromEntries(Object.entries(value).filter(([key]) => !/account|raw|credential|token|secret|password|cookie|oauth/i.test(key)));
  const safe = strip(snapshot);
  if (Array.isArray(snapshot.sources)) safe.sources = snapshot.sources.map((source) => plain(source) ? strip(source) : source);
  return safe;
}
function exact(value, allowed, required = []) {
  if (!plain(value)) fail("invalid_object");
  if (Object.keys(value).some((key) => !allowed.has(key))) fail("unknown_key");
  if (required.some((key) => !Object.prototype.hasOwnProperty.call(value, key))) fail("missing_key");
}
function label(value) { if (typeof value !== "string" || value.length === 0) fail("invalid_label"); }
function safeAmount(value) { return value === null || Number.isSafeInteger(value); }
function date(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) fail("invalid_reporting_date");
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value) fail("invalid_reporting_date");
}
function timestamp(value) {
  const m = typeof value === "string" && RFC3339.exec(value); if (!m) return false; const year = +m[1], month = +m[2], day = +m[3], hour = +m[4], minute = +m[5], second = +m[6], zone = m[8], zh = zone === "Z" ? 0 : +zone.slice(1, 3), zm = zone === "Z" ? 0 : +zone.slice(4), local = new Date(0), end = new Date(0), fraction = m[7] ? +(m[7].slice(1) + "000").slice(0, 3) : 0; local.setUTCFullYear(year, month - 1, day); local.setUTCHours(hour, minute, second, fraction); end.setUTCFullYear(year, month, 0); if (month < 1 || month > 12 || day < 1 || day > end.getUTCDate() || hour > 23 || minute > 59 || second > 59 || zh > 23 || zm > 59) return false; const offset = zone === "Z" ? 0 : (zone[0] === "-" ? -1 : 1) * (zh * 60 + zm), ms = local.getTime() - offset * 60000; return Number.isFinite(ms) && Date.parse(value) === ms;
}
function escapeHtml(value) { return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
function formatAmount(locale, value) {
  if (value === null) return CFO_STRINGS[locale].unknown;
  const number = new Intl.NumberFormat(locale === "ja" ? "ja-JP" : "en-US").format(value);
  return locale === "ja" ? `¥${number}` : `JPY ${number}`;
}
function formatChange(locale, value) {
  if (value === null) return CFO_STRINGS[locale].unknown;
  return `${value >= 0 ? "+" : "-"}${formatAmount(locale, Math.abs(value))}`;
}
function validateSnapshot(snapshot) {
  exact(snapshot, ROOT_KEYS, [...ROOT_KEYS]);
  if (snapshot.schemaVersion !== 1) fail("invalid_schema_version");
  date(snapshot.reportingDate);
  if (!Number.isSafeInteger(snapshot.revision) || snapshot.revision < 1) fail("invalid_revision");
  if (!STATES.has(snapshot.state)) fail("unsupported_state");
  if (snapshot.currency !== "JPY") fail("unsupported_currency");
  exact(snapshot.totals, TOTAL_KEYS, [...TOTAL_KEYS]);
  if (Object.values(snapshot.totals).some((value) => !safeAmount(value))) fail("invalid_amount");
  if (!Array.isArray(snapshot.sources) || snapshot.sources.length === 0) fail("missing_sources");
  snapshot.sources.forEach((source) => {
    exact(source, SOURCE_KEYS, [...SOURCE_KEYS]);
    [source.sourceId, source.label, source.asOf].forEach(label);
    if (!STATUSES.has(source.status) || !Object.prototype.hasOwnProperty.call(EVIDENCE, source.verificationStatus)) fail("invalid_source");
    if (!safeAmount(source.amountMinor)) fail("invalid_amount");
    if (source.amountMinor !== null && ["locally_estimated", "unavailable"].includes(source.verificationStatus)) fail("unconfirmed_amount");
    if (source.status === "unavailable" && (source.amountMinor !== null || source.verificationStatus !== "unavailable")) fail("inconsistent_source");
    if (source.status === "fresh" && (source.amountMinor === null || source.verificationStatus === "unavailable")) fail("inconsistent_source");
  });
  if (!Array.isArray(snapshot.excluded)) fail("invalid_excluded");
  snapshot.excluded.forEach((item) => { exact(item, EXCLUDED_KEYS, ["label"]); label(item.label); if (item.reason !== undefined) label(item.reason); });
  if (snapshot.repair !== null) {
    exact(snapshot.repair, REPAIR_KEYS, [...REPAIR_KEYS]);
    label(snapshot.repair.sourceLabel);
    if (typeof snapshot.repair.freshReread !== "boolean" || typeof snapshot.repair.reconciled !== "boolean") fail("invalid_repair");
  }
  if (snapshot.action !== null) {
    exact(snapshot.action, ACTION_KEYS, [...ACTION_KEYS]);
    if (!Object.prototype.hasOwnProperty.call(ACTION_LABELS, snapshot.action.kind) || snapshot.action.sourceLabel !== "Moneytree" || snapshot.action.retryLabel !== ACTION_LABELS[snapshot.action.kind] || !timestamp(snapshot.action.nextRetryAt)) fail("invalid_action");
  }
  const { state, totals, sources, excluded, repair, action } = snapshot;
  if (["complete", "partial", "recovered"].includes(state) && sources.some((source) => source.status !== "fresh")) fail("source_not_fresh");
  if (state === "recovered" && (!repair || repair.freshReread !== true || repair.reconciled !== true)) fail("recovery_unproven"); if (state === "complete" && [totals.assetsMinor, totals.liabilitiesMinor, totals.netWorthMinor, totals.changeMinor].some((value) => value === null)) fail("inconsistent_totals");
  if (state === "complete" && totals.assetsMinor - totals.liabilitiesMinor !== totals.netWorthMinor) fail("inconsistent_totals");
  if (state === "complete" && excluded.length) fail("inconsistent_state");
  if (["partial", "recovered"].includes(state) && (totals.netWorthMinor !== null || excluded.length === 0)) fail(totals.netWorthMinor === null ? "partial_excluded_required" : "partial_net_worth_forbidden");
  if (state === "action_required" && (totals.netWorthMinor !== null || action === null)) fail(totals.netWorthMinor === null ? "action_required_missing_action" : "action_required_net_worth_forbidden");
  if (state !== "recovered" && repair !== null) fail("inconsistent_repair");
  if (state !== "action_required" && action !== null) fail("inconsistent_action");
  return snapshot;
}
function evidenceLabel(locale, verificationStatus) {
  if (!CFO_STRINGS[locale]) fail("unsupported_locale");
  if (!EVIDENCE[verificationStatus]) fail("unsupported_evidence");
  return EVIDENCE[verificationStatus][locale];
}
function callbackData({ view, reportingDate, revision }) {
  if (!VIEWS.has(view) || !/^\d{4}-\d{2}-\d{2}$/.test(reportingDate) || !Number.isInteger(revision) || revision < 1) fail("callback");
  const value = `cfo:${view}:${reportingDate.replaceAll("-", "")}:${revision}`;
  if (Buffer.byteLength(value, "utf8") > 64) fail("callback_too_long");
  return value;
}
function parseCfoCallback(value) {
  const match = CALLBACK.exec(String(value || ""));
  if (!match) return null;
  const reportingDate = `${match[2].slice(0, 4)}-${match[2].slice(4, 6)}-${match[2].slice(6)}`;
  const revision = Number(match[3]);
  try { date(reportingDate); } catch { return null; }
  if (!Number.isSafeInteger(revision) || revision < 1 || String(revision) !== match[3]) return null;
  return { view: match[1], reportingDate, revision };
}
function nonEmpty(value) { return typeof value === "string" && value.length > 0 && value.trim() === value; }
function positiveMessageId(value) {
  const parsed = typeof value === "number" ? value : (typeof value === "string" && /^[1-9]\d*$/.test(value) ? Number(value) : NaN);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}
function closedFailure() { return Object.freeze({ status: "failed" }); }
async function handleCfoTelegramCallback(input, options = {}) {
  let answerAttempted = false;
  const call = options.tgCall || tgCall;
  const answer = async (text) => {
    if (answerAttempted || !nonEmpty(input && input.telegramToken) || !nonEmpty(input && input.callbackQueryId)) return;
    answerAttempted = true;
    try { await call(input.telegramToken, "answerCallbackQuery", { callback_query_id: input.callbackQueryId, ...(text ? { text } : {}) }); } catch {}
  };
  try {
    const parsed = parseCfoCallback(input && input.data);
    const chatId = input && input.chatId;
    const actorId = input && input.actorId;
    const messageId = positiveMessageId(input && input.messageId);
    if (!parsed || !nonEmpty(input && input.uid) || !nonEmpty(input && input.telegramToken) ||
        !nonEmpty(chatId) || !nonEmpty(actorId) || actorId !== chatId || !messageId ||
        !nonEmpty(input && input.callbackQueryId) || !nonEmpty(options.supaUrl) || !nonEmpty(options.supaKey)) throw new Error("invalid_callback");
    const endpoint = new URL(`${options.supaUrl.replace(/\/$/, "")}/rest/v1/lm_cfo_daily_snapshots`);
    endpoint.searchParams.set("uid", `eq.${input.uid}`);
    endpoint.searchParams.set("reporting_date", `eq.${parsed.reportingDate}`);
    endpoint.searchParams.set("revision", `eq.${parsed.revision}`);
    endpoint.searchParams.set("select", "report_payload");
    endpoint.searchParams.set("limit", "1");
    const response = await (options.fetchImpl || fetch)(endpoint, {
      method: "GET", headers: { apikey: options.supaKey, Authorization: `Bearer ${options.supaKey}` },
    });
    if (!response || response.ok !== true) throw new Error("snapshot_unavailable");
    const rows = await response.json();
    if (!Array.isArray(rows) || rows.length !== 1 || !plain(rows[0]) || !plain(rows[0].report_payload)) throw new Error("snapshot_unavailable");
    const snapshot = rows[0].report_payload;
    if (snapshot.reportingDate !== parsed.reportingDate || snapshot.revision !== parsed.revision) throw new Error("snapshot_mismatch");
    const rendered = renderCfoTelegram({ locale: "ja", view: parsed.view, snapshot });
    const editResponse = await call(input.telegramToken, "editMessageText", {
      chat_id: chatId, message_id: messageId, parse_mode: "HTML", text: rendered.text, ...(rendered.extra || {}),
    });
    if (!editResponse || editResponse.ok !== true) throw new Error("edit_unavailable");
    await answer();
    return Object.freeze({ status: "edited", view: parsed.view, reportingDate: parsed.reportingDate, revision: parsed.revision });
  } catch {
    await answer(RETRY_TOAST);
    return closedFailure();
  }
}
function extra(locale, snapshot, view) {
  return { reply_markup: { inline_keyboard: BUTTONS[view].map(([next, ja, en]) => [{ text: locale === "ja" ? ja : en, callback_data: callbackData({ view: next, reportingDate: snapshot.reportingDate, revision: snapshot.revision }) }]) } };
}
function renderCfoTelegram({ locale, view, snapshot }) {
  if (!CFO_STRINGS[locale]) fail("unsupported_locale");
  if (!VIEWS.has(view)) fail("unsupported_view");
  snapshot = sanitize(snapshot);
  validateSnapshot(snapshot);
  const strings = CFO_STRINGS[locale];
  if (snapshot.state === "action_required" && view === "summary") return { text: `${strings.actionTitle}\n\n${strings.actionBody}\n${strings.actionRetry}`, extra: extra(locale, snapshot, view) };
  const freshness = locale === "ja" ? { fresh: "最新", stale: "古い", unavailable: "不明" } : { fresh: "Fresh", stale: "Stale", unavailable: "Unknown" };
  const marks = locale === "ja" ? { colon: "：", open: "（", close: "）", join: "、" } : { colon: ": ", open: " (", close: ")", join: ", " };
  const safeLabel = (value) => escapeHtml(String(value).replace(/\d[\d -]{2,}\d/g, "••••"));
  const sourceText = snapshot.sources.map((source) => `✅ Moneytree${locale === "ja" ? "（" : " ("}${safeLabel(source.label)}${locale === "ja" ? "）" : ")"} ${escapeHtml(source.asOf)}${strings.updated}`).join("\n");
  const totals = `${strings.confirmedAssets}\t${formatAmount(locale, snapshot.totals.assetsMinor)}\n${strings.confirmedLiabilities}\t${formatAmount(locale, snapshot.totals.liabilitiesMinor)}\n${strings.confirmedDifference}\t${formatAmount(locale, snapshot.totals.netWorthMinor)}\n${strings.change}\t${formatChange(locale, snapshot.totals.changeMinor)}`;
  const title = ["partial", "recovered"].includes(snapshot.state) ? strings.partialTitle : strings.title;
  const excludedItems = [...snapshot.excluded, ...snapshot.sources.filter((source) => source.status !== "fresh").map((source) => ({ label: source.label }))];
  const excluded = [...new Map(excludedItems.map((item) => [item.label, item])).values()].map((item) => `${safeLabel(item.label)}${item.reason ? `${marks.open}${escapeHtml(item.reason)}${marks.close}` : ""}`).join(marks.join) || (locale === "ja" ? "なし" : "None");
  const exclusions = ["partial", "recovered"].includes(snapshot.state) ? `\n${strings.excluded}${marks.colon}${excluded}` : "";
  const repair = snapshot.state === "recovered" ? `\n${strings.recovered}` : "";
  const accounts = snapshot.sources.map((source) => `${safeLabel(source.label)}\t${formatAmount(locale, source.amountMinor)}${marks.open}${freshness[source.status]}${marks.close}`).join("\n");
  const evidence = snapshot.sources.map((source) => `${evidenceLabel(locale, source.verificationStatus)} ${escapeHtml(source.asOf)}`).join("\n");
  const why = `${strings.confirmedAssets} − ${strings.confirmedLiabilities} = ${strings.confirmedDifference} ${formatAmount(locale, snapshot.totals.netWorthMinor)}\n${strings.excluded}${marks.colon}${excluded}`;
  const text = view === "summary" ? `${title}\n\n${totals}${exclusions}\n\n${sourceText}${repair}\n${strings.noAction}`
    : view === "accounts" ? `${title}\n\n${accounts}\n${snapshot.state === "action_required" ? strings.actionBody : strings.noAction}`
      : view === "accuracy" ? `${title}\n\n${evidence}\n${strings.excluded}${marks.colon}${excluded}` : `${title}\n\n${why}`;
  return { text, extra: extra(locale, snapshot, view) };
}

module.exports = { renderCfoTelegram, callbackData, evidenceLabel, handleCfoTelegramCallback };
