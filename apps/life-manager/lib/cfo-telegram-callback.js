"use strict";

const { editMessageText, answerCallbackQuery } = require("./telegram.js");

const VIEWS = new Set(["summary", "accounts", "accuracy", "why", "business"]);
const CALLBACK = /^cfo:(summary|accounts|accuracy|why|business):(\d{8}):([1-9]\d*)$/;
const RETRY = "読み込めませんでした。もう一度お試しください";
const STATUSES = new Set(["fresh", "stale", "unavailable"]), EVIDENCE = new Set(["provider_billed", "provider_reported", "locally_estimated", "unavailable"]);
const BUTTONS = {
  summary: [["accounts", "口座を見る"], ["business", "仕事を見る"], ["accuracy", "正確さを見る"]],
  accounts: [["summary", "概要に戻る"], ["accuracy", "正確さを見る"]],
  accuracy: [["summary", "概要に戻る"], ["why", "なぜこの金額？"]],
  why: [["summary", "概要に戻る"]],
  business: [["summary", "概要に戻る"], ["accuracy", "数字の確かさ"]],
};
const plain = (v) => v !== null && typeof v === "object" && !Array.isArray(v) && Object.getPrototypeOf(v) === Object.prototype;
const nonEmpty = (v) => typeof v === "string" && v.length > 0 && v.trim() === v;
const amount = (v) => v === null || Number.isSafeInteger(v);
const html = (v) => String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const label = (v) => html(String(v).replace(/\d[\d -]{2,}\d/g, "••••"));
function parse(value) {
  const m = CALLBACK.exec(String(value || ""));
  if (!m) return null;
  const date = `${m[2].slice(0, 4)}-${m[2].slice(4, 6)}-${m[2].slice(6)}`;
  const parsed = new Date(`${date}T00:00:00Z`), revision = Number(m[3]);
  return Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== date ||
    !Number.isSafeInteger(revision) || String(revision) !== m[3] ? null : { view: m[1], date, revision };
}
function messageId(value) {
  const n = typeof value === "number" ? value : (/^[1-9]\d*$/.test(String(value || "")) ? Number(value) : NaN);
  return Number.isSafeInteger(n) && n > 0 ? n : null;
}
function format(value) { return value === null ? "不明" : `¥${new Intl.NumberFormat("ja-JP").format(value)}`; }
function validateBusiness(value) {
  if (value === undefined) return;
  if (!plain(value) || value.schemaVersion !== 1 || typeof value.observedAt !== "string" || !Number.isFinite(Date.parse(value.observedAt)) || value.status !== "partial" || !["partial", "unknown"].includes(value.evidenceStatus) || !Array.isArray(value.businesses) || !Array.isArray(value.exceptions)) throw new Error("invalid_business");
  if (value.recommendation !== undefined && (!plain(value.recommendation) || value.recommendation.schemaVersion !== 1 || !Number.isFinite(Date.parse(value.recommendation.observedAt)) || !["increase", "hold", "repair", "stop-review"].includes(value.recommendation.kind) || typeof value.recommendation.reason !== "string" || value.recommendation.execute !== false || typeof value.recommendation.ownerActionRequired !== "boolean" || !Array.isArray(value.recommendation.coverageExceptions))) throw new Error("invalid_business");
  value.businesses.forEach((item) => { if (!plain(item) || typeof item.financialUnitId !== "string" || typeof item.label !== "string" || !["observed", "unknown"].includes(item.providerReceiptStatus) || !Number.isSafeInteger(item.providerReceiptCount) || item.providerReceiptCount < 0 || !Array.isArray(item.activity) || item.landedCashStatus !== "unknown" || item.costStatus !== "unknown" || item.contributionProfit !== null || item.roi !== null) throw new Error("invalid_business"); item.activity.forEach((entry) => { if (!plain(entry) || !["external_income", "realized_pnl", "fee"].includes(entry.kind) || entry.currency !== "USD" || typeof entry.amountDecimal !== "string" || !/^-?(?:0|[1-9]\d*)(?:\.\d{1,8})?$/.test(entry.amountDecimal) || entry.evidenceStatus !== "verified_append_only_ledger") throw new Error("invalid_business"); }); });
}
function validate(snapshot, parsed) {
  if (!plain(snapshot) || snapshot.schemaVersion !== 1 || snapshot.currency !== "JPY" || snapshot.reportingDate !== parsed.date || snapshot.revision !== parsed.revision ||
      !plain(snapshot.totals) || !Array.isArray(snapshot.sources) || snapshot.sources.length === 0) throw new Error("invalid_snapshot");
  for (const key of ["assetsMinor", "liabilitiesMinor", "netWorthMinor", "changeMinor"]) if (!Object.prototype.hasOwnProperty.call(snapshot.totals, key) || !amount(snapshot.totals[key])) throw new Error("invalid_amount");
  validateBusiness(snapshot.business);
  for (const source of snapshot.sources) {
    if (!plain(source) || typeof source.label !== "string" || !source.label || typeof source.asOf !== "string" || !source.asOf || !STATUSES.has(source.status) || !EVIDENCE.has(source.verificationStatus) || !amount(source.amountMinor) || (source.amountMinor !== null && ["locally_estimated", "unavailable"].includes(source.verificationStatus)) || (source.status === "unavailable" && (source.amountMinor !== null || source.verificationStatus !== "unavailable")) || (source.status === "fresh" && (source.amountMinor === null || source.verificationStatus === "unavailable"))) throw new Error("invalid_source");
  }
  if (snapshot.excluded !== undefined && (!Array.isArray(snapshot.excluded) || snapshot.excluded.some((item) => !plain(item) || typeof item.label !== "string" || !item.label || (item.reason !== undefined && typeof item.reason !== "string")))) throw new Error("invalid_excluded");
  return snapshot;
}
function keyboard(snapshot, view) {
  return { inline_keyboard: BUTTONS[view].map(([next, text]) => [{ text, callback_data: `cfo:${next}:${snapshot.reportingDate.replaceAll("-", "")}:${snapshot.revision}` }]) };
}
function businessText(snapshot) {
  const business = snapshot.business;
  if (!business || !Array.isArray(business.businesses)) return "💼 今月の仕事\nまだbusiness readを接続していません";
  const rows = business.businesses.map((item) => {
    const activity = Array.isArray(item.activity) && item.activity.length
      ? item.activity.map((entry) => `${entry.kind}:${entry.amountDecimal} USD`).join(" / ") : "不明";
    return `${label(item.label)}\t${activity}\t利益 不明`;
  }).join("\n");
  const recommendation = business.recommendation ? `\nCFO判断：${business.recommendation.kind === "repair" ? "修復（証拠不足）" : business.recommendation.kind}` : "";
  return `💼 今月の仕事（実測範囲）\n${rows}\n利益：不明\nROI：不明\n根拠：${business.evidenceStatus === "partial" ? "一部実測・照合未完了" : "不明"}${recommendation}`;
}
function render(snapshot, view) {
  if (!VIEWS.has(view)) throw new Error("invalid_view");
  const totals = snapshot.totals, sources = snapshot.sources;
  const excluded = (snapshot.excluded || []).map((item) => `${label(item.label)}${item.reason ? `（${label(item.reason)}）` : ""}`).join("、") || "なし";
  const freshness = (s) => s.amountMinor === null ? "取得できず／銀行側データの新しさは不明" : s.status === "fresh" ? "取得済み／銀行側データの新しさは不明" : s.status === "stale" ? "取得済み／データが古い可能性・銀行側データの新しさは不明" : "取得できず／銀行側データの新しさは不明";
  const evidenceLabel = (s) => s.verificationStatus === "provider_billed" ? "確定" : s.verificationStatus === "provider_reported" ? "実測" : s.verificationStatus === "locally_estimated" ? "推定" : "不明";
  const accounts = sources.map((s) => `${label(s.label)}\t${format(s.amountMinor)}（${freshness(s)}）`).join("\n");
  const retrievalNote = "（ローカル取得時刻。銀行側データの新しさは不明）";
  const evidence = sources.map((s) => `${evidenceLabel(s)} ${html(s.asOf)}${retrievalNote}`).join("\n");
  const title = snapshot.state === "partial" ? "⚠️ 確認できた範囲のお金" : "💰 今日のお金";
  const action = snapshot.state === "action_required" ? "" : "\n\n今すること：ありません";
  // `fresh` means the provider read succeeded; it does not prove the bank has
  // refreshed its data. Keep the warning visible in every interactive view.
  const sourceText = snapshot.state === "action_required" ? "" : sources.map((s) => `⚠️ Moneytree（${label(s.label)}）${html(s.asOf)}${s.status === "fresh" ? retrievalNote : s.status === "stale" ? "（ローカル取得時刻。データが古い可能性・銀行側データの新しさは不明）" : "（取得できず。銀行側データの新しさは不明）"}`).join("\n");
  const summary = `${title}\n\n確認できた資産\t${format(totals.assetsMinor)}\n確認できた負債\t${format(totals.liabilitiesMinor)}\n差し引き\t${format(totals.netWorthMinor)}\n前回から\t${format(totals.changeMinor)}\n\n${sourceText}\n合計に入れていません：${excluded}${action}`;
  const text = view === "summary" ? `${summary}${snapshot.business ? `\n\n${businessText(snapshot)}` : ""}` : view === "accounts" ? `${title}\n\n${accounts}` : view === "accuracy" ? `${title}\n\n${evidence}\n合計に入れていません：${excluded}` : view === "business" ? businessText(snapshot) : `${title}\n\n確認できた資産 − 確認できた負債 = 差し引き ${format(totals.netWorthMinor)}\n合計に入れていません：${excluded}`;
  return { text, reply_markup: keyboard(snapshot, view) };
}
async function handleCfoTelegramCallback(input, options = {}) {
  let answered = false;
  const tgCall = options.tgCall;
  const answerCallback = options.answerCallbackQuery || (tgCall ? (token, id, text) => tgCall(token, "answerCallbackQuery", { callback_query_id: id, ...(text ? { text } : {}) }) : answerCallbackQuery);
  const edit = options.editMessageText || (tgCall ? (token, chat, id, text, extra) => tgCall(token, "editMessageText", { chat_id: chat, message_id: id, parse_mode: "HTML", text, ...(extra || {}) }) : editMessageText);
  const answer = async (text) => { if (answered || !nonEmpty(input && input.telegramToken) || !nonEmpty(input && input.callbackQueryId)) return; answered = true; try { await answerCallback(input.telegramToken, input.callbackQueryId, text); } catch {} };
  try {
    const parsed = parse(input && input.data), id = messageId(input && input.messageId);
    if (!parsed || !nonEmpty(input && input.uid) || !nonEmpty(input && input.chatId) || input.actorId !== input.chatId || !id ||
        !nonEmpty(input && input.telegramToken) || !nonEmpty(input && input.callbackQueryId) || !nonEmpty(options.supaUrl) || !nonEmpty(options.supaKey)) throw new Error("invalid_callback");
    const endpoint = new URL(`${options.supaUrl.replace(/\/$/, "")}/rest/v1/lm_cfo_daily_snapshots`);
    endpoint.searchParams.set("uid", `eq.${input.uid}`); endpoint.searchParams.set("reporting_date", `eq.${parsed.date}`); endpoint.searchParams.set("revision", `eq.${parsed.revision}`); endpoint.searchParams.set("select", "report_payload"); endpoint.searchParams.set("limit", "1");
    const response = await (options.fetchImpl || fetch)(endpoint, { method: "GET", headers: { apikey: options.supaKey, Authorization: `Bearer ${options.supaKey}` } });
    if (!response || response.ok !== true) throw new Error("snapshot_unavailable");
    const rows = await response.json();
    if (!Array.isArray(rows) || rows.length !== 1 || !plain(rows[0]) || !plain(rows[0].report_payload)) throw new Error("snapshot_unavailable");
    const snapshot = validate(rows[0].report_payload, parsed), rendered = render(snapshot, parsed.view);
    const edited = await edit(input.telegramToken, input.chatId, id, rendered.text, { reply_markup: rendered.reply_markup });
    if (!edited || edited.ok !== true) throw new Error("edit_unavailable");
    await answer();
    return Object.freeze({ status: "edited", view: parsed.view, reportingDate: parsed.date, revision: parsed.revision });
  } catch { await answer(RETRY); return Object.freeze({ status: "failed" }); }
}

module.exports = { handleCfoTelegramCallback, parseCfoCallback: parse, renderCfoTelegram: ({ view, snapshot }) => { const result = render(validate(snapshot, { date: snapshot.reportingDate, revision: snapshot.revision }), view); return { text: result.text, extra: { reply_markup: result.reply_markup } }; } };
