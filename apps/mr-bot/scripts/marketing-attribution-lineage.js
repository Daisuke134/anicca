#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const { importContentObject, resolveContentObject } = require("../lib/content-object-store.js");
const { resolveDataRoot } = require("../lib/runtime-paths.js");

const HASH = /^[0-9a-f]{64}$/;

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function readReceipts(file) {
  return fs.readFileSync(file, "utf8").split("\n").filter(Boolean).map(JSON.parse);
}

function platformOf(snapshot) {
  if (snapshot.kind === "tiktok_combined_metric_snapshot") return "tiktok";
  if (snapshot.kind === "instagram_combined_metric_snapshot") return "instagram";
  throw new Error(`unsupported metric snapshot kind: ${snapshot.kind}`);
}

function exactPublication(snapshot, receipts) {
  const platform = platformOf(snapshot);
  const matches = receipts.filter(({ receipt }) => receipt
    && receipt.kind === "marketing_video_distribution"
    && receipt.status === "published"
    && receipt.product_id === snapshot.product_id
    && receipt.locale === snapshot.locale
    && receipt.platform === platform
    && receipt.provider_post_id === snapshot.provider_post_id
    && receipt.public_url === snapshot.public_url);
  if (matches.length !== 1) {
    throw new Error(`${snapshot.account_id} ${snapshot.window} has ${matches.length} exact publication matches`);
  }
  return matches[0];
}

function exactCaption(receipt, objectDir) {
  const digest = String(receipt.caption_sha256 || "");
  if (!HASH.test(digest)) throw new Error("publication caption hash is invalid");
  const ref = `object://sha256/${digest}`;
  const caption = fs.readFileSync(resolveContentObject(ref, { objectDir }), "utf8");
  const hook = caption.split(/\r?\n/).map((line) => line.trim()).find(Boolean);
  if (!hook) throw new Error("publication caption has no hook line");
  const campaignUrl = caption.split(/\s+/).find((value) => { try { const url = new URL(value); return url.protocol === "https:" && url.hostname === "apps.apple.com" && /^honne_en_(?:base|hook)_[a-z0-9_]+$/.test(String(url.searchParams.get("ct") || "")); } catch { return false; } }) || null;
  const campaignId = campaignUrl ? new URL(campaignUrl).searchParams.get("ct") : null;
  return {
    caption_ref: ref,
    hook_text: hook,
    hook_sha256: crypto.createHash("sha256").update(hook).digest("hex"),
    campaign_url: campaignUrl,
    campaign_id: campaignId,
  };
}

function buildLineage({ dataDir, tenantId = "dais-local" }) {
  const objectDir = path.join(dataDir, "objects");
  const metricsDir = path.join(dataDir, "tenants", tenantId, "marketing", "metrics");
  const metricFiles = [];
  for (const account of fs.readdirSync(metricsDir, { withFileTypes: true })) {
    if (!account.isDirectory()) continue;
    for (const post of fs.readdirSync(path.join(metricsDir, account.name), { withFileTypes: true })) {
      if (!post.isDirectory()) continue;
      const file = path.join(metricsDir, account.name, post.name, "24h.combined.json");
      if (fs.statSync(file, { throwIfNoEntry: false })?.isFile()) metricFiles.push(file);
    }
  }
  metricFiles.sort();
  if (!metricFiles.length) throw new Error("no 24h combined metric snapshots found");
  const receipts = readReceipts(path.join(dataDir, "marketing", "receipts.jsonl"));
  const rows = metricFiles.map((file) => {
    const snapshot = readJson(file);
    const match = exactPublication(snapshot, receipts);
    const publication = match.receipt;
    const metricObject = importContentObject(file, { objectDir });
    const caption = exactCaption(publication, objectDir);
    const videoRef = `object://sha256/${publication.video_sha256}`;
    resolveContentObject(videoRef, { objectDir });
    return {
      attribution_status: caption.campaign_id ? "partial" : "unattributed",
      attribution_reason: caption.campaign_id ? "campaign_link_configured_no_product_readback" : "campaign_not_configured",
      product_id: snapshot.product_id,
      locale: snapshot.locale,
      platform: platformOf(snapshot),
      account_id: snapshot.account_id,
      integration_id: snapshot.integration_id,
      provider_post_id: snapshot.provider_post_id,
      public_url: snapshot.public_url,
      campaign_id: caption.campaign_id,
      campaign_url: caption.campaign_url,
      campaign_status: caption.campaign_id ? "configured" : "unavailable",
      creative_id: publication.creative_id,
      slot: publication.slot,
      published_at: publication.published_at,
      video_ref: videoRef,
      ...caption,
      metric_snapshot_ref: metricObject.ref,
      observed_at: snapshot.observed_at,
      window: snapshot.window,
    };
  });
  return {
    schema_version: 1,
    kind: "marketing_attribution_lineage",
    tenant_id: tenantId,
    observed_at: rows.map((row) => row.observed_at).sort().at(-1),
    rows,
    coverage: {
      included: rows.length,
      exact_publication_lineage: rows.length,
      campaign_attributed: 0,
      unattributed: rows.length,
      attribution_rate: null,
      attribution_rate_status: "unavailable",
      attribution_rate_reason: "campaign_not_configured",
    },
  };
}

function persistLineage({ dataDir, tenantId = "dais-local" }) {
  const lineage = buildLineage({ dataDir, tenantId });
  const directory = path.join(dataDir, "tenants", tenantId, "marketing", "attribution");
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const candidate = path.join(directory, `.lineage-${process.pid}.json`);
  fs.writeFileSync(candidate, `${JSON.stringify(lineage, null, 2)}\n`, { mode: 0o600 });
  const imported = importContentObject(candidate, { objectDir: path.join(dataDir, "objects") });
  fs.unlinkSync(candidate);
  const pointer = path.join(directory, "lineage.json");
  const previous = fs.statSync(pointer, { throwIfNoEntry: false })?.isFile() ? readJson(pointer) : null;
  const value = { ...lineage, snapshot_ref: imported.ref };
  const temporary = `${pointer}.tmp-${process.pid}`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temporary, pointer);
  return { created: previous?.snapshot_ref !== imported.ref, pointer, ...value };
}

if (require.main === module) {
  const result = persistLineage({ dataDir: resolveDataRoot(process.env) });
  process.stdout.write(`${JSON.stringify({
    created: result.created,
    snapshot_ref: result.snapshot_ref,
    included: result.coverage.included,
    exact_publication_lineage: result.coverage.exact_publication_lineage,
    campaign_attributed: result.coverage.campaign_attributed,
    unattributed: result.coverage.unattributed,
    pointer: result.pointer,
  })}\n`);
}

module.exports = { buildLineage, persistLineage };
