#!/usr/bin/env node
"use strict";

const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

function linkedUrls(markdown) {
  const values = [];
  for (const match of markdown.matchAll(/\]\((https:\/\/[^\s)]+)\)/g)) {
    try { const url = new URL(match[1]); url.hash = ""; values.push(url.toString()); } catch {}
  }
  return [...new Set(values)].sort();
}

async function fetchSource(source, fetchImpl = fetch) {
  const official = new URL(source.url);
  if (official.protocol !== "https:" || official.username || official.password) throw new Error("official source URL invalid");
  const retrievalUrl = `https://r.jina.ai/${official.toString()}`;
  const response = await fetchImpl(retrievalUrl, { signal: AbortSignal.timeout(30_000), headers: { Accept: "text/markdown" } });
  if (!response.ok) throw new Error(`official source fetch failed: ${source.source_id}`);
  const content = await response.text();
  if (!content || content.length > 2_000_000) throw new Error(`official source content invalid: ${source.source_id}`);
  return Object.freeze({ source_id: source.source_id, source_url: official.toString(), retrieved_via: "jina_reader",
    fetched_at: new Date().toISOString(), content, content_sha256: createHash("sha256").update(content).digest("hex"), links: linkedUrls(content) });
}

async function main() {
  const config = JSON.parse(fs.readFileSync(path.join(__dirname, "../config/funder-program-sources.json"), "utf8"));
  const extra = process.argv.slice(2).map((url, index) => ({ source_id: `agent-discovered-${index + 1}`, url }));
  const sources = [];
  for (const source of [...config.sources, ...extra]) sources.push(await fetchSource(source));
  process.stdout.write(`${JSON.stringify({ tenantId: process.env.LIFE_MANAGER_TENANT_ID || "dais-local", observedAt: new Date().toISOString(), sources,
    assessment: { assessed_source_ids: sources.map(({ source_id }) => source_id), candidates: [] } })}\n`);
}

if (require.main === module) main().catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
module.exports = { fetchSource, linkedUrls };
