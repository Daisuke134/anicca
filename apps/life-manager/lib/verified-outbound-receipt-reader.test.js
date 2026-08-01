"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const test = require("node:test");

const { buildEventApplicationJob } = require("./outbound-event-job.js");
const { assertVerifiedOutboundReceipt } = require("./outbound-success.js");
const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const {
  createVerifiedOutboundReceiptReader,
} = require("./verified-outbound-receipt-reader.js");

const TENANT = "dais-local";
const START = "2026-08-05T10:00:00.000Z";

function coverage() {
  return buildRollingEventCoverage({
    tenantId: TENANT,
    timeZone: "Asia/Tokyo",
    now: "2026-08-02T01:00:00.000Z",
    resolvedDays: [],
  });
}

function fixture() {
  const canonicalUrl = "https://luma.com/founder-night";
  const job = buildEventApplicationJob({
    tenantId: TENANT,
    eventUrl: canonicalUrl,
    eventStartIso: START,
    identityRef: "identity://dais-local/luma",
    browserProfileRef: "browser-profile://cloakbrowser/daily-driver",
    calendarRef: "calendar://google/primary",
  });
  const attempt = 1;
  const bytes = Buffer.alloc(5_000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(bytes);
  const artifactHash = createHash("sha256").update(bytes).digest("hex");
  const storedReceipt = {
    kind: "outbound_event_application",
    status: "verified",
    attempt_ref: `runtime-attempt://${TENANT}/${job.job_id}/${attempt}`,
    external_receipt_ref: "provider-receipt://luma/fixture-registration",
    artifact_ref: `object://sha256/${artifactHash}`,
    canonical_url: canonicalUrl,
    evidence_hash: "stored-hash-is-not-trusted",
    verified_at: "2026-08-02T01:00:01.000Z",
  };
  return {
    job,
    attempt,
    bytes,
    row: {
      ...job,
      attempt,
      status: "completed",
      outcome: "completed",
      receipt: storedReceipt,
    },
  };
}

test("completed runtime receipt is reverified from E1/E2/E3 before Calendar may consume it", async () => {
  const value = fixture();
  const calls = [];
  const reader = createVerifiedOutboundReceiptReader({
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [value.row] };
    },
    async readExternalReceipt(tenantId, ref) {
      assert.equal(tenantId, TENANT);
      assert.equal(ref, value.row.receipt.external_receipt_ref);
      return { kind: "provider_response", provider_id: "fixture", observed_at: "2026-08-02T01:00:00.000Z" };
    },
    async readArtifact(tenantId, ref) {
      assert.equal(tenantId, TENANT);
      assert.equal(ref, value.row.receipt.artifact_ref);
      return value.bytes;
    },
    async fetchImpl(url, options) {
      assert.equal(url, value.row.receipt.canonical_url);
      assert.equal(options.method, "HEAD");
      return { status: 200 };
    },
  });

  const [result] = await reader.listForCoverage({ tenantId: TENANT, coverage: coverage() });

  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].params, [TENANT, "2026-08-02", "2026-08-23"]);
  assert.match(calls[0].sql, /outcome\s*=\s*'completed'/i);
  assert.equal(result.event_ref, value.job.input_refs.event_ref);
  assert.equal(result.job.attempt, 1);
  assert.equal(assertVerifiedOutboundReceipt(result.receipt, result.job), result.receipt);
  assert.notEqual(result.receipt.evidence_hash, value.row.receipt.evidence_hash);
});

test("tenant drift, malformed job lineage, and missing fresh evidence fail closed", async () => {
  const value = fixture();
  const make = (row, overrides = {}) => createVerifiedOutboundReceiptReader({
    async query() { return { rows: [row] }; },
    async readExternalReceipt() {
      return { kind: "provider_response", provider_id: "fixture", observed_at: "2026-08-02T01:00:00.000Z" };
    },
    async readArtifact() { return value.bytes; },
    async fetchImpl() { return { status: 200 }; },
    ...overrides,
  });
  const input = { tenantId: TENANT, coverage: coverage() };

  await assert.rejects(
    make({ ...value.row, tenant_id: "another-tenant" }).listForCoverage(input),
    /verified outbound receipt reader unavailable/i,
  );
  await assert.rejects(
    make({ ...value.row, input_refs: { ...value.row.input_refs, identity_ref: "identity://other/luma" } }).listForCoverage(input),
    /verified outbound receipt reader unavailable/i,
  );
  await assert.rejects(
    make(value.row, { async readArtifact() { return null; } }).listForCoverage(input),
    /verified outbound receipt reader unavailable/i,
  );
  await assert.rejects(
    make(value.row).listForCoverage({ tenantId: "another-tenant", coverage: coverage() }),
    /verified outbound receipt reader invalid/i,
  );
});
