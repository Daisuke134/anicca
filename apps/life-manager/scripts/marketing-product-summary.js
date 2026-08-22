#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { createContentObjectStore } = require("../lib/content-object-store.js");
const { createMarketingLocalLedger } = require("../lib/marketing-local-ledger.js");
const { buildMarketingLivenessJob, executeMarketingLivenessJob } = require("../lib/marketing-liveness-adapter.js");
const { executeCapabilityJob } = require("./runtime-up.js");

const ACCOUNTS = Object.freeze([{ owner: "honne_reveal", account: "@honne_reveal", locale: "en" }, { owner: "honnevideo", account: "@honnevideo", locale: "ja" }]);

function latestDaily(dataDir, owner, reportDay) {
  const root = path.join(dataDir, "tenants/dais-local/marketing/metrics", owner); if (!fs.existsSync(root)) return null;
  return fs.readdirSync(root).flatMap((id) => { const daily = path.join(root, id, "daily"); if (!fs.existsSync(daily)) return []; const correction = path.join(daily, `${reportDay}.correction.json`); const base = path.join(daily, `${reportDay}.json`); return fs.existsSync(correction) ? [correction] : fs.existsSync(base) ? [base] : []; }).map((file) => ({ file, snapshot: JSON.parse(fs.readFileSync(file, "utf8")) })).sort((a, b) => Date.parse(b.snapshot.observed_at) - Date.parse(a.snapshot.observed_at))[0] || null;
}

function metricText(snapshot) {
  const labels = { views: "Views", likes: "Likes", comments: "Comments", shares: "Shares", saves: "Saves", engagement: "Engagement" }; const measured = []; const unavailable = [];
  for (const key of Object.keys(labels)) { const metric = snapshot.post?.[key]; if (!metric || metric.status === "unavailable") unavailable.push(labels[key]); else measured.push(`${labels[key]} ${metric.percent != null ? `${metric.percent}%` : metric.value}`); }
  for (const [key, label] of [["followers", "Followers"], ["following", "Following"], ["total_likes", "Account likes"], ["videos", "Videos"]]) { const metric = snapshot.account_metrics?.[key]; if (!metric || metric.status === "unavailable") unavailable.push(label); else measured.push(`${label} ${metric.value}`); }
  return `${measured.join("、")}。取得不可: ${unavailable.length ? unavailable.join("、") : "なし"}`;
}

function persistHonneDaily(dataDir, reportDay, observedAt) {
  const objectStore = createContentObjectStore({ objectDir: path.join(dataDir, "objects") }); const rows = ACCOUNTS.map((target) => { const row = latestDaily(dataDir, target.owner, reportDay); if (!row || row.snapshot.account_id !== target.account || row.snapshot.locale !== target.locale || !/^https:\/\/www\.tiktok\.com\/@[^/]+\/video\/\d+\/?$/.test(row.snapshot.public_url)) throw new Error(`Honne ${target.locale} daily source unavailable`); return { ...target, ...row, ref: objectStore.import(row.file).ref }; });
  const sourceRefs = rows.map((row) => row.ref); const message = `Life Manager::: Honne AIの${reportDay}日次プロダクトメトリクスです。\n${rows.map((row) => `${row.account}: ${metricText(row.snapshot)}。直接URL: ${row.snapshot.public_url}。Source: ${row.ref}`).join("\n")}\nInstalls: 取得不可（attribution未接続）、Trials: 取得不可（RevenueCat未接続）、Paid subscriptions: 取得不可（RevenueCat未接続）。`;
  const snapshot = { schema_version: 1, kind: "marketing_product_metric_summary", period: "daily", report_key: reportDay, observed_at: observedAt, product_id: "honne-ai", source_refs: sourceRefs, message }; const file = path.join(dataDir, "tenants/dais-local/marketing/metrics/summaries/honne-ai/daily", `${reportDay}.json`); fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  if (fs.existsSync(file)) return { created: false, file, snapshot: JSON.parse(fs.readFileSync(file, "utf8")) }; const temporary = `${file}.tmp-${process.pid}-${crypto.randomUUID()}`; fs.writeFileSync(temporary, `${JSON.stringify(snapshot, null, 2)}\n`, { mode: 0o600, flag: "wx" }); fs.renameSync(temporary, file); fs.chmodSync(file, 0o600); return { created: true, file, snapshot };
}

async function sendSummary(result, env, dataDir) {
  if (!result.created) return { created: false, reason: "summary_replay" }; const objectStore = createContentObjectStore({ objectDir: path.join(dataDir, "objects") }); const summaryRef = objectStore.import(result.file).ref;
  const job = buildMarketingLivenessJob({ tenantId: "dais-local", telegramTokenRef: "secret://telegram/bot-token", telegramChatRef: "telegram-chat://owner", payload: { lane: "marketing-product-summary-honne", product: "honne-ai", locale: "en", platform: "multi", status: "summary", period: "daily", observed_at: result.snapshot.observed_at, summary_ref: summaryRef } }); const store = createMarketingLocalLedger({ dataDir }); const queued = await store.enqueueJob({ jobId: job.job_id, tenantId: job.tenant_id, loopId: job.loop_id, capability: job.capability, effectClass: job.effect_class, effectKey: job.effect_key, inputRefs: job.input_refs, maxAttempts: job.max_attempts, availableAt: new Date().toISOString() }); if (!queued.created) return { created: false, reason: "telegram_replay" };
  const claim = await store.claimJob({ tenantId: job.tenant_id, jobId: job.job_id, capability: job.capability, workerId: "marketing-product-summary", leaseSeconds: 120 }); if (!claim) throw new Error("marketing product summary job is not claimable"); await executeCapabilityJob(claim, { workerId: "marketing-product-summary", handlers: { [job.capability]: (candidate) => executeMarketingLivenessJob(candidate, { secretProvider: { get: async () => env.LM_TELEGRAM_BOT_TOKEN }, chatProvider: { get: async () => env.LM_TELEGRAM_ALERT_CHAT_ID }, snapshotProvider: { get: async (_tenantId, ref) => JSON.parse(fs.readFileSync(objectStore.resolve(ref), "utf8")) } }) }, heartbeatJob: (input) => store.heartbeatJob(input), completeJob: (input) => store.completeJob(input), failJob: (input) => store.failJob(input), leaseSeconds: 120 }); const receipt = await store.readReceipt({ tenantId: job.tenant_id, jobId: job.job_id }); return { created: true, message_id: receipt?.message_id, summary_ref: summaryRef };
}

module.exports = { latestDaily, persistHonneDaily, sendSummary };
