"use strict";

const { types: { isProxy } } = require("node:util");
const { CFO_STRINGS } = require("./i18n.js");

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
const ACTION_KEYS = new Set(["kind", "sourceLabel", "retryLabel", "nextRetryAt"]);
const RFC3339 = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;
const BUTTONS = Object.freeze({
  summary: [["accounts", "口座を見る", "View accounts"], ["accuracy", "正確さを見る", "View accuracy"]],
  accounts: [["summary", "概要に戻る", "Back to summary"], ["accuracy", "正確さを見る", "View accuracy"]],
  accuracy: [["summary", "概要に戻る", "Back to summary"], ["why", "なぜこの金額？", "Why this amount?"]],
  why: [["summary", "概要に戻る", "Back to summary"]],
});

function fail(reason) { throw new Error(`cfo_telegram_invalid:${reason}`); }
function plain(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value) && !isProxy(value)
    && Object.getPrototypeOf(value) === Object.prototype;
}
function sanitize(snapshot) {
  if (!plain(snapshot)) return snapshot;
  const strip = (value) => Object.fromEntries(Object.entries(value).filter(([key]) => !/account|raw|credential|token|secret|password|cookie|oauth/i.test(key)));
  const safe = strip(snapshot);
  if (Array.isArray(snapshot.sources)) safe.sources = snapshot.sources.map((source) => plain(source) ? strip(source) : source);
  return safe;
}
function exact(value, allowed, required = []) {
  if (!plain(value)) fail("invalid_object");
  const keys = Reflect.ownKeys(value);
  if (keys.some((key) => !allowed.has(key))) fail("unknown_key");
  for (const key of keys) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (!descriptor || descriptor.enumerable !== true || !Object.prototype.hasOwnProperty.call(descriptor, "value")) fail("invalid_object");
  }
  if (required.some((key) => !keys.includes(key))) fail("missing_key");
}
function label(value) { if (typeof value !== "string" || value.length === 0) fail("invalid_label"); }
function rfc3339(value) {
  const match = typeof value === "string" && RFC3339.exec(value);
  if (!match) fail("invalid_action");
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6]);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  const zone = match[8];
  const zoneHour = zone === "Z" ? 0 : Number(zone.slice(1, 3));
  const zoneMinute = zone === "Z" ? 0 : Number(zone.slice(4));
  if (month < 1 || month > 12 || day < 1 || day > days[month - 1]
    || hour > 23 || minute > 59 || second > 59 || zoneHour > 23 || zoneMinute > 59) fail("invalid_action");
}
function safeAmount(value) { return value === null || Number.isSafeInteger(value); }
function date(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) fail("invalid_reporting_date");
  const [year, month, day] = value.split("-").map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (month < 1 || month > 12 || day < 1 || day > days[month - 1]) fail("invalid_reporting_date");
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
    if (!["reconsent", "provider_outage"].includes(snapshot.action.kind)) fail("invalid_action");
    [snapshot.action.sourceLabel, snapshot.action.retryLabel, snapshot.action.nextRetryAt].forEach(label);
    rfc3339(snapshot.action.nextRetryAt);
  }
  const { state, totals, sources, excluded, repair, action } = snapshot;
  if (["complete", "partial", "recovered"].includes(state) && sources.some((source) => source.status !== "fresh")) fail("source_not_fresh");
  if ((state === "complete" || state === "recovered") && [totals.assetsMinor, totals.liabilitiesMinor, totals.netWorthMinor, totals.changeMinor].some((value) => value === null)) fail("inconsistent_totals");
  if ((state === "complete" || state === "recovered") && totals.assetsMinor - totals.liabilitiesMinor !== totals.netWorthMinor) fail("inconsistent_totals");
  if ((state === "complete" || state === "recovered") && excluded.length) fail("inconsistent_state");
  if (state === "partial" && (totals.netWorthMinor !== null || excluded.length === 0)) fail(totals.netWorthMinor === null ? "partial_excluded_required" : "partial_net_worth_forbidden");
  if (state === "action_required" && (totals.netWorthMinor !== null || action === null)) fail(totals.netWorthMinor === null ? "action_required_missing_action" : "action_required_net_worth_forbidden");
  if (state !== "recovered" && repair !== null) fail("inconsistent_repair");
  if (state !== "action_required" && action !== null) fail("inconsistent_action");
  if (state === "recovered" && (!repair || repair.freshReread !== true || repair.reconciled !== true)) fail("recovery_unproven");
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
function extra(locale, snapshot, view) {
  return { reply_markup: { inline_keyboard: BUTTONS[view].map(([next, ja, en]) => [{ text: locale === "ja" ? ja : en, callback_data: callbackData({ view: next, reportingDate: snapshot.reportingDate, revision: snapshot.revision }) }]) } };
}
function renderCfoTelegram({ locale, view, snapshot }) {
  if (!CFO_STRINGS[locale]) fail("unsupported_locale");
  if (!VIEWS.has(view)) fail("unsupported_view");
  snapshot = sanitize(snapshot);
  validateSnapshot(snapshot);
  const strings = CFO_STRINGS[locale];
  const actionCopy = snapshot.state === "action_required"
    ? snapshot.action.kind === "provider_outage" ? strings.actionProviderOutage : strings.actionReconsent
    : null;
  if (snapshot.state === "action_required" && view === "summary") {
    const replaceRetryAt = (value) => value.replace("{nextRetryAt}", escapeHtml(snapshot.action.nextRetryAt));
    return { text: `${actionCopy.title}\n\n${actionCopy.body}\n${replaceRetryAt(actionCopy.retry)}`, extra: extra(locale, snapshot, view) };
  }
  const freshness = locale === "ja" ? { fresh: "最新", stale: "古い", unavailable: "不明" } : { fresh: "Fresh", stale: "Stale", unavailable: "Unknown" };
  const marks = locale === "ja" ? { colon: "：", open: "（", close: "）", join: "、" } : { colon: ": ", open: " (", close: ")", join: ", " };
  const safeLabel = (value) => escapeHtml(String(value).replace(/\d[\d -]{2,}\d/g, "••••"));
  const sourceText = snapshot.sources.map((source) => `✅ Moneytree${locale === "ja" ? "（" : " ("}${safeLabel(source.label)}${locale === "ja" ? "）" : ")"} ${escapeHtml(source.asOf)}${strings.updated}`).join("\n");
  const totals = `${strings.confirmedAssets}\t${formatAmount(locale, snapshot.totals.assetsMinor)}\n${strings.confirmedLiabilities}\t${formatAmount(locale, snapshot.totals.liabilitiesMinor)}\n${strings.confirmedDifference}\t${formatAmount(locale, snapshot.totals.netWorthMinor)}\n${strings.change}\t${formatChange(locale, snapshot.totals.changeMinor)}`;
  const title = snapshot.state === "partial" ? strings.partialTitle : strings.title;
  const excludedItems = [...snapshot.excluded, ...snapshot.sources.filter((source) => source.status !== "fresh").map((source) => ({ label: source.label }))];
  const excluded = [...new Map(excludedItems.map((item) => [item.label, item])).values()].map((item) => `${safeLabel(item.label)}${item.reason ? `${marks.open}${escapeHtml(item.reason)}${marks.close}` : ""}`).join(marks.join) || (locale === "ja" ? "なし" : "None");
  const exclusions = snapshot.state === "partial" ? `\n${strings.excluded}${marks.colon}${excluded}` : "";
  const repair = snapshot.state === "recovered" ? `\n${strings.recovered}` : "";
  const accounts = snapshot.sources.map((source) => `${safeLabel(source.label)}\t${formatAmount(locale, source.amountMinor)}${marks.open}${freshness[source.status]}${marks.close}`).join("\n");
  const evidence = snapshot.sources.map((source) => `${evidenceLabel(locale, source.verificationStatus)} ${escapeHtml(source.asOf)}`).join("\n");
  const why = `${strings.confirmedAssets} − ${strings.confirmedLiabilities} = ${strings.confirmedDifference} ${formatAmount(locale, snapshot.totals.netWorthMinor)}\n${strings.excluded}${marks.colon}${excluded}`;
  const text = view === "summary" ? `${title}\n\n${totals}${exclusions}\n\n${sourceText}${repair}\n${strings.noAction}`
    : view === "accounts" ? `${title}\n\n${accounts}\n${snapshot.state === "action_required" ? actionCopy.body : strings.noAction}`
      : view === "accuracy" ? `${title}\n\n${evidence}\n${strings.excluded}${marks.colon}${excluded}` : `${title}\n\n${why}`;
  return { text, extra: extra(locale, snapshot, view) };
}

module.exports = { renderCfoTelegram, callbackData, evidenceLabel };
