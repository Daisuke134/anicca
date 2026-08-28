#!/usr/bin/env node

import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCHEMA_VERSION = 1;
const RECORD_TYPE = "opportunity_evidence_snapshot";
const DEFAULT_TIMEOUT_MS = 15_000;
const EVALUATION_FIELDS = Object.freeze([
  "scope", "funding", "recent_payout", "competition", "signup_identity",
  "payout_rail", "deadline", "expected_compute", "official_receipt",
]);
const OLAS_HOST = "https://api.subgraph.autonolas.tech/api/proxy/marketplace-";
const OLAS_CHAINS = ["gnosis", "base", "polygon", "optimism"];
const PUBLIC_GETS = [
  ["agent_bounties_base_claimable", "https://api.agentbounties.app/v1/base/autonomous-bounties/feed?network=base-mainnet&claimable_only=true"],
  ["immunefi_bounty_directory", "https://immunefi.com/bug-bounty/"],
  ["ugig_gigs", "https://ugig.net/api/gigs?limit=100"],
  ["ugig_bounties", "https://ugig.net/api/bounties?limit=100"],
  ["code4rena_audits", "https://code4rena.com/audits"],
  ["sherlock_contests", "https://audits.sherlock.xyz/contests"],
  ["cantina_competitions", "https://cantina.xyz/competitions"],
];

const olasQuery = (cutoff) => `query OpportunityScout {
  global(id: "") { totalRequests totalDeliveries }
  meches(first: 1000, orderBy: receivedRequests, orderDirection: desc) {
    id address owner receivedRequests totalDeliveriesTransactions
    selfDeliveredFromReceived deliveredByOthersFromReceived maxDeliveryRate paymentType
  }
  requests(first: 1000, skip: 0, where: { blockTimestamp_gte: "${cutoff}" },
    orderBy: blockTimestamp, orderDirection: desc) {
    id blockNumber blockTimestamp transactionHash feeUSD finalFeeUSD
    mech deliveredByMech isDelivered
  }
  _meta { hasIndexingErrors block { number timestamp } }
}`;

function observedIso(value) {
  const date = new Date(value === undefined ? Date.now() : value);
  if (!Number.isFinite(date.getTime())) throw new TypeError("observedAt must be a valid date");
  return date.toISOString();
}

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function descriptors(observedAt) {
  const gets = PUBLIC_GETS.map(([source, url]) => ({ source, method: "GET", url }));
  const cutoff = Math.floor(Date.parse(observedAt) / 1000) - 86_400;
  const olas = OLAS_CHAINS.map((chain) => ({
    source: `olas_${chain}_marketplace`, method: "POST", url: `${OLAS_HOST}${chain}`,
    body: JSON.stringify({ query: olasQuery(cutoff) }),
  }));
  return [...gets, ...olas];
}

function requestOptions(descriptor, timeoutMs) {
  const options = {
    method: descriptor.method,
    credentials: "omit",
    signal: AbortSignal.timeout(timeoutMs),
    headers: { accept: "application/json" },
  };
  if (descriptor.body !== undefined) {
    options.headers["content-type"] = "application/json";
    options.body = descriptor.body;
  }
  return options;
}

function sourceRecord(descriptor, { status = null, contentType = null, bytes, ok, errorKind }) {
  const record = {
    source: descriptor.source,
    method: descriptor.method,
    url: descriptor.url,
    ...(descriptor.body === undefined ? {} : { request_body_sha256: sha256(descriptor.body) }),
    ok,
    http_status: status,
    content_type: contentType,
    content_bytes: bytes.byteLength,
    content_sha256: sha256(bytes),
  };
  if (descriptor.body !== undefined && ok) {
    const coverage = { page_limit: 1000, truncated: null, next_cursor: null, coverage: "unknown" };
    try {
      const rows = JSON.parse(Buffer.from(bytes).toString("utf8"))?.data?.requests;
      if (Array.isArray(rows)) {
        coverage.truncated = rows.length === 1000;
        coverage.next_cursor = coverage.truncated ? "skip:1000" : null;
        coverage.coverage = coverage.truncated ? "unknown" : "complete_for_window";
      }
    } catch {}
    Object.assign(record, coverage);
  }
  if (!ok) record.error_kind = errorKind;
  return record;
}

async function collectOne(descriptor, fetchImpl, timeoutMs) {
  let response;
  try {
    response = await fetchImpl(descriptor.url, requestOptions(descriptor, timeoutMs));
    const bytes = new Uint8Array(await response.arrayBuffer());
    const status = Number.isFinite(Number(response.status)) ? Number(response.status) : null;
    const ok = status !== null && status >= 200 && status < 300;
    return {
      record: sourceRecord(descriptor, {
        status,
        contentType: response.headers.get("content-type") || null,
        bytes,
        ok,
        errorKind: "http_non_2xx",
      }),
      body: bytes,
    };
  } catch {
    const status = response && Number.isFinite(Number(response.status)) ? Number(response.status) : null;
    const contentType = response?.headers?.get?.("content-type") || null;
    return {
      record: sourceRecord(descriptor, {
        status,
        contentType,
        bytes: new Uint8Array(),
        ok: false,
        errorKind: response ? "response_body_error" : "fetch_error",
      }),
      body: new Uint8Array(),
    };
  }
}

async function collectWithBodies({ fetchImpl = globalThis.fetch, observedAt, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  if (typeof fetchImpl !== "function") throw new TypeError("fetchImpl must be a function");
  if (!Number.isInteger(timeoutMs) || timeoutMs <= 0) throw new TypeError("timeoutMs must be a positive integer");
  const observed = observedIso(observedAt);
  const list = descriptors(observed);
  const settled = await Promise.allSettled(list.map((descriptor) => collectOne(descriptor, fetchImpl, timeoutMs)));
  const sources = [];
  const bodies = new Map();
  settled.forEach((result, index) => {
    const descriptor = list[index];
    const collected = result.status === "fulfilled"
      ? result.value
      : { record: sourceRecord(descriptor, { bytes: new Uint8Array(), ok: false, errorKind: "fetch_error" }), body: new Uint8Array() };
    sources.push(collected.record);
    bodies.set(descriptor.source, collected.body);
  });
  return {
    snapshot: {
      schema_version: SCHEMA_VERSION,
      record_type: RECORD_TYPE,
      observed_at: observed,
      mode: "read_only",
      evaluation_fields: [...EVALUATION_FIELDS],
      sources,
    },
    bodies,
  };
}

export async function collectOpportunityEvidence(options = {}) {
  return (await collectWithBodies(options)).snapshot;
}

function safeName(value) {
  return String(value).replace(/[^a-zA-Z0-9._-]+/g, "-").replace(/^-+|-+$/g, "") || "source";
}

export async function writeOpportunityEvidence({ snapshot, bodies, stateDir } = {}) {
  if (!snapshot || !Array.isArray(snapshot.sources)) throw new TypeError("snapshot.sources is required");
  if (!(bodies instanceof Map)) throw new TypeError("bodies must be a Map");
  if (typeof stateDir !== "string" || !stateDir.trim()) throw new TypeError("stateDir is required");
  const snapshotDir = path.join(stateDir, observedIso(snapshot.observed_at).replace(/[:.]/g, "-"));
  await fs.mkdir(path.join(snapshotDir, "responses"), { recursive: true });
  const sources = [];
  for (const [index, source] of snapshot.sources.entries()) {
    if (!bodies.has(source.source)) throw new TypeError(`missing evidence body for ${source.source}`);
    const bytes = Buffer.from(bodies.get(source.source));
    if (bytes.byteLength !== Number(source.content_bytes) || sha256(bytes) !== source.content_sha256) {
      throw new Error(`evidence body does not match ${source.source}`);
    }
    const fileName = `${String(index + 1).padStart(2, "0")}-${safeName(source.source)}.body`;
    const evidencePath = path.join("responses", fileName);
    await fs.writeFile(path.join(snapshotDir, evidencePath), bytes);
    sources.push({ ...source, evidence_path: evidencePath });
  }
  const manifestSnapshot = { ...snapshot, sources };
  const manifestPath = path.join(snapshotDir, "manifest.json");
  const tempPath = `${manifestPath}.tmp-${process.pid}`;
  await fs.writeFile(tempPath, `${JSON.stringify(manifestSnapshot, null, 2)}\n`);
  await fs.rename(tempPath, manifestPath);
  return { manifestPath, snapshot: manifestSnapshot };
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isMain) {
  try {
    const stateDir = process.env.SCOUT_STATE_DIR?.trim()
      || (process.env.ANICCA_HOME?.trim() && path.join(process.env.ANICCA_HOME.trim(), "skills", "agent-economy", "state", "opportunity-scout"));
    if (!stateDir) {
      const error = new Error("ANICCA_HOME is required");
      error.code = "SCOUT_CONFIG_MISSING";
      throw error;
    }
    const collected = await collectWithBodies({ observedAt: new Date().toISOString() });
    const result = await writeOpportunityEvidence({ ...collected, stateDir });
    const successes = result.snapshot.sources.filter((source) => source.ok).length;
    process.stdout.write(`${JSON.stringify({
      manifest_path: result.manifestPath,
      sources: result.snapshot.sources.length,
      successes,
      failures: result.snapshot.sources.length - successes,
    })}\n`);
    if (!successes) process.exitCode = 1;
  } catch (error) {
    const code = /^[A-Z][A-Z0-9_]*$/.test(String(error?.code || "")) ? error.code : "SCOUT_FAILED";
    process.stderr.write(`opportunity-scout: ${code}\n`);
    process.exitCode = code === "SCOUT_CONFIG_MISSING" ? 2 : 1;
  }
}
