import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, readFile, readdir, stat } from "node:fs/promises";
import { join, dirname } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";

import {
  collectOpportunityEvidence,
  writeOpportunityEvidence,
} from "./opportunity-scout.mjs";

const OBSERVED_AT = "2026-08-28T02:00:00.000Z";
const EMPTY_SHA256 = createHash("sha256").update(Buffer.alloc(0)).digest("hex");

function response(body, status = 200, contentType = "application/json") {
  const bytes = Buffer.from(body);
  return {
    status,
    headers: { get(name) { return name.toLowerCase() === "content-type" ? contentType : null; } },
    async arrayBuffer() {
      return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
    },
  };
}

test("collects read-only public evidence and preserves partial failures", async () => {
  const calls = [];
  const responseBodies = new Map();
  const failedUrl = "https://api.agentbounties.app/v1/base/autonomous-bounties/feed?network=base-mainnet&claimable_only=true";
  const thrownUrl = "https://api.subgraph.autonolas.tech/api/proxy/marketplace-base";
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, ...options, method: options.method || "GET", headers: options.headers || {} });
    assert.equal(options.credentials, "omit");
    if (url === failedUrl) return response("temporarily unavailable", 503, "text/plain");
    if (url === thrownUrl) throw new Error("network failure must not enter the manifest");
    const body = Buffer.from(JSON.stringify({ source: url, ok: true }));
    responseBodies.set(url, body);
    return response(body);
  };

  const snapshot = await collectOpportunityEvidence({ fetchImpl, observedAt: OBSERVED_AT });

  assert.deepEqual(new Set(calls.map((call) => call.method)), new Set(["GET", "POST"]));
  assert.equal(calls.some((call) => call.headers.authorization || call.headers.cookie), false);
  assert.equal(calls.every((call) => call.signal instanceof AbortSignal), true);
  assert.equal(snapshot.mode, "read_only");
  assert.deepEqual(snapshot.evaluation_fields, [
    "scope", "funding", "recent_payout", "competition", "signup_identity",
    "payout_rail", "deadline", "expected_compute", "official_receipt",
  ]);
  assert.equal(snapshot.sources.length >= 11, true);
  assert.equal(snapshot.sources.every((source) => /^[a-f0-9]{64}$/.test(source.content_sha256)), true);

  const failed = snapshot.sources.find((source) => source.url === failedUrl);
  assert.equal(failed.ok, false);
  assert.equal(failed.http_status, 503);
  assert.equal(failed.content_bytes, Buffer.byteLength("temporarily unavailable"));
  assert.equal(snapshot.sources.some((source) => source.ok), true);

  const thrown = snapshot.sources.find((source) => source.url === thrownUrl);
  assert.equal(thrown.ok, false);
  assert.equal(thrown.http_status, null);
  assert.equal(thrown.error_kind, "fetch_error");
  assert.equal(thrown.content_sha256, EMPTY_SHA256);

  const olasCalls = calls.filter((call) => call.method === "POST");
  assert.equal(olasCalls.length >= 4, true);
  for (const call of olasCalls) {
    const payload = JSON.parse(call.body);
    assert.deepEqual(Object.keys(payload), ["query"]);
    assert.equal(/\bmutation\b/i.test(payload.query), false);
    for (const field of ["global", "meches", "_meta", "requests", "isDelivered", "deliveredByMech"]) {
      assert.equal(payload.query.includes(field), true, `${call.url} missing ${field}`);
    }
    assert.equal(/claim|submit|fund|register|create|delete|update/i.test(payload.query), false);
  }

  const stateDir = await mkdtemp(join(tmpdir(), "opportunity-scout-test-"));
  const bodyBySource = new Map(snapshot.sources.map((source) => [
    source.source,
    responseBodies.get(source.url) || (source.http_status === 503
      ? Buffer.from("temporarily unavailable") : Buffer.alloc(0)),
  ]));
  const result = await writeOpportunityEvidence({ snapshot, bodies: bodyBySource, stateDir });
  assert.equal(result.manifestPath.endsWith("/manifest.json"), true);

  const manifest = JSON.parse(await readFile(result.manifestPath, "utf8"));
  assert.equal(manifest.mode, "read_only");
  for (const source of manifest.sources) {
    assert.equal(typeof source.evidence_path, "string");
    const evidencePath = join(dirname(result.manifestPath), source.evidence_path);
    const bytes = await readFile(evidencePath);
    assert.equal(bytes.byteLength, source.content_bytes);
    assert.equal(createHash("sha256").update(bytes).digest("hex"), source.content_sha256);
    assert.equal((await stat(evidencePath)).isFile(), true);
  }
  const manifestFiles = await readdir(dirname(result.manifestPath));
  assert.equal(manifestFiles.some((name) => name.startsWith("manifest.json.tmp")), false);
});

test("bounds hung public requests and rejects an invalid timeout before fetch", async () => {
  const calls = [];
  let invalidCalls = 0;
  await assert.rejects(
    () => collectOpportunityEvidence({
      fetchImpl: async () => { invalidCalls += 1; return response("unexpected"); },
      observedAt: OBSERVED_AT,
      timeoutMs: 0,
    }),
    /timeoutMs/,
  );
  assert.equal(invalidCalls, 0);

  const fetchImpl = async (url, options) => {
    calls.push(options);
    if (url === "https://api.agentbounties.app/v1/base/autonomous-bounties/feed?network=base-mainnet&claimable_only=true") {
      await new Promise((resolve, reject) => options.signal.addEventListener("abort", () => reject(options.signal.reason), { once: true }));
    }
    return response("{}", 200);
  };
  const snapshot = await collectOpportunityEvidence({ fetchImpl, observedAt: OBSERVED_AT, timeoutMs: 10 });
  assert.equal(calls.length >= 11, true);
  assert.equal(calls.every((options) => options.signal instanceof AbortSignal), true);
  assert.equal(snapshot.sources.find((source) => source.source === "agent_bounties_base_claimable").ok, false);
});

test("marks a full Olas page as truncated and preserves unknown coverage in the manifest", async () => {
  const calls = [];
  const responseBodies = new Map();
  const requests = Array.from({ length: 1000 }, (_, index) => ({ id: `request-${index}` }));
  const fetchImpl = async (url, options) => {
    calls.push({ url, ...options });
    const body = options.method === "POST"
      ? JSON.stringify({ data: { requests } })
      : "{}";
    responseBodies.set(url, Buffer.from(body));
    return response(body, 200);
  };

  const snapshot = await collectOpportunityEvidence({ fetchImpl, observedAt: OBSERVED_AT });
  const olasCalls = calls.filter((call) => call.method === "POST");
  assert.equal(olasCalls.length, 4);
  for (const call of olasCalls) {
    const query = JSON.parse(call.body).query;
    assert.equal(query.includes("orderBy: blockTimestamp, orderDirection: desc"), true);
    assert.equal(query.includes("orderBy: blockTimestamp, orderDirection: asc"), false);
  }
  const olasSources = snapshot.sources.filter((source) => source.method === "POST");
  assert.equal(olasSources.length, 4);
  for (const source of olasSources) {
    assert.equal(source.page_limit, 1000);
    assert.equal(source.truncated, true);
    assert.equal(source.next_cursor, "skip:1000");
    assert.equal(source.coverage, "unknown");
  }

  const stateDir = await mkdtemp(join(tmpdir(), "opportunity-scout-olas-"));
  const bodyBySource = new Map(snapshot.sources.map((source) => [source.source, responseBodies.get(source.url)]));
  const result = await writeOpportunityEvidence({ snapshot, bodies: bodyBySource, stateDir });
  const manifest = JSON.parse(await readFile(result.manifestPath, "utf8"));
  for (const source of manifest.sources.filter((entry) => entry.method === "POST")) {
    assert.equal(source.coverage, "unknown");
    const bytes = await readFile(join(dirname(result.manifestPath), source.evidence_path));
    assert.equal(createHash("sha256").update(bytes).digest("hex"), source.content_sha256);
  }
});
