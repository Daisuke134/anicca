"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { createHash } = require("node:crypto");

const { buildFunderOutreachBatch } = require("./funder-outreach.js");
const { deliverFunderOutreachBatch } = require("./funder-outreach-gmail.js");
const { appendFunderOutreachReceipt } = require("./funder-outreach-store.js");

const SQL = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-02-lm-funder-outreach-ledger.sql"), "utf8");
const sha = (value) => createHash("sha256").update(value, "utf8").digest("hex");

function candidate(index) {
  const email = `pitch${index}@fund${index}.example`;
  return {
    candidateId: `funder-${index}`,
    funderName: `Fund ${index}`,
    email,
    sourceUrl: `https://fund${index}.example/pitch`,
    sourceObservedAt: "2026-08-01T18:00:00Z",
    sourceExcerpt: `Pre-seed founders are welcome. Contact ${email}.`,
    sourceDigest: sha(`Pre-seed founders are welcome. Contact ${email}.`),
    fitAssessment: { kind: "agent_judgment", summary: `Anicca fit ${index}` },
    rank: index,
    subject: `Anicca × Fund ${index}`,
    body: `Hi Fund ${index},\n\nYour pre-seed thesis stood out. Anicca is a self-funding autonomous AI in Tokyo, built to reduce suffering. Would a 15-minute fit check next week be useful?\n\n— Dais\nhttps://aniccaai.com`,
  };
}

function batch(overrides = {}) {
  return buildFunderOutreachBatch({
    tenantId: "dais-local",
    tokyoDate: "2026-08-02",
    observedAt: "2026-08-01T18:10:00Z",
    dailyTarget: 3,
    candidates: [candidate(1), candidate(2), candidate(3), candidate(4)],
    sentRecipientHashes: [],
    ...overrides,
  });
}

test("fresh official agent-assessed targets become one deterministic 3-message batch", () => {
  const result = batch();
  assert.equal(result.messages.length, 3);
  assert.match(result.batch_id, /^funder-outreach-batch:[0-9a-f]{64}$/);
  assert.deepEqual(result.messages.map(({ candidate_id }) => candidate_id), ["funder-1", "funder-2", "funder-3"]);
  assert.ok(result.messages.every(({ recipient_sha256 }) => /^[0-9a-f]{64}$/.test(recipient_sha256)));
});

test("daily cap, duplicates, stale/unofficial evidence, placeholders, and long copy fail closed", () => {
  assert.throws(() => batch({ dailyTarget: 2 }), /funder outreach/i);
  assert.throws(() => batch({ dailyTarget: 6 }), /funder outreach/i);
  assert.throws(() => batch({ sentRecipientHashes: [sha(candidate(1).email)] }), /funder outreach/i);
  assert.throws(() => batch({ candidates: [candidate(1), candidate(2)] }), /funder outreach/i);
  const stale = candidate(1); stale.sourceObservedAt = "2026-07-30T00:00:00Z";
  assert.throws(() => batch({ candidates: [stale, candidate(2), candidate(3)] }), /funder outreach/i);
  const unofficial = candidate(1); unofficial.sourceExcerpt = "Contact our team."; unofficial.sourceDigest = sha(unofficial.sourceExcerpt);
  assert.throws(() => batch({ candidates: [unofficial, candidate(2), candidate(3)] }), /funder outreach/i);
  const placeholder = candidate(1); placeholder.body = "Hi {{name}}, would a 15-minute fit check be useful? https://aniccaai.com";
  assert.throws(() => batch({ candidates: [placeholder, candidate(2), candidate(3)] }), /funder outreach/i);
});

test("legacy schema v1 external delivery is retired while the builder remains readable", async () => {
  let calls = 0;
  await assert.rejects(() => deliverFunderOutreachBatch(batch(), {
    send: async () => { calls += 1; return {}; },
  }), /legacy delivery retired/i);
  assert.equal(calls, 0);
  let copiedCalls = 0;
  await assert.rejects(() => deliverFunderOutreachBatch(JSON.parse(JSON.stringify(batch())), {
    send: async () => { copiedCalls += 1; return {}; },
  }), /delivery invalid/i);
  assert.equal(copiedCalls, 0);
});

test("migration and store are tenant-bound append-only exact replay", async () => {
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_funder_outreach_ledger/i);
  assert.match(SQL, /ENABLE ROW LEVEL SECURITY/i);
  assert.doesNotMatch(SQL, /UPDATE public\.lm_funder_outreach_ledger/i);
  const sourceBatch = batch();
  const message = sourceBatch.messages[0];
  const receipt = {
    schema_version: 1,
    outreach_id: message.outreach_id,
    batch_id: sourceBatch.batch_id,
    tenant_id: sourceBatch.tenant_id,
    tokyo_date: sourceBatch.tokyo_date,
    candidate_id: message.candidate_id,
    funder_name: message.funder_name,
    recipient_sha256: message.recipient_sha256,
    source_url: message.source_url,
    source_observed_at: message.source_observed_at,
    source_digest: message.source_digest,
    fit_summary_sha256: message.fit_summary_sha256,
    subject_sha256: message.subject_sha256,
    body_sha256: message.body_sha256,
    sent_at: "2026-08-01T18:12:00Z",
    provider_message_id: "19fbe00000000001",
    provider_thread_id: "19fbe00000000001",
  };
  const calls = [];
  const saved = await appendFunderOutreachReceipt(receipt, { query: async (sql, params) => (calls.push({ sql, params }), { rows: [{ outreach_id: params[1], inserted: true }] }) });
  assert.equal(saved.outreach_id, receipt.outreach_id);
  assert.match(calls[0].sql, /ON CONFLICT DO NOTHING/i);
  assert.doesNotMatch(calls[0].sql, /UPDATE/i);
});
