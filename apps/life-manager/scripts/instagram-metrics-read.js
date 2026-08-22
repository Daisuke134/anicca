#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { resolveDataRoot } = require("../lib/runtime-paths.js");

const WINDOWS = new Set(["2h", "24h", "72h", "7d"]);
const EXPECTED = Object.freeze({
  tenant_id: "dais-local", product_id: "anicca-ios", locale: "ja",
  account_id: "@anicca.jp1", native_owner: "anicca.ios.jp",
  integration_id: "cmn8ycvtn02djqx0ytuisn9mw", provider_post_id: "cmt2sfjcx02bapj0ymsu4tapf",
  shortcode: "DcTFx_UjSio", public_url: "https://www.instagram.com/reel/DcTFx_UjSio/",
  caption: "強い人の口癖、5つだけ\n\n#anicca #セルフケア #習慣 #AI",
  published_at: "2026-08-21T10:10:15.268Z",
});
const POST_LABELS = Object.freeze({ Views: "views", Reach: "reach", Saves: "saves", Likes: "likes", Comments: "comments", Shares: "shares" });

function decodeHtml(value) {
  return String(value).replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)))
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n))).replace(/&quot;/g, '"').replace(/&amp;/g, "&");
}

function normalize(value) { return String(value).normalize("NFKC").replace(/\s+/g, " ").trim(); }

function verifyNativeHtml(html) {
  const description = /<meta property="og:description" content="([^"]*)"/.exec(String(html))?.[1];
  const canonical = /<link rel="canonical" href="([^"]*)"/.exec(String(html))?.[1];
  const decoded = decodeHtml(description || "");
  if (canonical !== EXPECTED.public_url || !decoded.includes(EXPECTED.native_owner) || !normalize(decoded).includes(normalize(EXPECTED.caption))) {
    throw new Error("Instagram native URL, owner, or caption mismatch");
  }
  return { status: "measured", identity_verified: true, native_owner: EXPECTED.native_owner };
}

function measured(value, source) {
  const number = Number(value);
  if (!Number.isSafeInteger(number) || number < 0) throw new Error("Instagram metric invalid");
  return { status: "measured", value: number, source };
}

function postMetrics(rows) {
  if (!Array.isArray(rows)) throw new Error("Instagram post analytics invalid");
  const byLabel = new Map(rows.map((row) => [row?.label, row?.data?.[0]?.total]));
  const result = {};
  for (const [label, key] of Object.entries(POST_LABELS)) {
    result[key] = byLabel.has(label) ? measured(byLabel.get(label), "postiz_post_analytics") : { status: "unavailable", value: null, reason: "metric_missing" };
  }
  for (const key of ["impressions", "watch_time", "average_watch_time", "completion"]) result[key] = { status: "unavailable", value: null, reason: "metric_not_supported" };
  const numerator = result.likes.value + result.comments.value + result.shares.value + result.saves.value;
  result.engagement = result.views.value === 0 ? { status: "unavailable", value: null, reason: "zero_view_denominator" }
    : { status: "derived", numerator, denominator: result.views.value, rate: Number((numerator / result.views.value).toFixed(8)), percent: Number((numerator / result.views.value * 100).toFixed(2)), formula: "(likes+comments+shares+saves)/views" };
  return result;
}

function persistSnapshot({ dataDir, window, observedAt, html, accountRows, postRows }) {
  if (!WINDOWS.has(window) || !Number.isFinite(Date.parse(observedAt))) throw new Error("Instagram metric window invalid");
  const native = verifyNativeHtml(html);
  const snapshot = {
    schema_version: 1, kind: "instagram_combined_metric_snapshot", ...EXPECTED,
    window, observed_at: observedAt, caption_sha256: crypto.createHash("sha256").update(EXPECTED.caption).digest("hex"),
    sources: { instagram_native: native, postiz_post: { status: "measured" }, postiz_account: Array.isArray(accountRows) && accountRows.length ? { status: "measured" } : { status: "unavailable", reason: "empty_response", response: "empty_array" } },
    post: postMetrics(postRows), account_metrics: Array.isArray(accountRows) && accountRows.length ? accountRows : { status: "unavailable", reason: "empty_response" },
  };
  const directory = path.join(path.resolve(dataDir), "tenants", EXPECTED.tenant_id, "marketing", "metrics", EXPECTED.native_owner, EXPECTED.shortcode);
  const file = path.join(directory, `${window}.combined.json`);
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  if (fs.existsSync(file)) {
    const existing = JSON.parse(fs.readFileSync(file, "utf8"));
    if (existing.public_url !== EXPECTED.public_url || existing.provider_post_id !== EXPECTED.provider_post_id || existing.caption_sha256 !== snapshot.caption_sha256) throw new Error("Instagram metric replay mismatch");
    return { created: false, file, snapshot: existing };
  }
  const temporary = `${file}.tmp-${process.pid}-${crypto.randomUUID()}`;
  fs.writeFileSync(temporary, `${JSON.stringify(snapshot, null, 2)}\n`, { mode: 0o600, flag: "wx" });
  fs.renameSync(temporary, file); fs.chmodSync(file, 0o600);
  return { created: true, file, snapshot };
}

async function main() {
  const window = process.argv[2] || "24h";
  const key = String(process.env.LM_POSTIZ_API_KEY || "").trim();
  if (!key) throw new Error("LM_POSTIZ_API_KEY is required");
  const get = async (url, headers = {}) => { const response = await fetch(url, { headers }); if (!response.ok) throw new Error(`Instagram metric HTTP ${response.status}`); return response; };
  const [page, account, post] = await Promise.all([
    get(EXPECTED.public_url).then((response) => response.text()),
    get(`https://api.postiz.com/public/v1/analytics/${EXPECTED.integration_id}?date=1`, { Authorization: key }).then((response) => response.json()),
    get(`https://api.postiz.com/public/v1/analytics/post/${EXPECTED.provider_post_id}?date=1`, { Authorization: key }).then((response) => response.json()),
  ]);
  const result = persistSnapshot({ dataDir: resolveDataRoot(process.env), window, observedAt: new Date().toISOString(), html: page, accountRows: account, postRows: post });
  process.stdout.write(`${JSON.stringify({ created: result.created, file: result.file, post: result.snapshot.post, account: result.snapshot.account_metrics })}\n`);
}

if (require.main === module) main().catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
module.exports = { EXPECTED, persistSnapshot, postMetrics, verifyNativeHtml };
