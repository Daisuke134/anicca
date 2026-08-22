"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const DIRECT = /^https:\/\/www\.tiktok\.com\/@([A-Za-z0-9._-]+)\/video\/(\d+)$/;
const WINDOWS = new Set(["2h", "24h", "72h", "7d"]);
const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const LOCALE = /^[a-z]{2}(?:-[A-Z]{2})?$/;

function normalized(value) {
  return String(value || "").normalize("NFKC").replace(/\s+/g, " ").trim();
}

function metric(value, label) {
  const number = Number(value);
  if (!Number.isSafeInteger(number) || number < 0) throw new Error(`TikTok ${label} metric invalid`);
  return { status: "measured", value: number, source: "tiktok_native_embedded_json" };
}

function extractTikTokNativeMetrics(scripts, expected) {
  const match = DIRECT.exec(String(expected.publicUrl || ""));
  if (!match || `@${match[1]}` !== expected.account || match[2] !== expected.videoId) {
    throw new Error("TikTok native metric identity invalid");
  }
  let item;
  for (const source of scripts) {
    try {
      const parsed = JSON.parse(source);
      const candidate = parsed?.__DEFAULT_SCOPE__?.["webapp.video-detail"]?.itemInfo?.itemStruct;
      if (String(candidate?.id || "") === expected.videoId) item = candidate;
    } catch {}
  }
  if (
    !item
    || `@${item.author?.uniqueId || ""}` !== expected.account
    || normalized(item.desc) !== normalized(expected.caption)
  ) throw new Error("TikTok native metric content mismatch");
  const stats = item.stats || {};
  const post = {
    views: metric(stats.playCount, "views"),
    likes: metric(stats.diggCount, "likes"),
    comments: metric(stats.commentCount, "comments"),
    shares: metric(stats.shareCount, "shares"),
    saves: metric(stats.collectCount, "saves"),
    reach: { status: "unavailable", value: null, reason: "metric_not_supported" },
    watch_time: { status: "unavailable", value: null, reason: "metric_not_supported" },
    completion: { status: "unavailable", value: null, reason: "metric_not_supported" },
  };
  const numerator = post.likes.value + post.comments.value + post.shares.value + post.saves.value;
  post.engagement = post.views.value === 0
    ? { status: "unavailable", value: null, reason: "zero_view_denominator" }
    : {
        status: "derived",
        numerator,
        denominator: post.views.value,
        rate: Number((numerator / post.views.value).toFixed(8)),
        percent: Number(((numerator / post.views.value) * 100).toFixed(2)),
        formula: "(likes+comments+shares+saves)/views",
      };
  return Object.freeze({ post, caption: item.desc, created_at: new Date(Number(item.createTime) * 1000).toISOString() });
}

function persistTikTokNativeSnapshot(input) {
  const direct = DIRECT.exec(String(input.publicUrl || ""));
  if (
    !WINDOWS.has(input.window)
    || !IDENTIFIER.test(String(input.tenantId || ""))
    || !IDENTIFIER.test(String(input.productId || ""))
    || !LOCALE.test(String(input.locale || ""))
    || !direct
    || `@${direct[1]}` !== input.account
    || direct[2] !== input.videoId
    || !Number.isFinite(Date.parse(input.publishedAt))
    || !Number.isFinite(Date.parse(input.observedAt))
  ) throw new Error("TikTok native metric snapshot identity invalid");
  const directory = path.resolve(input.dataDir, "tenants", input.tenantId, "marketing", "metrics", input.account.slice(1), input.videoId);
  const file = path.join(directory, `${input.window}.json`);
  const captionSha256 = crypto.createHash("sha256").update(Buffer.from(input.caption)).digest("hex");
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  if (fs.existsSync(file)) {
    const existing = JSON.parse(fs.readFileSync(file, "utf8"));
    if (
      existing.public_url !== input.publicUrl
      || existing.video_id !== input.videoId
      || existing.window !== input.window
      || existing.tenant_id !== input.tenantId
      || existing.product_id !== input.productId
      || existing.locale !== input.locale
      || existing.account_id !== input.account
      || existing.caption_sha256 !== captionSha256
    ) {
      throw new Error("TikTok native metric replay mismatch");
    }
    return Object.freeze({ created: false, file, snapshot: existing });
  }
  const snapshot = {
    schema_version: 1,
    kind: "tiktok_native_metric_snapshot",
    tenant_id: input.tenantId,
    product_id: input.productId,
    locale: input.locale,
    account_id: input.account,
    video_id: input.videoId,
    public_url: input.publicUrl,
    window: input.window,
    published_at: input.publishedAt,
    observed_at: input.observedAt,
    caption_sha256: captionSha256,
    post: input.metrics.post,
  };
  const temporary = `${file}.tmp-${process.pid}-${crypto.randomUUID()}`;
  fs.writeFileSync(temporary, `${JSON.stringify(snapshot, null, 2)}\n`, { mode: 0o600, flag: "wx" });
  fs.renameSync(temporary, file);
  fs.chmodSync(file, 0o600);
  return Object.freeze({ created: true, file, snapshot });
}

module.exports = { extractTikTokNativeMetrics, persistTikTokNativeSnapshot };
