"use strict";

const ERROR = "cfo_writer_invalid:business_fact";
const PLATFORMS = /^[a-z][a-z0-9-]{0,31}$/;

function fail() { throw new Error(ERROR); }
function plain(value) { return value !== null && typeof value === "object" && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype; }
function freeze(value, seen = new WeakSet()) { if (value === null || typeof value !== "object" || seen.has(value)) return value; seen.add(value); Object.values(value).forEach((child) => freeze(child, seen)); return Object.freeze(value); }
function iso(value) { return typeof value === "string" && value.length <= 64 && Number.isFinite(Date.parse(value)); }
function decimal(value) {
  if (typeof value === "string" && /^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(value) && value.length <= 32) return value;
  if (typeof value === "number" && Number.isFinite(value) && value >= 0 && value < 1e15) { const text = String(value); if (!/[eE]/.test(text)) return text; }
  return null;
}
function metric(article, name) { const value = article.metrics && article.metrics[name]; return plain(value) && value.status === "verified" ? value : null; }
function zeroMetric(value, unit) { return value && value.unit === unit && decimal(value.value) === "0"; }
function channelId(platform) { return `writer_${platform.replace(/-/g, "_")}`; }

/**
 * Projects the existing Writer report into a privacy-safe CFO observation.
 * Publisher amounts remain null unless the report has an explicit verified receipt.
 * A provider-verified Note zero is kept as a channel observation and never becomes
 * a Writer-wide zero or a profit/ROI input.
 */
function composeWriterBusinessFact(report) {
  try {
    if (!plain(report) || !iso(report.generated_at) || !["today", "latest_saved_run", "none"].includes(report.report_articles_scope)
      || !Number.isSafeInteger(report.measurement_unknown_count) || report.measurement_unknown_count < 0
      || !Array.isArray(report.report_articles)) fail();
    const channels = new Map(), runtime = [];
    for (const article of report.report_articles) {
      if (!plain(article) || typeof article.platform !== "string" || !PLATFORMS.test(article.platform) || typeof article.revenue_capable !== "boolean") fail();
      if (!article.revenue_capable) continue;
      if (article.metrics !== undefined && !plain(article.metrics)) fail();
      if (article.money !== undefined && !plain(article.money)) fail();
      const current = channels.get(article.platform) || { articles: 0, receipts: 0, providerReceipt: false, verifiedZero: 0, unknown: false };
      current.articles += 1;
      const receipts = article.money && article.money.receipts;
      if (receipts !== undefined && !Array.isArray(receipts)) fail();
      if (Array.isArray(receipts) && receipts.length > 0) { current.receipts += receipts.length; current.providerReceipt = true; }
      const purchases = metric(article, "purchases"), net = metric(article, "net_received");
      if (zeroMetric(purchases, "count") && zeroMetric(net, "JPY")) current.verifiedZero += 1;
      else if (!current.providerReceipt) current.unknown = true;
      const compute = metric(article, "compute_cost");
      if (compute && compute.unit === "wall_seconds") { const seconds = decimal(compute.value); if (seconds && iso(compute.observed_at)) runtime.push({ channel_id: channelId(article.platform), observed_at: compute.observed_at, wall_seconds: seconds, evidence_status: "runtime_measured" }); }
      channels.set(article.platform, current);
    }
    const observations = [...channels.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([platform, value]) => {
      const status = value.providerReceipt ? "provider_reported" : value.verifiedZero === value.articles && value.articles > 0 ? "provider_verified_zero" : "unknown";
      return { channel_id: channelId(platform), coverage_status: status, observed_article_count: value.articles, receipt_count: value.providerReceipt ? value.receipts : null, verified_zero_count: value.verifiedZero, net_received: status === "provider_verified_zero" ? { coverage_status: "provider_verified_zero", currency: "JPY", amount_decimal: "0" } : null };
    });
    const exceptions = new Set(["capital_unknown", "direct_cost_unknown", "human_cost_unknown", "landed_cash_unknown", "profit_disabled_until_reconciliation", "roi_disabled_until_reconciliation", "writer_total_not_closed"]);
    if (!observations.length || observations.some((item) => item.coverage_status === "unknown")) exceptions.add("publisher_receipts_unknown");
    if (report.measurement_unknown_count > 0) exceptions.add("measurement_unknown");
    return freeze({ schema_version: 1, financial_unit_id: "writer_agent", observed_at: report.generated_at, scope: report.report_articles_scope, status: "partial", revenue: { coverage_status: "partial", observations, total: null, landed_cash_status: "unknown" }, cost: { runtime: { coverage_status: runtime.length ? "verified" : "unknown", observations: runtime }, direct_api: { coverage_status: "unknown", amount: null }, human: { coverage_status: "unknown", amount: null } }, capital: { coverage_status: "unknown", amount: null }, profit: null, roi: null, coverage_exceptions: [...exceptions].sort() });
  } catch { throw new Error(ERROR); }
}

module.exports = { composeWriterBusinessFact };
