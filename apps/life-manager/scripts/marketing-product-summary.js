#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { createContentObjectStore } = require("../lib/content-object-store.js");
const { createMarketingLocalLedger } = require("../lib/marketing-local-ledger.js");
const { buildMarketingLivenessJob, executeMarketingLivenessJob } = require("../lib/marketing-liveness-adapter.js");
const { executeCapabilityJob } = require("./runtime-up.js");

const HONNE = Object.freeze({ product_id: "honne-ai", label: "Honne AI", targets: [{ owner: "honne_reveal", account: "@honne_reveal", locale: "en", platform: "TikTok", required: true }, { owner: "honnevideo", account: "@honnevideo", locale: "ja", platform: "TikTok", required: true }] });
const ANICCA = Object.freeze({ product_id: "anicca-ios", label: "Anicca iOS", targets: [{ owner: "anicca.jp", account: "@anicca.jp", locale: "ja", platform: "TikTok", required: true }, { owner: "anicca.ios.jp", account: "@anicca.jp1", locale: "ja", platform: "Instagram", required: true }, { owner: "anicca.jp4", account: "@anicca.jp4", locale: "ja", platform: "TikTok", required: false }, { owner: "anicca.he", account: "@anicca.he", locale: "ja", platform: "TikTok", required: false, public_url: "https://www.tiktok.com/@anicca.he/video/7676500512308481296" }] });
const SUMMARY_ROUTES = Object.freeze({ "honne-ai": Object.freeze({ lane: "marketing-product-summary-honne", locale: "en" }), "anicca-ios": Object.freeze({ lane: "marketing-product-summary-anicca", locale: "ja" }), "mobile-marketing": Object.freeze({ lane: "marketing-product-summary-weekly", locale: "ja" }) });

function latestDaily(dataDir, owner, reportDay) {
  const root = path.join(dataDir, "tenants/dais-local/marketing/metrics", owner); if (!fs.existsSync(root)) return null;
  return fs.readdirSync(root).flatMap((id) => { const daily = path.join(root, id, "daily"); if (!fs.existsSync(daily)) return []; const correction = path.join(daily, `${reportDay}.correction.json`); const base = path.join(daily, `${reportDay}.json`); return fs.existsSync(correction) ? [correction] : fs.existsSync(base) ? [base] : []; }).map((file) => ({ file, snapshot: JSON.parse(fs.readFileSync(file, "utf8")) })).sort((a, b) => Date.parse(b.snapshot.observed_at) - Date.parse(a.snapshot.observed_at))[0] || null;
}

function metricText(snapshot) {
  if (!snapshot) return "全social/account metrics取得不可（daily snapshot未接続）";
  const labels = { views: "Views", likes: "Likes", comments: "Comments", shares: "Shares", saves: "Saves", engagement: "Engagement" }; const measured = []; const unavailable = [];
  for (const key of Object.keys(labels)) { const metric = snapshot.post?.[key]; if (!metric || metric.status === "unavailable") unavailable.push(labels[key]); else measured.push(`${labels[key]} ${metric.percent != null ? `${metric.percent}%` : metric.value}`); }
  for (const [key, label] of [["followers", "Followers"], ["following", "Following"], ["total_likes", "Account likes"], ["videos", "Videos"]]) { const metric = snapshot.account_metrics?.[key]; if (!metric || metric.status === "unavailable") unavailable.push(label); else measured.push(`${label} ${metric.value}`); }
  return `${measured.join("、")}。取得不可: ${unavailable.length ? unavailable.join("、") : "なし"}`;
}

function persistProductDaily(dataDir, reportDay, observedAt, product) {
  const objectStore = createContentObjectStore({ objectDir: path.join(dataDir, "objects") }); const rows = product.targets.map((target) => { const row = latestDaily(dataDir, target.owner, reportDay); if (!row) { if (target.required) throw new Error(`${product.label} ${target.account} daily source unavailable`); return { ...target, snapshot: null, ref: null }; } const direct = target.platform === "Instagram" ? /^https:\/\/www\.instagram\.com\/(?:reel|p)\/[A-Za-z0-9_-]+\/?$/ : /^https:\/\/www\.tiktok\.com\/@[^/]+\/video\/\d+\/?$/; if (row.snapshot.account_id !== target.account || row.snapshot.locale !== target.locale || !direct.test(row.snapshot.public_url)) throw new Error(`${product.label} ${target.account} daily source mismatch`); return { ...target, ...row, ref: objectStore.import(row.file).ref }; });
  const sourceRefs = rows.map((row) => row.ref).filter(Boolean); const message = `Life Manager::: ${product.label}の${reportDay}日次プロダクトメトリクスです。\n${rows.map((row) => `${row.account} ${row.platform}: ${metricText(row.snapshot)}。直接URL: ${row.snapshot?.public_url || row.public_url || "取得不可"}。Source: ${row.ref || "取得不可"}`).join("\n")}\nInstalls: 取得不可（attribution未接続）、Trials: 取得不可（RevenueCat未接続）、Paid subscriptions: 取得不可（RevenueCat未接続）。`;
  const snapshot = { schema_version: 1, kind: "marketing_product_metric_summary", period: "daily", report_key: reportDay, observed_at: observedAt, product_id: product.product_id, source_refs: sourceRefs, message }; const file = path.join(dataDir, "tenants/dais-local/marketing/metrics/summaries", product.product_id, "daily", `${reportDay}.json`); fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  if (fs.existsSync(file)) return { created: false, file, snapshot: JSON.parse(fs.readFileSync(file, "utf8")) }; const temporary = `${file}.tmp-${process.pid}-${crypto.randomUUID()}`; fs.writeFileSync(temporary, `${JSON.stringify(snapshot, null, 2)}\n`, { mode: 0o600, flag: "wx" }); fs.renameSync(temporary, file); fs.chmodSync(file, 0o600); return { created: true, file, snapshot };
}

function persistHonneDaily(dataDir, reportDay, observedAt) { return persistProductDaily(dataDir, reportDay, observedAt, HONNE); }
function persistAniccaDaily(dataDir, reportDay, observedAt) { return persistProductDaily(dataDir, reportDay, observedAt, ANICCA); }

function isoWeek(reportDay) {
  const date = new Date(`${reportDay}T00:00:00.000Z`); if (!Number.isFinite(date.getTime())) throw new Error("weekly report day is invalid"); date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7)); const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1)); return `${date.getUTCFullYear()}-W${String(Math.ceil((((date - yearStart) / 86400000) + 1) / 7)).padStart(2, "0")}`;
}

function productDailySources(dataDir, productId, reportDay) {
  const root = path.join(dataDir, "tenants/dais-local/marketing/metrics/summaries", productId, "daily"); if (!fs.existsSync(root)) return [];
  const end = Date.parse(`${reportDay}T00:00:00.000Z`); const start = end - 6 * 86400_000;
  return fs.readdirSync(root).filter((name) => /^\d{4}-\d{2}-\d{2}\.json$/.test(name)).map((name) => ({ file: path.join(root, name), day: name.slice(0, 10) })).filter(({ day }) => { const time = Date.parse(`${day}T00:00:00.000Z`); return time >= start && time <= end; }).map((row) => ({ ...row, snapshot: JSON.parse(fs.readFileSync(row.file, "utf8")) })).sort((a, b) => a.day.localeCompare(b.day));
}

function persistWeeklyReview(dataDir, reportDay, observedAt) {
  const objectStore = createContentObjectStore({ objectDir: path.join(dataDir, "objects") }); const week = isoWeek(reportDay); const products = [["honne-ai", "Honne AI"], ["anicca-ios", "Anicca iOS"]].map(([productId, label]) => { const rows = productDailySources(dataDir, productId, reportDay); if (!rows.length) throw new Error(`${label} weekly daily source unavailable`); const latest = rows.at(-1); return { productId, label, rows, latest, refs: rows.map((row) => objectStore.import(row.file).ref) }; });
  const sourceRefs = products.flatMap((product) => product.refs); const message = `Life Manager::: ${week} mobile marketing週次レビューです。\n${products.map((product) => `${product.label}: coverage ${product.rows.length}/7日、latest ${product.latest.day}。\n${product.latest.snapshot.message}`).join("\n")}\nAttribution coverage: 取得不可（ASC/RevenueCat/product analytics未接続）。\nCross-product winner: 判定しない。HonneとAniccaの学習weightは分離します。\nKeep/revert・次のbounded change: attribution cohort取得まで判定不可。`;
  const snapshot = { schema_version: 1, kind: "marketing_product_metric_summary", period: "weekly", report_key: week, observed_at: observedAt, product_id: "mobile-marketing", source_refs: sourceRefs, message }; const file = path.join(dataDir, "tenants/dais-local/marketing/metrics/summaries/mobile-marketing/weekly", `${week}.json`); fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  if (fs.existsSync(file)) return { created: false, file, snapshot: JSON.parse(fs.readFileSync(file, "utf8")) }; const temporary = `${file}.tmp-${process.pid}-${crypto.randomUUID()}`; fs.writeFileSync(temporary, `${JSON.stringify(snapshot, null, 2)}\n`, { mode: 0o600, flag: "wx" }); fs.renameSync(temporary, file); fs.chmodSync(file, 0o600); return { created: true, file, snapshot };
}

async function sendSummary(result, env, dataDir) {
  if (!result.created) return { created: false, reason: "summary_replay" }; const objectStore = createContentObjectStore({ objectDir: path.join(dataDir, "objects") }); const summaryRef = objectStore.import(result.file).ref;
  const route = SUMMARY_ROUTES[result.snapshot.product_id]; if (!route) throw new Error("marketing product summary route is unavailable");
  const job = buildMarketingLivenessJob({ tenantId: "dais-local", telegramTokenRef: "secret://telegram/bot-token", telegramChatRef: "telegram-chat://owner", payload: { lane: route.lane, product: result.snapshot.product_id, locale: route.locale, platform: "multi", status: "summary", period: result.snapshot.period, observed_at: result.snapshot.observed_at, summary_ref: summaryRef } }); const store = createMarketingLocalLedger({ dataDir }); const queued = await store.enqueueJob({ jobId: job.job_id, tenantId: job.tenant_id, loopId: job.loop_id, capability: job.capability, effectClass: job.effect_class, effectKey: job.effect_key, inputRefs: job.input_refs, maxAttempts: job.max_attempts, availableAt: new Date().toISOString() }); if (!queued.created) return { created: false, reason: "telegram_replay" };
  const claim = await store.claimJob({ tenantId: job.tenant_id, jobId: job.job_id, capability: job.capability, workerId: "marketing-product-summary", leaseSeconds: 120 }); if (!claim) throw new Error("marketing product summary job is not claimable"); await executeCapabilityJob(claim, { workerId: "marketing-product-summary", handlers: { [job.capability]: (candidate) => executeMarketingLivenessJob(candidate, { secretProvider: { get: async () => env.LM_TELEGRAM_BOT_TOKEN }, chatProvider: { get: async () => env.LM_TELEGRAM_ALERT_CHAT_ID }, snapshotProvider: { get: async (_tenantId, ref) => JSON.parse(fs.readFileSync(objectStore.resolve(ref), "utf8")) } }) }, heartbeatJob: (input) => store.heartbeatJob(input), completeJob: (input) => store.completeJob(input), failJob: (input) => store.failJob(input), leaseSeconds: 120 }); const receipt = await store.readReceipt({ tenantId: job.tenant_id, jobId: job.job_id }); return { created: true, message_id: receipt?.message_id, summary_ref: summaryRef };
}

module.exports = { latestDaily, persistAniccaDaily, persistHonneDaily, persistProductDaily, persistWeeklyReview, sendSummary };
